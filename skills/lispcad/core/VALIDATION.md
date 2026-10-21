# LISPCAD Core — Validation

## V4.34 geometry-proof / manufacturing-attribute separation
A complete flat with unresolved Hairline grain **direction relative to the physical part** has `status=REVIEW`, `review_reason=HL_DIRECTION_UNPROVED`, and full proved geometry, never an invented Magenta cut or falsely passing individual DXF. This remains true even when the Excel M51 note states `HL 横目` without identifying physical part axes. Keep exact proof-backed entities in the REVIEW_ONLY composite. In V4.34 every proved HOLE/SLOT source member requires typed witness graph X/Y traces; slot members additionally require `slot_anchor_records`. Source QA must verify the crop and witness physically, not merely a self-declared boolean or closed DXF. For single PASS cut output, inverse-transform every LINE/ARC/CIRCLE from the exported pose to canonical and check entity IDs, radii, endpoints, topology and family counts. Missing evidence stays local REVIEW and prevents the affected code's standalone PASS.

## 2026-10-12 production validation precedence — customer CAD rules
For each code obtain only explicit numeric `customer_code` from the job statistics sheet. Missing code uses general rules without automatic REVIEW. A `DATA_NO_DIM_COMPARE` customer policy waives **only** the generic numeric PDF/DATA mismatch gate, never feature existence, physically wrong/missing holes, nominal M identity, topology, DATA/Geometry-JSON member completeness, or saved DXF read-back. A clear handwritten Nobi outranks a table value and table difference is an audit record, not blocking FLAG. SS t>=19 automatic R3 is only for corners on the material's **outer perimeter contour**, including concave corners of that exterior contour, never inner hole/slot contours. Machine minimum L/Z warnings are nonblocking when dimensions/geometry are independently proved. The NC toolpath stage is deferred; keep CAD PIERCING semantic rules. Never use numeric KH646 merely because the old job-family identifier contains digits 646.

# V4.33 — HOLISTIC_ENGINEERING_CHALLENGE hard gates

Before canonical serialization, run the routed holistic challenge and final sanity review.

- **SOURCE_LEDGER_PLAUSIBILITY:** source census/inventory/group/member records must be mutually accountable. Substantial physical DATA with zero proved members is an anomaly unless every physical member is explicitly classified drawing-only/helper/duplicate/canceled.
- **PART_IDENTITY_GRAPH:** multi-code / constituent / assembly source bundles must close barcode/code <-> constituent <-> source view <-> DATA cluster ownership. Duplicate whole-bundle assignment to independent codes is `PART_IDENTITY_COLLISION`.
- **BEND_EDGE_USAGE:** a `SHARED_BEND_EDGE_LENGTH` cannot be reused as `FACE_WIDTH` or `FLAT_BLANK_EXTENT` without same-physical-parameter proof.
- **LOCAL_UNCERTAINTY:** a local FLAG cannot force VIEWS_ONLY when a defensible flat is independently proved.
- **VIEWS_ONLY_SOURCE_VIEW_COMPLETENESS:** after justified source exhaustion, every independently proved source-view member required for the unresolved part must survive into the VIEWS_ONLY canonical review representation.
- **FINAL_ENGINEERING_SANITY_REVIEW:** unexplained unused views, missing downstream owners, suspiciously simple output, untested source-supported candidates or PASS by ledger self-equality return the job to source interpretation.

When a part remains unresolved, classify the blocker as `TRUE_SOURCE_AMBIGUITY`, `AI_INTERPRETATION_GAP`, `SOURCE_MEMBER_CENSUS_GAP`, `PART_IDENTITY_GAP`, `GEOMETRY_DECODE_GAP`, `ROUTING_COVERAGE_GAP`, or `CUSTOMER_CONFIRMATION_PENDING`. Do not label an AI interpretation failure as missing customer evidence.

For later sample/reference audit, freeze `SOURCE_ONLY_SNAPSHOT` before reference exposure and enforce `references/REFERENCE_EXPOSURE_FIREWALL.md`. A reference-only post hoc upgrade of a previously unresolved source claim is `POST_REFERENCE_SOURCE_REWRITE`, not source proof.

