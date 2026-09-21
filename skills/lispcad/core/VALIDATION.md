# LISPCAD Core — Validation

Source: approved V4.3 production baseline.

## 5. Error Detection & Manufacturing Validation Engine

Before emitting AutoLISP code, run the following automated checks:

### 5.1 Geometry & Dimension-Semantic Integrity Engine
- **Closed Polyline Check**: Outer boundary vertices must form a continuous loop that explicitly closes at $P_{\text{start}} = P_{\text{end}}$.
- **Self-Intersection Check**: Ensure no overlapping edges or intersecting outer polyline loops exist.
- **Vertex Ordering**: Outer boundaries must follow Counter-Clockwise (CCW) orientation; internal cutouts must follow Clockwise (CW) orientation.
- **Datum Graph Connectivity Check**: Every critical hole/notch/step coordinate must have a connected dimension path from an identified datum per Section 4.2.
- **Dimension-Type Check**: Each used dimension must be classified as baseline, chain, step/local, overall, or ordinate before arithmetic.
- **Dimension Endpoint Identity Check**: For every crowded or parallel dimension group, verify that each dimension's start/end node targets the correct entity type (`OUTER_EDGE`, `CONTOUR_EDGE/STEP`, `HOLE_CENTER`, etc.). Reusing a neighboring endpoint is a semantic FAIL.
- **Contour Topology Check**: Verify that the ordered visible boundary (including steps/recesses/protrusions) is reproduced before numerical closure. A geometrically closed but topologically wrong rectangle/step is FAIL.
- **Reference-Datum Check**: Parenthesized/reference dimensions must retain their actual extension-line datum; using the nominal value directly as a global coordinate without datum proof is FAIL.
- **Chain Closure Check**: Where an overall width/height is present, verify that the proven chain closes to the overall dimension. A closure failure is a semantic FAIL even if the CAD polyline itself is perfectly closed.
- **Reference DXF Comparison Check**: When Section 2.4 is active, compare feature coordinates and topology against the master DXF after PDF interpretation. Exclude the confirmed uncalled-out DXF-only `R0.5` shop addition per Section 2.4.3; do not automatically exclude other discrepancies.
- **Feature Count Closure Check**: For every explicit quantity callout (`n-Ø`, `n-M*`, `n-slot`, `n-R`, `n-C`, repeated notch family, etc.), the generated family count MUST equal `n`. Thread-to-pilot conversion changes diameter representation, not the required count. Missing or extra members are FAIL, not WARN.
- **Feature Family Isolation Check**: Keep each family (`Ø5.5`, `M4→Ø3.3`, `M5→Ø4.2`, slots, cutouts, etc.) independently counted and datum-traced. Do not use one family's centerline/dimension to create or position another family without explicit evidence.
- **Local-Face → Flat Transform Check**: Every feature dimensioned on a bent face must have a proven Section 4.2.7 transform into global flat coordinates. Copying a local formed-face coordinate directly into the flat pattern is FAIL.
- **Bend Sequence Check**: Verify face order independently of total-length closure. Matching overall blank length does not PASS bend order. Bend coordinates must follow the proven sequence in Sections 4.2.8 and 4.7.
- **Feature Containment Check**: Every closed hole/slot/internal cutout must lie fully inside the material region unless the drawing explicitly defines an open-edge notch/slot. Any closed feature wholly or partly outside the outer boundary is FAIL.
- **Bend-Line Material-Domain Check**: Bend lines may exist only where material crosses the bend. A line passing through a void, center cutout, open gap, or outside the part is FAIL; split the bend line into valid material segments when required.
- **Slot-Semantics Check**: Verify that every generated slot uses a classified source length and the canonical `L_TOTAL` semantics in Section 3.1. A center-distance value passed as overall length (or vice versa) is FAIL.
- **No Placeholder Bounding Rectangle Check**: If the source contour contains a step, protrusion, recess, leg, or open center, a bounding rectangle is not an acceptable placeholder. Closed geometry that has the right bounding box but the wrong topology is FAIL.
- **PASS Evidence Rule**: Never mark a checklist item `PASS` merely because the generated entity exists or looks plausible. `PASS` requires that the corresponding semantic/geometric validation was actually executed and succeeded. If the check cannot be executed from available evidence, use `FLAGGED`, `WARN`, or `N/A` as allowed by Section 9.

### 5.1.1 Full Internal Verification, Minimal External Noise
- Every check in Section 5.1 remains mandatory even when the user asks for a short report.
- Do not print a long PASS checklist by default. Internally execute the checks, then expose only:
  - one compact overall validation line when all required checks pass; and
  - every `FAIL`, `FLAGGED`, `WARN`, ambiguity, or user-confirmation item.
- A concise report MUST NOT hide an unresolved production risk. Brevity controls presentation, not engineering rigor.
- Do not narrate exploratory reasoning, discarded hypotheses, or general sheet-metal theory unless the user asks for an audit/explanation.

### 5.2 Manufacturing Feasibility Rules

| Feasibility Parameter | Constraint Rule | Violation Action |
| :--- | :--- | :--- |
| **Minimum Hole Diameter** | Hole $\varnothing \ge \text{Material Thickness } t$ (for SS/SUS/AL) | Flag warning & add Piasu center point |
| **Minimum Bridge / Web Width** | Distance between hole edge & part boundary $\ge t$ | Flag low confidence warning |
| **Laser Piercing Accessibility** | Distance between adjacent piercings $\ge 10\text{ mm}$ | Group piercing locations |
| **Bend Line Collision** | Distance between hole edge & bend line $\ge 2 \times t + R_{\text{bend}}$ | Flag potential hole deformation |

---
