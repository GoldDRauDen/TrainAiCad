# CAD output — packaging, template, geometry, layout and labels

This file is the single owner of the DXF packaging contract; other files point here.

## 1. Packaging (one owner)

- **Exporter.** Normal production/review DXF goes through `tools/export_canonical_dxf.py` with `canonical_contract: TrainAiCad-CANONICAL-V4.34` for NEW jobs (`tools/CANONICAL_INPUT_SCHEMA_V434.md`); approved V4.31 inputs stay readable (`tools/CANONICAL_INPUT_SCHEMA_V431.md`). Both require `references/CANONICAL_MEMBER_COMPLETENESS.md`. Never bypass canonicalization with a hand-picked `ezdxf.modelspace()` / `saveas()` subset; `export_dxf.py` is packaging/compatibility only and never overrides this contract.
- **Default deliverable:** exactly one entire-job `<JOB>_ALL.dxf` when every code is PASS, otherwise `<JOB>_ALL_REVIEW_ONLY.dxf` (any REVIEW/FLAG/PREVIEW/VIEWS_ONLY) with all codes and warnings. No JSON output: the canonical job JSON is input only; a debug manifest needs `--write-manifest`; legacy dual export only on explicit request.
- **Individual cuts only on explicit request** (`--individual-dxf`): `parts_dxf/<slip-no>.dxf` for independently verified PASS codes, CUT-only LINE/ARC/CIRCLE — no POINT, BEND, KEGAKI, labels, preview or source views. A different code's REVIEW never suppresses a proved PASS cut, but always makes the composite REVIEW_ONLY.
- **Before save** persist `source_groups`, enumerable source `members`, `canonical_members` and globally unique `entity_id`s. Hard-fail when a PROVED source member has no PROVED source-backed canonical member. FLAGGED members stay represented as PREVIEW/SOURCE_VIEW/FLAGGED_NO_GEOMETRY; a review flag never authorizes deleting another proved member.
- **After save** the wrapper stamps TRAINAICAD XDATA, reopens the file and verifies ordered piece IDs (`<entity_id>:S0001`, `:S0002`, …) against the manifest and full canonical coverage; one canonical entity may own several pieces, so raw counts need not match. All outputs derive from the same canonical geometry.

## 2. Delivery-slip identity and reference-only slip size

- **Code = 作業No on the delivery slip (CAD依頼書 / 納品書), verbatim.** The canonical `code`, composite label and individual file name are the slip work number `<YY>-<serial>`: drawing barcode `*056522*` with slip entry `26-056522` is written `26-056522` (`parts_dxf/26-056522.dxf`), never `056522`. Copy the `YY` prefix as printed, never derive it. Barcode/slip disagreement: the slip wins and the mismatch is reported. `export_canonical_dxf.py` rejects non-slip codes (`SLIP_WORK_NO_FORMAT`; test/synthetic jobs only may pass `--allow-nonslip-codes`). The composite name uses the slip order number (注番), e.g. `520928-06_ALL.dxf`.
- **Slip サイズ X/Y is reference only:** never geometry, datum, bbox/closure proof or a reason to PASS or override the drawing. Use it only as a plausibility cross-check; a mismatch is a report note and the drawing-derived flat stays authoritative.

## 3. Template, header and entity legend

- New DXFs start from `templates/CAD_OUTPUT_TEMPLATE.dxf` (environment, DASHED, dimstyles, AC1021); override only `$INSUNITS=4`, `$MEASUREMENT=1` (mm). Header: decimal `$LUNITS=2`, display-only `$LUPREC=2`; never truncate coordinates. Sample spec: `regression/export/CAD_OUTPUT_TEMPLATE_SAMPLE.md`.
- No DIMENSION entity and nothing on layer `DIM` in any CUT output (`DIM` is reserved for the checker).
- PDF-derived geometry matches the drawing 100 % after the routed manufacturing decisions. Customer DXF data may be exploded (XPLORE) with geometry unchanged.
- All real geometry is on Layer `0`; outlines, cutouts and slots are saved as LINE/ARC pieces whose endpoints meet within 0.001 mm. Only non-cut generated code/status/FLAG text uses non-plot `AI_META`.

