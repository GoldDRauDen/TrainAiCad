## V4.35 output, layout and label rules (approved 2026-10-14)

These rules supersede the older output wording below where they conflict. Canonical input may keep `LWPOLYLINE`; every saved CUT DXF does not.

1. **Output geometry.** Combined `*_ALL*.dxf` and individual `parts_dxf/<CODE>.dxf` contain only LINE, ARC and CIRCLE (and approved POINT) on Layer 0. Outlines, cutouts and slots are written as separate LINE/ARC pieces with canonical ids `<entity_id>:S0001`, `:S0002`, ... Piece endpoints must meet within 0.001 mm.
2. **Source data.** PDF-derived geometry must match the drawing 100 %. Customer DXF data may be exploded into elements (XPLORE) before use, with geometry unchanged.
3. **Template.** New DXFs start from `templates/CAD_OUTPUT_TEMPLATE.dxf` (environment, DASHED linetype, dimstyles, AC1021, ANSI_1252, LTSCALE 15). Only `$INSUNITS = 4` and `$MEASUREMENT = 1` are overridden: coordinates are millimetres. The template modelspace must be empty.
4. **Dimensions.** No DIMENSION entity and no entity on layer `DIM` in any CUT output. Layer `DIM` is reserved for the checker.
5. **Face orientation.**
   - a. A part with no bend: the visible top face of the drawing is the outer face.
   - b. A marked rib, emboss or checkered face (縞板 / エンボス): the opposite face is the outer face.
   - c. 表 (omote) is the outer face; 保護面 (protective-film face) counts as 表 only when the drawing marks a protective film.
   - d. Single-code files show the outer-face view. In the combined file, a part whose PDF is drawn from the back face (the drawing is front-facing but the part is seen from its back) gets a `dx` label (rule 7). A part drawn from the front gets none.
6. **Combined file layout.** Parts stack top-to-bottom in job order. A cluster is its outline bounding box plus the code label 2 mm above the outline (label height 3 mm). The gap between clusters is at least **150 mm**, measured from the bottom of the upper outline to the top of the lower cluster label. Source views inside one code keep the 10 mm separation.
7. **Labels (combined file only; AI_META, non-cut).**
   - `dx`: height 20 mm, left of the outline with at least 10 mm clearance, vertically centred on the outline. Written only when the part carries `dx_label: true`. Meaning for the checker: the individual DXF of this code is symmetric (đối xứng) to the PDF view, so `dx` tells the reader that the file is drawn mirrored relative to the combined drawing. Individual CUT files never carry `dx`.
   - FLAG: one horizontal line per flag, `<CODE> FLAG: <flag text>`, height 3 mm, top-right, at least 10 mm right of the outline. The first flag starts at the outline top; each further flag sits on the next line below.
   - Individual CUT files carry no labels.
8. **Customer conflicts.** When a customer's explicit corner instruction conflicts with an automatic rule (for example SS t>=19 R3 against a customer sharp corner), set FLAG and wait for customer confirmation. Do not silently override either way.

## V4.34 orientation and composite-only export (2026-10-13)
`tools/export_canonical_dxf.py` exports ONE composite by default, without any standalone CUT DXFs (`--composite-only` is a legacy no-op). Individual PASS CUT DXFs alone are pose-normalized: if there is no proved HL, choose bounding-box X>=Y (90-degree rotate only if Y>X); with proved HL, align the source-proved part-local grain vector parallel to X even when Y>X. HL direction missing relative to the part => REVIEW and NO individual PASS file. No scale/mirror, no user-visible TEXT/BEND/POINT in standalone CUT, and no change to source-canonical coordinate records. Record orientation transform and read back transformed LINE/ARC/CIRCLE/XDATA. Composite uses the readable source orientation (translation/layout only) and remains independent of the standalone rotation. Old V4.31 canonical jobs are accepted; NEW source jobs use V4.34 to require witness and grain proof.

# Current production packaging — combined DXF by default; individual PASS cuts only on request (no JSON output)

