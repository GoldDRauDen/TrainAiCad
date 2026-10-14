# 08 — MATERIAL / THICKNESS / EDGE R-C | Production rules V4.34

> Material exceptions, thickness, auto-R and explicit source R/C precedence. Machine-readable material aliases remain separate YAML.

<!-- BEGIN MODULE: references/MATERIAL_RULES.md -->
## V4.34 approved Excel alias resolution (2026-10-13)
Resolve printed material via `references/MATERIAL_ALIASES.yaml` and `tools/material_resolver.py` before selecting Laser R/hole-capacity rows. The alias table cites **Book1.xlsx / 一覧表2026.07.30 A28:E48**, including **SECC=ボンデ (A32) → SS**, **SECC-P (A38) → SS**, SPCC, SPHC, SS400, SUS and AL names. Preserve the printed grade separately. SUS430 retains its prior process split; surface `HL`, `2B`, `#400` are finishes, not independent grades. Excel `M51: H.L(ヘアライン)は横目` does NOT alone prove direction relative to the part: keep direction-uncertain HL as REVIEW with no production individual DXF. Customer-scoped exceptions and explicit PDF R/C still take precedence. Do not infer unidentified alloys from visual similarity.

# Production reference — Laser corner R, hole capacity, White Piercing

## Customer-approved 2026-10-12 SS t>=19 R3 scope clarification
The workbook `一覧表2026.07.30!I41:I42` states **鉄の外周R、19t以上は全ての角に3R**. Operationally, SS t>=19 automatic R3 applies only to corners on the **OUTER material perimeter contour**, including concave/re-entrant corners belonging to that same exterior contour. It **does not** auto-fillet contours of interior holes, slots or voids. Explicit customer drawing instructions override this table for each scoped corner (sharp/pin角 or R/C). This approved restriction supersedes the wider original row-9 transcription; keep original source cell as provenance, not active scope. Laser-NC pierce paths/joints are deferred from CAD.


## V4.24 PDF_DATA_RAW automatic-R execution hardening

No workbook value changes. In `PDF_DATA_RAW`, a customer DATA corner being sharp is **not** evidence to omit an automatic Laser R required by this table. After the DATA corner identity/topology is proved, every otherwise uncalled eligible outside corner `<=90°` receives the active material/thickness R as a recorded `DATA_AUTO_R_CANONICALIZATION`. Preserve the surrounding DATA geometry and build the true tangent replacement locally. An explicit PDF/source R or C at that corner retains precedence, and this rule never authorizes smoothing arbitrary internal notches or unrelated curve chains.

**Approved from user-supplied** `Rule_Bo_R&Hole.xlsx`, worksheet `Bo_R_Hole`, dated `2026.07.30`; calibration `520924-19`, approved 2026-09-25. This complete transcription is portable: do not require the original spreadsheet or past chat.

## V4.12 approved sheet-material prefix classification (2026-09-27)

For sheet-metal grade labels, normalize whitespace/case and match family prefixes: `SUS…→SUS`, `SP…/SS…→SS`, `A…→AL`. Preserve the complete printed grade and source thickness; this routing is not proof that different exact grades are interchangeable. Previously approved SUS430 **process split** overrides generic SUS for Nobi (SS/SUS430/BRASS), whereas SUS430 laser corner R, hole limit and White Piercing use SUS/他. Unknown sheet-metal prefixes remain flagged. On job 520217-27, user directly confirmed both 009252/009253 belong to the SS family; the full SPHC-versus-SS400 grade is not adjudicated by that family statement. This V4.12 clarification leaves original workbook cells unchanged.

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

## L09 — Approved SUS430 process-specific routing (2026-09-25)

**SUS430 has DIFFERENT lookup groups by manufacturing process; never apply a single SS or SUS group to all operations.**

| Process | Authoritative group |
|---|---|
| Nobi / bend deduction | **SS, SUS430, BRASS** in `references/NOBI_TABLES.md` (portable Section 7.3); numeric values unchanged |
| Laser R | Workbook **SUS, 他** |
| Cut-hole minimum | Workbook **SUS, 他**; hole-limit blanks inherit only within this group |
| 白ピアス / White Piercing capability | Workbook **SUS, 他**; 〇 is capability, not a request for a POINT |

