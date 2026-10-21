"""Command line for the app's deterministic tools.

In the default host mode the model asks the host for these through `tool_requests`. In the experimental agent mode
(setting run_mode=agent) the Claude CLI is also allowed to run exactly this script through its shell tool, so the same
tools run inside one turn instead of one provider round per tool. Every sub-command prints one JSON object; failures
print {"error": ...} and exit 1. Nothing here writes outside --stage-dir and --out.

    python agent_cli.py calc "28+4.5*2"
    python agent_cli.py unfold_calc '{"segments":[...],"nobi_mm":7.84}'
    python agent_cli.py build_part '{"sketch":{...}}' --stage-dir DIR
    python agent_cli.py render_preview '{"part_ref":"PART-..."}' --stage-dir DIR --out FILE.png
    python agent_cli.py validate '{"part_ref":"PART-..."}' --stage-dir DIR --engine ENGINE_DIR --job-name JOB
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from LuanAppTools.ai.tools import calculate  # noqa: E402
from LuanAppTools.cad.builders import (BuilderError, build_part, render_part_png, resolve_part, stage_part,  # noqa: E402
                                       summarize_part, unfold_calc)


def _load(text):
    value = json.loads(text)
    if not isinstance(value, dict):
        raise BuilderError("The argument must be a JSON object")
    return value


async def _validate(part, engine, job_name, customer, workdir):
    from LuanAppTools.cad.contract import split_blocker
    from LuanAppTools.cad.repository import PinnedRepository

    root = Path(engine).resolve()
    pin = json.loads((root / "pin.json").read_text(encoding="utf-8"))
    repo = PinnedRepository(root, pin["commit"], pin["hashes"])
    job = {"canonical_contract": repo.contract, "job_id": job_name, **({"customer_code": customer} if customer else {}),
           "parts": [split_blocker(part)[0]]}
    return await repo.validate(job, Path(workdir), asyncio.Event())


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="tool", required=True)
    sub.add_parser("calc").add_argument("expression")
    for name in ("unfold_calc", "build_part", "render_preview", "validate"):
        p = sub.add_parser(name)
        p.add_argument("json")
        p.add_argument("--stage-dir", default=".")
        p.add_argument("--out")
        p.add_argument("--engine")
        p.add_argument("--job-name", default="JOB")
        p.add_argument("--customer", type=int)
    a = ap.parse_args(argv)
    if a.tool == "calc":
        return {"value": calculate(a.expression)}
    args = _load(a.json)
    if a.tool == "unfold_calc":
        return unfold_calc(args)
    if a.tool == "build_part":
        part = build_part(args.get("sketch"))
        return {"part_ref": stage_part(a.stage_dir, part), "summary": summarize_part(part)}
    part = resolve_part(a.stage_dir, {"part_ref": args["part_ref"]} if "part_ref" in args else args.get("part"))
    if not isinstance(part, dict):
        raise BuilderError("Give part_ref or part")
    if a.tool == "render_preview":
        return render_part_png(part, a.out or Path(a.stage_dir) / "preview.png")
    if not a.engine:
        raise BuilderError("validate needs --engine")
    return asyncio.run(_validate(part, a.engine, a.job_name, a.customer, Path(a.stage_dir) / "cli-validation"))


def main(argv=None):
    try:
        result = run(argv)
    except Exception as exc:  # the caller reads one JSON line either way
        print(json.dumps({"error": str(exc)[-4000:]}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
