# CAD output — current template, geometry, layout and labels

Canonical input may keep `LWPOLYLINE`; saved manufacturing curves are exploded into LINE/ARC pieces. The current packaging and schema contract below applies to both new and compatible jobs.

1. **Output geometry.** Combined `*_ALL*.dxf` contains LINE, ARC, CIRCLE and approved POINT on Layer 0 (plus explicitly scoped Magenta review content under REVIEW_PREVIEW_POLICY). Individual `parts_dxf/<CODE>.dxf` contains CUT-only LINE/ARC/CIRCLE, with no POINT, BEND, KEGAKI, labels or preview. Outlines, cutouts and slots are written as separate LINE/ARC pieces with canonical ids `<entity_id>:S0001`, `:S0002`, ... Piece endpoints must meet within 0.001 mm.
2. **Source data.** PDF-derived geometry must match the drawing 100 %. Customer DXF data may be exploded into elements (XPLORE) before use, with geometry unchanged.
3. **Template.** New DXFs start from `templates/CAD_OUTPUT_TEMPLATE.dxf` (environment, DASHED linetype, dimstyles, AC1021, ANSI_1252, LTSCALE 15). Only `$INSUNITS = 4` and `$MEASUREMENT = 1` are overridden: coordinates are millimetres. The template modelspace must be empty.
4. **Dimensions.** No DIMENSION entity and no entity on layer `DIM` in any CUT output. Layer `DIM` is reserved for the checker.
5. **Face orientation.**
   - a. A part with no bend: the visible top face of the drawing is the outer face.
   - b. A marked rib, emboss or checkered face (縞板 / エンボス): the opposite face is the outer face.
   - c. 表 (omote) is the outer face; 保護面 (protective-film face) counts as 表 only when the drawing marks a protective film.
   - d. Single-code files show the outer-face view. In the combined file, a part whose PDF/DATA is drawn from the INNER (back) face gets a `dx` label (rule 7); its geometry stays exactly as drawn in the source. A part drawn from the outer face gets none. Never assume the outer face: compare the section view and the lower/side views of sibling codes of the same family (a mirrored section or flipped lower view relative to the sibling means the INNER face) before choosing `dx_label`.
   - e. A part marked 対称 / symmetric to another code (for example 059937 against 059936) is NOT a reason for `dx`. Reuse the sibling geometry and draw the mirror image directly (axis proved by the user or source; for a flat plate the axis along its length is x' = W - x), with `dx_label: false`.
6. **Combined file layout.** Parts stack top-to-bottom in job order. A cluster is its outline bounding box plus the code label 2 mm above the outline (label height 3 mm). The gap between clusters is at least **150 mm**, measured from the bottom of the upper outline to the top of the lower cluster label. Source views inside one code keep the 10 mm separation.
7. **Labels (combined file only; AI_META, non-cut).**
   - `dx`: height 20 mm, left of the outline with at least 10 mm clearance, vertically centred on the outline. Written only when the part carries `dx_label: true`, i.e. only when the part is drawn from its INNER face (rule 5d). It is not written for mirror-image (対称) parts, which are drawn mirrored directly (rule 5e). Individual CUT files never carry `dx`.
   - FLAG: one horizontal line per flag, `<CODE> FLAG: <flag text>`, height 3 mm, top-right, at least 10 mm right of the outline. The first flag starts at the outline top; each further flag sits on the next line below.
   - Individual CUT files carry no labels.
8. **Customer conflicts.** When a customer's explicit corner instruction conflicts with an automatic rule (for example SS t>=19 R3 against a customer sharp corner), set FLAG and wait for customer confirmation. Do not silently override either way.

## Individual cut orientation
Pose normalization applies only to explicitly requested individual PASS cuts: without HL choose bbox X>=Y by a 90-degree rotation if needed; with proved part-local HL grain align it parallel to X even if Y>X. Missing physical grain evidence means REVIEW and no individual PASS file. No scale/mirror or canonical/source-witness mutation. Composite remains source-readable (translation/layout only). Record the pose and inverse-read-back LINE/ARC/CIRCLE/XDATA. New jobs require V4.34 witness/grain proof; V4.31 inputs remain compatible.

## Current production packaging — combined DXF by default; individual PASS cuts only on request (no JSON output)

Normal E2E uses `tools/export_canonical_dxf.py` after canonical member validation and saved-DXF XDATA read-back. Default delivery is exactly one entire-job `<JOB>_ALL.dxf`, or `<JOB>_ALL_REVIEW_ONLY.dxf` if any code is REVIEW/FLAG/PREVIEW/VIEWS_ONLY, with all codes and warnings; no JSON output. The canonical job JSON is input only.

Only explicit `--individual-dxf` requests add `parts_dxf/<slip-no>.dxf` for independently verified PASS codes, as CUT-only LINE/ARC/CIRCLE. A different code's REVIEW never suppresses a proved PASS cut. Exclude marks, BEND, POINT, annotations, previews and source views. Lower-level `export_dxf.py` modes are compatibility only and never override this contract. All outputs derive from the same canonical geometry and require actual saved-file read-back.

## Delivery-slip identity and reference-only slip size

- **Code = 作業No on the delivery slip (CAD依頼書 / 納品書), verbatim.** The part `code` in the canonical job, the composite label and the individual file name are all the slip work number `<YY>-<serial>`, e.g. the drawing barcode `*056522*` with slip entry `26-056522` is written as `26-056522` (`parts_dxf/26-056522.dxf`), never `056522`. The `YY` year prefix changes by year; always copy the slip as printed, never derive or hard-code the prefix. When the barcode and the slip disagree, the slip wins and the mismatch is reported. `export_canonical_dxf.py` rejects non-slip codes (`SLIP_WORK_NO_FORMAT`; test/synthetic jobs only may pass `--allow-nonslip-codes`). The composite name uses the slip order number (注番), e.g. `520928-06_ALL.dxf`.
- **Slip サイズ X/Y is reference only.** The size columns on the slip are never geometry, never a datum, never a bbox/closure proof and never a reason to PASS or to override the drawing. Use them only as a plausibility cross-check of the independently solved flat; a mismatch is reported as a note, and the drawing-derived flat stays authoritative.
- **No JSON deliverable.** The exporter writes no per-code JSON. With no explicit request the only deliverable is the combined DXF; PASS-only individual DXFs are produced only when the user asks for them.

# TrainAiCad Core — CAD Output

## Executable canonical-completeness path

Normal production/review DXF emission must use `tools/export_canonical_dxf.py` with `canonical_contract: TrainAiCad-CANONICAL-V4.34` for NEW jobs (`tools/CANONICAL_INPUT_SCHEMA_V434.md`); previously approved V4.31 inputs remain readable under `tools/CANONICAL_INPUT_SCHEMA_V431.md`. Both require `references/CANONICAL_MEMBER_COMPLETENESS.md`.

Before any DXF save, persist `source_groups`, enumerable source `members`, `canonical_members`, and globally unique canonical `entity_id` values. Hard-fail when a PROVED source member has no PROVED source-backed canonical member. FLAGGED source members remain explicitly represented as PREVIEW/SOURCE_VIEW/FLAGGED_NO_GEOMETRY; a review flag never authorizes deletion of another proved member.

Do not bypass canonicalization with a hand-picked `ezdxf.modelspace()` / `saveas()` subset. `export_dxf.py` is packaging only. The wrapper stamps TRAINAICAD XDATA, saves/reopens and verifies ordered piece IDs against the manifest and full canonical coverage (§8.4). SAVED_DXF_LAYER0_ENTITY_IDS may contain several `:S0001` pieces for one canonical entity; raw counts need not match.

## 8.1 ONE independently verified canonical geometry model

Before generating any file, apply ALL current PDF-first rules: real outline topology, actual witness-line datum graph, independent quantity counts, material/thickness/handwritten evidence, approved material-table Laser R, scoped POINT/CIRCLE decisions, mid-tolerance, ID→OD rounding, Nobi, exact face/bend order, local-face→global-flat transforms, containment and bend-domain checks. A user-declared reference DXF may be used for calibration AFTER independent drawing interpretation, not as a hidden coordinate source.

Store part-local coordinates in millimeters, one record per declared drawing code, with provenance/trace records and one canonical sequence of CAD primitives. Use THIS SAME geometry for the default combined DXF, optional individual files and optional Lisp; never solve dimensions independently a second time.

Canonical job fields (new V4.34 and compatible V4.31): `canonical_contract`, `job_id`, ordered `parts`. Part fields include `code`, `material`, `thickness_mm`, `status`, independently executed `checks`, optional `flags`, mandatory `source_groups`, mandatory `canonical_members`, and ordered `entities`. Every entity has a globally unique stable `entity_id`. See the new-job V4.34 schema and compatible V4.31 base schema above.

Canonical entity representations:
- `LWPOLYLINE`: `vertices:[[x,y,bulge],...]`, `closed:true` for one CCW proved outer outline and each CW interior cutout or slot. No duplicate final vertex; no fake bounding rectangle. Bake all qualified C/R into true tangent points/bulges, no faceting.
- `CIRCLE`: `center:[x,y]`, positive `radius` for a verified cut hole or thread-pilot hole after applicable manufacturing decisions.
- `POINT`: `point:[x,y]`, actual point entity, never a tiny circle. Ordinary POINT is ByLayer; only explicitly scoped PDF PIERCING+THROUGH HOLE yields a Green POINT.
- `LINE` (start/end) and `ARC` (center/radius/start_angle/end_angle, degrees) for proven manufacturing line/relief; double bend lines DASHED and clipped to real material. The approved `055958` one Green slit comprises two LINEs + one ARC R0.5 connected end-to-end; 3 entities = 1 operation, never a universal R0.5 slit formula.
- `TEXT` only for an adjacent Magenta review warning (preview policy) or J/LJ (`role:mark`, ByLayer POINT+TEXT h10 on top edge; composite only, gate-enforced): blank Oy≤100 and Ox≥1000, L≤1500 1J+LJ, ≤2000 2J+LJ, ≤2500 3J+LJ, x=30…L−30 evenly, LJ last; labels use non-plot `AI_META`.

One manufacturing member may own multiple primitives, and multiple semantic members may share one physical contour entity when required by topology. Feature quantity is therefore closed by the source/canonical member ledgers, never by raw DXF entity count alone.

Slot source semantics must be classified first: `L_TOTAL` means actual end-to-end; `W` means end circle diameter; center distance `C` becomes `L_TOTAL=C+W`. Use one closed LWPOLYLINE with two straight tangents and two semicircular bulges of magnitude 1. Do not encode a source center distance as overall length.

## 8.2 DXF header, Layer 0 and V4.6 entity legend

Write real DXF with millimeter `$INSUNITS=4`, `$MEASUREMENT=1`, decimal `$LUNITS=2`, display-only precision `$LUPREC=2`. Preserve numeric calculation precision; do NOT truncate CAD coordinates to two decimals. Define the `DASHED` linetype. ALL actual geometry stays on Layer `0`. Only non-cut, automatically generated code/status/FLAG `TEXT` uses dedicated non-plot `AI_META`, with gray code labels or Magenta review notes.

| V4.6 feature | DXF entity | Color 62 | Linetype |
| :-- | :-- | :-- | :-- |
| Outer/inner contour and slot | LINE/ARC pieces exploded from canonical LWPOLYLINE | ByLayer (omit/256) | ByLayer |
| Verified cut circle/M pilot | CIRCLE | ByLayer | ByLayer |
| Ordinary PIERCING or capability POINT | actual POINT | ByLayer | ByLayer |
| Explicit PDF PIERCING + THROUGH HOLE | actual POINT | Green 3 | ByLayer |
| Kegaki/formed mark | LINE/ARC pieces from LINE or proved LWPOLYLINE | Red 1 | ByLayer |
| Double bend lines on material only | LINE ×2 | ByLayer | DASHED |
| Proven explicitly Green slit/relief | LINE or ARC per source | Green 3 | ByLayer |
| Non-production estimate and adjacent note | appropriate entity and TEXT | Magenta 6 | ByLayer |

Do NOT reintroduce superseded blanket DXF-only R0.5 omission, green-by-default Piasu or universal minimum-hole rules. Apply current routed material workbook and case-specific precedence in every export. A source-only feature/quantity unknown blocks production instead of inventing it.

## 8.3 Composite content record

Use the declared page-1 code order. Every code appears exactly once beside its own cluster as generated `TEXT` on non-plot `AI_META` (never a Layer-0 cut path). Record per code: code, status, bbox, XY translation, flags and machining entity counts, even without an external manifest. Review/preview handling: `references/REVIEW_PREVIEW_POLICY.md`. Legacy dual export only on explicit request.

## 8.4 Executed verification, read-back and limitations

Execute all routed validation checks for every production PASS part before serialization. A source view with no proveable flat retains explicit `VIEWS_ONLY` flags and does NOT inherit invented PASS results. PREVIEW keeps proved members exact and uncertainty local.

First run source-member → canonical-member equality. Reopen/audit the exact saved composite for mm units, approved Layer-0 geometry/properties, physical contour continuity/orientation and counts, source-cluster geometry equality by inverse XY translation, descending job order with distinct non-cut AI_META labels, and the **150 mm** minimum inter-cluster gap in rule 6. A flagged job uses REVIEW_ONLY filename/global NO CUT semantics. Do not expect saved LWPOLYLINE/bulges: compare the exact exploded LINE/ARC/CIRCLE/approved POINT geometry instead.

Verify every ordered derived piece ID and canonical member owner in TRAINAICAD XDATA against the serialization manifest; stripping the piece suffix must cover every canonical entity exactly as the exporter requires. One canonical outline may own several saved pieces. Canceled families have zero surviving manufacturing members/entities. Individual PASS cuts also require inverse-pose physical/provenance read-back; never use raw entity count as source quantity proof. Labels remain excluded from CAM toolpaths.

The lower-level exporter performs structural serialization, schema, packaging and geometry read-back checks; it never proves PDF datum/face order, missing Nobi, material selection or source-member completeness by itself. The V4.31 wrapper adds executable member/identity closure but still depends on the routed drawing interpretation and canonicalization stages being source-correct.

## 8.5 Optional request-only AutoLISP

Only if explicitly requested, generate existing approved `c:DRAW` AutoLISP and dynamic DCL (multi-select `*parts*`, temporary DCL under `TEMPPREFIX`, placement `getpoint`) from THE SAME verified canonical entities, not a second PDF coordinate solution. Initialize `INSUNITS=4`, `LUNITS=2`, `LUPREC=2`. No interactive geometry picking with FILLET/CHAMFER/SLOT/OFFSET. Optional legacy `*parts*` fields remain drawing code, material, thickness, OUTLINE, OUTER_FILLETS, CHAMFERS, BEND_LINES, CORNER_RELIEFS, INTERNAL_FILLETS, HOLES, KEGAKI_LINES and PIASUS. Legacy `(SLOTX L_TOTAL W)` / `(SLOTY L_TOTAL W)` use OVERALL slot length. Retain V4.6 Layer 0 and all color/POINT rules. Lisp is never automatic fallback when DXF generation is unavailable.

## 9. DXF-first compact dual-stage response

**Stage 1:** concise per-code barcode/material/thickness/proved flat extent table, real geometry-affecting corrections (handwritten Nobi, mid-tolerance, rounded ID→OD, table selection/material R), one aggregate PASS only for actually executed checks, and EVERY FAIL/FLAG/WARN/outstanding customer confirmation. Do not bury unproven dimensions or claim that bounding extents prove topology.

**Stage 2 (default):** link exactly ONE verified top-to-bottom composite DXF, `_ALL.dxf` when all parts PASS or `_ALL_REVIEW_ONLY.dxf` when any part remains FLAG/VIEWS_ONLY/PREVIEW. Individual DXFs require explicit request; the optional debug/compatibility manifest requires `--write-manifest` and is never a default deliverable. Generate Lisp only when explicitly requested. An audit-only request skips CAD emission. When critical topology/type/datum/bend/material is unresolved, preserve independently proved geometry under the routed review policy; when the environment cannot create or verify DXF links, report that limitation instead of inventing attachments or silently outputting Lisp.
