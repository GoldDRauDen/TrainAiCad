"""Small host-owned tool vocabulary; no model commands or arbitrary Python."""

import ast
import json
import math
import operator
import re
import sys
from pathlib import Path
from LuanAppTools.cad.builders import (BuilderError, build_part, render_part_png, resolve_part, stage_part,
                                       summarize_part, unfold_calc)
from LuanAppTools.cad.contract import check_flat_attempt, prepare_part, split_blocker
from LuanAppTools.cad.evidence import compact_entity, crop_page_bounded
from LuanAppTools.cad.repository import run_tool

# A validation error's `gates` name the exporter/guard source line that rejected the part. The model's own
# file tools cannot reach the pinned repository (the CLI runs --restricted inside the run workspace), so the
# host serves those lines: only pinned tools/NAME.py files, always as a bounded numbered range.
TOOL_SOURCE = re.compile(r"tools/[A-Za-z0-9_]+\.py")
MAX_SOURCE_LINES = 120

TOOL_DESCRIPTION = """Optional tool_requests: [{"name":"crop","arguments":{"page_id":"...","rect":[x0,y0,x1,y1]}}, {"name":"read_rule","arguments":{"path":"an already routed path"}} (optionally with "start" and "limit" for a line range), {"name":"read_rule","arguments":{"path":"tools/NAME.py as named in a validation error's gates","start":first line,"limit":lines to read, at most 120}} (the checking code behind an exporter error; start and limit are required for tools/NAME.py), {"name":"calculate","arguments":{"expression":"numeric arithmetic"}}, {"name":"data_group","arguments":{"group_id":"a DATA group id from the evidence","offset":0,"limit":200}} (compact DXF entities of one group, at most 300 per call), {"name":"validate","arguments":{"part":{complete canonical part}}} (or {"part_ref":"PART-..."} for a part build_part staged), {"name":"unfold_calc","arguments":{"thickness_mm":t,"segments":[{"id_mm":28,"t_count":1} or {"od_mm":32.5}, ... in order along the unfold axis],"nobi_mm":N (or "nobi_each_mm":[one per bend]),"expect_flat_mm":optional,"place":[{"name":"x","from":"start|end|center","offset":mm}]}} (OD per segment, flat length = sum(OD) - sum(Nobi), each bend's line pair and ledger numbers; t_count 0-2 is YOUR reading of how many sheet thicknesses the printed dimension lacks), {"name":"build_part","arguments":{"sketch":{...},"validate":true}} (the host writes the bookkeeping from your decisions and runs validate in the same call; sketch: code, material, thickness_mm, status, checks with all eight names, flags, outer {"rect":[L,W],"corner_r":r} or {"vertices":[[x,y,bulge]]}, segments + nobi_mm or nobi_each_mm + bend_axis + bend_span + faces + strip_width_mm + bends [{faces:[A,B],shared_edges:[..],edge_orientation,attachment_evidence,signed_angle_deg,rotation_axis,evidence}], features [{id,group,family,center,radius,evidence,witness:{"X":[{value_mm,to_type,evidence,endpoint_verified}],"Y":[...]}}] or kind:"entities" with raw entities, extra_groups [{group_id,family,evidence,members:[{id,entities}]}], part_fields {any other part keys}; you state status, checks and every endpoint_verified yourself: the host never decides PASS, a Nobi or an endpoint), {"name":"render_preview","arguments":{"part_ref":"PART-..." or "part":{...}}} (a picture of the part's entities, to compare with the source page). Send every independent request of one step in ONE tool_requests array (up to 8) and do plain arithmetic yourself: each extra round re-reads the whole conversation. Return a tool request OR the final stage object. Host will return tool results and any crop image. No shell, file writes, network or child agents are available."""


GENERATOR_DESCRIPTION = (
    ' {"name":"run_generator","arguments":{"name":"boxmet_job","arguments":{"code":"26-...","L":..,"W":..,"H":[H1,H2,H3,H4],'
    '"T":..,"material":"SS","N":..,"holes":[[x,y,dia,"evidence"]],"drawn_corners":"SHARP"}}} stages the repository\'s '
    'own BOXMET part (returns part_ref); "boxmet_flat" returns flat geometry only. You still read every number.'
)
REF_DESCRIPTION = (
    ' Your final answer may give "part" as {"part_ref":"PART-..."} for a part you built or generated and validated '
    'in this attempt; the host substitutes the staged part.'
)

GENERATORS = {"boxmet_flat", "boxmet_job"}


