# Production reference — Laser corner R, hole capacity, White Piercing

**Use `python tools/lookup.py laser-r --material <grade> --t <t>` and `python tools/lookup.py hole --material <grade> --t <t> --dia <effective Ø> [--piercing] [--through]`.** They parse the worksheet table below and apply the algorithm in this file; read the table by eye only without Python. Which corners get the R (corner class) stays an engineering decision. Approved value regressions are executable in `tests/test_lookup.py`.

Source: user-supplied `Rule_Bo_R&Hole.xlsx`, worksheet `Bo_R_Hole`, `2026.07.30`; calibration `520924-19`, approved 2026-09-25. This transcription is portable: do not require the spreadsheet or past chat.

## Material group

- Resolve the printed grade via `references/MATERIAL_ALIASES.yaml` / `tools/material_resolver.py` (Book1.xlsx 一覧表2026.07.30 A28:E48: **SECC=ボンデ (A32) → SS**, **SECC-P (A38) → SS**, SPCC, SPHC, SS400, SUS, AL…). Without an alias, prefixes `SUS…→SUS`, `SP…/SS…→SS`, `A…→AL`. Keep the full printed grade; a family is not proof that grades are interchangeable. Unknown prefixes and unidentified alloys are FLAG, never guessed from appearance.
- Surface `HL`, `2B`, `#400` are finishes, not grades. Excel `M51: H.L(ヘアライン)は横目` does NOT prove direction relative to the part: direction-uncertain HL stays REVIEW with no individual production DXF.
- **SUS430 process split (L09):** Nobi uses table 1 **SS, SUS430, BRASS** in `references/NOBI_TABLES.md`; Laser R, cut-hole minimum and 白ピアス use workbook **SUS, 他**. E.g. SUS430 t6: SS Nobi, row 11 Laser R0.5, inherited min hole t/2 from row 10, White Piercing 〇. Using SS t6 R2 for SUS430 is wrong.
- Customer-scoped exceptions and explicit PDF R/C take precedence over this table.

## SS t>=19 R3 scope and explicit-corner decisions

Automatic R3 applies only to corners on the **OUTER material perimeter contour**, including its concave/re-entrant corners. It never auto-rounds interior hole/slot/void contours. Preserve workbook provenance `一覧表2026.07.30!I41:I42` (鉄の外周R、19t以上は全ての角に3R); the broader original row-9 transcription is not active scope.

| Scoped corner | Decision |
|---|---|
| Eligible outer corner, no explicit source corner instruction | Apply automatic R3 |
| Explicit customer sharp/pin-corner instruction conflicts with automatic R3 | Draw the explicit customer corner, FLAG and obtain customer confirmation (REVIEW); no silent override either way |
| Explicit proved R/C, without the sharp/pin conflict above | Preserve the explicit family/value/scope under CHAMFER_RADIUS; do not silently convert C to R |
| Inner hole, slot or void contour | No automatic R3 from this outer-perimeter rule |

This conflict decision controls the generic explicit-instruction precedence below. NC pierce paths/joints remain deferred.


## PDF_DATA_RAW automatic R

In `PDF_DATA_RAW`, a sharp customer DATA corner is **not** evidence to omit a required automatic Laser R. After the corner identity/topology is proved, every otherwise uncalled eligible outside corner `<=90°` gets the active material/thickness R as a recorded `DATA_AUTO_R_CANONICALIZATION`, built as a local true tangent replacement; surrounding DATA stays untouched. An explicit PDF/source R or C at that corner keeps precedence; never smooth arbitrary internal notches or unrelated curve chains.

## Original worksheet entries (a dash means the CELL IS BLANK, not zero)

