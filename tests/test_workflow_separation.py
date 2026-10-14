"""Production CAD and MCP research workflows must stay separated."""
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
CAD_WF=ROOT/".github/workflows/dxf-export-tests.yml"

def test_cad_workflow_excludes_mcp():
    text=CAD_WF.read_text(encoding="utf-8")
    data=yaml.safe_load(text)
    assert "services/trainaicad-mcp/**" not in text
    assert "MCP Inspector" not in text
    assert "mcp" not in data.get("jobs", {})
    assert set(data.get("jobs", {})) == {"serializer"}

def test_entrypoint_declares_repo_direct_default():
    entry=((ROOT/"AI_ENTRYPOINT.md").read_text(encoding="utf-8") + (ROOT/"docs/RELEASE_WIRING_INDEX.md").read_text(encoding="utf-8"))
    assert "The experimental MCP service has been removed from this repository" in entry
    assert "Default CAD behavior is repo-direct" in entry
    assert "Do not route CAD production through any MCP service" in entry
