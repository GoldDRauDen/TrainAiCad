# 11 — VALIDATION / CANONICAL / DXF EXPORT | Production rules V4.34

> Fail-closed QA, cross-feature geometry, exact source/canonical and post-save DXF/XDATA readback; no PASS shortcuts.

<!-- BEGIN MODULE: skills/lispcad/core/VALIDATION.md -->
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

# LISPCAD Core — Validation

2026-10-12 CUSTOMER CAD OVERRIDE: correct source geometry can PASS with nonblocking WARN for machine L/Z/reach; customer-authorized DATA_NO_DIM_COMPARE waives only PDF/DATA dimension-only conflict, never missing or mismatched holes, topology, count or physical DATA audit. SS>=19 R3 is exterior-perimeter-only (outer contour may contain concave corners). A legible handwritten Nobi/table discrepancy is logged as audit, not a blocking FLAG.



## V4.24 — DATA_MANUFACTURING_CANONICALIZATION hard gates

For every `PDF_DATA_RAW` production part, run these checks in addition to V4.23 bidirectional closure:

- **DATA_AUTO_R_CANONICALIZATION_CHECK:** enumerate otherwise uncalled eligible outside corners `<=90°`, resolve the active material/thickness row, and prove each required automatic R exists in canonical and serialized geometry. A sharp raw DATA vertex is not a pass condition. Every added/replaced R must retain source-corner provenance and an explicit material-rule canonicalization record. Explicit source R/C overrides the automatic rule at that corner.
- **DATA_TAP_NOMINAL_VALIDATION_CHECK:** for every proved `M<n>`, if DATA provides an identifiable nominal thread reference, compare that nominal diameter with `n`; `Delta >= 0.1 mm` is `DATA_PDF_DIM_DIFF`. Do not apply this nominal comparison to the raw pre-hole/pilot. Prove the nominal-reference entity is non-cut, the final effective CUT matches the approved thread-pilot table or explicit PDF override, and exactly one manufactured pilot representation exists per tap.
- **CANONICALIZATION_LEDGER_CHECK:** every manufacturing entity that differs from raw DATA because of auto-R, thread-pilot conversion or another approved rule must name its source members and controlling rule. Unchanged neighboring DATA geometry still requires source reprojection; an unrecorded extra arc/circle is FAIL.

Saved-DXF read-back must re-confirm the resulting R geometry, effective pilot diameter/count, Layer-0 semantics and absence of nominal-reference duplicate CUT. Read-back cannot waive a failed nominal delta or missing canonicalization ledger.

## V4.23 — BIDIRECTIONAL_SOURCE_CANONICAL_QA hard gate

For every `PDF_DATA_RAW` part, saved-DXF validation is downstream of: complete semantic DATA entity census; physical-family inventory and drawing-only exclusion; `SOURCE_PHYSICAL_TO_CANONICAL` completeness; `CANONICAL_TO_SOURCE_PHYSICAL` no-extra-manufacturing closure; per-family quantity/value/host closure; `PER_BEND_WITNESS_LEDGER` with `THICKNESS_SINGLE_USE`; material-domain BEND clipping; and fold-back/source reprojection.

Do not emit `SOURCE_REPROJECTION_PASS` merely because the primitives selected by the AI map back to DATA. That claim requires census completeness and both directions of the source/canonical diff. Bbox/read-back/entity existence cannot repair an upstream missing family, extra manufacturing edge or bend-witness mismatch.

When a user-approved sample contains exact coincident duplicates, normalize them for physical comparison and report `REFERENCE_ANOMALY`; never promote duplicate entity count into physical feature quantity.


## V4.22 SOURCE_FEATURE_COMPLETENESS — mandatory upstream QA

Before any export, compare the complete active source manufacturing-family inventory against the canonical model and the final serialized DXF. Every source-active family (CUT, HOLE/SLOT, BEND, KEGAKI, PIASU/PIERCING, SLIT/RELIEF, RIB, R/C/chamfer or other forming feature) must have an explicit canonical/output status. A family that disappears without an explicit source cancellation is **FAIL**, even when the outer contour, bbox and DXF read-back are otherwise clean.

For `PDF_DATA_RAW`, also enforce `SOURCE_EXHAUSTED_BEFORE_VIEWS_ONLY`: do not route a code to `VIEWS_ONLY` until all available relevant DATA views/faces/primitives have been harvested/classified and all source-supported FACE_GRAPH closure attempts have been exhausted. Semantic classification of a feature does not authorize refitting unchanged DATA curves into a simpler analytic shape. QA must include both source/DATA -> canonical -> inverse reprojection and canonical -> DXF -> read-back.