| Feature | DXF entity | Color 62 | Linetype |
| :-- | :-- | :-- | :-- |
| Outer/inner contour and slot | LINE/ARC pieces exploded from canonical LWPOLYLINE | ByLayer | ByLayer |
| Verified cut circle/M pilot | CIRCLE | ByLayer | ByLayer |
| Ordinary PIERCING or capability POINT | actual POINT | ByLayer | ByLayer |
| Explicit PDF PIERCING + THROUGH HOLE | actual POINT | Green 3 | ByLayer |
| Kegaki/formed mark | LINE/ARC pieces | Red 1 | ByLayer |
| Double bend lines on material only | LINE ×2 | ByLayer | DASHED |
| Proven explicitly Green slit/relief | LINE or ARC per source | Green 3 | ByLayer |
| Review estimate and adjacent note | entity + TEXT | Magenta 6 | ByLayer |

Apply the current material workbook (`python tools/lookup.py laser-r` / `hole`) and case-specific precedence in every export; do not reintroduce a blanket rule that drops DXF-only R0.5, makes every Piasu green or imposes a universal minimum hole.

## 4. Canonical model (one geometry for every output)

Before generating any file apply all routed PDF-first rules (outline topology, witness datum graph, quantity counts, material/thickness/handwriting, Laser R, POINT/CIRCLE, mid-tolerance, ID→OD, Nobi, face/bend order, local-face→flat transforms, containment, bend domain). A user-declared reference DXF may calibrate only AFTER independent interpretation, never as a hidden coordinate source. Store part-local mm coordinates, one record per code, with provenance, and use THIS SAME geometry for the composite, optional individual files and optional Lisp.

Job fields: `canonical_contract`, `job_id`, ordered `parts`; part fields `code`, `material`, `thickness_mm`, `status`, executed `checks`, optional `flags`, mandatory `source_groups`, `canonical_members`, ordered `entities`, each with a stable unique `entity_id`.

- `LWPOLYLINE`: `vertices:[[x,y,bulge],...]`, `closed:true`, one CCW outer outline and CW cutouts/slots; no duplicate final vertex; no fake bounding rectangle; qualified C/R baked as true tangent points/bulges, no faceting.
- `CIRCLE`: `center`, positive `radius`, for a verified cut hole or thread pilot.
- `POINT`: real point entity, never a tiny circle; ByLayer except explicitly scoped PIERCING+THROUGH HOLE (Green).
- `LINE` / `ARC` (degrees) for proven manufacturing lines/reliefs; double bend lines DASHED and clipped to real material. The approved `055958` Green slit is two LINEs + one ARC R0.5 joined end-to-end: 3 entities = 1 operation, not a universal slit formula.
- `TEXT` only for an adjacent Magenta review note (Vietnamese, `REVIEW_PREVIEW_POLICY.md`) or J/LJ marks (`role:mark`, ByLayer POINT+TEXT h10 on the long straight edge as top (max-Y) edge; if only the bottom edge is straight (notches/slope on top) turn the part 180°, same rule for sibling codes; composite only): blank Oy≤100 and Ox≥1000; L≤1500 1J+LJ, ≤2000 2J+LJ, ≤2500 3J+LJ; first J at X1+30, LJ at X2−30 (X1/X2 = ends of the max-Y edge; with C5/C2 use 35/L−32), others evenly spaced, TEXT on Layer 0 at the POINT, LJ last.
- One manufacturing member may own several primitives and several members may share one contour; quantity closes by the member ledgers, never by raw entity count.
- Slots: classify the source first — `L_TOTAL` is end-to-end, `W` the end-circle Ø, a center distance `C` gives `L_TOTAL=C+W`; one closed LWPOLYLINE with two tangents and two semicircular bulges of magnitude 1.

## 5. Face orientation and `dx`

