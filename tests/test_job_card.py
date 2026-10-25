"""JOB_CARD.md stays short, is read first, and only names tools that exist."""
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from resolve_rules import BOOTSTRAP, census_template, resolve_rules  # noqa: E402

CARD = ROOT / "JOB_CARD.md"


def test_card_is_short_and_first_in_l0():
    assert CARD.stat().st_size <= 6_000
    assert BOOTSTRAP[0] == "JOB_CARD.md"
    template = census_template()
    template["source_mode"] = "PDF_ONLY"
    plan = resolve_rules(template)
    assert plan["stage_plans"]["L0_BOOTSTRAP"]["rule_paths"][0] == "JOB_CARD.md"


def test_card_commands_point_at_existing_tools():
    text = CARD.read_text(encoding="utf-8")
    tools = set(re.findall(r"python (tools/[a-z_]+\.py)", text))
    assert {"tools/lookup.py", "tools/pdf_views.py", "tools/pair_consistency.py",
            "tools/resolve_rules.py", "tools/run_job.py"} <= tools
    for rel in tools:
        assert (ROOT / rel).exists(), rel


def test_card_keeps_user_decisions_2026_10_21():
    text = CARD.read_text(encoding="utf-8")
    for phrase in ("UNKNOWN ≠ NO", "Always draw, never stop", "SPLIT_FLANGE_10MM", "Vietnamese", "DUYỆT"):
        assert phrase in text


def test_template_cli_is_fail_safe_unknown():
    out = subprocess.run([sys.executable, str(ROOT / "tools/resolve_rules.py"), "--template"],
                         capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    assert data["features"] and all(v["state"] == "UNKNOWN" for v in data["features"].values())