## V4.19 FOLD_BACK_SOURCE_REPROJECTION — mandatory for bent/multi-face production

After canonical unfold but **before** production DXF serialization, replay the flat through the signed FACE_GRAPH and compare/reproject against the source-proved formed constraints. PASS requires the used face dimensions/adjacency, bend signs, outside dimensions, feature host faces/local offsets, quantities and local material topology to reproduce the source. A correct flat bbox, entity count or saved-DXF read-back cannot compensate for a failed fold-back.

Also require `CONSTRAINTS_CLOSED`: no unresolved semantic owner, face transform, bend sign/domain or materially different competing topology may remain. If ambiguity remains, route to FLAG/PREVIEW/VIEWS_ONLY under existing policy.


## V4.13 approved 520315-18 independent checks

- Before comparing a reference DXF, reconcile $INSUNITS metadata with independently established PDF/user-confirmed actual numeric units. If contradictory and unresolved, FLAG SOURCE_UNIT_CONFLICT; do not automatically scale by 25.4. Output DXF remains mm, $INSUNITS=4.
- Treat original and mirrored drawing CODES as separate records. A mirror requires an established original/target relation, axis and feature scope, including actual holes/slots/R/C/bends, then independent count/containment validation. When inner formed faces are shown, assemble the proved INSIDE_VIEW first, apply only the evidenced reflection and compare hole family/center only in a shared final frame.
- If bend J, legible handwritten Nobi and a genuinely comparable table row ALL exist, draw with N_hand and record HANDWRITTEN_NOBI_DIFFERS_FROM_TABLE as a nonblocking audit note when the prescribed values disagree. Comparing a 165° note to a 90° table is an invalid conflict; no compatible row does not override handwriting.
- EXACT printed PDF inputs never receive a comparison tolerance. Only absolute differences strictly <0.01 mm caused by internal precision/rounding in an already-correct DERIVED result can pass an arithmetic-only comparison with reference DXF. Exactly 0.01 fails this test. This does not waive feature/datum/topology/bend/manufacturing checks. V4.12 already prohibits routine shop-spacing customer approval questions; do not duplicate that rule.


Source: approved V4.3 production baseline.

## V4.11 PREVIEW vs production validation — active

The user approved **DRAW → FLAG → CONFIRM**: draw a reasonable PDF-supported provisional shape in Magenta with adjacent assumptions, or separate independently proved source/orthographic views when no defensible flat is possible; ask targeted questions after drawing. Record uncertain type/topology/size/datum as `FLAGGED` and mark such parts `PREVIEW` or `VIEWS_ONLY`, never `PASS`. Any such part makes the entire default composite `*_ALL_REVIEW_ONLY.dxf` / **NO CUT**. A previous user QA PASS on a delivered file does not certify any later changed file. The original Section 5 geometry, datum, counts, containment, material and bend-domain production gates remain fully mandatory once uncertainties are resolved. The earlier 'numeric-only Magenta' restriction is historical for previews but remains superseded by this user-approved review-only rule. See [approved regression](../../../regression/qa/520625-15_V4_11_APPROVED.md).

## V4.8 required cancellation and regression audit

Classify each source feature-family callout as ACTIVE or unequivocally CANCELED before count closure. Require original quantity for each active family and ZERO produced entities for confirmed full-family deletions; include individual and translated composite DXF read-back. Ambiguous/partial strike-through blocks deletion and requires clarification. Apply approved regression/datum/520709-07_APPROVED.md for 039915 external-step datum, 039918/039919 diagonal/hole family and full reflection, and 040006 deletion of the complete 2-Ø8H7 family with active 6-M8 and 4-Ø9 retained. Matching overall extents alone cannot PASS these checks.

## 5. Error Detection & Manufacturing Validation Engine

Before exporting ANY production DXF or optional AutoLISP, run the following automated checks:

### 5.1 Geometry & Dimension-Semantic Integrity Engine
- **Closed Polyline Check**: Outer boundary vertices must form a continuous loop that explicitly closes at $P_{\text{start}} = P_{\text{end}}$.
- **Self-Intersection Check**: Ensure no overlapping edges or intersecting outer polyline loops exist.
- **Vertex Ordering**: Outer boundaries must follow Counter-Clockwise (CCW) orientation; internal cutouts must follow Clockwise (CW) orientation.
- **V4.18 SOURCE_CALLOUT_CANONICAL_CHECK:** Before production PASS, compare every explicit R/C family in the canonical model back to the source tuple `family + value + quantity/scope + target corner class + leader/witness`. A source `C2` represented as `R2`, `R3`, auto-R0.5, ARC, or bulged radius is FAIL even if the saved DXF reopens perfectly. Read-back verifies serialization/model fidelity; it is not source-semantic verification.
- **V4.18 DETAILED_SOURCE_BUNDLE conflict check:** When a job-list/summary row conflicts with the same-code detailed page, record whether the detailed page independently closes identity, explicit material/thickness, dimension-witnessed geometry, and Nobi/flat arithmetic, and verify there is no higher-authority revision/red correction/cancellation. Only a closed bundle resolves the summary conflict automatically; otherwise FLAG/ask. A reference DXF cannot be used as the missing input in NEW_PDF_TO_DXF.

