#!/usr/bin/env python3
"""Look at a drawing PDF precisely: page info, exact vector text, gridded
renders and high-resolution crops. Requires PyMuPDF (`pip install pymupdf`).

    python tools/pdf_views.py info drawing.pdf
    python tools/pdf_views.py render drawing.pdf --page 1 --out p1.png          # 10x10 grid A1..J10
    python tools/pdf_views.py crop drawing.pdf --page 1 --cells C3:E5 --out c.png  # zoomed crop (default 600 dpi)
    python tools/pdf_views.py text drawing.pdf --page 1 [--cells C3:E5] [--dims]
    python tools/pdf_views.py pairs drawing.pdf --page 1 [--dist 25] [--out-dir crops/]   # close same-axis dims

Why: CAD-exported PDFs usually keep dimension text as vector text. ``text``
returns the exact printed string and its position, which removes OCR swaps
(B/8, O/0, S/5, Ø/O, M6/MG). Use the image to decide which witness lines a
value belongs to; use the text to read the value. A scanned page has no
vector text (``info`` reports it): then read from 600-dpi crops twice.
Grid cells are page-relative: columns A–J left→right, rows 1–10 top→bottom.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

try:
    import pymupdf as fitz
except ImportError:  # older PyMuPDF
    try:
        import fitz  # type: ignore
    except ImportError:
        fitz = None

GRID = 10
DIM_RE = re.compile(r"(?:\d+-)?(?:[ØφΦ]|M|R|C|t\s*=?\s*)?\d+(?:\.\d+)?|[±+\-]\s*\d|[ØφΦ]|\bM\d|\bR\d|\bC\d")


def _need():
    if fitz is None:
        sys.exit("PyMuPDF missing: pip install pymupdf")


def _cells_rect(page, cells: str | None):
    r = page.rect
    if not cells:
        return r
    m = re.fullmatch(r"([A-J])(\d{1,2})(?::([A-J])(\d{1,2}))?", cells.upper())
    if not m:
        raise SystemExit(f"bad cells '{cells}', use e.g. C3 or C3:E5")
    c0, r0 = ord(m.group(1)) - 65, int(m.group(2)) - 1
    c1, r1 = (ord(m.group(3)) - 65, int(m.group(4)) - 1) if m.group(3) else (c0, r0)
    c0, c1 = sorted((c0, c1))
    r0, r1 = sorted((r0, r1))
    w, h = r.width / GRID, r.height / GRID
    return fitz.Rect(r.x0 + c0 * w, r.y0 + r0 * h, r.x0 + (c1 + 1) * w, r.y0 + (r1 + 1) * h)


def info(path: str) -> dict:
    _need()
    doc = fitz.open(path)
    pages = []
    for i, page in enumerate(doc, 1):
        words = page.get_text("words")
        pages.append({"page": i, "width_pt": round(page.rect.width, 1), "height_pt": round(page.rect.height, 1),
                      "rotation": page.rotation, "vector_words": len(words),
                      "drawings": len(page.get_drawings()), "images": len(page.get_images()),
                      "kind": "VECTOR" if words else ("SCANNED_IMAGE" if page.get_images() else "VECTOR_NO_TEXT")})
    return {"file": path, "pages": pages}


def render(path: str, page_no: int, out: str, dpi: int = 150, grid: bool = True) -> dict:
    _need()
    page = fitz.open(path)[page_no - 1]
    if grid:  # drawn in displayed space, mapped back to the page's unrotated space
        shape = page.new_shape()
        r = page.rect
        m = page.derotation_matrix
        w, h = r.width / GRID, r.height / GRID
        for i in range(1, GRID):
            shape.draw_line(fitz.Point(r.x0 + i * w, r.y0) * m, fitz.Point(r.x0 + i * w, r.y1) * m)
            shape.draw_line(fitz.Point(r.x0, r.y0 + i * h) * m, fitz.Point(r.x1, r.y0 + i * h) * m)
        shape.finish(color=(1, 0, 1), width=0.4, dashes="[2 2] 0")
        size = max(6, min(w, h) / 6)
        for c in range(GRID):
            for rr in range(GRID):
                pt = fitz.Point(r.x0 + c * w + 2, r.y0 + rr * h + size + 1) * m
                shape.insert_text(pt, f"{chr(65 + c)}{rr + 1}", fontsize=size, color=(1, 0, 1),
                                  rotate=page.rotation)
        shape.commit()
    pix = page.get_pixmap(dpi=dpi)
    pix.save(out)
    return {"out": out, "dpi": dpi, "px": [pix.width, pix.height], "grid": grid}


def crop(path: str, page_no: int, cells: str, out: str, dpi: int = 600) -> dict:
    _need()
    page = fitz.open(path)[page_no - 1]
    clip = _cells_rect(page, cells)
    pix = page.get_pixmap(dpi=dpi, clip=clip)
    pix.save(out)
    return {"out": out, "dpi": dpi, "cells": cells, "px": [pix.width, pix.height]}


def text(path: str, page_no: int, cells: str | None = None, dims_only: bool = False) -> dict:
    _need()
    page = fitz.open(path)[page_no - 1]
    r = page.rect  # displayed (rotated) page space, same as renders and cells
    clip = _cells_rect(page, cells) * page.derotation_matrix if cells else None
    spans = []
    for block in page.get_text("dict", clip=clip)["blocks"]:
        for line in block.get("lines", []):
            angle = round(-__import__("math").degrees(__import__("math").atan2(line["dir"][1], line["dir"][0])))
            for sp in line["spans"]:
                s = sp["text"].strip()
                if not s or (dims_only and not DIM_RE.search(s)):
                    continue
                x0, y0, x1, y1 = fitz.Rect(sp["bbox"]) * page.rotation_matrix
                cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
                col = min(GRID - 1, int((cx - r.x0) / (r.width / GRID)))
                row = min(GRID - 1, int((cy - r.y0) / (r.height / GRID)))
                spans.append({"text": s, "cell": f"{chr(65 + col)}{row + 1}", "angle": angle,
                              "size": round(sp["size"], 1), "bbox_pt": [round(v, 1) for v in (x0, y0, x1, y1)]})
    spans.sort(key=lambda d: (d["bbox_pt"][1], d["bbox_pt"][0]))
    return {"file": path, "page": page_no, "cells": cells, "count": len(spans), "spans": spans}


def pairs(path: str, page_no: int, dist_pt: float = 25.0, out_dir: str | None = None, dpi: int = 900) -> dict:
    """Dimension values of the same direction whose labels sit close together (e.g. 70 / 65).

    Such pairs are where witness lines are most easily swapped: crop each one at >=900 dpi and
    decide which edge every extension line touches before drawing (DRAWING_READING.md).
    """
    _need()
    page = fitz.open(path)[page_no - 1]
    if not page.get_text("words"):
        return {"file": path, "page": page_no, "kind": "SCANNED_IMAGE", "pairs": [],
                "note": "no vector text: crop every close same-axis dimension pair by hand at >=900 dpi"}
    spans = [s for s in text(path, page_no, None, True)["spans"] if re.search(r"\d", s["text"])]
    found = []
    for i, a in enumerate(spans):
        for b in spans[i + 1:]:
            if a["angle"] != b["angle"]:
                continue
            ca = ((a["bbox_pt"][0] + a["bbox_pt"][2]) / 2, (a["bbox_pt"][1] + a["bbox_pt"][3]) / 2)
            cb = ((b["bbox_pt"][0] + b["bbox_pt"][2]) / 2, (b["bbox_pt"][1] + b["bbox_pt"][3]) / 2)
            d = ((ca[0] - cb[0]) ** 2 + (ca[1] - cb[1]) ** 2) ** 0.5
            if d <= dist_pt:
                box = [min(a["bbox_pt"][0], b["bbox_pt"][0]) - 30, min(a["bbox_pt"][1], b["bbox_pt"][1]) - 30,
                       max(a["bbox_pt"][2], b["bbox_pt"][2]) + 30, max(a["bbox_pt"][3], b["bbox_pt"][3]) + 30]
                rec = {"values": [a["text"], b["text"]], "cells": [a["cell"], b["cell"]], "angle": a["angle"],
                       "distance_pt": round(d, 1), "crop_bbox_pt": [round(v, 1) for v in box]}
                if out_dir:
                    from pathlib import Path as _P
                    _P(out_dir).mkdir(parents=True, exist_ok=True)
                    out = str(_P(out_dir) / f"pair_p{page_no}_{len(found) + 1}.png")
                    clip = fitz.Rect(*box) * page.derotation_matrix
                    page.get_pixmap(dpi=dpi, clip=clip).save(out)
                    rec["out"] = out
                found.append(rec)
    return {"file": path, "page": page_no, "kind": "VECTOR", "pairs": found}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("info")
    i.add_argument("pdf")
    r = sub.add_parser("render")
    r.add_argument("pdf")
    r.add_argument("--page", type=int, default=1)
    r.add_argument("--out", required=True)
    r.add_argument("--dpi", type=int, default=150)
    r.add_argument("--no-grid", action="store_true")
    c = sub.add_parser("crop")
    c.add_argument("pdf")
    c.add_argument("--page", type=int, default=1)
    c.add_argument("--cells", required=True)
    c.add_argument("--out", required=True)
    c.add_argument("--dpi", type=int, default=600)
    t = sub.add_parser("text")
    t.add_argument("pdf")
    t.add_argument("--page", type=int, default=1)
    t.add_argument("--cells")
    t.add_argument("--dims", action="store_true", help="only spans that look like dimensions/callouts")
    q = sub.add_parser("pairs")
    q.add_argument("pdf")
    q.add_argument("--page", type=int, default=1)
    q.add_argument("--dist", type=float, default=25.0, help="max label-center distance in pt")
    q.add_argument("--out-dir")
    q.add_argument("--dpi", type=int, default=900)
    a = ap.parse_args(argv)
    if a.cmd == "info":
        res = info(a.pdf)
    elif a.cmd == "render":
        res = render(a.pdf, a.page, a.out, a.dpi, not a.no_grid)
    elif a.cmd == "crop":
        res = crop(a.pdf, a.page, a.cells, a.out, a.dpi)
    elif a.cmd == "pairs":
        res = pairs(a.pdf, a.page, a.dist, a.out_dir, a.dpi)
    else:
        res = text(a.pdf, a.page, a.cells, a.dims)
    print(json.dumps(res, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
