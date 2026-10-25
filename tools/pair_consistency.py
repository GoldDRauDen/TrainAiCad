#!/usr/bin/env python3
"""Cross-check two codes that the source says are a pair (対称 / same family).

Lesson 520925-07 (2026-10-18): 056159 got a slot 10 mm short while its
pair 056160 was right; nothing compared the two. This tool compares the
canonical geometry of two parts after normalizing each to its own bbox origin
and, optionally, mirroring one of them.

    python tools/pair_consistency.py job.json 26-056159 26-056160 --mirror auto

``--mirror``: ``none`` (same orientation), ``x`` (x' = W - x), ``y``
(y' = H - y), ``xy`` (180° rotation) or ``auto`` (best of the four).

It reports differences only. A difference is not proof that either code is
wrong: re-read both sources at the reported feature and correct the wrong one,
or record why the pair legitimately differs. Exit code 1 on any mismatch.
"""
from __future__ import annotations
import sys

import argparse
import json
import math
from pathlib import Path

from geom import bulge_points

TOL = 0.01  # mm


def _bulge_points(p0, p1, bulge, n=24):
    if abs(bulge) < 1e-12 or p0 == p1:
        return [p0]
    return [p0] + bulge_points(p0, p1, bulge, n)


def _poly_points(entity):
    v = entity["vertices"]
    pts = []
    count = len(v) if entity.get("closed") else len(v) - 1
    for i in range(count):
        a, b = v[i], v[(i + 1) % len(v)]
        bulge = a[2] if len(a) > 2 else 0.0
        pts.extend(_bulge_points((a[0], a[1]), (b[0], b[1]), bulge))
    if not entity.get("closed"):
        pts.append((v[-1][0], v[-1][1]))
    return pts


def _bbox(points):
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def features(part: dict) -> dict:
    """Family -> list of comparable records, in part-local coordinates."""
    ents = [e for e in part.get("entities", []) if e.get("type") != "TEXT"]
    outers = [e for e in ents if e.get("type") == "LWPOLYLINE" and e.get("role") == "outer"]
    pts = [p for e in outers for p in _poly_points(e)] or [
        p for e in ents if e.get("type") == "LWPOLYLINE" for p in _poly_points(e)]
    if not pts:
        raise ValueError(f"{part.get('code')}: no outline")
    x0, y0, x1, y1 = _bbox(pts)
    out = {"bbox": (x1 - x0, y1 - y0), "origin": (x0, y0), "HOLE": [], "POINT": [], "CUTOUT": [],
           "BEND": [], "KEGAKI": []}
    for e in ents:
        t = e.get("type")
        if t == "CIRCLE":
            out["HOLE"].append({"c": tuple(e["center"]), "size": (2 * e["radius"],), "id": e.get("entity_id")})
        elif t == "POINT":
            out["POINT"].append({"c": tuple(e["point"]), "size": (), "id": e.get("entity_id")})
        elif t == "LWPOLYLINE" and e.get("role") != "outer" and e.get("closed"):
            bx0, by0, bx1, by1 = _bbox(_poly_points(e))
            out["CUTOUT"].append({"c": ((bx0 + bx1) / 2, (by0 + by1) / 2),
                                  "size": tuple(sorted((bx1 - bx0, by1 - by0))), "id": e.get("entity_id")})
        elif t == "LINE":
            fam = ("KEGAKI" if e.get("color") == 1 or e.get("role") in ("kegaki", "mark_line")
                   else "BEND" if e.get("linetype") == "DASHED" or "bend" in str(e.get("role", "")) else None)
            if fam:
                (sx, sy), (ex, ey) = e["start"], e["end"]
                out[fam].append({"c": ((sx + ex) / 2, (sy + ey) / 2),
                                 "size": (round(math.hypot(ex - sx, ey - sy), 3),), "id": e.get("entity_id")})
    for fam in ("HOLE", "POINT", "CUTOUT", "BEND", "KEGAKI"):
        for rec in out[fam]:
            rec["c"] = (rec["c"][0] - x0, rec["c"][1] - y0)
    return out


def _transform(c, mode, w, h):
    x, y = c
    if mode in ("x", "xy"):
        x = w - x
    if mode in ("y", "xy"):
        y = h - y
    return x, y


def compare(fa: dict, fb: dict, mode: str, tol: float = TOL) -> list[str]:
    diffs = []
    (wa, ha), (wb, hb) = fa["bbox"], fb["bbox"]
    if abs(wa - wb) > tol or abs(ha - hb) > tol:
        diffs.append(f"bbox A {wa:.3f}x{ha:.3f} vs B {wb:.3f}x{hb:.3f}")
    for fam in ("HOLE", "POINT", "CUTOUT", "BEND", "KEGAKI"):
        a, b = fa[fam], list(fb[fam])
        if len(a) != len(b):
            diffs.append(f"{fam} count A {len(a)} vs B {len(b)}")
        for rec in a:
            target = _transform(rec["c"], mode, wb, hb)
            best = None
            for cand in b:
                if len(cand["size"]) == len(rec["size"]) and all(
                        abs(s - t) <= tol for s, t in zip(cand["size"], rec["size"])):
                    dist = math.hypot(cand["c"][0] - target[0], cand["c"][1] - target[1])
                    if best is None or dist < best[0]:
                        best = (dist, cand)
            if best is not None and best[0] <= tol:
                b.remove(best[1])
                continue
            near = min(b, key=lambda c: math.hypot(c["c"][0] - target[0], c["c"][1] - target[1]), default=None)
            hint = ""
            if near is not None:
                hint = (f"; nearest B {near['id']} at ({near['c'][0]:.2f},{near['c'][1]:.2f}) "
                        f"size {tuple(round(s, 3) for s in near['size'])}")
            diffs.append(f"{fam} A {rec['id']} at ({rec['c'][0]:.2f},{rec['c'][1]:.2f}) size "
                         f"{tuple(round(s, 3) for s in rec['size'])} has no match in B{hint}")
        for cand in b:
            diffs.append(f"{fam} B {cand['id']} at ({cand['c'][0]:.2f},{cand['c'][1]:.2f}) unmatched")
    return diffs


def check_pair(job: dict, code_a: str, code_b: str, mirror: str = "auto", tol: float = TOL) -> dict:
    parts = {p["code"]: p for p in job["parts"]}
    for code in (code_a, code_b):
        if code not in parts:
            raise KeyError(f"code {code} not in job")
    fa, fb = features(parts[code_a]), features(parts[code_b])
    modes = ["none", "x", "y", "xy"] if mirror == "auto" else [mirror]
    results = {m: compare(fa, fb, m, tol) for m in modes}
    best = min(modes, key=lambda m: len(results[m]))
    diffs = results[best]
    return {"status": "OK" if not diffs else "MISMATCH", "pair": [code_a, code_b], "mirror": best,
            "differences": diffs,
            "flag_vi": None if not diffs else
            f"Cặp {code_a}/{code_b} lệch nhau {len(diffs)} điểm: đọc lại bản vẽ tại các vị trí này"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job")
    ap.add_argument("code_a")
    ap.add_argument("code_b")
    ap.add_argument("--mirror", default="auto", choices=["auto", "none", "x", "y", "xy"])
    ap.add_argument("--tol", type=float, default=TOL)
    a = ap.parse_args(argv)
    job = json.loads(Path(a.job).read_text(encoding="utf-8"))
    res = check_pair(job, a.code_a, a.code_b, a.mirror, a.tol)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0 if res["status"] == "OK" else 1


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