- **Source-Origin/Axis Mapping Check (V4.10):** For every absolute or ordinate-based feature, confirm the actual source-view origin and positive X/Y directions from drawing evidence BEFORE any DXF coordinate assignment; record its target CAD datum and signed source→CAD equation, then verify an independent edge/overall closure when available. Negative source Y is NOT a CAD Y coordinate. Transferring `Y=-30` from a proved top-left origin on a view 138 mm high to a bottom-left CAD datum MUST give `Y=108`, not `-30` or `88`. Missing origin/axis evidence is FLAGGED and prevents production PASS; do not borrow an adjacent hole/contour datum.
- **Datum Graph Connectivity Check**: Every critical hole/notch/step coordinate must have a connected dimension path from an identified datum per Section 4.2.
- **Dimension-Type Check**: Each used dimension must be classified as baseline, chain, step/local, overall, or ordinate before arithmetic.
- **Dimension Endpoint Identity Check**: For every crowded or parallel dimension group, verify that each dimension's start/end node targets the correct entity type (`OUTER_EDGE`, `CONTOUR_EDGE/STEP`, `HOLE_CENTER`, etc.). Reusing a neighboring endpoint is a semantic FAIL.
- **Contour Topology Check**: Verify that the ordered visible boundary (including steps/recesses/protrusions) is reproduced before numerical closure. A geometrically closed but topologically wrong rectangle/step is FAIL.
- **Reference-Datum Check**: Parenthesized/reference dimensions must retain their actual extension-line datum; using the nominal value directly as a global coordinate without datum proof is FAIL.
- **Chain Closure Check**: Where an overall width/height is present, verify that the proven chain closes to the overall dimension. A closure failure is a semantic FAIL even if the CAD polyline itself is perfectly closed.
- **Reference DXF Comparison Check**: When Section 2.4 is active, compare feature coordinates and topology against the master DXF after PDF interpretation. First apply the approved material-table automatic Laser R rule for eligible corners; do not exclude matching DXF-only R0.5/R2 simply because PDF omitted the callout. Only explicitly approved downstream shop-only differences may be excluded.
- **V4.22 SOURCE_FEATURE_COMPLETENESS Check — HARD FAIL**: Build the source-active family set before canonicalization, then diff it against canonical and serialized output. Missing an active family such as SLIT/RELIEF or KEGAKI is FAIL even if CUT/BEND are otherwise correct. Count semantic manufacturing features by proved topology/connectivity, while separately preserving unchanged DATA curve provenance; a feature may be one operation composed of many LINE/ARC primitives. For PDF+DATA, also prove source exhaustion before any `VIEWS_ONLY` status.
- **Feature Count Closure Check**: For every explicit quantity callout (`n-Ø`, `n-M*`, `n-slot`, `n-R`, `n-C`, repeated notch family, etc.), the generated family count MUST equal `n`. Thread-to-pilot conversion changes diameter representation, not the required count. Missing or extra members are FAIL, not WARN.
- **Connected primitives are not separate manufacturing features (approved `055958` regression)**: Count by proved topology, actual manufacturing operation, and endpoint connectivity, **not** by the number of same-colored DXF LINE/ARC entities. One approved `055958` Section 4.10 slit contains Green `LINE 55A` + `ARC 55B R0.5` + `LINE 55C`, which meet at their endpoints: feature count **1**, constituent entity count **3**. Common color alone does not prove that unrelated entities form one feature. The local R0.5 in this specific case is not a universal requirement of all slit reliefs. Remove only this slit method/count FLAG; independently uncertain customer sizes/datum still FLAG.
- **Feature Family Isolation Check**: Keep each family (`Ø5.5`, `M4→Ø3.3`, `M5→Ø4.2`, slots, cutouts, etc.) independently counted and datum-traced. Do not use one family's centerline/dimension to create or position another family without explicit evidence.
- **Local-Face → Flat Transform Check**: Every feature dimensioned on a bent face must have a proven Section 4.2.7 transform into global flat coordinates. Copying a local formed-face coordinate directly into the flat pattern is FAIL.
- **Bend Sequence Check**: Verify face order independently of total-length closure. Matching overall blank length does not PASS bend order. Bend coordinates must follow the proven sequence in Sections 4.2.8 and 4.7.
- **Feature Containment Check**: Every closed hole/slot/internal cutout must lie fully inside the material region unless the drawing explicitly defines an open-edge notch/slot. Any closed feature wholly or partly outside the outer boundary is FAIL.
- **Bend-Line Material-Domain Check**: Bend lines may exist only where material crosses the bend. A line passing through a void, center cutout, open gap, or outside the part is FAIL; split the bend line into valid material segments when required.
- **Slot-Semantics Check**: Verify that every generated slot uses a classified source length and the canonical `L_TOTAL` semantics in Section 3.1. A center-distance value passed as overall length (or vice versa) is FAIL.
- **No Placeholder Bounding Rectangle Check**: If the source contour contains a step, protrusion, recess, leg, or open center, a bounding rectangle is not an acceptable placeholder. Closed geometry that has the right bounding box but the wrong topology is FAIL.
- **PASS Evidence Rule**: Never mark a checklist item `PASS` merely because the generated entity exists or looks plausible. `PASS` requires that the corresponding semantic/geometric validation was actually executed and succeeded. If the check cannot be executed from available evidence, use `FLAGGED`, `WARN`, or `N/A` as allowed by Section 9.

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
| **Minimum Bridge / Web Width** | Distance between hole edge & part boundary $\ge t$ | Flag low confidence warning |
| **Laser Piercing Accessibility** | Distance between adjacent piercings $\ge 10\text{ mm}$ | Group piercing locations |
| **Bend Line Collision** | Distance between hole edge & bend line $\ge 2 \times t + R_{\text{bend}}$ | Flag potential hole deformation |

