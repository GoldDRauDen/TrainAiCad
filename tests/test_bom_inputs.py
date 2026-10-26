"""Input files written by Windows PowerShell 5.1 / Notepad carry a UTF-8 BOM: every tool that reads one must accept it."""
import codecs
import json
import subprocess
import sys
from pathlib import Path

import ezdxf
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import build_canonical as bc  # noqa: E402
import dxf_assemble  # noqa: E402
import dxf_digest  # noqa: E402


def _bom(path: Path, text: str) -> Path:
    path.write_bytes(codecs.BOM_UTF8 + text.encode("utf-8"))
    return path


def test_spec_files_with_a_bom_load(tmp_path):
    spec = {"job_id": "J", "parts": [{"code": "26-000930", "material": "SPCC", "t": 2, "page": 1, "envelope": [10, 10],
                                      "outline": [[0, 0], [10, 0], [10, 10], [0, 10]]}]}
    for name, text in (("a.yaml", yaml.safe_dump(spec)), ("a.json", json.dumps(spec))):
        job = bc.build_from_files([_bom(tmp_path / name, text)])
        assert job["parts"][0]["code"] == "26-000930"


def test_resolve_rules_reads_a_census_with_a_bom(tmp_path):
    template = subprocess.run([sys.executable, str(ROOT / "tools/resolve_rules.py"), "--template"],
                              capture_output=True, text=True, encoding="utf-8", check=True).stdout
    census = json.loads(template)
    census.update(part_code="26-000930", source_mode="PDF_ONLY", part_mode="FLAT_NO_BEND", reference_present="NO",
                  multi_code_or_assembly="NO")
    for fam in census["features"].values():
        fam["state"] = "NO"
    path = _bom(tmp_path / "census.json", json.dumps(census, ensure_ascii=False))
    done = subprocess.run([sys.executable, str(ROOT / "tools/resolve_rules.py"), str(path)],
                          capture_output=True, text=True, encoding="utf-8")
    assert done.returncode == 0, done.stderr


def test_dxf_assemble_reads_a_digest_and_plan_with_a_bom(tmp_path):
    doc = ezdxf.new("R2010")
    doc.modelspace().add_circle((5, 5), 2)
    dxf = tmp_path / "c.dxf"
    doc.saveas(dxf)
    dg = dxf_digest.digest(str(dxf))
    plan = {"members": [{"id": "H1", "role": "hole", "pieces": [p["id"] for p in dg["pieces"] if p["type"] == "CIRCLE"]}],
            "excluded": [{"reason": "OTHER", "note": "rest", "pieces": [p["id"] for p in dg["pieces"] if p["type"] != "CIRCLE"]}]}
    a = _bom(tmp_path / "digest.json", json.dumps(dg))
    b = _bom(tmp_path / "plan.json", json.dumps(plan))
    assert dxf_assemble.main([str(a), str(b), "--out", str(tmp_path / "out.json")]) == 0
