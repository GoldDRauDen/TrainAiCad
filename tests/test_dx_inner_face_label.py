"""521015-04: `dx` marks an INNER-face drawing; mirror (対称) parts are drawn mirrored, no `dx`."""
import sys
from pathlib import Path

import ezdxf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from export_canonical_dxf import export_canonical_job
from export_dxf import CHECKS


def part(code, verts):
    eid = "E_" + code.replace("-", "_") + "_OUTER"
    gid = "G_" + eid
    mid = "M_" + eid
    return {
        "code": code, "material": "SS", "thickness_mm": 1.2, "status": "PASS",
        "checks": {key: "PASS" for key in CHECKS}, "flags": [],
        "entities": [{"entity_id": eid, "type": "LWPOLYLINE", "role": "outer",
                      "closed": True, "vertices": verts}],
        "source_groups": [{"group_id": gid, "family": "OUTER", "status": "PROVED", "source_quantity": 1,
                           "members": [{"member_id": mid, "status": "PROVED"}]}],
        "canonical_members": [{"canonical_member_id": "CM_" + mid, "origin": "SOURCE",
                               "source_member_id": mid, "group_id": gid,
                               "status": "PROVED", "entity_ids": [eid]}],
    }


# asymmetric L plate and its X-mirror about the plate centre (x' = W - x)
W = 60
L_SHAPE = [[0, 0, 0], [W, 0, 0], [W, 10, 0], [20, 10, 0], [20, 40, 0], [0, 40, 0]]
MIRROR = [[W - x, y, 0] for x, y, _ in L_SHAPE][::-1]


def labels(tmp_path, parts):
    job = {"canonical_contract": "TrainAiCad-CANONICAL-V4.34", "job_id": "QA_DX", "parts": parts}
    export_canonical_job(job, tmp_path, require_slip_codes=False)
    doc = ezdxf.readfile(tmp_path / "QA_DX_ALL.dxf")
    return [e.dxf.text for e in doc.modelspace() if e.dxf.layer == "AI_META"]


def test_dx_only_on_inner_face_part_and_not_on_mirrored_partner(tmp_path):
    inner = part("26-000001", L_SHAPE)
    inner["dx_label"] = True          # drawn from the inner face
    sibling = part("26-000002", L_SHAPE)  # outer face
    mirror = part("26-000003", MIRROR)    # 対称 partner: drawn mirrored directly
    mirror["dx_label"] = False
    out = labels(tmp_path, [inner, sibling, mirror])
    assert out.count("dx") == 1
    assert {"26-000001", "26-000002", "26-000003"} <= set(out)


def test_mirrored_partner_needs_no_dx(tmp_path):
    mirror = part("26-000003", MIRROR)
    mirror["dx_label"] = False
    assert "dx" not in labels(tmp_path, [part("26-000002", L_SHAPE), mirror])