This section supersedes inherited V4.9/V4.11 composite-only defaults below,
without changing approved geometry, material/Nobi/bend or canonical schema.
Normal E2E uses `tools/export_canonical_dxf.py`; on successful canonical
member and composite saved-DXF XDATA read-back, it writes **no JSON output**
(the canonical job JSON is an input only) and by **default delivers only the one
entire-job composite** `<JOB>_ALL.dxf` or `<JOB>_ALL_REVIEW_ONLY.dxf` with all
codes and warnings. Individual DXFs are written **only when the user explicitly
requests them** (`--individual-dxf`): then `parts_dxf/<slip-no>.dxf` for
**verified PASS only**, using analytic LINE/ARC/CIRCLE CUT primitives.
No non-cut marks, annotations, bend entities, preview or VIEWS_ONLY source
views may enter individual CUT files. A REVIEW in one code cannot downgrade
another's independent proved geometry, but the combined file always becomes
REVIEW_ONLY. Existing lower-level V4.9/dual serializations are compatibility,
not the canonical production entry point. Canonical data remain the sole
physical geometry source, and saved-DXF read-back is mandatory.

## Delivery-slip identity and reference-only slip size (V4.35, 2026-10-14)

- **Code = 作業No on the delivery slip (CAD依頼書 / 納品書), verbatim.** The part `code` in the canonical job, the composite label and the individual file name are all the slip work number `<YY>-<serial>`, e.g. the drawing barcode `*056522*` with slip entry `26-056522` is written as `26-056522` (`parts_dxf/26-056522.dxf`), never `056522`. The `YY` year prefix changes by year; always copy the slip as printed, never derive or hard-code the prefix. When the barcode and the slip disagree, the slip wins and the mismatch is reported. `export_canonical_dxf.py` rejects non-slip codes (`SLIP_WORK_NO_FORMAT`; test/synthetic jobs only may pass `--allow-nonslip-codes`). The composite name uses the slip order number (注番), e.g. `520928-06_ALL.dxf`.
- **Slip サイズ X/Y is reference only.** The size columns on the slip are never geometry, never a datum, never a bbox/closure proof and never a reason to PASS or to override the drawing. Use them only as a plausibility cross-check of the independently solved flat; a mismatch is reported as a note, and the drawing-derived flat stays authoritative.
- **No JSON deliverable.** The exporter writes no per-code JSON. With no explicit request the only deliverable is the combined DXF; PASS-only individual DXFs are produced only when the user asks for them.

# V4.33 VIEWS_ONLY completeness / reference provenance output gate

When a flat truly remains unresolved after source exhaustion and `HOLISTIC_ENGINEERING_CHALLENGE`, `VIEWS_ONLY` is an executable review output, not a report-only status. Preserve all independently proved source/orthographic view members as separate labeled subgroups under the correct code. For customer DATA, preserve the physical source curves unless an approved manufacturing canonicalization explicitly changes them. Missing proved source-view members is `VIEWS_ONLY_SOURCE_VIEW_COMPLETENESS` FAIL.

A local unresolved feature does not erase an independently proved flat; output the proved flat and isolate the local FLAG/PREVIEW.

If a sample/reference is introduced later, output/audit reporting must preserve the frozen source-only status. Sample FLAG/Magenta geometry declared pending is `CUSTOMER_CONFIRMATION_PENDING`, not approved manufacturing geometry.

# TrainAiCad Core — CAD Output

## V4.31 executable canonical-completeness path

Normal production/review DXF emission must use `tools/export_canonical_dxf.py` with `canonical_contract: TrainAiCad-CANONICAL-V4.31` as defined in `tools/CANONICAL_INPUT_SCHEMA_V431.md` and `references/CANONICAL_MEMBER_COMPLETENESS.md`.

Before any DXF save, persist `source_groups`, enumerable source `members`, `canonical_members`, and globally unique canonical `entity_id` values. Hard-fail when a PROVED source member has no PROVED source-backed canonical member. FLAGGED source members remain explicitly represented as PREVIEW/SOURCE_VIEW/FLAGGED_NO_GEOMETRY; a review flag never authorizes deletion of another proved member.

