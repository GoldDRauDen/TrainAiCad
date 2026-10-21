# LISPCAD Core — Validation checklist (L3, before any export)

Every line is one check. **PASS Evidence Rule:** a check is PASS only when it was actually executed and succeeded; existence or plausibility of an entity is not PASS. A check that cannot be executed from the evidence is `FLAGGED`, `WARN` or `N/A`. A FAIL blocks production PASS; anything unresolved is still drawn under `references/REVIEW_PREVIEW_POLICY.md` (Magenta + Vietnamese FLAG, REVIEW). Read-back proves serialization, never source semantics.

## A. Geometry integrity
- **Closed Polyline Check:** the outer boundary closes (`P_start = P_end`). **Self-Intersection Check:** no overlapping edges or intersecting loops. **Vertex Ordering:** outer CCW, internal cutouts CW.
- **No Placeholder Bounding Rectangle Check:** a source contour with step, protrusion, recess, leg or open center is never a rectangle; right bbox with wrong topology is FAIL.
- **Feature Containment Check:** every closed hole/slot/cutout lies fully inside material unless the drawing defines an open-edge notch/slot.
- **Retained inner piece semantics:** a PDF note to retain a cut-out piece never clones a second detached cut-out.

## B. Source semantics (every used dimension and feature)
- **Source-Origin/Axis Mapping Check (V4.10):** prove each view's origin and +X/+Y from the drawing before any coordinate; record the signed source→CAD equation and an independent closure. Negative source Y is not a CAD Y: `Y=-30` from a proved top-left origin on a 138 mm view to a bottom-left CAD datum is `Y=108`, not `-30` or `88`. Missing origin/axis evidence is FLAGGED; never borrow an adjacent datum.
- **Datum Graph Connectivity Check:** every critical hole/notch/step coordinate has a connected dimension path from an identified datum (`DATUM_DIMENSION.md` §4.2.2).
- **Dimension-Type Check:** baseline, chain, step/local, overall or ordinate classified before arithmetic.
- **Dimension Endpoint Identity Check:** in crowded/parallel groups each start/end node targets the right entity type (`OUTER_EDGE`, `CONTOUR_EDGE/STEP`, `HOLE_CENTER`, …); a borrowed neighbor endpoint is FAIL.
- **Contour Topology Check:** ordered visible boundary (steps/recesses/protrusions) reproduced before numeric closure.
- **Reference-Datum Check:** parenthesized/reference dimensions keep their own extension-line datum.
- **Chain Closure Check:** a proven chain closes to the overall dimension; a closure failure is FAIL even if the polyline closes.
- **Typed witness graph (V4.34):** every proved HOLE/SLOT source member has X and Y witness traces (`tools/dimension_witness.py`); slots also need `slot_anchor_records`. Source QA inspects the crop and the physical endpoints; a self-declared `endpoint_verified=true` is not proof.
- **V4.18 SOURCE_CALLOUT_CANONICAL_CHECK:** every explicit R/C matches the source tuple `family + value + quantity/scope + corner class + leader/witness`. Source `C2` drawn as `R2`, `R3`, auto-R0.5 or a bulge is FAIL.
- **V4.18 DETAILED_SOURCE_BUNDLE conflict check:** a summary-row conflict is resolved only by a detailed page that closes the bundle in `DRAWING_READING.md` (Multi-page and clustered DATA); otherwise FLAG and draw per policy.
- **Slot-Semantics Check:** classified source length and canonical `L_TOTAL` (`features/SLOTS.md`); a center distance used as overall length (or the reverse) is FAIL.
- **Feature Family Isolation Check:** each family (`Ø5.5`, `M4→Ø3.3`, `M5→Ø4.2`, slots, cutouts…) counted and datum-traced on its own; never position one family from another's dimension.
- **V4.17 hard anti-regression gates (520929-10):** `SLOT_WITNESS_FAIL` — slot W/R, center distance and length come from the callout plus witness endpoints, never a nearby number of another chain. `MIRROR_SCOPE_FAIL` — reflection needs source/user proof of partner, axis and scope. `DATUM_WITNESS_FAIL` — a coordinate from top/right/another edge is transformed from that proved datum, never replaced by tangent/radius/bbox inference. `KEGAKI_SCOPE_FAIL` — CUT PASS never implies KEGAKI PASS; check count, endpoints, position and property; a missing required KEGAKI blocks PASS. `STALE_PREVIEW_FAIL` (QA ERROR) — once resolved, a provisional KEGAKI is regenerated Red and its Magenta flag removed.

