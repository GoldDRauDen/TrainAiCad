# TrainAiCad V4.7 Core — DXF-first CAD Output

**Current approved output mode:** direct DXF by default; BOTH individual and composite DXFs; optional AutoLISP on explicit request ONLY. This V4.7 change affects output/packaging, not V4.6-approved engineering, material, feature, relief, or regression logic.

## 8.1 ONE independently verified canonical geometry model

Before generating any file, apply ALL current V4.6 Section 2–7 PDF-first rules: real outline topology, actual witness-line datum graph, independent quantity counts, material/thickness/handwritten evidence, approved material-table Laser R, scoped POINT/CIRCLE decisions, mid-tolerance, ID→OD rounding, Nobi, exact face/bend order, local-face→global-flat transforms, containment and bend-domain checks. A user-declared reference DXF may be used for calibration AFTER independent drawing interpretation, not as a hidden coordinate source.

Store part-local coordinates in millimeters, one record per declared drawing code, with provenance/trace records and one canonical sequence of CAD primitives. Use THIS SAME geometry for individual DXF, translated composite DXF and optional Lisp; never solve dimensions independently a second time.

Canonical job fields: `job_id`, ordered `parts`. Part fields: `code`, `material`, `thickness_mm`, `status` (`PASS` or explicitly non-production `PREVIEW`), independently executed `checks`, optional `flags`, and ordered `entities`.

Canonical entity representations:
- `LWPOLYLINE`: `vertices:[[x,y,bulge],...]`, `closed:true` for one CCW proved outer outline and each CW interior cutout or slot. No duplicate final vertex; no fake bounding rectangle. Bake all qualified C/R into true tangent points/bulges, no faceting.
- `CIRCLE`: `center:[x,y]`, positive `radius` for a verified cut hole or thread-pilot hole *after* V4.6 decisions.
- `POINT`: `point:[x,y]`, actual point entity, never a tiny circle. Ordinary POINT is ByLayer; only explicitly scoped PDF PIERCING+THROUGH HOLE yields a Green POINT.
- `LINE` (start/end) and `ARC` (center/radius/start_angle/end_angle, degrees) for proven manufacturing line/relief; double bend lines DASHED and clipped to real material. The approved `055958` one Green slit comprises two LINEs + one ARC R0.5 connected end-to-end; 3 entities = 1 operation, never a universal R0.5 slit formula.
- `TEXT` is allowed ONLY as adjacent Magenta warning on an expressly requested numeric-only non-production preview; never add code labels to production modelspace.

Slot source semantics must be classified first: `L_TOTAL` means actual end-to-end; `W` means end circle diameter; center distance `C` becomes `L_TOTAL=C+W`. Use one closed LWPOLYLINE with two straight tangents and two semicircular bulges of magnitude 1. Do not encode a source center distance as overall length.

## 8.2 DXF header, Layer 0 and V4.6 entity legend

Write real DXF with millimeter `$INSUNITS=4`, `$MEASUREMENT=1`, decimal `$LUNITS=2`, display-only precision `$LUPREC=2`. Preserve numeric calculation precision; do NOT truncate CAD coordinates to two decimals. Define the `DASHED` linetype. ALL modelspace entities stay strictly on Layer `0`, without changing layer defaults.

| V4.6 feature | DXF entity | Color 62 | Linetype |
| :-- | :-- | :-- | :-- |
| Outer/inner contour and slot | Closed LWPOLYLINE with real bulges | ByLayer (omit/256) | ByLayer |
| Verified cut circle/M pilot | CIRCLE | ByLayer | ByLayer |
| Ordinary PIERCING or capability POINT | actual POINT | ByLayer | ByLayer |
| Explicit PDF PIERCING + THROUGH HOLE | actual POINT | Green 3 | ByLayer |
| Kegaki/formed mark | LINE or proved LWPOLYLINE | Red 1 | ByLayer |
| Double bend lines on material only | LINE ×2 | ByLayer | DASHED |
| Proven explicitly Green slit/relief | LINE or ARC per source | Green 3 | ByLayer |
| Numeric-only non-production estimate and adjacent note | appropriate entity and TEXT | Magenta 6 | ByLayer |

Do NOT reintroduce superseded V4.3 blanket DXF-only R0.5 omission, green-by-default Piasu or universal minimum-hole rules. Apply V4.6 approved material workbook and case-specific precedence in every export. A source-only feature/quantity unknown blocks production instead of inventing it.