## V4.24 — DATA_MANUFACTURING_CANONICALIZATION hard gates

For every `PDF_DATA_RAW` production part, run these checks in addition to V4.23 bidirectional closure:

- **DATA_AUTO_R_CANONICALIZATION_CHECK:** enumerate otherwise uncalled eligible outside corners `<=90°`, resolve the active material/thickness row, and prove each required automatic R exists in canonical and serialized geometry. A sharp raw DATA vertex is not a pass condition. Every added/replaced R must retain source-corner provenance and an explicit material-rule canonicalization record. Explicit source R/C overrides the automatic rule at that corner.
- **DATA_TAP_NOMINAL_VALIDATION_CHECK:** for every proved `M<n>`, if DATA provides an identifiable nominal thread reference, compare that nominal diameter with `n`; `Delta >= 0.1 mm` is `DATA_PDF_DIM_DIFF`. Do not apply this nominal comparison to the raw pre-hole/pilot. Prove the nominal-reference entity is non-cut, the final effective CUT matches the approved thread-pilot table or explicit PDF override, and exactly one manufactured pilot representation exists per tap.
- **CANONICALIZATION_LEDGER_CHECK:** every manufacturing entity that differs from raw DATA because of auto-R, thread-pilot conversion or another approved rule must name its source members and controlling rule. Unchanged neighboring DATA geometry still requires source reprojection; an unrecorded extra arc/circle is FAIL.

Saved-DXF read-back must re-confirm the resulting R geometry, effective pilot diameter/count, Layer-0 semantics and absence of nominal-reference duplicate CUT. Read-back cannot waive a failed nominal delta or missing canonicalization ledger.

## V4.23 — BIDIRECTIONAL_SOURCE_CANONICAL_QA hard gate

For every `PDF_DATA_RAW` part, saved-DXF validation is downstream of: complete semantic DATA entity census; physical-family inventory and drawing-only exclusion; `SOURCE_PHYSICAL_TO_CANONICAL` completeness; `CANONICAL_TO_SOURCE_PHYSICAL` no-extra-manufacturing closure; per-family quantity/value/host closure; `PER_BEND_WITNESS_LEDGER` with `THICKNESS_SINGLE_USE`; material-domain BEND clipping; and fold-back/source reprojection.

Do not emit `SOURCE_REPROJECTION_PASS` merely because the primitives selected by the AI map back to DATA. That claim requires census completeness and both directions of the source/canonical diff. Bbox/read-back/entity existence cannot repair an upstream missing family, extra manufacturing edge or bend-witness mismatch.

## V4.22 SOURCE_FEATURE_COMPLETENESS — mandatory upstream QA

Before any export, compare the complete active source manufacturing-family inventory against the canonical model and the final serialized DXF. Every source-active family (CUT, HOLE/SLOT, BEND, KEGAKI, PIASU/PIERCING, SLIT/RELIEF, RIB, R/C/chamfer or other forming feature) must have an explicit canonical/output status. A family that disappears without an explicit source cancellation is **FAIL**, even when the outer contour, bbox and DXF read-back are otherwise clean.

For `PDF_DATA_RAW`, also enforce `SOURCE_EXHAUSTED_BEFORE_VIEWS_ONLY`: do not route a code to `VIEWS_ONLY` until all available relevant DATA views/faces/primitives have been harvested/classified and all source-supported FACE_GRAPH closure attempts have been exhausted. Semantic classification of a feature does not authorize refitting unchanged DATA curves into a simpler analytic shape. QA must include both source/DATA -> canonical -> inverse reprojection and canonical -> DXF -> read-back.

## V4.19 FOLD_BACK_SOURCE_REPROJECTION — mandatory for bent/multi-face production