def generator_argv(name, params, output):
    def number(key):
        value = params.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{key} must be a number")
        return str(value)

    heights = params.get("H")
    if not (isinstance(heights, list) and len(heights) == 4 and all(isinstance(h, (int, float)) for h in heights)):
        raise ValueError("H must be four numbers [H1_BOTTOM, H2_RIGHT, H3_TOP, H4_LEFT]")
    material = params.get("material")
    if not isinstance(material, str) or not re.fullmatch(r"[A-Za-z0-9._-]{1,40}", material):
        raise ValueError("material must be a short alphanumeric grade")
    argv = ["--L", number("L"), "--W", number("W"), "--H", *map(str, heights), "--T", number("T"),
            "--material", material, "--N", number("N")]
    if name == "boxmet_flat":
        return argv + ["--json", str(output)]
    code = params.get("code")
    if not isinstance(code, str) or not re.fullmatch(r"[A-Za-z0-9-]{3,40}", code):
        raise ValueError("code must be the slip work number")
    argv = ["--code", code, *argv, "--out", str(output)]
    for hole in params.get("holes") or []:
        if not (isinstance(hole, list) and len(hole) == 4 and all(isinstance(v, (int, float)) for v in hole[:3])
                and isinstance(hole[3], str) and hole[3]):
            raise ValueError("each hole is [x, y, diameter, evidence]")
        argv += ["--hole", *map(str, hole)]
    corners = params.get("drawn_corners", "SHARP")
    if corners not in {"SHARP", "ROUNDED", "CHAMFERED", "UNKNOWN"}:
        raise ValueError("drawn_corners must be SHARP, ROUNDED, CHAMFERED or UNKNOWN")
    return argv + ["--drawn-corners", corners]


