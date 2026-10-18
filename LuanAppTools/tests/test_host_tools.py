"""The model is pointed at exporter/guard source lines (`gates`); the host tool must let it read them.

Recorded in run 18798d71 (job 520925-07): after four identical validation errors the model tried the CLI's
built-in Read on tools/canonical_contract.py lines 360-430 (the gate named in the advice). The CLI refused
(--restricted keeps file tools inside the workspace) and the model was left to guess again.
"""
import asyncio

import pytest

from LuanAppTools.ai.tools import TOOL_DESCRIPTION, HostTools
from LuanAppTools.cad.repository import CadError

BODY = "\n".join(f"line {number}" for number in range(1, 501))


class Repo:
    hashes = {"tools/canonical_contract.py": "x", "skills/lispcad/rule.md": "y", "tools/DXF_INPUT_SCHEMA.md": "z"}

    def read(self, name):
        if name not in self.hashes:
            raise CadError("Unapproved rule/tool path: " + str(name), "routing_gap")
        return BODY


def read_rule(**arguments):
    tools = HostTools(Repo(), None, ["skills/lispcad/rule.md"], "JOB", asyncio.Event())
    answer, image = asyncio.run(tools.execute({"name": "read_rule", "arguments": arguments}))
    assert image is None
    return answer


def test_a_tool_source_range_comes_back_with_line_numbers():
    answer = read_rule(path="tools/canonical_contract.py", start=360, limit=3)
    assert answer["path"] == "tools/canonical_contract.py"
    assert (answer["start"], answer["end"]) == (360, 362)
    assert answer["text"] == "360: line 360\n361: line 361\n362: line 362"


def test_a_tool_source_needs_a_bounded_range():
    for arguments in ({}, {"start": 1}, {"limit": 10}, {"start": 0, "limit": 5}, {"start": 1, "limit": 121},
                      {"start": "1", "limit": 5}, {"start": 1, "limit": True}):
        with pytest.raises(ValueError, match="start and limit"):
            read_rule(path="tools/canonical_contract.py", **arguments)


@pytest.mark.parametrize("path", [
    "tools/../AI_ENTRYPOINT.md", "tools/sub/x.py", "tools/DXF_INPUT_SCHEMA.md", "tools/missing.py",
    "/etc/passwd", "skills/lispcad/other.md", "tools\\canonical_contract.py"])
def test_only_pinned_tool_sources_and_routed_rules_are_readable(path):
    with pytest.raises((ValueError, CadError)):
        read_rule(path=path, start=1, limit=5)


def test_a_routed_rule_is_still_returned_whole_or_by_range():
    assert read_rule(path="skills/lispcad/rule.md")["text"] == BODY
    ranged = read_rule(path="skills/lispcad/rule.md", start=2, limit=2)
    assert ranged["text"] == "2: line 2\n3: line 3"


def test_end_of_file_clips_the_range():
    answer = read_rule(path="tools/canonical_contract.py", start=499, limit=50)
    assert answer["end"] == 500 and answer["text"].endswith("500: line 500")
    with pytest.raises(ValueError, match="past the end"):
        read_rule(path="tools/canonical_contract.py", start=501, limit=5)


def test_tool_description_tells_the_model_how_to_read_a_gate():
    assert "tools/" in TOOL_DESCRIPTION and "start" in TOOL_DESCRIPTION and "limit" in TOOL_DESCRIPTION
