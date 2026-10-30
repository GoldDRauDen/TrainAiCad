#!/usr/bin/env python3
"""Measure a feature on a scanned crop (the estimate behind a Magenta FLAG, never a proved value).

    python tools/scan_measure.py circle crop.png --near 870,1130 --r 40 90 --dpi 600 [--scale-px 1163 --scale-mm 100]
    python tools/scan_measure.py scale --px 1163 --mm 100 --dpi 600

``circle``: least-squares circle through the dark pixels in a ring around --near (x,y px) between the two radii. Millimetres:
a drawing printed at another scale than 1:1 needs --scale-px/--scale-mm (a dimension on the same view: pixels spanned and its
printed mm); without them --dpi gives PAPER millimetres only. Result also lists the integer-rounded estimate
(rules/DATUM.md §6: estimates are integer-rounded). Used for 521030-10 `φB`: ring fit Ø8.2 -> estimate Ø8 (FLAG).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def load_gray(path) -> np.ndarray:
    try:
        import pymupdf as fitz
    except ImportError:  # PyMuPDF < 1.24.3
        import fitz
    pm = fitz.Pixmap(str(path))
    if pm.n != 1 or pm.colorspace is None or pm.colorspace.n != 1:
        pm = fitz.Pixmap(fitz.csGRAY, pm)
    return np.frombuffer(pm.samples, dtype=np.uint8).reshape(pm.h, pm.w)


def px_per_mm(dpi=None, scale_px=None, scale_mm=None) -> tuple[float, str]:
    if scale_px and scale_mm:
        return float(scale_px) / float(scale_mm), "drawing scale (known dimension)"
    if dpi:
        return float(dpi) / 25.4, "paper mm (print scale unknown)"
    raise SystemExit("give --dpi or --scale-px/--scale-mm")


def fit_circle(gray: np.ndarray, near, r_lo: float, r_hi: float, threshold: int = 120) -> dict:
    cx0, cy0 = near
    h, w = gray.shape
    ys, xs = np.nonzero(gray < threshold)
    d = np.hypot(xs - cx0, ys - cy0)
    m = (d >= r_lo) & (d <= r_hi)
    if m.sum() < 20:
        raise SystemExit(f"only {int(m.sum())} dark pixels in the ring: check --near / --r")
    x, y = xs[m].astype(float), ys[m].astype(float)
    a = np.c_[2 * x, 2 * y, np.ones_like(x)]
    c = np.linalg.lstsq(a, x ** 2 + y ** 2, rcond=None)[0]
    xc, yc = float(c[0]), float(c[1])
    r = float(np.sqrt(c[2] + xc ** 2 + yc ** 2))
    resid = float(np.std(np.hypot(x - xc, y - yc) - r))
    return {"center_px": [round(xc, 2), round(yc, 2)], "radius_px": round(r, 2), "ring_pixels": int(m.sum()),
            "residual_px": round(resid, 2), "image_px": [w, h]}


def circle(path, near, r_lo, r_hi, dpi=None, scale_px=None, scale_mm=None) -> dict:
    res = fit_circle(load_gray(path), near, r_lo, r_hi)
    k, basis = px_per_mm(dpi, scale_px, scale_mm)
    dia = 2 * res["radius_px"] / k
    res.update(px_per_mm=round(k, 4), mm_basis=basis, diameter_mm=round(dia, 2), estimate_mm=round(dia),
               note="estimate only: FLAG + Magenta, never a proved dimension")
    return res


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("circle")
    c.add_argument("image")
    c.add_argument("--near", required=True, help="x,y px: approximate centre")
    c.add_argument("--r", nargs=2, type=float, required=True, metavar=("R_MIN", "R_MAX"), help="ring radii in px")
    c.add_argument("--dpi", type=float)
    c.add_argument("--scale-px", type=float)
    c.add_argument("--scale-mm", type=float)
    s = sub.add_parser("scale")
    s.add_argument("--px", type=float, required=True)
    s.add_argument("--mm", type=float, required=True)
    s.add_argument("--dpi", type=float)
    a = ap.parse_args(argv)
    if a.cmd == "scale":
        k = a.px / a.mm
        out = {"px_per_mm": round(k, 4)}
        if a.dpi:
            out["print_scale"] = round((a.dpi / 25.4) / k, 3)    # drawing is printed at 1:<this>
        print(json.dumps(out))
        return 0
    x, y = (float(v) for v in a.near.split(","))
    print(json.dumps(circle(Path(a.image), (x, y), a.r[0], a.r[1], a.dpi, a.scale_px, a.scale_mm), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