**V4.12 shop-distance question suppression:** Treat minimum bridge/web, inter-piercing spacing and hole-to-bend proximity as optional/internal nonblocking **advisories** for geometry drawn as printed in the PDF. Do not shift/remove such geometry, block a source-faithful preview, or ask routine customer clearance acceptance solely for these heuristics. Maintain mandatory PDF-specific clearances, actual self-intersection and containment, source datum, hole-capacity rules, unproved dimensions and real demonstrated production conflicts; a genuine conflict still receives an actionable FLAG.

---


## Historical V4.7 saved-DXF dual-export audit (explicit-request legacy only)
Before declaring the canonical model PASS, actually execute every preceding V4.6 PDF-semantic, source/material, true contour topology, datum, feature-count, containment and bend-domain check. A serializer's structural validations cannot prove these engineering facts.
Under explicit-request **legacy V4.7 dual export** only, for EACH individual and combined DXF reopen the SAVED file and audit: real mm DXF, Layer 0 only, correct V4.6 entity/linetype/color/POINT/CIRCLE and bulges, geometry/count against the canonical source, no extra code-label TEXT. Combined drawing MUST contain exactly one translated copy of each production-PASS part, in explicitly declared code order descending Y, separated by at least 10 mm layout-only bbox clearance; record/check all offsets in the manifest. Keep numeric-only user-requested Magenta _PREVIEW outside production _ALL.dxf and do not mark preview PASS. Unknown topology/type/bend/material/datum blocks export. Count the `055958` Green LINE+ARC+LINE as ONE slit operation, not three.

## V4.9/V4.10 current output precedence

Default output is **ONE** top-to-bottom code-labeled composite, or `_ALL_REVIEW_ONLY.dxf` with all source-view groups/FLAGs and global NO CUT when any code is not independently production PASS. Exclude `AI_META` non-cut labels from the Layer-0 manufacturing audit. The historical V4.7 dual-export section above does NOT require default individual DXFs or manifest. The V4.10 source-origin/axis check in Section 5.1 is mandatory upstream BEFORE a production PASS or composite entity serialization.

### V4.14 direct existing-output audit and overlapping-cut QA