- a. A part with no bend: the visible top face of the drawing is the outer face.
- b. A marked rib, emboss or checkered face (縞板 / エンボス): the opposite face is the outer face.
- c. 表 (omote) is the outer face; 保護面 (protective-film face) counts as 表 only when the drawing marks a protective film.
- d. Single-code files: outer-face view. In the combined file, a part whose PDF/DATA is drawn from the INNER (back) face gets a `dx` label; geometry stays as drawn; an outer-face part gets none. Never assume the outer face: compare section and lower/side views of sibling codes of the same family (a mirrored section/flipped lower view vs the sibling means INNER) before choosing `dx_label`. The KEGAKI face is the OUTER face: KEGAKI on the drawn face means no `dx`.
- e. A part marked 対称 / symmetric to another code (e.g. 059937 against 059936) is NOT a reason for `dx`. Reuse the sibling geometry and draw the mirror image directly (axis proved by user or source; for a flat plate along its length x' = W - x), with `dx_label: false`.
- `dx` label: height 20 mm, 23 mm left of the outline, centred vertically, written only when the part carries `dx_label: true`, i.e. only when the part is drawn from its INNER face. Never for mirror-image (対称) parts and never in individual CUT files.

## 6. Combined file layout and labels

- Parts stack top-to-bottom in the declared page-1 job order. A cluster is its outline bbox plus the code label 10 mm above the outline (height 10 mm, non-plot `AI_META`, exactly once per code). Gap between clusters ≥ **150 mm**, from the bottom of the upper outline to the top of the lower cluster label. Source views of one code stay 10 mm apart.
- FLAG lines: `FLAG: <Vietnamese text>` (no repeated work code), height 15 mm, pitch 25 mm, top-right, 49 mm right of the outline; first flag at the outline top, each further flag on the next line below.
- Record per code: code, status, bbox, XY translation, flags and machining entity counts. Individual CUT files carry no labels.

## 7. Individual cut orientation (only for requested PASS cuts)

Without HL choose bbox X≥Y by a 90° rotation if needed; with proved part-local HL grain align it with X even if Y>X. Missing physical grain evidence means REVIEW and no individual PASS file. No scale/mirror and no canonical/source-witness mutation; the composite stays source-readable (translation/layout only). Record the pose and inverse-read-back LINE/ARC/CIRCLE/XDATA.

## 8. Executed verification and read-back

- Execute all routed checks before serialization. A source view with no proveable flat keeps explicit `VIEWS_ONLY` flags and inherits no PASS; PREVIEW keeps proved members exact.
- First source-member → canonical-member equality. Then reopen the exact saved composite: mm units, Layer-0 geometry/properties, contour continuity/orientation and counts, cluster geometry equality by inverse XY translation, job order with distinct AI_META labels, the 150 mm gap, REVIEW_ONLY filename/NO CUT semantics for a flagged job. Compare exploded LINE/ARC/CIRCLE/POINT, not LWPOLYLINE bulges.
- Verify every derived piece ID and member owner in XDATA; stripping the piece suffix must cover every canonical entity. Canceled families have zero surviving entities. Individual PASS cuts also need inverse-pose read-back. Labels stay out of CAM toolpaths.
- The exporter proves serialization and member/identity closure; it never proves PDF datum/face order, Nobi, material selection or source-member completeness by itself.

## 9. Customer conflicts

When a customer's explicit corner instruction conflicts with an automatic rule (e.g. SS t>=19 R3 against a customer sharp corner), draw the explicit customer corner, set FLAG and list the question for customer confirmation (REVIEW). Do not silently override either way.

## 10. Optional request-only AutoLISP

Only if explicitly requested, generate the approved `c:DRAW` AutoLISP and dynamic DCL (multi-select `*parts*`, temporary DCL under `TEMPPREFIX`, placement `getpoint`) from THE SAME canonical entities. Initialize `INSUNITS=4`, `LUNITS=2`, `LUPREC=2`. No interactive FILLET/CHAMFER/SLOT/OFFSET picking. Legacy `*parts*` fields: drawing code, material, thickness, OUTLINE, OUTER_FILLETS, CHAMFERS, BEND_LINES, CORNER_RELIEFS, INTERNAL_FILLETS, HOLES, KEGAKI_LINES, PIASUS; `(SLOTX L_TOTAL W)` / `(SLOTY L_TOTAL W)` use OVERALL slot length. Lisp is never an automatic fallback when DXF generation is unavailable.

## 11. Report

- **Stage 1:** concise per-code table (barcode/slip code, material, thickness, proved flat extent, status), real geometry-affecting corrections (handwritten Nobi, mid-tolerance, ID→OD, table/material R, split flanges), one aggregate PASS line only for executed checks, then EVERY FAIL/FLAG/WARN and the list of questions for the customer. Never claim that bbox proves topology.
- **Stage 2:** the one verified composite DXF (`_ALL` or `_ALL_REVIEW_ONLY`). An audit-only request skips CAD emission. When the environment cannot create or verify DXF, report that limitation instead of inventing attachments or silently outputting Lisp.
