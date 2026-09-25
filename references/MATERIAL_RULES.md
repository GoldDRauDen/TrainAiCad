# Production reference — Laser corner R, hole capacity, White Piercing

**Approved from user-supplied** `Rule_Bo_R&Hole.xlsx`, worksheet `Bo_R_Hole`, dated `2026.07.30`; calibration `520924-19`, approved 2026-09-25. This complete transcription is portable: do not require the original spreadsheet or past chat.

## Original worksheet entries (a dash means the CELL IS BLANK, not zero)

| Excel row | Material group | t Min | t Max | Laser corner condition | Laser R | Minimum cut-hole diameter | 白ピアス capacity |
|---:|---|---:|---:|---|---|---|:---:|
| 4 | SS | — | 3.2 | outside corner ≤90° | R0.5 | ≥ t/2 | × |
| 5 | SS | 4 | 5 | outside corner ≤90° | R0.5 | — | 〇 |
| 6 | SS | 6 | 9 | outside corner ≤90° | R2 | — | 〇 |
| 7 | SS | 10 | 12 | — | none (無) | — | 〇 |
| 8 | SS | 16 | 16 | — | none (無) | ≥ t | 〇 |
| 9 | SS | 19 | — | inside/outside corners, including chamfer (内外角/面取含) | R3 (※3 ignored) | — | 〇 |
| 10 | SUS, 他 | — | 5 | outside corner ≤90° | R0.5 | ≥ t/2 | × |
| 11 | SUS, 他 | 6 | 6 | outside corner ≤90° | R0.5 | — | 〇 |
| 12 | SUS, 他 | 7 | 8 | — | none (無) | — | 〇 |
| 13 | SUS, 他 | 9 | 12 | — | none (無) | — | 〇 |
| 14 | SUS, 他 | 14 | 14 | — | none (無) | — | 〇 |
| 15 | SUS, 他 | 15 | 16 | — | none (無) | ≥ Ø10 | 〇 |
| 16 | SUS, 他 | 19 | 19 | — | none (無) | — | 〇 |
| 17 | SUS, 他 | 20 | — | — | none (無) | ≥ t | 〇 |
| 18 | AL | — | 0.5 | outside corner ≤90° | R0.5 | ≥ 0.8t | × |
| 19 | AL | — | 6 | outside corner ≤90° | R0.5 | — | 〇 |
| 20 | AL | 7 | 8 | — | none (無) | — | 〇 |
| 21 | AL | 9 | — | — | none (無) | — | 〇 |
| 22 | AL | 12 | — | — | none (無) | — | 〇 |
| 23 | AL | 16 | — | — | none (無) | ≥ t | 〇 |
| 24 | AL | 19 | — | — | none (無) | — | 〇 |
| 25 | Cu / Brass (銅・真ちゅう) | — | 5 | outside corner ≤90° | R0.5 | ≥ t/2 | × |
| 26 | Cu / Brass; ※ケガキ不可 | 6 | — | outside corner ≤90° | — [UNSPECIFIED] | ≥ t | × |

The `※ケガキ不可` remark on the Cu/Brass last row means scribing/marking unavailable there; it does not specify a laser radius. The worksheet says `※3` at SS t≥19 but has no supplied explanatory text; **ignore only the annotation, retain R3** per approval. `無` explicitly means **no automatic laser fillet**. A blank R cell is **unknown**, not `無`.

## Approved lookup algorithm

1. Lock the explicit drawing material group and real thickness `t`. Never silently equate `SUS430` and the SS group without an approved material mapping; ambiguous alloys require a question/FLAG.
2. Find a row containing `t` in its stated Min–Max range. A first row with blank Min covers positive t up to its Max; for AL the next blank-Min row ending at 6 covers t>0.5 through 6 (the preceding row handles t≤0.5). If several rows with open Min are candidates, choose the most specific applicable row.
3. If t falls between two explicit ranges, use the **next higher thickness row** (no interpolation). For a nonfinal row that has Min but blank Max, treat only its specified Min as explicit; for intermediate t choose the next higher row. A **last** row with a Min and no Max covers that Min and all greater thicknesses. Outside the material's defined ranges, or with no unambiguous row, ASK; do not invent a range.
4. For a BLANK **hole-capacity** cell, inherit the last nonblank hole-capacity value above it **within the same material group only**. Do not inherit Laser R or White Piercing cells; their values are row-specific.
5. Determine laser R only at corners belonging to the row's corner class. A PDF-specific R or C at that corner overrides the Excel R. Where Excel specifies R0.5/R2/R3 and PDF has no explicit R/C, bake it automatically into the actual contour; keep convex vs concave classification and do not blindly round internal notches. `R=t` bend-intersection relief is a separate feature class and must never be mistaken for material-table laser R.
6. Calculate the **effective cut diameter** from an explicit drawing Ø when present, otherwise the pilot diameter from approved thread table 7.1 for a proved tapped M feature. PIERCING arrow/note scoped to that feature family => `POINT` ByLayer regardless of capacity. PIERCING plus THROUGH HOLE => `POINT` Color 3. Ø < t/2 => `POINT` ByLayer without a capacity FLAG. Else when effective Ø is below Excel minimum => `POINT` ByLayer without a capacity FLAG; otherwise `CIRCLE` ByLayer. An ambiguous feature identity => temporary `CIRCLE` Color 6 + FLAG; geometry/position uncertainty produces a separate independent FLAG.
7. White Piercing `〇` and `×` are **machine-capability indicators**, never instructions to turn every hole into POINT; follow the explicit PDF PIERCING for the specified feature group even if worksheet is `×`, without a capacity-only FLAG. User-approved PROCESS POINT Color 3 is restricted to explicit `PIERCING + THROUGH HOLE`; other POINTs default ByLayer on Layer 0.
8. Document the selected Excel row and any upward-thickness selection for ambiguous/nonstandard thickness; preserve unrelated dimensional/customer-approval FLAGs.

## Regression examples (user-approved)

- SS t9: hole threshold t/2 = 4.5. M4 pilot Ø3.3 and M5 pilot Ø4.2 => POINT ByLayer with no capacity FLAG. M6 pilot Ø5.0 => CIRCLE if no PIERCING, assuming verified M6 and coordinates.
- SS t9 outside corner ≤90° with no explicit PDF R/C => R2 added (e.g. `055955`). SS t≤3.2 outside ≤90° => R0.5 added.
- SUS t15–16 => minimum cut hole Ø10, independent of the unconditional POINT rule for Ø < t/2.
- AL t5 => minimum cut hole 0.8t = Ø4. Ø3 with no PIERCING => POINT ByLayer with no capacity FLAG, although Ø3 is not < t/2.
- SS t19+ => laser R3 with inside/outside-corner scope as printed; ignore unexplained `※3` notation, not the R3 value.

## Scope separation

This sheet governs **hole capability and automatic material-based laser corner R only**. Nobi/bend allowance still comes from approved Nobi tables and handwritten corrections. Special J marks and shop-specific relief geometry require their own explicit drawing evidence; the three reliefs of `055958` remain unresolved and MUST NOT be inferred from this workbook.