After canonical unfold but **before** production DXF serialization, replay the flat through the signed FACE_GRAPH and compare/reproject against the source-proved formed constraints. PASS requires the used face dimensions/adjacency, bend signs, outside dimensions, feature host faces/local offsets, quantities and local material topology to reproduce the source. A correct flat bbox, entity count or saved-DXF read-back cannot compensate for a failed fold-back.

Also require `CONSTRAINTS_CLOSED`: no unresolved semantic owner, face transform, bend sign/domain or materially different competing topology may remain. If ambiguity remains, route to FLAG/PREVIEW/VIEWS_ONLY under existing policy.

## Preview / review status

PREVIEW, VIEWS_ONLY and FLAGGED parts are never PASS and make the composite REVIEW_ONLY: `references/REVIEW_PREVIEW_POLICY.md`. Section 5 gates remain mandatory.

## V4.8 required cancellation and regression audit

Classify each source feature-family callout as ACTIVE or unequivocally CANCELED before count closure. Require original quantity for each active family and ZERO produced entities for confirmed full-family deletions; include individual and translated composite DXF read-back. Ambiguous/partial strike-through blocks deletion and requires clarification.  Matching overall extents alone cannot PASS these checks.

## 5. Error Detection & Manufacturing Validation Engine

Before exporting ANY production DXF or optional AutoLISP, run the following automated checks:

### 5.1 Geometry & Dimension-Semantic Integrity Engine
- **Closed Polyline Check**: Outer boundary vertices must form a continuous loop that explicitly closes at $P_{\text{start}} = P_{\text{end}}$.
- **Self-Intersection Check**: Ensure no overlapping edges or intersecting outer polyline loops exist.
- **Vertex Ordering**: Outer boundaries must follow Counter-Clockwise (CCW) orientation; internal cutouts must follow Clockwise (CW) orientation.
- **V4.18 SOURCE_CALLOUT_CANONICAL_CHECK:** Before production PASS, compare every explicit R/C family in the canonical model back to the source tuple `family + value + quantity/scope + target corner class + leader/witness`. A source `C2` represented as `R2`, `R3`, auto-R0.5, ARC, or bulged radius is FAIL even if the saved DXF reopens perfectly. Read-back verifies serialization/model fidelity; it is not source-semantic verification.
- **V4.18 DETAILED_SOURCE_BUNDLE conflict check:** record whether the same-code detailed page closes the bundle defined in `DRAWING_READING.md` (Multi-page and clustered DATA); only a closed bundle resolves a summary-row conflict, otherwise FLAG and draw per `REVIEW_PREVIEW_POLICY.md`.

