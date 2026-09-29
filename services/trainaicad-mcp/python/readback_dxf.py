#!/usr/bin/env python3
import argparse
import json
from collections import Counter
from pathlib import Path

import ezdxf


def r(v, n=6):
    return round(float(v), n)


def xy(v):
    return [r(v[0]), r(v[1])]


def entity(e):
    t = e.dxftype()
    base = {
        "type": t,
        "layer": e.dxf.layer,
        "color": e.dxf.get("color", 256),
        "linetype": e.dxf.get("linetype", "BYLAYER"),
    }
    if t == "LWPOLYLINE":
        base.update({
            "closed": bool(e.closed),
            "vertices": [[r(x), r(y), round(float(b), 8)] for x, y, b in e.get_points("xyb")],
        })
    elif t == "CIRCLE":
        base.update({"center": xy(e.dxf.center), "radius": r(e.dxf.radius)})
    elif t == "LINE":
        base.update({"start": xy(e.dxf.start), "end": xy(e.dxf.end)})
    elif t == "ARC":
        base.update({
            "center": xy(e.dxf.center),
            "radius": r(e.dxf.radius),
            "start_angle": r(e.dxf.start_angle),
            "end_angle": r(e.dxf.end_angle),
        })
    elif t == "POINT":
        base.update({"point": xy(e.dxf.location)})
    elif t == "TEXT":
        base.update({"insert": xy(e.dxf.insert), "text": e.dxf.text, "height": r(e.dxf.height)})
    else:
        base["unsupported"] = True
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dxf", type=Path)
    args = ap.parse_args()

    doc = ezdxf.readfile(args.dxf)
    audit = doc.audit()
    msp = list(doc.modelspace())
    entities = [entity(e) for e in msp]
    layers = Counter(e["layer"] for e in entities)
    types = Counter(e["type"] for e in entities)
    layer0 = [e for e in entities if e["layer"] == "0"]
    meta = [e for e in entities if e["layer"] == "AI_META"]
    result = {
        "file": str(args.dxf),
        "audit_errors": len(audit.errors),
        "insunits": doc.header.get("$INSUNITS"),
        "measurement": doc.header.get("$MEASUREMENT"),
        "entity_count": len(entities),
        "layer_counts": dict(layers),
        "type_counts": dict(types),
        "layer0": layer0,
        "meta": meta,
    }
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
