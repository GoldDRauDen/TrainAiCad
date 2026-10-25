# OUTPUT — canonical model, DXF package, review policy, report (L3, always)

## 1. Pipeline (never bypassed)
FLAT and single-axis BENT parts: `spec.yaml → python tools/run_job.py spec.yaml OUT/` (spec format `tools/BUILD_CANONICAL_SPEC.md`, examples `examples/flat_minimal.yaml`, `examples/bend_minimal.yaml`).
Other parts: canonical job JSON (`canonical_contract: TrainAiCad-CANONICAL-V4.34`, schema `tools/CANONICAL_INPUT_SCHEMA_V434.md` — read it only when writing JSON by hand) → `python tools/export_canonical_dxf.py job.json OUT/`.
Never write DXF with `ezdxf.modelspace()` from your own interpretation (`NO_DIRECT_DXF_FROM_INTERPRETATION`). The exporter hard-fails unless `PROVED SOURCE MEMBERS == PROVED CANONICAL MEMBERS` before save and `SAVED DXF ENTITY IDs == CANONICAL ENTITY IDs` after reopening.

Ledger contract: every manufacturing callout → `source_group` (id, family, status PROVED/FLAGGED/CANCELED, qty) with enumerable `members`; each active member → exactly one `canonical_member` (PROVED→PROVED, FLAGGED→PREVIEW or FLAGGED_NO_GEOMETRY, CANCELED→none); each Layer-0 entity has a unique `entity_id` owned by a member. Rule-derived members use `origin: DERIVED_RULE` + `controlling_rule`. One member may own several primitives; quantity closes by members, not entity count.

## 2. Package
- Default: ONE `<JOB>_ALL.dxf` if every code is PASS, else `<JOB>_ALL_REVIEW_ONLY.dxf` (all codes, warnings intact). `<JOB>` = slip order number (注番), e.g. `520928-06`. No JSON output (`--write-manifest` only for debug).
- Individual cuts only with `--individual-dxf`: `parts_dxf/<slip-no>.dxf` for verified PASS codes, CUT only (LINE/ARC/CIRCLE; no POINT/BEND/KEGAKI/labels). Another code's REVIEW never suppresses a PASS cut.
- **Code = 作業No on the delivery slip verbatim** (`26-056522`, never `056522`); slip vs barcode mismatch → slip wins, reported. Slip サイズ X/Y is a plausibility check only.

## 3. Entities (all geometry on Layer 0; template `templates/CAD_OUTPUT_TEMPLATE.dxf`, mm)
| Feature | Entity | Colour | Linetype |
|---|---|---|---|
| Outer/inner contour, slot | LINE/ARC pieces (from canonical LWPOLYLINE) | ByLayer | ByLayer |
| Cut hole, tap pilot | CIRCLE | ByLayer | ByLayer |
| PIERCING / capacity POINT | POINT | ByLayer | ByLayer |
| PIERCING + English `THROUGH HOLE` stamp | POINT | 3 Green | ByLayer |
| KEGAKI / formed mark | LINE/ARC | 1 Red | ByLayer |
| Bend (double line, material only) | LINE ×2 | ByLayer | DASHED |
| Proved Green slit/relief | LINE/ARC | 3 Green | ByLayer |
| Review estimate + note | entity + TEXT | 6 Magenta | ByLayer |
No DIMENSION entities, nothing on layer `DIM`. Code/status labels on non-plot `AI_META`. Customer DATA may be exploded with geometry unchanged.

## 4. Canonical geometry
- LWPOLYLINE `[[x,y,bulge],…]` closed, outer CCW, cut-outs CW, R/C baked as true tangent points/bulges, no faceting. CIRCLE for cut holes; real POINT (never a tiny circle).
- Slot: one closed LWPOLYLINE, two tangents + two bulges of magnitude 1 (`SLOT.md`).
- Canonical flat frame = orientation of the primary/plan view; the composite stays source-readable (translation only).
- **J/LJ marks** (composite only, ByLayer POINT + TEXT h10 on Layer 0): blank Oy≤100 and Ox≥1000; on the long straight edge as the max-Y edge (if only the bottom edge is straight, turn the part 180°; same for sibling codes); L≤1500 1J+LJ, ≤2000 2J+LJ, ≤2500 3J+LJ; first J at X1+30, LJ at X2−30 (with C5/C2: 35 / L−32), others evenly spaced, LJ last. `build_canonical` does this.