- **Source-Origin/Axis Mapping Check (V4.10):** For every absolute or ordinate-based feature, confirm the actual source-view origin and positive X/Y directions from drawing evidence BEFORE any DXF coordinate assignment; record its target CAD datum and signed source→CAD equation, then verify an independent edge/overall closure when available. Negative source Y is NOT a CAD Y coordinate. Transferring `Y=-30` from a proved top-left origin on a view 138 mm high to a bottom-left CAD datum MUST give `Y=108`, not `-30` or `88`. Missing origin/axis evidence is FLAGGED and prevents production PASS; do not borrow an adjacent hole/contour datum.
- **Datum Graph Connectivity Check**: Every critical hole/notch/step coordinate must have a connected dimension path from an identified datum per `DATUM_DIMENSION.md` §4.2.
- **Dimension-Type Check**: Each used dimension must be classified as baseline, chain, step/local, overall, or ordinate before arithmetic.
- **Dimension Endpoint Identity Check**: For every crowded or parallel dimension group, verify that each dimension's start/end node targets the correct entity type (`OUTER_EDGE`, `CONTOUR_EDGE/STEP`, `HOLE_CENTER`, etc.). Reusing a neighboring endpoint is a semantic FAIL.
- **Contour Topology Check**: Verify that the ordered visible boundary (including steps/recesses/protrusions) is reproduced before numerical closure. A geometrically closed but topologically wrong rectangle/step is FAIL.
- **Reference-Datum Check**: Parenthesized/reference dimensions must retain their actual extension-line datum; using the nominal value directly as a global coordinate without datum proof is FAIL.
- **Chain Closure Check**: Where an overall width/height is present, verify that the proven chain closes to the overall dimension. A closure failure is a semantic FAIL even if the CAD polyline itself is perfectly closed.
- **V4.22 SOURCE_FEATURE_COMPLETENESS Check — HARD FAIL**: Build the source-active family set before canonicalization, then diff it against canonical and serialized output. Missing an active family such as SLIT/RELIEF or KEGAKI is FAIL even if CUT/BEND are otherwise correct. Count semantic manufacturing features by proved topology/connectivity, while separately preserving unchanged DATA curve provenance; a feature may be one operation composed of many LINE/ARC primitives. For PDF+DATA, also prove source exhaustion before any `VIEWS_ONLY` status.
- **Feature Count Closure Check**: For every explicit quantity callout (`n-Ø`, `n-M*`, `n-slot`, `n-R`, `n-C`, repeated notch family, etc.), the generated family count MUST equal `n`. Thread-to-pilot conversion changes diameter representation, not the required count. Missing or extra members are FAIL, not WARN.
- **Connected primitives are not separate manufacturing features:** count by proved topology, manufacturing operation and endpoint connectivity, not by same-colored LINE/ARC entities. A Green slit made of `LINE + ARC R0.5 + LINE` meeting at endpoints (`BEND_EDGE_RELIEF_90.md` §9) is feature count 1, entity count 3; the local R0.5 is not a universal slit requirement. Common color alone never proves one feature. Truly overlapping cut holes need one non-self-intersecting Boolean-union contour with separate family quantity closure.
- **Feature Family Isolation Check**: Keep each family (`Ø5.5`, `M4→Ø3.3`, `M5→Ø4.2`, slots, cutouts, etc.) independently counted and datum-traced. Do not use one family's centerline/dimension to create or position another family without explicit evidence.
- **Local-Face → Flat Transform Check**: Every feature dimensioned on a bent face must have a proven `references/BEND_DATUM_MAPPING.md` §4.2.7 transform into global flat coordinates. Copying a local formed-face coordinate directly into the flat pattern is FAIL.
- **Bend Sequence Check**: Verify face order independently of total-length closure. Matching overall blank length does not PASS bend order. Bend coordinates must follow the proven sequence in `references/BEND_DATUM_MAPPING.md` §4.2.8 and `BEND_UNFOLD.md` §4.7.
- **Feature Containment Check**: Every closed hole/slot/internal cutout must lie fully inside the material region unless the drawing explicitly defines an open-edge notch/slot. Any closed feature wholly or partly outside the outer boundary is FAIL.
- **Bend-Line Material-Domain Check**: Bend lines may exist only where material crosses the bend. A line passing through a void, center cutout, open gap, or outside the part is FAIL; split the bend line into valid material segments when required.
- **Slot-Semantics Check**: Verify that every generated slot uses a classified source length and the canonical `L_TOTAL` semantics in `features/SLOTS.md`. A center-distance value passed as overall length (or vice versa) is FAIL.
- **No Placeholder Bounding Rectangle Check**: If the source contour contains a step, protrusion, recess, leg, or open center, a bounding rectangle is not an acceptable placeholder. Closed geometry that has the right bounding box but the wrong topology is FAIL.
- **PASS Evidence Rule**: Never mark a checklist item `PASS` merely because the generated entity exists or looks plausible. `PASS` requires that the corresponding semantic/geometric validation was actually executed and succeeded. If the check cannot be executed from available evidence, use `FLAGGED`, `WARN`, or `N/A` as the status vocabulary above allows.

