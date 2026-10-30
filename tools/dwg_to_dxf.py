#!/usr/bin/env python3
"""DWG -> DXF (2018) so ezdxf / tools/dxf_digest.py can read a DWG (QA or a checked sample).

    python tools/dwg_to_dxf.py file.dwg [out.dxf] [--accore PATH]

Runs AutoCAD's headless `accoreconsole.exe` on a COPY of the DWG (the original is never opened, no .dwl/.bak next to it) with
`_.DXFOUT <out> V 2018 16`. Do not pass /readonly (ErrorStatus=53). Found automatically: env ACCORECONSOLE, AutoCAD 2026..2018,
then DWG TrueView. The result is cached next to out.dxf (<out>.src.json with the DWG's sha256): an unchanged DWG is not
converted again.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_PF = [Path(os.environ.get("ProgramFiles", "C:/Program Files"))]
CANDIDATES = [*(_PF[0] / "Autodesk" / f"AutoCAD {y}" / "accoreconsole.exe" for y in range(2027, 2017, -1)),
              *(_PF[0] / "Autodesk").glob("DWG TrueView*/accoreconsole.exe")]


class DwgConvertError(RuntimeError):
    pass


def find_accore(explicit: str | None = None) -> Path:
    for c in [explicit, os.environ.get("ACCORECONSOLE"), *CANDIDATES]:
        if c and Path(c).is_file():
            return Path(c)
    raise DwgConvertError("accoreconsole.exe not found: install AutoCAD/DWG TrueView or set ACCORECONSOLE")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def script_text(out_dxf: Path) -> str:
    return "\r\n".join(["FILEDIA 0", "_.DXFOUT", str(out_dxf), "V", "2018", "16", "_.QUIT", "Y", ""])


def convert(dwg, out_dxf=None, accore: str | None = None, timeout: int = 240, runner=subprocess.run) -> Path:
    dwg = Path(str(dwg).replace("\\", "/") if str(dwg).startswith("\\\\") else dwg)
    if not dwg.is_file():
        raise DwgConvertError(f"{dwg} not found")
    out = Path(out_dxf) if out_dxf else dwg.with_suffix(".dxf")
    meta = out.with_name(out.name + ".src.json")
    digest = _sha(dwg)
    if out.is_file() and meta.is_file() and json.loads(meta.read_text(encoding="utf-8")).get("sha256") == digest:
        return out
    exe = find_accore(accore)
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dwg2dxf_") as tmp:
        work = Path(tmp)
        src, tmp_out, scr = work / "in.dwg", work / "out.dxf", work / "run.scr"
        shutil.copyfile(dwg, src)
        scr.write_bytes(script_text(tmp_out).encode("utf-8"))
        res = runner([str(exe), "/i", str(src), "/s", str(scr), "/l", "en-US"], capture_output=True, timeout=timeout)
        if not tmp_out.is_file():
            tail = (getattr(res, "stdout", b"") or b"")[-400:].decode("utf-16", "ignore") or "no output"
            raise DwgConvertError(f"DXFOUT produced no file for {dwg.name}: {tail.strip()[-300:]}")
        shutil.copyfile(tmp_out, out)
    meta.write_text(json.dumps({"sha256": digest, "dwg": dwg.name, "accore": str(exe)}, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dwg")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--accore")
    a = ap.parse_args(argv)
    try:
        print(convert(a.dwg, a.out, a.accore))
    except DwgConvertError as exc:
        print(f"DWG_CONVERT_FAIL: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