The normal production path must not bypass this contract by writing a hand-picked source subset directly to `ezdxf.modelspace()` / `saveas()`. The lower-level `tools/export_dxf.py` remains a packaging component only. After packaging, V4.31 stamps `TRAINAICAD` XDATA entity IDs into every saved Layer-0 entity, saves/reopens the exact file, and requires `CANONICAL_ENTITY_IDS == SAVED_DXF_LAYER0_ENTITY_IDS` before delivery.

## V4.12 approved local-FLAG precedence

Keep a source-proved flat even when a separate round-hole Ø or center awaits confirmation: represent only the unresolved hole dimension/position with Magenta `CIRCLE` and adjacent `Ø?`/coordinate FLAG. Never make an unknown Ø a guessed capacity POINT. Use the existing V4.11 separate labeled source views only if no defensible flat/unfold order exists. No PREVIEW can be called production PASS; the entire mixed-confidence composite stays `REVIEW ONLY — NO CUT`. Routine shop bridge/spacing/bend-proximity acceptance questions are suppressed, without weakening actual geometric containment, source tracing or material-capacity checks.

## V4.11 approved non-production provisional clusters

The default remains exactly ONE top-to-bottom code-labeled DXF. When a drawing supports a plausible but not fully proved shape, retain exact confirmed geometry and include the assumed portion in **Magenta Layer-0** with an adjacent Magenta explanatory FLAG; label the code `PREVIEW`. Truly estimated numeric values are integer-rounded. If the flat shape or bend sequence cannot be inferred responsibly, include independently proved source/orthographic views as **separate labeled subgroups** under that code and mark `VIEWS_ONLY`; do not silently omit it. Any estimate or unresolved view makes the entire combined file `*_ALL_REVIEW_ONLY.dxf` with **NO CUT**. Explicit user QA confirmation closes only its specific resolved question, and later changes require full Section 5 and saved-DXF validation. This V4.11 approval supersedes previous **numeric-only preview** constraints for non-production output, not production shape/type/datum requirements. See portable §4.4.1 and [520625-15 approved regression](../../../regression/qa/520625-15_V4_11_APPROVED.md).

**Current V4.9 user-approved packaging:** ONE top-to-bottom composite DXF, with exact code labels outside each nonoverlapping part cluster; per-code files and manifest only by explicit request. Incomplete flats remain source-view groups under the correct code; any FLAG makes the entire combined file `REVIEW_ONLY - NO CUT`. This changes only packaging, not the V4.8-approved or earlier manufacturing rules. AutoLISP remains explicit-request only.

**V4.8 upstream gate:** Write canceled source-family provenance and effective zero-count into canonical job trace, omit all deleted hole entities, and verify that the deleted group is also absent in the translated composite. No CAD serialization or DXF schema change; only user-confirmed PDF reading, counts and regression cases were approved.

## 8.1 ONE independently verified canonical geometry model

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

## 8.2 DXF header, Layer 0 and V4.6 entity legend

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

## 8.3 V4.9 mandatory single composite

Default **one DXF only**: `<JOB>_ALL.dxf` if every code has independent manufacturing PASS; otherwise `<JOB>_ALL_REVIEW_ONLY.dxf` including all codes and visible **NO CUT** annotation. Individual DXFs/manifest are NOT default and require explicit request. Preserve Stage 1 per-code status/report without delivering unnecessary individual CAD files.

Use the declared page-1 code order strictly top-to-bottom, with >=10 mm **layout-only** clearance between part/view-group geometry bboxes, no overlaps and no geometric rescaling. Every code appears exactly once beside its own cluster as generated `TEXT` on non-plot `AI_META`, not as a Layer-0 cut path. Internally record code, status, bbox, XY translation, flags and per-code machining entity counts even when the user did not request an external manifest.

For known-topology numeric-only uncertainty: preserve all proved sizes and positions, isolate an integer-rounded Magenta estimate plus adjacent Magenta FLAG note. For unknown unfold dimensions/order: output only independently proved orthographic/source views, grouped and labeled by source view under the correct code (`VIEWS_ONLY`), never a fabricated flat. If a temporary Ø is user-authorized, label it `Ø?` and treat it as review-only, not a verified hole. If there is not enough evidence even to draw a source view or assign the correct code, STOP and ask.

