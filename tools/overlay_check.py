#!/usr/bin/env python3
"""Overlay one code's canonical geometry on a drawing crop to catch misread shapes.

Give >=2 anchors "x,y=px,py" (part-local canonical mm = pixel in the crop). A similarity
transform (scale + rotation + shift, scan skew included) is fitted by least squares; the
outline, holes and slots are drawn in red on the crop. With >=3 anchors the residual of
each anchor is reported in mm: a large residual means the geometry does not match the drawing
(e.g. a reversed slope). Read the PNG yourself; the tool proves nothing without that look.

    python tools/overlay_check.py job.json 26-062961 --image crop.png \
        --anchor 1720,70=473,405 --anchor 1440,25=1610,243 --anchor 1720,5=478,140 --out ov.png
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from geometry_containment import _loop  # noqa: E402


def parse_anchor(text):
    try:
        left, right = text.split("=")
        x, y = (float(v) for v in left.split(","))
        px, py = (float(v) for v in right.split(","))
    except ValueError as exc:
        raise SystemExit(f"bad --anchor {text!r}; use x,y=px,py") from exc
    return complex(x, y), complex(px, -py)  # pixel y grows downward


def fit(anchors):
    if len(anchors) < 2:
        raise SystemExit("need at least 2 anchors")
    zs = [z for z, _ in anchors]
    ws = [w for _, w in anchors]
    zm, wm = sum(zs) / len(zs), sum(ws) / len(ws)
    den = sum(abs(z - zm) ** 2 for z in zs)
    if den <= 1e-12:
        raise SystemExit("anchors must be distinct points")
    a = sum((w - wm) * (z - zm).conjugate() for z, w in anchors) / den
    b = wm - a * zm
    residual = [abs(a * z + b - w) / abs(a) for z, w in anchors]
    return a, b, residual


def part_paths(part):
    paths = []
    for e in part["entities"]:
        if e["type"] == "LWPOLYLINE" and e.get("closed"):
            paths.append(_loop(e["vertices"], tolerance=0.05))
        elif e["type"] == "CIRCLE":
            cx, cy = e["center"]
            r = e["radius"]
            paths.append([(cx + r * math.cos(k * math.pi / 32), cy + r * math.sin(k * math.pi / 32)) for k in range(64)])
    return paths


def overlay(job, code, image, anchors, out, width=3):
    """Draw with PyMuPDF (already a repo requirement): 1 pt = 1 px on a page the size of the crop."""
    from pdf_views import fitz
    if fitz is None:
        raise SystemExit("PyMuPDF missing: pip install pymupdf")
    part = next((p for p in job["parts"] if p["code"] == code), None)
    if part is None:
        raise SystemExit(f"code {code} not in job")
    a, b, residual = fit(anchors)
    pix = fitz.Pixmap(str(image))
    doc = fitz.open()
    page = doc.new_page(width=pix.width, height=pix.height)
    page.insert_image(page.rect, filename=str(image))
    shape = page.new_shape()

    def px(p):
        w = a * complex(*p) + b
        return fitz.Point(w.real, -w.imag)
    for path in part_paths(part):
        pts = [px(p) for p in path]
        shape.draw_polyline(pts + pts[:1])
    shape.finish(color=(0.9, 0, 0), width=width, closePath=False)
    for _z, w in anchors:
        shape.draw_circle(fitz.Point(w.real, -w.imag), 8)
    shape.finish(color=(0, 0.47, 1), width=3)
    shape.commit()
    page.get_pixmap(dpi=72).save(str(out))
    return {"code": code, "out": str(out), "scale_px_per_mm": round(abs(a), 4),
            "rotation_deg": round(math.degrees(math.atan2(a.imag, a.real)), 3),
            "residual_mm": [round(r, 3) for r in residual], "max_residual_mm": round(max(residual), 3)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job", type=Path)
    ap.add_argument("code")
    ap.add_argument("--image", required=True, type=Path)
    ap.add_argument("--anchor", action="append", default=[], help="x,y=px,py (canonical mm = crop pixel)")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--max-residual-mm", type=float, default=1.0)
    a = ap.parse_args(argv)
    job = json.loads(a.job.read_text(encoding="utf-8"))
    res = overlay(job, a.code, a.image, [parse_anchor(t) for t in a.anchor], a.out)
    res["status"] = "OK" if len(a.anchor) < 3 or res["max_residual_mm"] <= a.max_residual_mm else "MISMATCH"
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["status"] == "OK" else 1


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        _stream.reconfigure(encoding="utf-8")  # Vietnamese FLAG text on a Windows console
    raise SystemExit(main())
