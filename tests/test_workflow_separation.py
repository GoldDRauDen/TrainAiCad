"""Production CAD and MCP research workflows must stay separated."""
from pathlib import Path
import yaml

ROOT=Path(__file__).resolve().parents[1]
CAD_WF=ROOT/".github/workflows/dxf-export-tests.yml"
MCP_WF=ROOT/".github/workflows/mcp-research.yml"

def test_cad_workflow_excludes_mcp():
    text=CAD_WF.read_text(encoding="utf-8")
    data=yaml.safe_load(text)
    assert "services/trainaicad-mcp/**" not in text
    assert "MCP Inspector" not in text
    assert "mcp" not in data.get("jobs", {})
    assert set(data.get("jobs", {})) == {"serializer"}

def test_no_research_workflow_without_its_source_tree():
    source = ROOT / "services/trainaicad-mcp"
    if not source.is_dir():
        assert not MCP_WF.exists(), "Do not dispatch a workflow whose working directory is absent"
    else:
        data = yaml.safe_load(MCP_WF.read_text(encoding="utf-8"))
        assert set(data["jobs"]) == {"mcp-research"}
        assert "serializer" not in data["jobs"]

def test_entrypoint_declares_repo_direct_default():
    entry=((ROOT/"AI_ENTRYPOINT.md").read_text(encoding="utf-8") + (ROOT/"docs/RELEASE_WIRING_INDEX.md").read_text(encoding="utf-8"))
    assert "MCP is research-only and is NOT part of the production CAD pipeline" in entry
    assert "Default CAD behavior remains repo-direct" in entry
    assert "Do not route through MCP" in entry
