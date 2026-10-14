# TrainAiCad Core — CAD Output (current, V4.35)

Single current statement of the CAD output contract. Earlier stacked version patches (V4.8–V4.34, superseded wording) are archived in `docs/history/CAD_OUTPUT_STACKED_PRE_V4.35_REWRITE.md` and are not production authority.

## 1. Deliverables and identity

- **Default deliverable: ONE combined DXF** — `<JOB>_ALL.dxf` when every code is independent production PASS, otherwise `<JOB>_ALL_REVIEW_ONLY.dxf` (all codes, visible **REVIEW ONLY - NO CUT**). `<JOB>` is the slip order number (注番), e.g. `520928-06`.
- **No JSON output.** The canonical job JSON is an input only; the exporter writes no per-code JSON. `--write-manifest` is an explicit opt-in.
- **Individual DXFs only on explicit user request** (`tools/export_canonical_dxf.py --individual-dxf`, `individual_dxf=True`): `parts_dxf/<slip-no>.dxf` for verified PASS codes only, LINE/ARC/CIRCLE CUT primitives, no text/bend/marking/POINT/preview/source views. A REVIEW code never has an individual file and never downgrades another code's independently proved geometry, but always makes the combined file REVIEW_ONLY. `--composite-only` is a legacy no-op. AutoLISP is request-only (§8).
- **Code = 作業No on the delivery slip, verbatim** (`<YY>-<serial>`, e.g. barcode `*056522*` with slip entry `26-056522` → code `26-056522`, file `parts_dxf/26-056522.dxf`). The `YY` prefix changes yearly; copy the slip as printed, never derive or hard-code it. If barcode and slip disagree, the slip wins and the mismatch is reported. The CLI rejects other codes (`SLIP_WORK_NO_FORMAT`; synthetic/test jobs only: `--allow-nonslip-codes`).
- **Slip サイズ X/Y is reference only.** Never geometry, datum, bbox/closure proof, or a reason to PASS/override the drawing; use only as a plausibility cross-check of the independently solved flat (a mismatch is a note; the drawing-derived flat stays authoritative).

## 2. Canonical entry path (V4.31/V4.34)

Normal production/review DXF emission uses `tools/export_canonical_dxf.py` with `canonical_contract: TrainAiCad-CANONICAL-V4.34` (new jobs; V4.31 jobs remain valid) per `tools/CANONICAL_INPUT_SCHEMA_V434.md` / `tools/CANONICAL_INPUT_SCHEMA_V431.md` and `references/CANONICAL_MEMBER_COMPLETENESS.md`.

Before any DXF save, persist `source_groups`, enumerable source `members`, `canonical_members` and globally unique `entity_id`s. Hard-fail when a PROVED source member has no PROVED source-backed canonical member. FLAGGED members stay explicit as PREVIEW/SOURCE_VIEW/FLAGGED_NO_GEOMETRY; a review flag never authorizes deleting another proved member. Never bypass the contract by writing an ad-hoc subset to `ezdxf.modelspace()`/`saveas()`; `tools/export_dxf.py` is a packaging component only. After packaging, `TRAINAICAD` XDATA entity IDs are stamped into every saved Layer-0 entity, the exact file is reopened, and `CANONICAL_ENTITY_IDS == SAVED_DXF_LAYER0_ENTITY_IDS` is required before delivery. Canceled families (V4.8): write canceled provenance and effective zero-count into the job trace, emit no deleted entities, and verify absence in the saved composite.

## 3. Output geometry and template (V4.35)