| Excel row | Material group | t Min | t Max | Laser corner condition | Laser R | Minimum cut-hole diameter | 白ピアス capacity |
|---:|---|---:|---:|---|---|---|:---:|
| 4 | SS | — | 3.2 | outside corner ≤90° | R0.5 | ≥ t/2 | × |
| 5 | SS | 4 | 5 | outside corner ≤90° | R0.5 | — | 〇 |
| 6 | SS | 6 | 9 | outside corner ≤90° | R2 | — | 〇 |
| 7 | SS | 10 | 12 | — | none (無) | — | 〇 |
| 8 | SS | 16 | 16 | — | none (無) | ≥ t | 〇 |
| 9 | SS | 19 | — | outer material perimeter corners only (2026-10-12 active scope; original 内外角/面取含) | R3 (※3 ignored) | — | 〇 |
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

The `※ケガキ不可` remark on the Cu/Brass last row means scribing/marking unavailable there; it does not specify a laser radius. The worksheet says `※3` at SS t≥19 but has no supplied explanatory text; **ignore only the annotation, retain R3** per approval. `無` explicitly means **no automatic laser fillet**. A blank R cell is **unknown in the original Excel transcription**; the separately approved L10 defines the Cu/Brass t6 R0.5 and t>6 NO-auto-R operation.


## L10 — Cu / Brass Laser R at t6 (approved override)

The worksheet row-26 R cell stays BLANK; this approved operation does not claim the workbook printed it. Eligible uncalled outside corner ≤90°: `0<t≤5` R0.5 (row 25); `5<t<6` R0.5 (next-higher t6); `t=6` **R0.5** (direct user clarification); `t>6` **NONE**. Explicit PDF R/C at that corner still wins; separately proved bend relief is unaffected; row-26 min hole **≥t**, White Piercing **×** and `※ケガキ不可` are unchanged.

## Approved lookup algorithm

1. Lock material and `t`; apply the L09 split and the L10 override first.
2. Row = the row whose Min–Max contains `t`. A first blank-Min row covers 0 < t ≤ Max; a later blank-Min row starts after the previous row's Max (AL: row 18 t≤0.5, row 19 0.5<t≤6). If several open rows match, use the most specific.
3. `t` between two explicit ranges → the **next higher thickness row** (no interpolation). A nonfinal row with Min and blank Max is explicit only at Min; the **last** row with Min and no Max covers Min and above. Outside the defined ranges → FLAG/ask, never invent a range.
4. A BLANK **hole-capacity** cell inherits the last nonblank value above it **within the same material group only**. Laser R and White Piercing cells never inherit.
5. Laser R applies only to the row's corner class, only at corners without an explicit PDF R/C, keeping convex/concave classification and never rounding internal notches blindly. `R=t` bend-intersection relief is a separate feature class, never material-table R. SS t>=19: R3 only on outer-perimeter corners, including concave corners of that perimeter, excluding interior holes/slots (decision table above).
6. Effective cut Ø = explicit drawing Ø, else the pilot Ø of a proved tapped M (`python tools/lookup.py pilot`). PIERCING scoped to that feature family → `POINT` ByLayer regardless of capacity; PIERCING + THROUGH HOLE → `POINT` Color 3; Ø < t/2 → `POINT` ByLayer; Ø below the Excel minimum → `POINT` ByLayer (no capacity FLAG); otherwise `CIRCLE` ByLayer. Ambiguous feature identity → temporary Magenta `CIRCLE` + FLAG; position uncertainty is a separate FLAG.
7. White Piercing `〇`/`×` is machine capability, never an instruction to turn holes into POINT; an explicit PDF PIERCING is followed even when the worksheet says `×`.
8. Record the selected Excel row and any upward-thickness choice; keep unrelated dimensional/customer FLAGs.

## Scope separation

This sheet governs hole capability and automatic material laser corner R only. Nobi comes from approved Nobi tables and handwritten corrections. The approved ONE Green slit in `055958` is a same-direction box corner under `BEND_EDGE_RELIEF_90.md` §9, not this table: 2 LINEs + 1 local ARC R0.5 as one feature. Special J marks and other unapproved shop reliefs need their own drawing evidence.