When explicitly asked to compare a PREVIOUSLY EXPORTED AI DXF with a user-approved reference, compare **AI DXF vs reference DXF FIRST**, not PDF vs sample. Normalize only independently proved source-unit interpretation, source orientation and layout translations; compare actual machining curves, typed hole/slot families and original source-callout counts, cut unions, complete unfold coordinates, all bend-pair coordinates and bend-line clipping to material. Geometric identity accepts ARC+LINE versus equivalent exact closed LWPOLYLINE/bulge; raw entity counts are not semantic feature counts. A partial source/orthographic view does not pass against a reference completed flat. Classify MATCH/PARTIAL/DIFF per code and test originally matched codes again after any rebuild. THEN inspect PDF to diagnose mismatches; independent PDF-FIRST interpretation remains the creation procedure. For truly overlapping cut holes require one non-self-intersecting Boolean-union contour and separate family quantity closure, rather than several overlapping interior cut circles. Strict `<0.01 mm` arithmetic residual is permitted ONLY for already-correct derived values per existing V4.13; every PRINTED source number remains exact. Six-code test: `regression/qa/520217-26_V4_14_APPROVED.md`.


## V4.17 hard anti-regression gates — approved 520929-10

These gates operationalize existing interpretation rules and are production-blocking where stated:

- **SLOT_WITNESS_FAIL — HARD FAIL:** slot W/R, center distance and overall length must come from the actual callout plus witness endpoints. A nearby number belonging to another chain/edge may not substitute for the slot width. The 520929-10 regression specifically fails W10/R5 where source/sample proves W9/R4.5.
- **MIRROR_SCOPE_FAIL — HARD FAIL:** never reflect a partner because codes are adjacent, sizes match, or shapes look paired. Reflection requires source/user proof of partner identity, axis/orientation and feature scope. Otherwise reconstruct each code independently.
- **DATUM_WITNESS_FAIL — HARD FAIL:** a coordinate dimension from top/right/other outside edge must be transformed from that proved source datum. Do not replace an edge-to-center witness with a tangent/radius/bbox inference. Regression: H32 and top-edge-to-center 10 => bottom-origin Y22.
- **KEGAKI_SCOPE_FAIL — HARD FAIL:** CUT PASS never implies KEGAKI PASS. Check marking count, segment endpoints, position and property independently. Missing required KEGAKI blocks production PASS.
- **STALE_PREVIEW_FAIL — QA ERROR:** when source/reference/user evidence resolves a KEGAKI that was previously provisional, regenerate it with normal production KEGAKI property (Red under current CAD_OUTPUT) and remove the stale Magenta uncertainty flag for that resolved feature.
- **REFERENCE_METADATA_NONBLOCKING:** for approved-reference audits, a conflicting `$INSUNITS` header does not by itself fail physical geometry once actual numeric units are independently proved from source/user/reference scale. Do not apply 25.4 scaling from metadata alone. Production exports still follow the normal mm metadata rule.
<!-- END MODULE: skills/lispcad/core/VALIDATION.md -->

---

<!-- BEGIN MODULE: skills/lispcad/core/CROSS_FEATURE_VALIDATION.md -->
# V4.33 holistic cross-feature anomaly checks

In addition to feature-family interactions, run these whole-part contradictions before final PASS:

- source physical/view inventory vs source-group/member ledger completeness;
- barcode/constituent/assembly ownership vs assigned DATA/view bundles;
- BEND shared-edge semantic ownership vs face/blank extents;
- handwritten/printed flat arithmetic vs claimed inability to attempt a flat;
- local unresolved feature vs whole-part VIEWS_ONLY escalation;
- complete proved source-view inventory vs VIEWS_ONLY canonical members.

Any contradiction raises `ENGINEERING_ANOMALY_DETECTED` and returns the part to source interpretation. Do not choose a missing answer by confidence, symmetry or sample geometry.

# LISPCAD Core — Cross-feature validation

## Scope

Always run after feature routing and before production DXF export. This module adds no new dimensional formula; it prevents individually-correct feature modules from producing an incorrect combined part.

## Mandatory interactions