A single unresolved `PREVIEW`/`VIEWS_ONLY`/FLAG invalidates *production use of the entire composite*, even if other part clusters are individually correct. An explicitly requested legacy dual export may be supplied for compatible jobs but never silently substituted for the V4.9 default.

## 8.4 Executed verification, read-back and limitations

Execute all routed validation checks for every production PASS part before serialization. A source view with no proveable flat retains explicit `VIEWS_ONLY` flags and does NOT inherit invented PASS results. PREVIEW keeps proved members exact and uncertainty local.

V4.31 first runs source-member -> canonical-member equality. Then reopen/audit the ONE saved DXF for units mm, all manufacturing primitives Layer 0 and their approved properties, actual CCW/CW bulges and counts, source-cluster geometry equality by inverse XY translation, correct distinct descending-Y source-code labels on non-plot `AI_META`, >=10 mm layout gaps and explicit NO CUT filename/global note whenever a FLAG exists. Finally verify `TRAINAICAD` XDATA `ENTITY_ID` values on the exact saved Layer-0 entities equal the canonical entity-ID sequence/set. Check canceled families for zero surviving machining members/entities. Labels must be excluded from CAM toolpaths.

The lower-level exporter performs structural serialization, schema, packaging and geometry read-back checks; it never proves PDF datum/face order, missing Nobi, material selection or source-member completeness by itself. The V4.31 wrapper adds executable member/identity closure but still depends on the routed drawing interpretation and canonicalization stages being source-correct.

## 8.5 Optional request-only AutoLISP

Only if explicitly requested, generate existing approved `c:DRAW` AutoLISP and dynamic DCL (multi-select `*parts*`, temporary DCL under `TEMPPREFIX`, placement `getpoint`) from THE SAME verified canonical entities, not a second PDF coordinate solution. Initialize `INSUNITS=4`, `LUNITS=2`, `LUPREC=2`. No interactive geometry picking with FILLET/CHAMFER/SLOT/OFFSET. Optional legacy `*parts*` fields remain drawing code, material, thickness, OUTLINE, OUTER_FILLETS, CHAMFERS, BEND_LINES, CORNER_RELIEFS, INTERNAL_FILLETS, HOLES, KEGAKI_LINES and PIASUS. Legacy `(SLOTX L_TOTAL W)` / `(SLOTY L_TOTAL W)` use OVERALL slot length. Retain V4.6 Layer 0 and all color/POINT rules. Lisp is never automatic fallback when DXF generation is unavailable.

## 9. DXF-first compact dual-stage response

**Stage 1:** concise per-code barcode/material/thickness/proved flat extent table, real geometry-affecting corrections (handwritten Nobi, mid-tolerance, rounded ID→OD, table selection/material R), one aggregate PASS only for actually executed checks, and EVERY FAIL/FLAG/WARN/outstanding customer confirmation. Do not bury unproven dimensions or claim that bounding extents prove topology.

**Stage 2 (default):** link exactly ONE verified top-to-bottom composite DXF, `_ALL.dxf` when all parts PASS or `_ALL_REVIEW_ONLY.dxf` when any part remains FLAG/VIEWS_ONLY/PREVIEW. Only explicit request produces individual DXFs and manifest. Generate Lisp only when explicitly requested. An audit-only request skips CAD emission. When critical topology/type/datum/bend/material is unresolved, preserve independently proved geometry under the routed review policy; when the environment cannot create or verify DXF links, report that limitation instead of inventing attachments or silently outputting Lisp.

### V4.14 physical-geometry equivalence when auditing user DXF

An audit of already generated AI CAD against a declared customer-reference CAD compares actual manufactured curves after verified unit/part-local-frame normalization; equivalent LINE+ARC versus closed LWPOLYLINE with true bulges need NOT have identical entity types or raw entity totals. However, prove exactly matching contour topology, source family membership/counts and positions, radius/chamfer geometry, the complete unfolded part and each true bend pair clipped to material. Regression-match parts remain invariant before/after repacking and any corrections elsewhere. For NEW production DXF, the current canonical Layer-0 export contract and mandatory independent PDF/validation checks remain unchanged.