**Regression:** SUS430 t6 uses SS/SUS430 Nobi but SUS/他 row 11 for auto Laser **R0.5** on eligible uncalled-out outside corners ≤90°, inherited min cut-hole diameter **t/2** from SUS/他 row 10, and White Piercing **〇** from row 11. Using SS t6 Laser R2 for SUS430 is incorrect. Other unmapped alloys still require clarification.

## L10 — Approved Cu / Brass boundary at t6 (2026-09-25)

**The original Excel row-26 Laser R cell remains BLANK in the transcription below. This separately approved production override does not claim that the workbook itself printed R0.5 or 無.**

| Real thickness | Automatic Laser R at eligible uncalled-out outside corners ≤90° |
|---|---|
| `0<t≤5` mm | R0.5 from original row 25 |
| `5<t<6` mm | Approved next-higher row t6 → **R0.5** |
| `t=6` mm | **R0.5** per direct user clarification |
| `t>6` mm | **NONE**: do not add an automatic Laser R |

An explicit PDF R/C still takes priority **at that corner**, including t>6. This does not prohibit separately proven bend relief. The original row-26 minimum cut-hole **≥t**, White Piercing **×** and `※ケガキ不可` remain unchanged; do not generalize the Laser R override to other processes.

## Approved lookup algorithm

1. Lock the drawing material and thickness `t`. **SUS430 is explicitly mapped by L09: SS/SUS430/BRASS Nobi, but SUS/他 Laser R, holes and White Piercing.** Other ambiguous alloy groups without an approved mapping still require a question/FLAG.
2. Find a row containing `t` in its stated Min–Max range. A first row with blank Min covers positive t up to its Max; for AL the next blank-Min row ending at 6 covers t>0.5 through 6 (the preceding row handles t≤0.5). If several rows with open Min are candidates, choose the most specific applicable row.
3. If t falls between two explicit ranges, use the **next higher thickness row** (no interpolation). For a nonfinal row that has Min but blank Max, treat only its specified Min as explicit; for intermediate t choose the next higher row. A **last** row with a Min and no Max covers that Min and all greater thicknesses. Outside the material's defined ranges, or with no unambiguous row, ASK; do not invent a range.
4. For a BLANK **hole-capacity** cell, inherit the last nonblank hole-capacity value above it **within the same material group only**. Do not inherit Laser R or White Piercing cells; their values are row-specific.
5. Apply the approved L09 process split and L10 Cu/Brass thickness override first; then determine laser R only at corners belonging to the row's corner class. A PDF-specific R or C at that corner overrides the Excel R. Where Excel specifies R0.5/R2/R3 and PDF has no explicit R/C, bake it automatically into the actual contour; keep convex vs concave classification and do not blindly round internal notches. `R=t` bend-intersection relief is a separate feature class and must never be mistaken for material-table laser R.
6. Calculate the **effective cut diameter** from an explicit drawing Ø when present, otherwise the pilot diameter from approved thread table 7.1 for a proved tapped M feature. PIERCING arrow/note scoped to that feature family => `POINT` ByLayer regardless of capacity. PIERCING plus THROUGH HOLE => `POINT` Color 3. Ø < t/2 => `POINT` ByLayer without a capacity FLAG. Else when effective Ø is below Excel minimum => `POINT` ByLayer without a capacity FLAG; otherwise `CIRCLE` ByLayer. An ambiguous feature identity => temporary `CIRCLE` Color 6 + FLAG; geometry/position uncertainty produces a separate independent FLAG.
7. White Piercing `〇` and `×` are **machine-capability indicators**, never instructions to turn every hole into POINT; follow the explicit PDF PIERCING for the specified feature group even if worksheet is `×`, without a capacity-only FLAG. User-approved PROCESS POINT Color 3 is restricted to explicit `PIERCING + THROUGH HOLE`; other POINTs default ByLayer on Layer 0.
8. Document the selected Excel row and any upward-thickness selection for ambiguous/nonstandard thickness; preserve unrelated dimensional/customer-approval FLAGs.

## Regression examples (user-approved)