- **BEND ↔ FACE EDGE OWNERSHIP (V4.32):** every bend must pass `BEND_ATTACHMENT_EDGE_LOCKED` from `references/BEND_ATTACHMENT_EDGE_OWNERSHIP.md`. Prove the physical `FACE_A.edge_i <-> BEND <-> FACE_B.edge_j` connection; `NEAREST_VIEW_EDGE`, paper proximity and page-side assumptions are forbidden evidence.
- **FEATURE DATUM ↔ ATTACHED FACE ORIENTATION (V4.32):** holes/cutouts/notches/chamfers on a bent face retain physical edge identity such as `BEND_EDGE` or `FREE_EDGE` through rotation/reflection and local-face -> flat mapping. A reversed attachment that swaps those identities is FAIL even when total flat length is unchanged.
- **FORMED OD ↔ NOBI ↔ FLAT (V4.32):** when `references/FORMED_PROFILE_OD_MEASUREMENT.md` applies, establish `OD_actual` from the source-supported formed profile/outside envelope and explicit thickness/offset ownership before subtracting Nobi. Directly treating an inside/formed scalar as OD without proof is FAIL.
- **MEASUREMENT VIEW ↔ MANUFACTURING OUTPUT (V4.32):** a `MEASUREMENT_CONSTRUCTION_VIEW` may prove topology, attachment or outside length but is not CUT merely because it is present beside a flat or on Layer 0 in a reference.
- **SOURCE MANUFACTURING NOTE ↔ feature family (V4.29):** every production-affecting printed/handwritten instruction must retain a resolved family/output status under `references/SOURCE_MANUFACTURING_NOTE_CENSUS.md`. A source-active instruction may not disappear between preliminary census, routed modules, canonical geometry and serialized output.
- **HOLE/TAP ↔ BEND:** preserve host-face ownership and the proved local-face -> flat transform. Do not move printed geometry merely to satisfy a generic shop-distance advisory.
- **KEGAKI ↔ BEND/MULTI_FACE:** transform each mark with its owning face and verify fold-back locating function, count and segmentation.
- **SLIT/RELIEF ↔ BEND:** verify the slit/relief mechanism, source scope, quantity/value when specified, direction, connectivity, host edge/face and actual BEND interaction. For a V4.29 custom source-instructed slit, do not infer size or position from BEND geometry: relation to a bend center/domain must be source-proved. BOXMET rules apply only when BOXMET topology is proved.
- **CHAMFER/FILLET ↔ MATERIAL auto-R:** explicit source R/C semantics and quantities take precedence over automatic material corner treatment.
- **TAP ↔ HOLE:** thread-to-pilot conversion changes the manufactured diameter representation, not source family quantity or datum ownership.
- **PIASU ↔ HOLE/MATERIAL:** apply the active point/circle and material-capacity rules without changing source quantity or identity.
- **REVISION/CANCELLATION ↔ every family:** cancellation is scoped to the actual callout/leader/family. Never delete neighboring families by proximity.
- **RIB ↔ KEGAKI:**- **WELD SITE ↔ CUSTOMER 851 ↔ KEGAKI:** independently identify every A/B assembly view, proved parent/child weld contact and host face before KEGAKI routing. Numeric KH851 requires marking each proved weld site, even without a printed mark callout. Run references/WELD_SITE_KEGAKI_CLOSURE.md and enforce source weld-site IDs == canonical scoped KEGAKI/FLAG ownership; an omitted source weld site or required mark is FAIL regardless of otherwise valid DXF read-back.
 RIB-part CUT/HOLE and main-part locating KEGAKI are independent families; cancellation of one does not imply cancellation of the other.
- **WELD_REQUIRED_CUE ↔ RIB/support ↔ KEGAKI (V4.27):** `REVERSED_E_ABOVE_BARCODE` is scoped to its associated barcode/code cluster and proves a welding-process expectation, not KEGAKI geometry. If a welded child cannot self-locate, locating KEGAKI must be source-proved/derived from actual contact function or remain locally `UNKNOWN`/FLAG; it must not disappear from the final family closure. A specific KEGAKI instruction is independently sufficient. If neither barcode weld cue nor specific KEGAKI instruction exists, do not infer welding/KEGAKI from a RIB/support alone.
- **DATA provenance ↔ all features:** semantic cleanup/canonicalization must not silently redraw unchanged customer DATA geometry.
- **DATA provenance ↔ MATERIAL auto-R:** a sharp DATA corner does not suppress a required material-table R. For otherwise uncalled eligible outside corners <=90 degrees, preserve source-corner provenance, apply the active R as recorded `DATA_AUTO_R_CANONICALIZATION`, and retain explicit source R/C precedence.
- **DATA TAP representation ↔ THREAD_PILOT:** for every proved M*, distinguish `THREAD_NOMINAL_REFERENCE` from `THREAD_PREHOLE_SOURCE`; apply the nominal DATA<->PDF delta gate only to the nominal reference, then serialize exactly one controlled pilot CUT. Never output nominal-reference + pilot as two cuts.

## Closure

For every final family record, confirm:

1. source identity and quantity;
2. applicable source manufacturing-note provenance/resolution;
3. host face / datum ownership, including physical edge identity for bent-face datums;
4. routed rule modules;
5. canonical geometry representation;
6. interactions with other active families;
7. serialized DXF representation;
8. applicable source-reprojection and saved-DXF read-back.

For bent/multi-face parts, fold-back must also reproduce the proved **attachment edge identity**, not only the same silhouette, bbox or total length.

