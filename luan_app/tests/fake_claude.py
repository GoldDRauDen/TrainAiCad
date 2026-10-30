"""Stand-in for `claude -p ... --output-format stream-json` in tests (no AI, no quota).

Reads the prompt on stdin. Flags: the first `--add-dir` is the run's out dir, the second the job dir.
Env: FAKE_MODE ok|preview|limit|hang|crash|garbage|touch|slow, FAKE_JOB, FAKE_CODES (comma list),
FAKE_DELAY (s between events), FAKE_CHILD_PID_FILE (hang: where to write the child's pid).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def tool(name, inp):
    emit({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}})


def main():
    args = sys.argv[1:]
    add = [args[i + 1] for i, a in enumerate(args) if a == "--add-dir" and i + 1 < len(args)]
    out_dir = Path(add[0]) if add else Path.cwd() / "out"
    job_dir = Path(add[1]) if len(add) > 1 else Path.cwd()
    prompt = sys.stdin.read()
    mode = os.environ.get("FAKE_MODE", "ok")
    job = os.environ.get("FAKE_JOB") or job_dir.name
    codes = [c for c in os.environ.get("FAKE_CODES", "26-000001,26-000002").split(",") if c]
    delay = float(os.environ.get("FAKE_DELAY", "0.05"))

    emit({"type": "system", "subtype": "init", "cwd": os.getcwd(), "model": "fake", "permissionMode": "dontAsk"})
    emit({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "resetsAt": int(time.time()) + 3600,
          "unifiedWindows": {"five_hour": {"utilization": 0.42, "resetsAt": int(time.time()) + 3600}}}})
    if mode == "garbage":
        sys.stdout.write("not json at all\n{\"type\": \"assist\n")
        sys.stdout.flush()
    tool("Bash", {"command": f"python tools/job.py init {job} --source {job_dir}"})
    time.sleep(delay)

    if mode == "crash":
        sys.stderr.write("Traceback: boom\nRuntimeError: fake crash\n")
        sys.exit(3)
    if mode == "limit":
        emit({"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "resetsAt": int(time.time()) + 7200}})
        emit({"type": "result", "subtype": "error", "is_error": True, "result": "Claude AI usage limit reached|1793400000"})
        sys.exit(1)
    if mode == "hang":
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(600)"])
        pid_file = os.environ.get("FAKE_CHILD_PID_FILE")
        if pid_file:
            Path(pid_file).write_text(str(child.pid))
        time.sleep(600)
    if mode == "slow":
        time.sleep(float(os.environ.get("FAKE_SLOW", "3")))

    work = Path.cwd() / ".work" / job
    work.mkdir(parents=True, exist_ok=True)
    status = "PREVIEW" if mode == "preview" else "PASS"
    state = {"job": job, "codes": {c: {"stage": "L3", "status": "PASS", "flags": [], "notes": []} for c in codes}}
    if status == "PREVIEW":
        state["codes"][codes[-1]].update(status="PREVIEW", flags=["Nobi chưa rõ"])
    (work / "job_state.json").write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    tool("Edit", {"file_path": str(work / "spec.yaml")})
    if mode == "touch":
        (Path.cwd() / "rules" / "X.md").write_text("touched by job\n", encoding="utf-8")
    time.sleep(delay)

    is_qa = prompt.startswith("QA ")
    if not is_qa:
        ai_l = job_dir / "AI_L"
        ai_l.mkdir(exist_ok=True)
        (ai_l / f"{job}_ALL.dxf").write_text("0\nEOF\n", encoding="utf-8")
    out_dir.mkdir(parents=True, exist_ok=True)
    verdict = "ISSUES" if status == "PREVIEW" else "OK"
    (out_dir / "result.json").write_text(json.dumps({"verdict": verdict, "summary": f"fake {mode}",
                                                     "codes": {c: state["codes"][c]["status"] for c in codes}},
                                                    ensure_ascii=False), encoding="utf-8")
    (out_dir / "report.md").write_text(f"# Báo cáo {job}\n\nfake {mode}\n", encoding="utf-8")
    items = [{"type": "NEW_LESSON", "code": codes[-1], "card": "rules/BEND.md", "title": "Kiểu gấp lạ",
              "detail": "FACT → ROOT_CAUSE → LESSON", "evidence": "p1"}] if status == "PREVIEW" else []
    (out_dir / "review_items.json").write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    emit({"type": "result", "subtype": "success", "is_error": False, "result": "xong", "num_turns": 3,
          "total_cost_usd": 0.0, "usage": {"input_tokens": 10, "output_tokens": 5}})


if __name__ == "__main__":
    main()