## C. Completeness and counts
- **V4.22 SOURCE_FEATURE_COMPLETENESS Check — HARD FAIL:** build the source-active family set (CUT, HOLE/SLOT, BEND, KEGAKI, PIASU/PIERCING, SLIT/RELIEF, RIB, R/C, forming) and diff it against canonical and the serialized DXF. A family that disappears without explicit cancellation is FAIL even when contour, bbox and read-back are clean. For PDF+DATA also `SOURCE_EXHAUSTED_BEFORE_VIEWS_ONLY`: no VIEWS_ONLY before every relevant DATA view/face/primitive is harvested and FACE_GRAPH closure attempts are exhausted; semantic classification never authorizes refitting unchanged DATA curves.
- **V4.8 required cancellation and regression audit:** each callout family is ACTIVE or unequivocally CANCELED before count closure; canceled families have zero produced entities in the composite (and individual) read-back. Ambiguous/partial strike-through is FLAG, not deletion.
- **Feature Count Closure Check:** every explicit quantity (`n-Ø`, `n-M*`, `n-slot`, `n-R`, `n-C`, repeated notches) equals the generated family count; thread→pilot changes diameter, not count.
- **Connected primitives are not separate features:** count by proved topology and endpoint connectivity, not by color. The Green slit `LINE + ARC R0.5 + LINE` (`BEND_EDGE_RELIEF_90.md` §9) is feature count 1, entity count 3; R0.5 is not a universal slit rule. Truly overlapping holes become one non-self-intersecting Boolean-union contour with separate quantity closure.
- **Point/Circle semantic check:** per-feature PIERCING scope, Ø<t/2, effective pilot Ø for M, Excel threshold inheritance, ordinary POINT ByLayer vs PIERCING+THROUGH HOLE POINT Green — computed by `python tools/lookup.py hole`. Missing capacity data is never silently cuttable.
- **Laser R automatic check:** material row, eligible corner class, R0.5/R2/R3 only on otherwise uncalled corners (`python tools/lookup.py laser-r`), explicit PDF R/C precedence, independent R=t bend reliefs.

## D. Bent / multi-face parts
- **Local-Face → Flat Transform Check:** every feature on a bent face has a proven `references/BEND_DATUM_MAPPING.md` §4.2.7 transform; copying a local coordinate into the flat is FAIL.
- **Bend Sequence Check:** face order proved independently of total length (`BEND_DATUM_MAPPING.md` §4.2.8, `BEND_UNFOLD.md` §4.7).
- **Bend-Line Material-Domain Check:** bend lines exist only where material crosses the bend; split around voids.
- **V4.19 FOLD_BACK_SOURCE_REPROJECTION:** after unfold and before serialization replay the flat through the signed FACE_GRAPH; face dimensions/adjacency, bend signs, outside dimensions, feature host faces/offsets, quantities and local topology must reproduce the source. `CONSTRAINTS_CLOSED`: no unresolved owner, transform, sign/domain or competing topology remains, else REVIEW.
- **Nobi:** every bend has a recorded Nobi source (HANDWRITTEN or TABLE via `lookup.py nobi`) or a `SPLIT_FLANGE_10MM` FLAG; never a 90° row on a non-90° bend.

## E. PDF_DATA_RAW parts
- **V4.23 BIDIRECTIONAL_SOURCE_CANONICAL_QA:** saved-DXF validation comes after complete semantic DATA census, physical-family inventory and drawing-only exclusion, `SOURCE_PHYSICAL_TO_CANONICAL` completeness, `CANONICAL_TO_SOURCE_PHYSICAL` no-extra closure, per-family quantity/value/host closure, `PER_BEND_WITNESS_LEDGER` with `THICKNESS_SINGLE_USE`, material-domain BEND clipping and fold-back/reprojection. `SOURCE_REPROJECTION_PASS` needs census completeness and both diff directions, not just selected primitives mapping back.
- **V4.24 DATA_MANUFACTURING_CANONICALIZATION:** `DATA_AUTO_R_CANONICALIZATION_CHECK` — every otherwise uncalled eligible outside corner `<=90°` has the required R in canonical and serialized geometry with source-corner provenance; a sharp raw DATA vertex is not a pass; explicit source R/C wins. `DATA_TAP_NOMINAL_VALIDATION_CHECK` — for every proved `M<n>` with an identifiable DATA nominal reference, `Delta >= 0.1 mm` is `DATA_PDF_DIM_DIFF`; never compare the raw pre-hole; the nominal reference is non-cut and exactly one pilot exists per tap. `CANONICALIZATION_LEDGER_CHECK` — every entity differing from raw DATA names its source members and rule; an unrecorded extra arc/circle is FAIL. Read-back re-confirms R, pilot Ø/count and no nominal duplicate CUT, but cannot waive a failed delta or missing ledger.
- **Customer policy (2026-10-12):** take only the explicit numeric `customer_code` from the job statistics sheet; missing code → general rules without automatic REVIEW. `DATA_NO_DIM_COMPARE` waives only the generic numeric PDF/DATA mismatch gate, never feature existence, wrong/missing holes, M identity, topology, member completeness or read-back. Never use KH646 because an old job-family identifier contains 646. Machine minimum L/Z warnings are nonblocking when geometry is proved; the NC toolpath stage is deferred.

