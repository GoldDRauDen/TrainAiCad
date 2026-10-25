# HOLE_TAP — round holes, taps, piercing / POINT (lỗ, lỗ mồi ren, piasu)

Triggers: `Ø`, `n-Ø`, `穴`, `キリ`, `M6`/`M8x1`, `タップ`, `ネジ`, `ピアス`, `PIERCING`, `THROUGH HOLE`, `白ピアス`, `皿`, `ザグリ`, `通シ`, `貫通`.

## 1. Effective cut diameter
- Explicit drawing Ø; for a proved `M<n>` the pilot: `python tools/lookup.py pilot --thread M8` (coarse) / `--thread M8x1` (fine only when the pitch is printed). M4 3.3, M5 4.2, M6 5.0, M8 6.8. A nut symbol alone is not a tap. One M = exactly one pilot CUT/POINT; tap→pilot never changes quantity or datum. Keep table values (M2 Ø1.6, M12 Ø10.3, M38×1.5 Ø36.6); Ø1.7 / Ø8 only for a proved tool-breakage / outside-process instruction.
- Countersink/counterbore (`皿`/`ザグリ`): only the through-hole/pilot is a laser cut, never the mouth Ø (`data/countersink.md`: M3 3.4, M4 4.5, M5 5.5, M6 6.6, M8 9.0). Reamer −0.1 only by explicit shop/customer instruction. Drill-machine reach 170 mm is a WARN.
- DATA tap: a concentric nominal ring = `THREAD_NOMINAL_REFERENCE` (non-cut); compare only it with M<n> (`Δ ≥ 0.1` → `DATA_PDF_DIM_DIFF`); raw pre-hole is provenance; output one pilot (PDF M6 + DATA Ø6 ring + raw Ø5.1 → one Ø5.0). Ring role ambiguous → FLAG, never choose by size.

## 2. POINT or CIRCLE (`python tools/lookup.py hole --material M --t T --dia D [--piercing] [--through]`), per feature family, first match
1. PIERCING + the English `THROUGH HOLE` stamp on that family → POINT Green (62=3) = "piasu xanh". Japanese `通シ`/`貫通` and `M12通シ` do NOT qualify.
2. PIERCING scoped by the leader to that family → POINT ByLayer, whatever `白ピアス 〇/×` says (that column is machine capability, not drawing intent).
3. `d < t/2` (strict) → POINT ByLayer, no capacity FLAG.
4. `d` below the workbook minimum for the material/t row → POINT ByLayer, no capacity FLAG. Otherwise CIRCLE ByLayer.
5. Row/material unresolved and `d ≥ t/2` → provisional Magenta CIRCLE + FLAG.
- Trace PIERCING by its arrow/leader; a large label elsewhere is not blanket authority. SUS430 uses the SUS/他 rows for hole limits and 白ピアス (SS rows only for Nobi).
- No circle or Ø/M text around a POINT; list converted POINTs (source Ø/M, centre, reason) in the report.

## 3. Unknown or pending
- Round hole with pending Ø: Magenta CIRCLE at an integer estimated Ø, note `Ø? - xác nhận đường kính`, FLAG, PREVIEW; never run the `d<t/2` test on a guessed Ø; never omit the hole.
- Unknown centre/identity → Magenta + separate FLAGs; keep other proved holes exact.

## 4. Geometry rules
- Truly intersecting cut regions → ONE closed CW union contour (exact arcs), not overlapping circles; count each original callout member separately (010447: Ø28.5 + 4×Ø5.5 = one contour). Tangent contact or unproved overlap → no union.
- A printed special `J` POINT set needs its own PDF note/leader; never inferred from a sample (055957). Different from the bend `J`.
- Holes on bent faces: host face + local datum, transformed by `BEND.md` §5. Feasibility distances are advisory only.

## 5. Check
Original callout count = produced count, effective Ø per member, POINT/CIRCLE type and colour, datum per centre, containment.

## Lessons
`regression/lessons/HOLE_TAP/` — 520924-19 (workbook, POINT rules), 521001-13 (DATA M*), 521015-14 (通シ is not THROUGH HOLE), 520217-27 (V4.12 pending Ø).