## 8.3 Mandatory two-format DXF delivery for multi-part jobs

Deliver **both** `<JOB_ID>_<DRAWING_CODE>.dxf` for every production-PASS part in original part-local coordinates AND `<JOB_ID>_ALL.dxf` with exact translated copies of ALL PASS parts, each once. Composite places disjoint parts in the explicitly declared job-list order **top-to-bottom (descending global Y)** with at least 10 mm *layout-only* clearance between complete geometric bounding extents. This is **not** nesting, kerf, an added manufacturing dimension or a revision to source geometry. No extra production label TEXT.

Always create `<JOB_ID>_MANIFEST.json`: ordered part codes, material, thickness, PASS/FLAG status, individual filename, local geometry bbox, entity counts, per-part composite XY translation and composite bbox. Use manifest offsets to verify code→cluster mapping and composite equivalence, not heuristic visual proximity.

If the user explicitly requests a numeric-only preview on PROVEN topology, deliver separate `<JOB_ID>_<CODE>_PREVIEW.dxf` and, as needed, `<JOB_ID>_PREVIEW_ALL.dxf`, visibly Magenta with adjacent Magenta TEXT and independent numeric FLAGs. Never mix PREVIEW into production `_ALL.dxf` and never mark PREVIEW PASS. Unknown contour, feature type, bend order, critical material/datum or unsupported handwritten revision BLOCKS speculative production export.

## 8.4 Executed verification, actual DXF read-back and limitations

Perform ALL V4.6 Section 5 semantic/manufacturing checks BEFORE constructing a production-PASS canonical record. Required recorded keys: `contour_topology`, `datum`, `feature_count`, `unfold`, `containment`, `bend_domain`, `material_rules`, `slot_semantics`, each really executed PASS or genuinely nonapplicable N/A. Critical topology/datum/count/containment/material must PASS and no unresolved production FLAG may remain.

Reopen/audit each SAVED DXF: parser validity, header units, Layer 0, approved entity type/property/color/POINT hierarchy, outline closure/orientation, actual arcs/bulges, full independent feature counts, proven extents and source datum precision, closed-feature containment and bend lines clipped to material. For merged DXF verify individual-to-composite equivalence by inverse translation, global/per-part counts, original source order, no bbox overlap and manifest offsets. A mere successful file save is never PASS evidence.

The included `tools/export_dxf.py` performs **structural** schema, packaging and roundtrip checks, NOT PDF-reading, full material/datum arithmetic or complete polygonal manufacturing containment. Those require independently executed V4.6 upstream checks and ground-truth regression when available. Do not claim they ran just because JSON declares PASS.

## 8.5 Optional request-only AutoLISP

Only if explicitly requested, generate existing approved `c:DRAW` AutoLISP and dynamic DCL (multi-select `*parts*`, temporary DCL under `TEMPPREFIX`, placement `getpoint`) from THE SAME verified canonical entities, not a second PDF coordinate solution. Initialize `INSUNITS=4`, `LUNITS=2`, `LUPREC=2`. No interactive geometry picking with FILLET/CHAMFER/SLOT/OFFSET. Optional legacy `*parts*` fields remain drawing code, material, thickness, OUTLINE, OUTER_FILLETS, CHAMFERS, BEND_LINES, CORNER_RELIEFS, INTERNAL_FILLETS, HOLES, KEGAKI_LINES and PIASUS. Legacy `(SLOTX L_TOTAL W)` / `(SLOTY L_TOTAL W)` use OVERALL slot length. Retain V4.6 Layer 0 and all color/POINT rules. Lisp is never automatic fallback when DXF generation is unavailable.

## 9. DXF-first compact dual-stage response

**Stage 1:** concise per-code barcode/material/thickness/proved flat extent table, real geometry-affecting corrections (handwritten Nobi, mid-tolerance, rounded ID→OD, table selection/material R), one aggregate PASS only for actually executed checks, and EVERY FAIL/FLAG/WARN/outstanding customer confirmation. Do not bury unproven dimensions or claim that bounding extents prove topology.

**Stage 2 (default):** link the actual verified separate DXFs, merged `_ALL.dxf` and manifest; ZIP of same files is optional convenience. Clearly separate user-requested non-production `_PREVIEW` files and flags. Generate Lisp only when explicitly requested. An audit-only request skips CAD emission. When critical topology/type/datum/bend/material is unresolved, stop before speculative production files; when the environment cannot create or verify DXF links, report that limitation instead of inventing attachments or silently outputting Lisp.