- **Point/Circle semantic check (V4.4):** enforce per-feature PIERCING scope, strict Ø<t/2, effective pilot Ø for M, approved Excel threshold inheritance and ordinary POINT ByLayer vs PIERCING+THROUGH HOLE POINT Green. Missing capacity data must not silently be treated as cuttable.
- **Laser R automatic check (V4.4):** verify material row, eligible convex/concave corner class, correct R0.5/R2/R3 only on otherwise uncalled-out corners, precedence of explicit PDF R/C, and independent R=t bend reliefs.
- **Unknown numeric preview isolation (V4.4):** a known-topology estimated size/coordinate may be Magenta, integer-rounded and FLAGGED if the user wants preview output; a feature of unknown identity or invented topology cannot PASS or be output as speculative production geometry.
- **Retained inner piece semantics (V4.4):** a PDF note to retain a cut-out piece must not automatically clone a second detached cut-out.

### 5.1.1 Full Internal Verification, Minimal External Noise
- Every check in Section 5.1 remains mandatory even when the user asks for a short report.
- Do not print a long PASS checklist by default. Internally execute the checks, then expose only:
  - one compact overall validation line when all required checks pass; and
  - every `FAIL`, `FLAGGED`, actionable `WARN`, unresolved ambiguity or needed user confirmation; exclude nonblocking shop-distance-only advisories under §5.2.
- A concise report MUST NOT hide an unresolved production risk. Brevity controls presentation, not engineering rigor.
- Do not narrate exploratory reasoning, discarded hypotheses, or general sheet-metal theory unless the user asks for an audit/explanation.

### 5.2 Manufacturing Feasibility Rules

| Feasibility Parameter | Constraint Rule | Violation Action |
| :--- | :--- | :--- |
| **Minimum Cut Hole Diameter** | Use the applicable, inherited minimum from `references/MATERIAL_RULES.md` after approved thickness selection; the unconditional `Ø<t/2` POINT rule is checked before the table | Verified below-capacity hole becomes POINT ByLayer **without a capacity FLAG**; unresolved table/material becomes provisional CIRCLE Magenta + FLAG |
| **Minimum Bridge / Web Width** | Distance between hole edge & part boundary $\ge t$ | Internal advisory only (no FLAG, no geometry change) |
| **Laser Piercing Accessibility** | Distance between adjacent piercings $\ge 10\text{ mm}$ | Internal advisory only (no FLAG, no geometry change) |
| **Bend Line Collision** | Distance between hole edge & bend line $\ge 2 \times t + R_{\text{bend}}$ | Internal advisory only (no FLAG, no geometry change) |

**V4.12 shop-distance question suppression:** Treat minimum bridge/web, inter-piercing spacing and hole-to-bend proximity as optional/internal nonblocking **advisories** for geometry drawn as printed in the PDF. Do not shift/remove such geometry, block a source-faithful preview, or ask routine customer clearance acceptance solely for these heuristics. Maintain mandatory PDF-specific clearances, actual self-intersection and containment, source datum, hole-capacity rules, unproved dimensions and real demonstrated production conflicts; a genuine conflict still receives an actionable FLAG.

---

## V4.17 hard anti-regression gates — approved 520929-10

These gates operationalize existing interpretation rules and are production-blocking where stated:

- **SLOT_WITNESS_FAIL — HARD FAIL:** slot W/R, center distance and overall length must come from the actual callout plus witness endpoints. A nearby number belonging to another chain/edge may not substitute for the slot width.
- **MIRROR_SCOPE_FAIL — HARD FAIL:** never reflect a partner because codes are adjacent, sizes match, or shapes look paired. Reflection requires source/user proof of partner identity, axis/orientation and feature scope. Otherwise reconstruct each code independently.
- **DATUM_WITNESS_FAIL — HARD FAIL:** a coordinate dimension from top/right/other outside edge must be transformed from that proved source datum. Do not replace an edge-to-center witness with a tangent/radius/bbox inference.
- **KEGAKI_SCOPE_FAIL — HARD FAIL:** CUT PASS never implies KEGAKI PASS. Check marking count, segment endpoints, position and property independently. Missing required KEGAKI blocks production PASS.
- **STALE_PREVIEW_FAIL — QA ERROR:** when source/reference/user evidence resolves a KEGAKI that was previously provisional, regenerate it with normal production KEGAKI property (Red under current CAD_OUTPUT) and remove the stale Magenta uncertainty flag for that resolved feature.