def calculate(expression):
    if not isinstance(expression, str) or len(expression) > 1000:
        raise ValueError("Arithmetic too large")
    tree = ast.parse(expression, mode="eval")
    if len(list(ast.walk(tree))) > 100:
        raise ValueError("Arithmetic too large")
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Mod: operator.mod,
    }

    def evaluate(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(
            node.op, (ast.UAdd, ast.USub)
        ):
            value = evaluate(node.operand) * (
                1 if isinstance(node.op, ast.UAdd) else -1
            )
        elif isinstance(node, ast.BinOp) and type(node.op) in ops:
            value = ops[type(node.op)](evaluate(node.left), evaluate(node.right))
        else:
            raise ValueError("Only bounded numeric arithmetic is available")
        if not math.isfinite(value) or abs(value) > 1e100:
            raise ValueError("Arithmetic out of bounds")
        return value

    return evaluate(tree.body)


def line_range(text, start, limit):
    """Numbered lines start..start+limit-1 of `text` (clipped at the end of the file)."""
    if type(start) is not int or type(limit) is not int or start < 1 or not 1 <= limit <= MAX_SOURCE_LINES:
        raise ValueError(f"start and limit are required: start >= 1 and limit 1-{MAX_SOURCE_LINES}")
    lines = text.splitlines()
    if start > len(lines):
        raise ValueError(f"start is past the end of the file ({len(lines)} lines)")
    end = min(len(lines), start + limit - 1)
    return {"start": start, "end": end, "text": "\n".join(f"{n}: {lines[n - 1]}" for n in range(start, end + 1))}


class HostTools:
    def __init__(self, repo, evidence, allowed_rules, job_name, cancel, notes=(), customer_code=None, census=None,
                 closure=None, stage_dir=None, generators=False):
        self.repo, self.evidence, self.allowed_rules, self.job_name, self.cancel = (
            repo,
            evidence,
            set(allowed_rules),
            job_name,
            cancel,
        )
        self.notes = list(notes)
        self.customer_code, self.census = customer_code, census
        self.closure = closure  # cad.closure.ClosureContext: gates VIEWS_ONLY when printed flat arithmetic closes
        # Parts built by build_part / generators live on disk so a resumed run still finds them.
        self._stage_dir = Path(stage_dir) if stage_dir else None
        self.generators = generators

    @property
    def stage_dir(self):
        return self._stage_dir or Path(self.evidence.workspace) / "staged"

    def remember(self, part):
        """The newest part handed to a validating tool: the draft a failed code can still be exported from."""
        try:
            self.stage_dir.mkdir(parents=True, exist_ok=True)
            (self.stage_dir / "last.json").write_text(json.dumps(part), encoding="utf-8")
        except (OSError, TypeError):
            pass

    async def _validate(self, part, history, timeout):
        self.remember(part)
        if self.closure is not None:
            self.closure.admit(part, history)
        part = prepare_part(split_blocker(part)[0], self.notes, self.census)
        check_flat_attempt(part, self.notes)
        job = {
            "canonical_contract": self.repo.contract,
            "job_id": self.job_name,
            **({"customer_code": self.customer_code} if self.customer_code else {}),
            "parts": [part],
        }
        return await self.repo.validate(job, self.evidence.workspace / "tool-validation", self.cancel, timeout=timeout)

    async def _generate(self, args, timeout):
        if not self.generators:
            raise ValueError("Repository generators are not enabled")
        name = args.get("name")
        if name not in GENERATORS:
            raise ValueError("Unknown generator")
        script = self.repo.root / "tools" / f"{name}.py"
        if not script.is_file():
            raise ValueError(f"This pinned repository snapshot has no tools/{name}.py")
        output = self.evidence.workspace / "generated" / f"{name}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.unlink(missing_ok=True)
        params = args.get("arguments") or {}
        await run_tool([sys.executable, "-X", "utf8", script, *generator_argv(name, params, output)],
                       self.repo.root, self.cancel, timeout=timeout)
        data = json.loads(output.read_text(encoding="utf-8"))
        if name == "boxmet_flat":
            text = json.dumps(data)
            return {"generator": name, "result": data if len(text) <= 20000 else {"truncated": True}}
        parts = (data.get("job") or data).get("parts") or []
        if len(parts) != 1:
            raise ValueError("The generator did not return exactly one part")
        ref = stage_part(self.stage_dir, parts[0])
        return {"generator": name, "part_ref": ref, "summary": summarize_part(parts[0])}

    def data_group(self, args):
        group_id = args.get("group_id")
        offset, limit = args.get("offset", 0), args.get("limit", 200)
        if type(offset) is not int or type(limit) is not int or offset < 0 or not 1 <= limit <= 300:
            raise ValueError("offset must be >= 0 and limit must be 1-300")
        for drawing in self.evidence.dxf:
            for group in drawing.get("groups", []):
                if group["id"] == group_id:
                    entities = {e["id"]: e for e in drawing["entities"]}
                    ids = group["entity_ids"]
                    return {
                        "group_id": group_id,
                        "total": len(ids),
                        "offset": offset,
                        "entities": [compact_entity(entities[i.split("#", 1)[1]]) for i in ids[offset : offset + limit]],
                    }
        raise ValueError("Unknown DATA group")

    async def execute(self, call, *, timeout: float = 1200, history=()):
        name = call["name"]
        args = call["arguments"]
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be an object")
        if name == "crop":
            path = await crop_page_bounded(
                self.evidence,
                args["page_id"],
                args["rect"],
                self.cancel,
                timeout=timeout,
            )
            return {
                "image": str(path),
                "page_id": args["page_id"],
                "rect": args["rect"],
            }, path
        if name == "data_group":
            return self.data_group(args), None
        if name == "calculate":
            return {"value": calculate(args["expression"])}, None
        if name == "read_rule":
            path = args.get("path")
            routed = path in self.allowed_rules
            if not routed and not (isinstance(path, str) and TOOL_SOURCE.fullmatch(path)):
                raise ValueError("Rule is not routed for this stage")
            text = self.repo.read(path)
            if routed and args.get("start") is None and args.get("limit") is None:
                return {"path": path, "text": text}, None
            return {"path": path, **line_range(text, args.get("start"), args.get("limit"))}, None
        if name == "validate":
            if "part_ref" in args:
                part = resolve_part(self.stage_dir, {"part_ref": args["part_ref"]})
            elif isinstance(args.get("part"), dict):
                part = resolve_part(self.stage_dir, args["part"])
            else:
                raise ValueError("validate needs the complete part object or a part_ref")
            return await self._validate(part, history, timeout), None
        if name == "unfold_calc":
            try:
                return unfold_calc(args), None
            except BuilderError as exc:
                raise ValueError(str(exc)) from exc
        if name == "build_part":
            try:
                part = build_part(args.get("sketch"))
            except BuilderError as exc:
                raise ValueError(str(exc)) from exc
            ref = stage_part(self.stage_dir, part)
            answer = {"part_ref": ref, "summary": summarize_part(part)}
            if args.get("validate", True):
                answer["validation"] = await self._validate(part, history, timeout)
            return answer, None
        if name == "render_preview":
            try:
                part = resolve_part(self.stage_dir, {"part_ref": args["part_ref"]} if "part_ref" in args
                                    else args.get("part"))
                if not isinstance(part, dict):
                    raise BuilderError("render_preview needs part_ref or a part object")
                label = args.get("part_ref") or "inline"
                result = render_part_png(part, self.evidence.workspace / "previews" / f"{label}.png")
            except BuilderError as exc:
                raise ValueError(str(exc)) from exc
            return result, Path(result["image"])
        if name == "run_generator":
            return await self._generate(args, timeout), None
        raise ValueError("Unapproved host tool")