1. Combined and individual DXFs contain only LINE, ARC and CIRCLE (and approved POINT) on Layer 0. Outlines, cutouts and slots are separate LINE/ARC pieces with canonical ids `<entity_id>:S0001`, `:S0002`, ... Piece endpoints meet within 0.001 mm. Canonical input may keep `LWPOLYLINE`.
2. PDF-derived geometry must match the drawing 100 %. Customer DXF data may be exploded (XPLORE) before use, geometry unchanged.
3. New DXFs start from `templates/CAD_OUTPUT_TEMPLATE.dxf` (environment, DASHED, dimstyles, AC1021, ANSI_1252, LTSCALE 15); only `$INSUNITS = 4`, `$MEASUREMENT = 1` are overridden. The template modelspace must be empty.
4. No DIMENSION entity and no entity on layer `DIM` in any CUT output (`DIM` is reserved for the checker).
5. **Face orientation.** (a) No-bend part: the visible top face is the outer face. (b) Marked rib/emboss/checkered face (縞板/エンボス): the opposite face is outer. (c) 表 (omote) is outer; 保護面 counts as 表 only when the drawing marks a protective film. (d) Single-code files show the outer-face view; in the combined file a part whose PDF is drawn from its back face gets a `dx` label (§5).
6. **Pose of individual PASS cuts (V4.34).** Without proved HL: bounding box X>=Y (90° rotation only if Y>X). With proved HL: source-proved part-local grain vector parallel to X. HL direction missing relative to the part → `REVIEW` (`HL_DIRECTION_UNPROVED`), no individual file. No scale/mirror; record the transform and read back transformed LINE/ARC/CIRCLE/XDATA. The combined file keeps the readable source orientation (translation/layout only).
7. **Customer conflicts.** An explicit customer corner instruction that conflicts with an automatic rule (e.g. SS t>=19 R3 vs customer sharp corner) → FLAG and wait for confirmation; never silently override either way.

## 4. Combined-file layout

Codes stack top-to-bottom in slip/job order. A cluster is its outline bounding box plus the code label 2 mm above the outline (label height 3 mm). The gap **between code clusters is at least 150 mm**, measured from the bottom of the upper outline to the top of the lower cluster label. **Within one code**, independent source views keep at least **10 mm** separation (part-local geometry). No overlaps, no geometric rescaling. Every code appears exactly once as generated `TEXT` on non-plot `AI_META`, never as Layer-0 cut geometry. Internally record code, status, bbox, XY translation, flags and per-code entity counts even when no external manifest is requested.

## 5. Labels (combined file only; `AI_META`, non-cut)

- `dx`: height 20 mm, left of the outline with at least 10 mm clearance, vertically centred; written only when the part carries `dx_label: true`. It tells the checker the individual DXF of this code is mirrored (đối xứng) relative to the combined drawing. Individual CUT files never carry `dx` or any label.
- FLAG: one horizontal line per flag, `<CODE> FLAG: <flag text>`, height 3 mm, top-right, at least 10 mm right of the outline; the first flag starts at the outline top, each further flag on the next line below.

## 6. Status policy (local FLAG, PREVIEW, VIEWS_ONLY)

- **Local FLAG precedence (V4.12).** Keep a source-proved flat even when a separate round-hole Ø or centre awaits confirmation: only the unresolved dimension/position is a Magenta `CIRCLE` plus adjacent `Ø?`/coordinate FLAG; never a guessed capacity POINT. Routine shop bridge/spacing/bend-proximity acceptance questions are suppressed without weakening geometric containment, source tracing or material-capacity checks.
- **PREVIEW (V4.11).** Known topology with numeric uncertainty only: keep exact confirmed geometry, put the assumed portion in Magenta Layer 0 with an adjacent Magenta FLAG note, label the code `PREVIEW`; truly estimated values are integer-rounded. Never production PASS.
- **VIEWS_ONLY (V4.11/V4.33).** When the flat shape or bend sequence cannot be inferred after source exhaustion and `HOLISTIC_ENGINEERING_CHALLENGE`, output independently proved source/orthographic views as separate labeled subgroups under the correct code (`VIEWS_ONLY`), never a fabricated flat; preserve ALL independently proved source-view members (missing members = `VIEWS_ONLY_SOURCE_VIEW_COMPLETENESS` FAIL; customer DATA keeps its physical source curves unless an approved manufacturing canonicalization changes them). A local unresolved feature never erases an independently proved flat. A temporary user-authorized Ø is labeled `Ø?` and is review-only. If evidence is insufficient even to draw a source view or assign the code, STOP and ask.
- Any PREVIEW/VIEWS_ONLY/FLAG makes the entire combined file `*_ALL_REVIEW_ONLY.dxf` with **NO CUT**, even if other clusters are individually correct. Explicit user QA confirmation closes only its specific question; later changes require full validation and saved-DXF read-back.
- **Slots.** Classify source semantics first: `L_TOTAL` = actual end-to-end, `W` = end-circle diameter, centre distance `C` → `L_TOTAL = C + W`. One closed LWPOLYLINE with two straight tangents and two semicircular bulges of magnitude 1.

