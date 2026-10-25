"""Claude Code project config: the compaction hook and the two entry skills point at real things."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_session_start_hook_reloads_the_job_state():
    settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    assert settings["env"]["PYTHONUTF8"] == "1"
    (entry,) = settings["hooks"]["SessionStart"]
    assert set(entry["matcher"].split("|")) == {"compact", "resume"}
    cmd = entry["hooks"][0]["command"]
    assert "tools/job.py" in cmd and cmd.endswith(" hook")


def test_skills_have_frontmatter_and_real_paths():
    for skill in ("cad-e2e", "cad-qa"):
        text = (ROOT / ".claude/skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert text.startswith(f"---\nname: {skill}\ndescription: ")
        for path in re.findall(r"`((?:rules|tools)/[\w./-]+|JOB_CARD\.md)", text):
            assert (ROOT / path).exists(), (skill, path)