## 5. Review policy — ALWAYS DRAW, NEVER STOP
- Every code is drawn. Proved geometry exact; the uncertain item as the best source-supported estimate in Magenta (62=6) with an adjacent `FLAG:` note; part `status: PREVIEW` (`preview_reason: numeric_only_known_topology`). `REVIEW` is only `HL_DIRECTION_UNPROVED`. Questions go in the report after the DXF.
- Local FLAG: isolate the unknown; it never forces VIEWS_ONLY. Unknown hole → Magenta CIRCLE at the estimated Ø/position + FLAG, never omitted, never a capacity POINT.
- Competing topology/order/attachment → draw the best-supported one in Magenta, name the alternative. Missing Nobi → `SPLIT_FLANGE_10MM` (`BEND.md` §6). Never a bounding rectangle.
- `VIEWS_ONLY` only when no defensible flat exists after source exhaustion and the holistic challenge: draw every proved source-view member as a labelled subgroup `<CODE> VIEW <id>`, DATA curves preserved, FLAG only the unresolved relation. Unknown identity → `<CODE>?` + FLAG.
- PREVIEW / VIEWS_ONLY / FLAGGED are never PASS → composite `_ALL_REVIEW_ONLY` with the banner `CHỈ XEM XÉT - KHÔNG CẮT - CÒN MÃ CHƯA GIẢI QUYẾT`. A user's earlier QA PASS never certifies a later changed file.
- What the drawing itself settles is never a FLAG: general corner note = Laser R, sibling of a called family, bare R on a slot end = W/2, an unprinted optional label, anything measurable in the DXF. Never call an existing DXF entity unclear.
- **Notes in the DXF are Vietnamese with diacritics**: `FLAG: <nội dung>` (no repeated work code), e.g. `Kích thước ước lượng - kiểm tra bản vẽ`, `M6 hoặc M8?`. Codes, entity IDs, file names and Japanese source text stay verbatim.

## 6. Face and `dx`
- No bend: the visible top face is the outer face. Rib/emboss/checker face (縞板/エンボス) → the opposite face is outer. 表 = outer; 保護面 only when a protective film is marked. The KEGAKI face is the outer face.
- Decide inner/outer by comparing section/lower views of sibling codes; never assume outer. A part drawn from its INNER face gets `dx_label: true` (label h20, 23 mm left of the outline, vertically centred; geometry unchanged); outer face → none.
- 対称 partner: reuse the sibling geometry mirrored on the proved axis (flat plate along its length `x' = W − x`), `dx_label: false`.

## 7. Composite layout
Parts top-to-bottom in page-1 job order; code label 10 mm above the outline (h10, AI_META, once); ≥150 mm between clusters; FLAG lines h15, pitch 25, 49 mm right of the outline from its top. Source views of one code 10 mm apart.

## 8. Individual cut pose (requested PASS only)
No HL: rotate 90° so bbox X ≥ Y. Proved HL: grain along X. No mirror/scale; inverse read-back of every LINE/ARC/CIRCLE/XDATA.

## 9. Customer corner conflict
Explicit customer corner vs automatic rule (e.g. SS t≥19 R3 vs customer sharp): draw the customer corner, FLAG, ask.

## 10. Report (`<JOB>` chat report)
1. Per-code table: slip code, material, t, proved flat extent, status. 2. Geometry-affecting corrections (handwritten Nobi, mid-tolerance, ID→OD, table R, split flanges). 3. One PASS line for executed checks. 4. EVERY FAIL/FLAG/WARN. 5. Questions for the customer. 6. Total time (short). Proposed rule lessons go here, never into the repo during a job.
AutoLISP only on explicit request, generated from the same canonical entities.

## Lessons
`regression/lessons/OUTPUT/` — 521005-05 (members lost before DXF), 521015-04 (dx = inner face, 対称 mirrored), 521020-08 (Vietnamese notes), 520625-15 (draw → flag → confirm), CAD_OUTPUT_TEMPLATE_SAMPLE, DXF_SINGLE_COMPOSITE, DXF_DUAL_EXPORT.