## 7. Executed verification and read-back

Execute all routed validation checks for every production PASS part before serialization. A source view with no proveable flat keeps explicit `VIEWS_ONLY` flags and inherits no invented PASS. Source-member → canonical-member equality runs first. Then reopen/audit the saved combined DXF: units mm, all manufacturing primitives on Layer 0 with approved properties, actual CCW/CW bulges and counts, source-cluster geometry equality by inverse XY translation, distinct descending-Y code labels on `AI_META`, the §4 gaps, and the explicit NO CUT filename/global note whenever a FLAG exists; finally verify `TRAINAICAD` XDATA `ENTITY_ID`s equal the canonical entity-ID set. When individual DXFs are requested, inverse-transform each exported pose to canonical and check ids, radii, endpoints, topology and family counts. Check canceled families have zero surviving entities. Labels are excluded from CAM.

The exporters perform structural serialization, schema and geometry read-back only; they never prove PDF datum/face order, Nobi, material selection or member completeness. Those depend on source-correct interpretation and independent QA.

## 8. Canonical geometry model and entity legend

### 8.1 ONE independently verified canonical geometry model

Before generating any file, apply ALL current PDF-first rules: real outline topology, actual witness-line datum graph, independent quantity counts, material/thickness/handwritten evidence, approved material-table Laser R, scoped POINT/CIRCLE decisions, mid-tolerance, ID→OD rounding, Nobi, exact face/bend order, local-face→global-flat transforms, containment and bend-domain checks. A user-declared reference DXF may be used for calibration AFTER independent drawing interpretation, not as a hidden coordinate source.

Store part-local coordinates in millimeters, one record per declared drawing code, with provenance/trace records and one canonical sequence of CAD primitives. Use THIS SAME geometry for the default combined DXF, optional individual files and optional Lisp; never solve dimensions independently a second time.

V4.31 canonical job fields: `canonical_contract`, `job_id`, ordered `parts`. Part fields include `code`, `material`, `thickness_mm`, `status`, independently executed `checks`, optional `flags`, mandatory `source_groups`, mandatory `canonical_members`, and ordered `entities`. Every entity has a globally unique stable `entity_id`. See `tools/CANONICAL_INPUT_SCHEMA_V431.md`.

Canonical entity representations:
- `LWPOLYLINE`: `vertices:[[x,y,bulge],...]`, `closed:true` for one CCW proved outer outline and each CW interior cutout or slot. No duplicate final vertex; no fake bounding rectangle. Bake all qualified C/R into true tangent points/bulges, no faceting.
- `CIRCLE`: `center:[x,y]`, positive `radius` for a verified cut hole or thread-pilot hole after applicable manufacturing decisions.
- `POINT`: `point:[x,y]`, actual point entity, never a tiny circle. Ordinary POINT is ByLayer; only explicitly scoped PDF PIERCING+THROUGH HOLE yields a Green POINT.
- `LINE` (start/end) and `ARC` (center/radius/start_angle/end_angle, degrees) for proven manufacturing line/relief; double bend lines DASHED and clipped to real material. The approved `055958` one Green slit comprises two LINEs + one ARC R0.5 connected end-to-end; 3 entities = 1 operation, never a universal R0.5 slit formula.
- `TEXT` is allowed only for an adjacent Magenta review warning in the routed preview policy; code/status labels are generated on non-plot `AI_META` rather than being cut geometry.

One manufacturing member may own multiple primitives, and multiple semantic members may share one physical contour entity when required by topology. Feature quantity is therefore closed by the source/canonical member ledgers, never by raw DXF entity count alone.

Slot source semantics must be classified first: `L_TOTAL` means actual end-to-end; `W` means end circle diameter; center distance `C` becomes `L_TOTAL=C+W`. Use one closed LWPOLYLINE with two straight tangents and two semicircular bulges of magnitude 1. Do not encode a source center distance as overall length.

