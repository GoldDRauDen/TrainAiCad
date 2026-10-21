"""tools/pair_consistency.py catches a pair whose slot length differs
(lesson 520925-07: 056159 slot 10 mm short, 056160 correct)."""
import copy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from pair_consistency import check_pair  # noqa: E402


def slot(cx, cy, length, w, eid):
    h, r = (length - w) / 2, w / 2
    return {"type": "LWPOLYLINE", "role": "slot", "closed": True, "entity_id": eid,
            "vertices": [[cx - h, cy - r, 0], [cx + h, cy - r, 1], [cx + h, cy + r, 0], [cx - h, cy + r, 1]]}


def part(code, slot_x=20.0, slot_len=30.0, mirror=False):
    W, H = 110.0, 130.22
    hx = 15.0 if not mirror else W - 15.0
    scx = slot_x + slot_len / 2
    scx = scx if not mirror else W - scx
    return {"code": code, "entities": [
        {"type": "LWPOLYLINE", "role": "outer", "closed": True, "entity_id": f"{code}_O",
         "vertices": [[0, 0, 0], [W, 0, 0], [W, H, 0], [0, H, 0]]},
        {"type": "CIRCLE", "center": [hx, 100.0], "radius": 3.3, "entity_id": f"{code}_H1"},
        slot(scx, 40.0, slot_len, 8.0, f"{code}_S1"),
        {"type": "LINE", "linetype": "DASHED", "role": "bend", "start": [0, 120], "end": [W, 120],
         "entity_id": f"{code}_B1"},
    ]}


def test_identical_mirror_pair_is_ok():
    job = {"parts": [part("26-056159"), part("26-056160", mirror=True)]}
    res = check_pair(job, "26-056159", "26-056160")
    assert res["status"] == "OK" and res["mirror"] == "x"


def test_short_slot_is_reported_with_location():
    job = {"parts": [part("26-056159", slot_len=20.0), part("26-056160", mirror=True)]}
    res = check_pair(job, "26-056159", "26-056160")
    assert res["status"] == "MISMATCH"
    assert any("CUTOUT" in d and "26-056159_S1" in d for d in res["differences"])
    assert "đọc lại bản vẽ" in res["flag_vi"]


def test_bbox_difference_reported():
    b = part("B")
    b["entities"][0]["vertices"][1][0] = 120.0
    b["entities"][0]["vertices"][2][0] = 120.0
    res = check_pair({"parts": [part("A"), b]}, "A", "B", mirror="none")
    assert any(d.startswith("bbox") for d in res["differences"])


def test_translation_does_not_matter():
    b = copy.deepcopy(part("B"))
    for e in b["entities"]:
        if e["type"] == "LWPOLYLINE":
            for v in e["vertices"]:
                v[0] += 500; v[1] -= 30
        elif e["type"] == "CIRCLE":
            e["center"] = [e["center"][0] + 500, e["center"][1] - 30]
        elif e["type"] == "LINE":
            e["start"] = [e["start"][0] + 500, e["start"][1] - 30]
            e["end"] = [e["end"][0] + 500, e["end"][1] - 30]
    assert check_pair({"parts": [part("A"), b]}, "A", "B", mirror="none")["status"] == "OK"