## F. Holistic engineering challenge (before canonical serialization)
Run `HOLISTIC_ENGINEERING_CHALLENGE` (`references/HOLISTIC_ENGINEERING_CHALLENGE.md`, `tools/holistic_engineering_guard.py`); on an anomaly re-open the source and re-solve.
- `SOURCE_LEDGER_PLAUSIBILITY`: census/inventory/group/member records are mutually accountable; substantial DATA with zero proved members is an anomaly unless each member is classified drawing-only/helper/duplicate/canceled.
- `PART_IDENTITY_GRAPH`: multi-code/assembly bundles close barcode/code ↔ constituent ↔ view ↔ DATA cluster; one bundle assigned to two codes is `PART_IDENTITY_COLLISION`.
- `BEND_EDGE_USAGE`: a `SHARED_BEND_EDGE_LENGTH` is never reused as `FACE_WIDTH` or `FLAT_BLANK_EXTENT` without same-parameter proof.
- `LOCAL_UNCERTAINTY`: a local FLAG cannot force VIEWS_ONLY when a defensible flat is proved. `VIEWS_ONLY_SOURCE_VIEW_COMPLETENESS`: every proved source-view member survives into the VIEWS_ONLY representation.
- `FINAL_ENGINEERING_SANITY_REVIEW`: unused views, missing owners, suspiciously simple output, untested candidates or PASS by ledger self-equality send the job back to source interpretation.
- Pair codes: `python tools/pair_consistency.py` reports no unexplained difference.
- An unresolved part names its blocker: `TRUE_SOURCE_AMBIGUITY`, `AI_INTERPRETATION_GAP`, `SOURCE_MEMBER_CENSUS_GAP`, `PART_IDENTITY_GAP`, `GEOMETRY_DECODE_GAP`, `ROUTING_COVERAGE_GAP` or `CUSTOMER_CONFIRMATION_PENDING`; an AI interpretation failure is never reported as missing customer evidence. For sample/reference audits freeze `SOURCE_ONLY_SNAPSHOT` first (`REFERENCE_EXPOSURE_FIREWALL`); a reference-only upgrade of an unresolved source claim is `POST_REFERENCE_SOURCE_REWRITE`.

## G. Manufacturing attributes and individual cuts
- **Hairline (V4.34):** a complete flat whose HL grain direction relative to the physical part is unproved is `status=REVIEW`, `review_reason=HL_DIRECTION_UNPROVED`, with full proved geometry and no individual PASS DXF, even when Excel M51 says `HL 横目`.
- SS t>=19 automatic R3 only on the outer material perimeter contour (including its concave corners), never on hole/slot contours. A clear handwritten Nobi outranks a table value; the difference is an audit record.
- Requested individual PASS cut: inverse-transform every LINE/ARC/CIRCLE from the exported pose to canonical and check IDs, radii, endpoints, topology and family counts.

## H. Feasibility advisories (never block, never move geometry)

| Parameter | Advisory threshold | Action |
| :--- | :--- | :--- |
| Minimum cut hole Ø | `MATERIAL_RULES.md` (`lookup.py hole`) | below capacity → POINT ByLayer without a capacity FLAG; unresolved table/material → Magenta CIRCLE + FLAG |
| Minimum Bridge / Web Width | hole edge to boundary ≥ t | Internal advisory only (no FLAG, no geometry change) |
| Laser Piercing Accessibility | adjacent piercings ≥ 10 mm | Internal advisory only (no FLAG, no geometry change) |
| Bend Line Collision | hole edge to bend line ≥ 2t + R_bend | Internal advisory only (no FLAG, no geometry change) |

**V4.12 shop-distance question suppression:** geometry drawn as printed is never shifted, removed or questioned for these heuristics. Mandatory PDF clearances, real self-intersection/containment, source datum, hole capacity, unproved dimensions and a demonstrated production conflict still get an actionable FLAG.

## I. Reporting the checks
All checks stay mandatory even for a short report. Show one compact validation line when all pass, plus every FAIL, FLAGGED, actionable WARN, ambiguity and customer question; no long PASS list, no exploratory narration unless asked. Brevity never hides a production risk. PREVIEW, VIEWS_ONLY and FLAGGED parts are never PASS and make the composite REVIEW_ONLY.