- SS t9: hole threshold t/2 = 4.5. M4 pilot Ø3.3 and M5 pilot Ø4.2 => POINT ByLayer with no capacity FLAG. M6 pilot Ø5.0 => CIRCLE if no PIERCING, assuming verified M6 and coordinates.
- SS t9 outside corner ≤90° with no explicit PDF R/C => R2 added (e.g. `055955`). SS t≤3.2 outside ≤90° => R0.5 added.
- SUS t15–16 => minimum cut hole Ø10, independent of the unconditional POINT rule for Ø < t/2.
- AL t5 => minimum cut hole 0.8t = Ø4. Ø3 with no PIERCING => POINT ByLayer with no capacity FLAG, although Ø3 is not < t/2.
- SS t19+ => laser R3 with inside/outside-corner scope as printed; ignore unexplained `※3` notation, not the R3 value.
- L09 SUS430 t6: SS Nobi, SUS/他 Laser R0.5, SUS/他 inherited min hole t/2, 白ピアス 〇 as capacity only.
- L10 Cu/Brass t6: R0.5 at eligible outside corner; t>6 NO automatic Laser R; at 5<t<6 use next-higher t6 row with R0.5.

## Scope separation

This sheet governs **hole capability and automatic material-based laser corner R only**. Nobi/bend allowance still comes from approved Nobi tables and handwritten corrections. The user-approved **ONE** Green slit in `055958` is governed by **Section 4.10**, not the automatic material Laser R table: the reference DXF has 2 LINEs + 1 local ARC R0.5 joined as one feature. Its old method/count FLAG is resolved. Special J marks and OTHER unapproved shop reliefs require their own explicit drawing evidence.
<!-- END MODULE: references/MATERIAL_RULES.md -->

---

<!-- BEGIN MODULE: skills/lispcad/features/CHAMFER_RADIUS.md -->
# LISPCAD Feature — Chamfer / Radius / Automatic Laser R

**2026-10-12 scope update (higher priority than old text):** SS t>=19 automatic R3 applies **ONLY** to the OUTER material perimeter contour, including concave corners of that contour. Never auto-round contours of inner holes/slots. Explicit customer instruction at the affected corner overrides R3. NC lead-in and pierce paths are outside CAD scope. See `references/MATERIAL_RULES.md`.


Approved calibration 520924-19, 2026-09-25. Governing table: `../../../references/MATERIAL_RULES.md`. The old V4.3 unconditional DXF-only R0.5 exclusion is SUPERSEDED when this approved table prescribes a radius.

### 4.5 Corner Filleting & Chamfer Baking

- **No global FILLET command** or global outline fillet pass: trace real topology before arithmetic.
- Classify each target by **material interior angle**: convex/outside `<180°`; concave/re-entrant `>180°`. The term `outside corner ≤90°` in the workbook describes a convex exterior corner of the stated angle; do not apply the rule to similarly drawn inner corners.
- **Order of authority per CORNER**: drawing-specific revision/red correction → explicit PDF R/C callout (with applicable quantity) → approved workbook automatic Laser R (if the PDF has NO R/C instruction for that corner). A PDF C remains a straight chamfer and must never silently become R2/R0.5. Where a PDF R/C overrides a material table at one corner, still use automatic Laser R at other eligible uncalled-out corners.

- **V4.18 C/R_SEMANTIC_LOCK — source before geometry:** Before constructing any called corner, lock the tuple `(family=R|C, value, quantity/scope, target corner class, leader/witness evidence)`. Family identity is a hard semantic input: `C` produces straight chamfer segment(s) and MUST NOT be emitted as ARC/bulge; `R` produces the proved circular radius. Numeric equality alone never makes C and R equivalent. For rotated/oblique or low-quality callouts, inspect the unrotated source/context and neighboring glyph shape before committing the family/value; if still ambiguous, FLAG instead of converting by appearance. After canonical geometry is built, independently compare this tuple back to the source; DXF read-back only proves the file matches the canonical model, not that the canonical model read the PDF correctly.