### 8.2 DXF header, Layer 0 and entity legend

Write real DXF with millimeter `$INSUNITS=4`, `$MEASUREMENT=1`, decimal `$LUNITS=2`, display-only precision `$LUPREC=2`. Preserve numeric calculation precision; do NOT truncate CAD coordinates to two decimals. Define the `DASHED` linetype. ALL actual geometry stays on Layer `0`. Only non-cut, automatically generated code/status/FLAG `TEXT` uses dedicated non-plot `AI_META`, with gray code labels or Magenta review notes.

| V4.6 feature | DXF entity | Color 62 | Linetype |
| :-- | :-- | :-- | :-- |
| Outer/inner contour and slot | LINE/ARC pieces exploded from canonical LWPOLYLINE (V4.35) | ByLayer (omit/256) | ByLayer |
| Verified cut circle/M pilot | CIRCLE | ByLayer | ByLayer |
| Ordinary PIERCING or capability POINT | actual POINT | ByLayer | ByLayer |
| Explicit PDF PIERCING + THROUGH HOLE | actual POINT | Green 3 | ByLayer |
| Kegaki/formed mark | LINE or proved LWPOLYLINE | Red 1 | ByLayer |
| Double bend lines on material only | LINE ×2 | ByLayer | DASHED |
| Proven explicitly Green slit/relief | LINE or ARC per source | Green 3 | ByLayer |
| Non-production estimate and adjacent note | appropriate entity and TEXT | Magenta 6 | ByLayer |

Do NOT reintroduce superseded blanket DXF-only R0.5 omission, green-by-default Piasu or universal minimum-hole rules. Apply current routed material workbook and case-specific precedence in every export. A source-only feature/quantity unknown blocks production instead of inventing it.

### 8.3 Optional request-only AutoLISP

Only if explicitly requested, generate existing approved `c:DRAW` AutoLISP and dynamic DCL (multi-select `*parts*`, temporary DCL under `TEMPPREFIX`, placement `getpoint`) from THE SAME verified canonical entities, not a second PDF coordinate solution. Initialize `INSUNITS=4`, `LUNITS=2`, `LUPREC=2`. No interactive geometry picking with FILLET/CHAMFER/SLOT/OFFSET. Optional legacy `*parts*` fields remain drawing code, material, thickness, OUTLINE, OUTER_FILLETS, CHAMFERS, BEND_LINES, CORNER_RELIEFS, INTERNAL_FILLETS, HOLES, KEGAKI_LINES and PIASUS. Legacy `(SLOTX L_TOTAL W)` / `(SLOTY L_TOTAL W)` use OVERALL slot length. Retain V4.6 Layer 0 and all color/POINT rules. Lisp is never automatic fallback when DXF generation is unavailable.

## 9. Compact dual-stage response

**Stage 1:** concise per-code slip work-number/material/thickness/proved flat extent table, real geometry-affecting corrections (handwritten Nobi, mid-tolerance, rounded ID→OD, table selection/material R), one aggregate PASS only for actually executed checks, and EVERY FAIL/FLAG/WARN/outstanding customer confirmation. Do not bury unproven dimensions or claim bounding extents prove topology.

**Stage 2 (default):** link exactly ONE verified combined DXF. Individual DXFs, manifest and Lisp only on explicit request. An audit-only request skips CAD emission. If critical topology/type/datum/bend/material is unresolved, preserve independently proved geometry under §6; if the environment cannot create or verify DXF links, report that instead of inventing attachments or silently outputting Lisp.

### V4.14 physical-geometry equivalence when auditing user DXF

An audit of already generated AI CAD against a declared customer-reference CAD compares actual manufactured curves after verified unit/part-local-frame normalization; equivalent LINE+ARC versus closed LWPOLYLINE with true bulges need NOT have identical entity types or raw entity totals. However, prove exactly matching contour topology, source family membership/counts and positions, radius/chamfer geometry, the complete unfolded part and each true bend pair clipped to material. Regression-match parts remain invariant before/after repacking and any corrections elsewhere. For NEW production DXF, the current canonical Layer-0 export contract and mandatory independent PDF/validation checks remain unchanged.
