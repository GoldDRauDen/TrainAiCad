#!/usr/bin/env python3
"""Source-cell-backed material classification (not a manufacturing parameter solver)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
import unicodedata
import yaml

_SOURCE = Path(__file__).resolve().parents[1] / "data" / "material_aliases.yaml"
_PROCESSES = {"LASER_R", "CUT_HOLE", "WHITE_PIERCING", "NOBI"}


class MaterialResolveError(ValueError):
    pass


def _norm(value: str) -> str:
    return unicodedata.normalize("NFKC", value).upper().replace(" ", "").replace("　", "")


@lru_cache(maxsize=1)
def _aliases():
    cfg = yaml.safe_load(_SOURCE.read_text(encoding="utf-8"))
    index = []
    for group, aliases in cfg["groups"].items():
        for alias, cell in aliases.items():
            index.append((_norm(str(alias)), group, str(cell)))
    return sorted(index, key=lambda item: len(item[0]), reverse=True)


def is_hairline(text: str) -> bool:
    value = unicodedata.normalize("NFKC", text).upper()
    return bool(re.search(r"(?<![A-Z])HL(?![A-Z])", value)) or "ヘアライン" in value


def resolve_material(printed: str, process: str = "LASER_R") -> dict:
    if not isinstance(printed, str) or not printed.strip():
        raise MaterialResolveError("MATERIAL_UNSPECIFIED")
    if process not in _PROCESSES:
        raise MaterialResolveError("UNKNOWN_PROCESS")
    value = _norm(printed)
    short_430 = bool(re.match(r"^430(?=$|[-_/.(,=]|HL|ヘアライン|2B|#)", value))
    # A complete SUS grade takes precedence over short numerical aliases;
    # SUS430 retains the already-approved process split.
    if value.startswith("SUS430") or short_430:
        group, cell = "SUS", "C35"
    elif value.startswith("SUS"):
        group, cell = "SUS", "C28"
    else:
        group = cell = None
        for alias, candidate, source_cell in _aliases():
            if value == alias or (
                (len(alias) >= 3 or re.match(r"[-_]?\d", value[len(alias):])) and value.startswith(alias) and (
                    len(value) == len(alias) or value[len(alias)] in "-_/.(,=0123456789#"
                    or is_hairline(printed) or value[len(alias):].startswith("ボンデ")
                )
            ):
                group, cell = candidate, source_cell
                break
        if group is None and value.startswith("SP"):
            group, cell = "SS", "A28"  # approved family-prefix fallback
        elif group is None and value.startswith("SS"):
            group, cell = "SS", "A28"
        elif group is None and re.match(r"A\d", value):
            group, cell = "AL", "E28"
    if group is None:
        raise MaterialResolveError(f"MATERIAL_GROUP_UNRESOLVED:{printed}")
    if group == "OTHER":
        # The Excel '他' column is insufficient to assert a universal
        # hole/Nobi rule for an arbitrary alloy.
        if process == "NOBI":
            raise MaterialResolveError(f"MATERIAL_PROCESS_UNRESOLVED:{printed}:{process}")
        applied = "SUS_OTHER"
    elif group == "SUS" and (value.startswith("SUS430") or short_430) and process == "NOBI":
        applied = "SS_SUS430_BRASS"
    else:
        applied = group
    return {
        "printed_material": printed,
        "material_family": group,
        "process": process,
        "process_group": applied,
        "source_cell": f"一覧表2026.07.30!{cell}",
        "hairline": is_hairline(printed),
    }


def material_info(text) -> dict:
    """Family of a printed/slip material text (`304-2B**`, `SPHCP(酸洗)`): {material_text, family, surface[, unresolved]}."""
    text = unicodedata.normalize("NFKC", text).strip() if isinstance(text, str) else ""
    base = re.sub(r"\*+$", "", text).strip()
    info = {"material_text": text, "family": None,
            "surface": "#1" if "#1" in base else ("HL" if is_hairline(base) else None)}
    try:
        info["family"] = resolve_material(base)["material_family"]
    except MaterialResolveError:
        info["unresolved"] = True
    return info


def material_check(slip_text, drawing_text) -> dict:
    """The slip material wins; a different FAMILY on the drawing is a FLAG (flag_vi), the same family is silent."""
    s, d = material_info(slip_text), material_info(drawing_text)
    out = {"slip_family": s["family"], "drawing_family": d["family"], "flag_vi": None}
    if s["family"] and d["family"] and s["family"] != d["family"]:
        out["flag_vi"] = (f"Vật liệu phiếu {slip_text} ({s['family']}) khác bản vẽ {drawing_text} ({d['family']}): "
                          "dùng vật liệu phiếu, cần xác nhận khách")
    elif not s["family"] or not d["family"]:
        out["flag_vi"] = f"Không xác định nhóm vật liệu ({slip_text} / {drawing_text}): kiểm tra phiếu"
    return out
