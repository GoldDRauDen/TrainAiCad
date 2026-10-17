"""Small host-owned tool vocabulary; no model commands or arbitrary Python."""

import ast
import math
import operator
from LuanAppTools.cad.contract import check_flat_attempt, prepare_part
from LuanAppTools.cad.evidence import compact_entity, crop_page_bounded

TOOL_DESCRIPTION = """Optional tool_requests: [{"name":"crop","arguments":{"page_id":"...","rect":[x0,y0,x1,y1]}}, {"name":"read_rule","arguments":{"path":"an already routed path"}}, {"name":"calculate","arguments":{"expression":"numeric arithmetic"}}, {"name":"data_group","arguments":{"group_id":"a DATA group id from the evidence","offset":0,"limit":200}} (compact DXF entities of one group, at most 300 per call), {"name":"validate","arguments":{"part":{complete canonical part}}}]. Return a tool request OR the final stage object. Host will return tool results and any crop image. No shell, file writes, network or child agents are available."""


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


class HostTools:
    def __init__(self, repo, evidence, allowed_rules, job_name, cancel, notes=()):
        self.repo, self.evidence, self.allowed_rules, self.job_name, self.cancel = (
            repo,
            evidence,
            set(allowed_rules),
            job_name,
            cancel,
        )
        self.notes = list(notes)

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

    async def execute(self, call, *, timeout: float = 1200):
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
            if args["path"] not in self.allowed_rules:
                raise ValueError("Rule is not routed for this stage")
            return {"path": args["path"], "text": self.repo.read(args["path"])}, None
        if name == "validate":
            if not isinstance(args.get("part"), dict):
                raise ValueError("validate needs the complete part object")
            part = prepare_part(args["part"], self.notes)
            check_flat_attempt(part, self.notes)
            job = {
                "canonical_contract": self.repo.contract,
                "job_id": self.job_name,
                "parts": [part],
            }
            return (
                await self.repo.validate(
                    job,
                    self.evidence.workspace / "tool-validation",
                    self.cancel,
                    timeout=timeout,
                ),
                None,
            )
        raise ValueError("Unapproved host tool")