- Workbook automatic laser radii: SS up to t5 as tabulated R0.5 for exterior ≤90°; SS t6–9 R2; SUS/other or AL rows with R0.5 for exterior ≤90°; Cu/Brass t≤5 R0.5 exterior ≤90° (see L10 below for t≥6); SS t≥19 R3 only at outer material perimeter corners (convex or concave within that outer contour), excluding hole/slot contours **only when there is no conflicting PDF-specific R/C**. Honor exact row/range lookup, and `無` means no automatic radius. A blank R is UNKNOWN unless a separate approved operational override such as L10 applies. Ignore unexplained `※3` annotation but do use the workbook's R3.
- **Approved L09 process split:** SUS430 Nobi → SS/SUS430/BRASS; SUS430 Laser R, cut-hole minimum and White Piercing → workbook SUS/他. Thus SUS430 t6 eligible uncalled-out outside corner gets R0.5, NOT SS R2.
- **Approved L10 Cu/Brass:** t6 eligible uncalled-out outside corner gets R0.5; at 5<t<6 approved upward-row selection gives t6/R0.5; at t>6 apply NO automatic Laser R. PDF-explicit R/C remains higher priority. Original Excel t6 cell is still BLANK, and hole min ≥t, White Piercing × and no-Kegaki stay unchanged. These are approved operational overrides, not a rewritten worksheet.
- **Two R2 of part `055955` are required in generated geometry** under the SS t9 material-table rule; this explicitly reverses the earlier hypothesis to omit them as downstream shop additions. Never treat the old DXF-only R0.5 omission as a reason to omit a radius required by the current approved table.
- **DXF-only shop radius beyond the table:** a PDF-unmarked radius that does **not** follow an approved material rule may be omitted as a separate later shop operation only with direct user approval or an approved shop specification. Otherwise source conflict/FLAG. Do not infer an arbitrary R from thickness.
- **Callout topology and count:** a leader is evidence of target corner class, not global scope; identify the candidate equivalent corners by their material topology and count (`6-C5`, `2-C10`, `4-R5` etc). Distinct R and C families MUST match their own n-calls.
- **Geometry:** bake an explicit R into polyline tangent points/bulges (for a CCW 90° arc, `bulge=tan(90°/4)=0.41421356` with sign from actual sweep). A straight C replaces the corner with two tangent-offset vertices and bulge 0. A sharp interior U-notch stays sharp unless the PDF explicitly requires an interior R or an approved material rule for that particular class applies.
- **Relief is not Laser R:** an `R=t` relief at two oppositely folding edges whose outside extents must remain unchanged is a manufacturing clearance with distinct topology. Do not spread Laser R to reliefs. `055958` contains **ONE** confirmed Section 4.10 slit relief composed of two connected LINEs and one local ARC R0.5; the arc is not a second relief or a material-table automatic Laser R.

### Material-table validation
Record source material, thickness, chosen worksheet row, eligible corner class, R/C overrides, and each generated automatic radius; compare PDF and ground-truth DXF *after* this classification. A DXF R0.5 that matches the approved material table is expected and must not be excluded from regression comparisons.


#### V4.16 Explicit R/C family quantity closure

Before any automatic Laser-R pass, close each explicit R/C family from the source:

1. identify the actual view and callout/leader target;
2. classify the initially targeted candidate corner class as convex/outside or concave/re-entrant;
3. count that class first and verify each candidate is visibly rounded/chamfered, not sharp;
4. close the printed quantity before searching another view/corner class;
5. if quantity still does not close, inspect remaining visible candidate corners/views and their actual topology — customer drafting conventions differ, so callout text position alone is not global scope;
6. only after all explicit R/C families close may automatic material Laser R be applied to genuinely uncalled eligible corners.

Approved 044841 regression: left `4×R5` + right `4×R5` + bottom `2×R5` = **10×R5**. Replacing any of those explicit-family corners with auto R0.5 is FAIL.

#### V4.14 — width-proven semicircular notch/groove R and scoped n×m-R

Extend existing V4.12 stadium-slot end logic to a **real semicircular notch/groove BOTTOM** only where the PDF contour and dimension witnesses uniquely prove the shown groove width W is the full diameter of its half-circle: **R=W/2**. Read `n×m-R` by actual source grouping and the m eligible arc positions within each group; do not treat it as n separate shapes or borrow a nearby R callout. Independent mouth/edge radius families retain their own quantities. If width, half-circle topology, leader scope, or different inner/outer R is uncertain, FLAG rather than infer R from the picture. Directly approved regression 010421: width 6 → `2×2-R` means **4 bottom R3**, separately `2×4-R1` means **8 mouth R1**. Explicit PDF R overrides any material automatic Laser R at THAT corner.
<!-- END MODULE: skills/lispcad/features/CHAMFER_RADIUS.md -->
