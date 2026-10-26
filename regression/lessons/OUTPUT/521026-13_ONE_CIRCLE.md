# 521026-13 — a circle is ONE CIRCLE, an arc ONE ARC (user DUYỆT 2026-10-26)

Rule: `rules/OUTPUT.md` §4, `rules/KEGAKI.md` §4; executable `tools/curve_guard.py`, spec `outline: {circle}` / `kegaki: circles`, `tests/test_circle_one_entity.py`.

## FACT
- 26-063299 (disc Ø100) was saved as two ARCs; the KEGAKI rings of 26-063296 / 063297 / 063299 as 72 short LINEs each, plus an inner Ø27.6 ring. HD: one CIRCLE r50, one red CIRCLE r17 (tube: "định vị vòng ngoài là được"), red CIRCLE r8 on the bar plates.
- The user: serious, frequent error — a circle is drawn as one circle, an arc as one arc, except when a customer DATA DXF already has them.

## ROOT_CAUSE
`AI_RULE_GAP` in tools: the guards accepted only LINE for a KEGAKI group and only a LWPOLYLINE for the outline, and the exporter wrote a two-bulge circle as two ARCs. The job worked around the gap with polygons instead of reporting it.

## LESSON
A tool gap that forces a split curve is reported, never worked around. Full-circle outline → one CIRCLE; round mark → one red CIRCLE (tube end: outer ring only); `curve_guard.py` fails SPLIT_ARC / SPLIT_CIRCLE (faceted runs too) on every non-DATA part.