Any unexplained source-note loss, family loss, duplication, ownership conflict, bend-edge attachment conflict, measurement-view leakage into manufacturing geometry, or cross-feature contradiction is production FAIL/FLAG under the active validation rules.
<!-- END MODULE: skills/lispcad/core/CROSS_FEATURE_VALIDATION.md -->

---

<!-- BEGIN MODULE: references/CANONICAL_MEMBER_COMPLETENESS.md -->
# CANONICAL_MEMBER_COMPLETENESS — V4.33 ledger-plausibility hardening over V4.31

**Status:** USER APPROVED 2026-10-06.

This is an executable production hard gate. It closes the gap where a job can correctly name a source family/group in text yet serialize only a hand-picked subset of the proved geometry.

## 0. V4.33 upstream ledger-plausibility gate

The V4.31 equalities remain necessary but are not sufficient when the source ledger itself is incomplete.

Before member equality, run the routed holistic challenge and verify:
- every relevant source physical/view inventory entry maps to a source member or an explicit drawing-only/helper/duplicate/canceled classification;
- every final feature-family YES/UNKNOWN has a scoped group/member or explicit unresolved group;
- substantial physical DATA with zero proved source members is challenged rather than accepted by self-equality;
- VIEWS_ONLY contains every independently proved source-view member required for the unresolved part;
- multi-code/constituent jobs pass PART_IDENTITY_GRAPH with no unexplained whole-bundle collision;
- a shared bend-edge dimension is not reused as an unrelated blank/face extent without same-physical-parameter proof.

If census/inventory/group/member records disagree, fail upstream with `SOURCE_LEDGER_PLAUSIBILITY_FAIL`. Do not proceed merely because `PROVED_SOURCE_MEMBER_IDS == PROVED_SOURCE_BACKED_CANONICAL_MEMBER_IDS`.

## 1. Required production chain

Normal repo-direct CAD production is:

`SOURCE -> SOURCE_FEATURE_GROUP ledger -> SOURCE MEMBER ledger -> DIMENSION/WITNESS graph -> CANONICAL MEMBER model -> CANONICAL ENTITIES -> V4.31 canonical serializer -> SAVED DXF -> READ-BACK`.

`tools/export_canonical_dxf.py` is the normal production serialization entrypoint. `tools/export_dxf.py` remains the lower-level packaging serializer and is not, by itself, evidence that source-member completeness was proved.

**NO_DIRECT_DXF_FROM_INTERPRETATION:** a job builder must not create production/review DXF directly from source interpretation by writing an ad-hoc subset to `ezdxf.modelspace()` and then calling `saveas()`. Build the canonical JSON contract first and pass it through the V4.31 gate.

## 2. Source groups and members

Every source-scoped leader/callout group that affects manufacturing must be persisted as a `source_group` with:

- stable `group_id`;
- `family`;
- `status = PROVED | FLAGGED | CANCELED`;
- `source_quantity` when quantity is proved, otherwise null;
- member records when members are enumerable;
- source/evidence note sufficient to trace the group back to the drawing.

Same family/size does not merge groups. Shared X witnesses do not imply shared Y witnesses.

Each enumerable member has a stable `member_id` and local status. A FLAGGED member/group stays in the ledger; uncertainty is local and does not authorize deletion of independently PROVED members.

## 3. Canonical member model

Every active enumerable source member must have exactly one source-backed canonical member record.

- source `PROVED` -> canonical `PROVED`;
- source `FLAGGED` -> canonical `PREVIEW` or `FLAGGED_NO_GEOMETRY`;
- source `CANCELED` -> no source-backed canonical member.

A canonical member may reference one or more entity IDs. One physical manufacturing feature can require multiple primitives (for example a slit composed of LINE+ARC+LINE or a bend represented by two DASHED lines). Conversely, several semantic members such as corner-R ownership may reference one shared contour entity when the physical DXF representation is a single polyline. Raw DXF entity count is not manufacturing quantity.

Rule-derived manufacturing members not explicitly called out by source may use `origin = DERIVED_RULE` only when they record `controlling_rule` and the source member(s)/source feature that triggered the derivation.

## 4. Mandatory equalities

Before serialization:

`PROVED_SOURCE_MEMBER_IDS == PROVED_SOURCE_BACKED_CANONICAL_MEMBER_IDS`

and all enumerable FLAGGED source members must remain represented as `PREVIEW` or `FLAGGED_NO_GEOMETRY`.

Before delivery:

`CANONICAL_ENTITY_IDS == SAVED_DXF_LAYER0_ENTITY_IDS`

The V4.31 wrapper stamps stable canonical `entity_id` values into Layer-0 DXF entities as `TRAINAICAD` XDATA, saves again, reopens the exact file, audits it, and proves the ID set/order survived. AI_META annotations are excluded from manufacturing-entity equality.

