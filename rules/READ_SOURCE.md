# READ_SOURCE — read the drawing, classify the source, census notes and groups (L1, always)

OCR, filenames, bbox, entity counts, symmetry and familiar shapes are search hints, never proof. Keep facts, interpretations and unresolved items apart.

## 1. Source class (exactly one per job)
| Class | When | Effect |
|---|---|---|
| `PDF_ONLY` | PDF/image only | PDF is geometry. A boxed `DATA` stamp whose DXF is absent → `DATA_EXPECTED_MISSING` when the task needs it. |
| `PDF_DATA_RAW` | customer DXF supplied with its PDF (default for PDF+DXF) | DATA = physical geometry, PDF = meaning → load `DATA_DXF.md`. |
| `TRAIN_REFERENCE` | user declares the DXF a sample/approved/training file | solve from source first; sample only audits → `REFERENCE.md`. |
| `DIRECT_EXISTING_DXF_AUDIT` | user asks to compare an existing AI DXF with a sample | DXF↔DXF first, then PDF for causes → `REFERENCE.md`. |

Job family 646 (not customer 646) expects DATA: absent → `DATA_REQUIRED_MISSING`, ask, no production geometry for it.

## 2. Read sequence
1. Map codes, pages, views; lock code, material, thickness, revision before any table lookup.
2. `pdf_views.py render` (grid) → `text --dims` (vector values, exact) → `crop --dpi 600` where witness lines/leaders/handwriting decide meaning. Scanned page: read every value twice from two crops. Close same-axis dims (70/65): ≥900 dpi, name the edge each extension line touches; after building run `overlay_check.py` (≥3 anchors, ≤1 mm).
3. Trace the real contour first (steps, notches, reliefs, R/C, openings). Census EVERY notch/cut-out/relief (bend end, box corner too): built as drawn (`SLIT_RELIEF.md` §0), cancelled (reason) or FLAG with coordinates.
4. Each used dimension → ledger row with both witness endpoints (`DATUM.md`).
5. One feature shown in several views = one source member, owned by its controlling view/face.
6. Handwritten corrections / Nobi apply only to the member the leader scopes; unclear scope = local FLAG.
7. `加工不可` / unmachinable = production blocker, not an omission.

**Projection:** read the method in the title block (`三角法` = third angle: top/bottom views above/below the main view, their edge nearest the main view is the FRONT). Web edge-on at the rear with flanges toward the viewer ⇒ main view shows the INNER face (`OUTPUT.md` dx). End tab side = thick edge-on line at the end of the top/bottom view; a rotated section cannot give left/right. Mirror a partner only when source/user proves code, axis and scope; a mirrored inside view alone is not a new code.

**Multi-page:** summary vs detailed page conflict → the detailed page wins only if it independently closes code, material/t, witnessed formed geometry and Nobi/flat arithmetic with no higher revision (`DETAILED_SOURCE_BUNDLE`); else FLAG. Merged multi-part DXF: only a user-declared or source-proved code↔cluster map (stated top-to-bottom = descending Y).

## 3. Manufacturing-note census (before any family = NO)
Record every production note (printed, handwritten, revision): `text | scope code | target/leader | candidate family | qty | value | resolution` with resolution `ROUTED | CANCELLED | IRRELEVANT_TO_MANUFACTURING | UNRESOLVED`.
- Note proves family + scope → family YES. Plausible family, unresolved scope/qty/value/location → UNKNOWN. NO only after the note is resolved elsewhere.
- `スリット` / `SLIT` → SLIT_RELIEF (custom slit, `SLIT_RELIEF.md` §1). `スリット 8` is that drawing's value, not a rule.
- A general note for uncalled corners → `CORNER_RC.md` §2 (AUTO_R, not a FLAG).

## 4. Source groups (one per callout/leader)
`group_id | family | callout | qty | leader scope | view | host face | X witnesses | Y witnesses | datum | evidence status`.
- Same family or size never merges groups; a shared X chain does not lend its Y chain.
- Close each group: callout → qty → size → X → Y → datum → host face → members. `GROUP_COUNT_CLOSURE`: a correct total with one group short and another over is FAIL.
- A detail/section view's paper position is not a coordinate; bind it to its target by its label/leader.
- Before calling a PDF/DATA/reference value a conflict, prove it is the SAME physical parameter (code, group, face, both witnesses, inside/outside, frame, units). Otherwise re-trace; never `SOURCE_CONFLICT` from two different numbers.

## 5. Revision / cancellation
Precedence (high → low): latest revision note/cloud → red handwritten correction → explicit callout → detail → section → projection → implied DXF geometry → visual estimate.
- Struck callout = cancelled (circled ② beside it = sure), all its members: draw nothing, spec `cancelled:` → ledger `CANCELED`, report note, no FLAG, can PASS. Struck tolerance/finish/chamfer (`4-C1`, `4-Ø16` stays) cancels only itself. Strike on no single callout → UNKNOWN + FLAG.

## 6. Customer
Customer = the numeric code in JOB STATISTICS only (never a Japanese name, barcode or job-family 646). Absent/unlisted → general rules, no REVIEW. `resolve_rules.py` prints that customer's notes; tools apply its structured fields. Precedence per physical parameter: source handwriting/correction > customer exception > shop table.

## 7. Census closure
Every source view, DATA member and note ends as a scoped member, an explicit drawing-only/helper/duplicate/cancelled item, or an unresolved member. A family YES/UNKNOWN with no group/member is not closed. Several barcodes / constituents ①② / weld relations in one view → `MULTI_PART.md`.

## Lessons
`regression/lessons/READ_SOURCE/` — 520709-07 (two whole Ø8H7 holes cancelled; scope only), 521027-26 (locating pin), 521030-16 (struck + ②).