If either equality fails: `SOURCE_FEATURE_COMPLETENESS_FAIL` / `CANONICAL_SERIALIZATION_COMPLETENESS_FAIL`. Do not report generic READBACK PASS.

## 5. No orphan geometry

Every Layer-0 canonical manufacturing entity must have a unique `entity_id` and be referenced by at least one canonical member. Preview annotation TEXT may be exempt from manufacturing-member ownership but still receives an entity ID for read-back fidelity.

A canonical member referencing a missing entity is FAIL. A saved Layer-0 entity with no canonical entity ID is FAIL in the V4.31 normal production path.

## 6. 521005-05 failure lesson

The failed V4.30 runtime job demonstrated a workflow/implementation failure, not a serializer reduction failure: source groups for 057862/057864 and the M8 family on 057873 were not instantiated into a member-level canonical model before the raw `ezdxf` save. Selected read-back checks therefore passed a structurally valid but incomplete DXF.

V4.31 regression must prove at minimum:

- `057862`: independent `2-Ø9`, `6-M6`, `6-Ø9`, `2-Ø9` groups survive source -> canonical -> saved DXF member closure;
- `057864`: the proved 7 hole centers survive even while the separate `8-R5` issue remains customer-pending/FLAGGED;
- `057873`: four M8 members survive together with bend-edge lengths 248/50 and the already-approved 90-degree no-slit decision for positive bend-end offset;
- negative fixtures that reproduce the old subset behavior are rejected before/at canonical serialization.

The numeric fixture coordinates used by regression are synthetic test coordinates only. They are not construction data for future drawings.

## 7. Root-cause vocabulary

If source group/member records are missing despite readable source: `AI_WORKFLOW_ERROR`.
If a builder bypasses or violates the canonical contract: `AI_IMPLEMENTATION_BUG`.
If the gate/checker does not cover a demonstrated failure: `REGRESSION_COVERAGE_GAP`.
Do not label `AI_MISREAD` unless there is direct evidence that the source was semantically interpreted incorrectly; absence from a persisted ledger alone does not prove misreading.
<!-- END MODULE: references/CANONICAL_MEMBER_COMPLETENESS.md -->

---

<!-- BEGIN MODULE: skills/lispcad/core/CAD_OUTPUT.md -->
## V4.34 orientation and composite-only export (2026-10-13)
`tools/export_canonical_dxf.py --composite-only` persists per-code canonical JSON and exports ONE composite, without any standalone CUT DXFs. Individual PASS CUT DXFs alone are pose-normalized: if there is no proved HL, choose bounding-box X>=Y (90-degree rotate only if Y>X); with proved HL, align the source-proved part-local grain vector parallel to X even when Y>X. HL direction missing relative to the part => REVIEW and NO individual PASS file. No scale/mirror, no user-visible TEXT/BEND/POINT in standalone CUT, and no change to source-canonical coordinate records. Record orientation transform and read back transformed LINE/ARC/CIRCLE/XDATA. Composite uses the readable source orientation (translation/layout only) and remains independent of the standalone rotation. Old V4.31 canonical jobs are accepted; NEW source jobs use V4.34 to require witness and grain proof.

# Current production packaging — canonical code JSON + isolated PASS cuts

This section supersedes inherited V4.9/V4.11 composite-only defaults below,
without changing approved geometry, material/Nobi/bend or canonical schema.
Normal E2E uses `tools/export_canonical_dxf.py`; on successful canonical
member and composite saved-DXF XDATA read-back, it persists per-code
`geometry_json/<CODE>.json` even for REVIEW, emits
`parts_dxf/<PASS_CODE>.dxf` **only for verified PASS** using analytic
LINE/ARC/CIRCLE CUT primitives, and retains one entire-job composite
`<JOB>_ALL.dxf` or `<JOB>_ALL_REVIEW_ONLY.dxf` with all codes and warnings.
No non-cut marks, annotations, bend entities, preview or VIEWS_ONLY source
views may enter individual CUT files. A REVIEW in one code cannot downgrade
another's independent proved geometry, but the combined file always becomes
REVIEW_ONLY. Existing lower-level V4.9/dual serializations are compatibility,
not the canonical production entry point. Canonical data remain the sole
physical geometry source, and saved-DXF read-back is mandatory.

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
| Outer/inner contour and slot | Closed LWPOLYLINE with real bulges | ByLayer (omit/256) | ByLayer |
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
<!-- END MODULE: skills/lispcad/core/CAD_OUTPUT.md -->
