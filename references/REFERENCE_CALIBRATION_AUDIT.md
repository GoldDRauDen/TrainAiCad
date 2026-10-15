# Reference DXF calibration / direct audit (loaded when a reference/sample exists)

Moved verbatim from `DRAWING_READING.md` §0.3 and §2.4 (with duplicate V4.13/V4.14/V4.17 reference wording from `VALIDATION.md` and `CAD_OUTPUT.md` consolidated here). Production PDF-only jobs do not load this file.

### 0.3 Calibration / Regression Learning Protocol
When the user supplies a reference DXF or corrected CAD for PDF-interpretation calibration (NOT a specifically requested direct audit of an already created AI DXF):
1. **Interpret the PDF first** without using DXF coordinates to fill missing information.
2. Compare the independently derived geometry against the user-approved reference.
3. Classify each mismatch by semantic cause: datum, dimension-chain type, step/local dimension, feature type, C/R topology, tolerance/Nobi, or source conflict.
4. Convert only the **generalizable semantic cause** into a rule or regression test.
5. Do not encode one-off coordinates as generic rules.
6. Store validated examples as regression tests under `regression/` when they materially prevent recurrence.
7. Any future run must be able to apply those rules even when no DXF is supplied.

### 2.4 User-Declared Reference DXF Calibration / Ground-Truth Mode
This mode is activated ONLY when the user explicitly states that a supplied DXF is a correct production CAD / **ground-truth reference** used to audit and calibrate the executing AI's interpretation of the PDF.

#### 2.4.1 Purpose and Scope
- The purpose of the reference DXF is **calibration and verification of PDF-reading skill**, not blind geometry copying.
- The executing AI MUST first interpret the PDF/drawing using Sections 2–7, including datum tracing, dimension-string classification, feature recognition, C/R topology, and tolerance/Nobi rules.
- The executing AI then compares that independently-derived result with the reference DXF and identifies why any mismatch occurred.
- Learn **generalizable interpretation rules** from the comparison (datum origin, chain-vs-baseline distinction, step dimensions, convex/concave C/R mapping, feature-count logic). Do NOT learn or memorize raw coordinates as a substitute for drawing interpretation.
- A reference DXF may be used to confirm that a particular PDF interpretation is correct. It MUST NOT be used as a hidden bounding-box ruler to invent a dimension that cannot be traced on the PDF.

#### 2.4.2 Ground-Truth Comparison Rules
- Compare: feature position, feature size, contour topology, hole/slot locations, chamfer geometry, explicitly specified radii, and part-to-code mapping.
- When a mismatch is found, classify the root cause explicitly as one of: `DATUM ERROR`, `CHAIN/BASELINE ERROR`, `STEP DIMENSION ERROR`, `FEATURE TYPE ERROR`, `FEATURE-COUNT ERROR`, `C/R TOPOLOGY ERROR`, `REFERENCE/FORMED-DIMENSION ERROR`, `UNFOLD TRANSFORM ERROR`, `BEND-SEQUENCE ERROR`, `CONTAINMENT ERROR`, `CODE/SCHEMA SEMANTICS ERROR`, `MISSING/AMBIGUOUS PDF DIMENSION`, or `DXF-ONLY SHOP FEATURE`.
- If the DXF and PDF differ but the mismatch can be explained by a PDF dimension string that was previously misread, correct the PDF interpretation and record the anti-regression rule in the portable skill when validated.
- If the DXF differs from the PDF in a way that **cannot** be supported by the PDF dimensions/callouts, do NOT silently teach that difference as a general rule. Report it as a production-CAD adjustment or source conflict and ask the user when it materially changes the part.
- A newer visible revision note / red correction on the PDF must still be reported if it conflicts with the supplied DXF; ground-truth calibration does not erase revision chronology.

#### 2.4.2b V4.14 approved DIRECT AUDIT of a PREVIOUSLY EXPORTED AI DXF against a reference

If the user's objective is to evaluate **the AI's already-exported DXF** against a customer-approved reference DXF, compare **those TWO DXFs FIRST**, matching only proved drawing-code clusters and actual user/PDF-confirmed coordinate units, then normalizing layout-only translation and any independently proved orientation. Audit full physical outer/inner boundaries, each hole/slot/cutout family (type, diameter, original quantity and coordinates), true R/C, complete unfolded extent, each double-line bend-pair coordinate and its clipping to real material. ARC+LINE in the reference and exact, closed LWPOLYLINE/bulge in the AI output are geometrically equivalent; raw entity counts alone are not a failure. A source/orthographic face is only PARTIAL if the reference has a complete flat, irrespective of its locally correct holes. Report MATCH/PARTIAL/DIFF **per code**, protect MATCHed parts from later edits, and **only THEN** revisit the PDF to identify why the AI made each error. This is distinct from creating a NEW PDF-based drawing: existing PDF-FIRST rules are unchanged, and sample DXF is never a hidden replacement for an unproved PDF dimension. Approved case: `regression/qa/520217-26_V4_14_APPROVED.md`.

#### 2.4.4 Calibration / Portable Learning Discipline
- Every reference-DXF comparison is an **anti-regression calibration case**: record the semantic reason for each corrected mismatch, not merely the corrected coordinate. Validated general rules belong in this portable skill file.
- Future PDF-only jobs, including in unrelated chats or on another AI, must apply those semantic rules from this file without requiring a DXF.
- Do not generalize one-off production edits from a single DXF into universal rules unless the user explicitly confirms they are standard practice.
- Do not rely on conversational memory for this learning. If the lesson must survive across chats/AIs, encode it in this master skill or a required companion regression file.

#### Reference-audit extras (consolidated)

**Reference SOURCE_UNIT_CONFLICT:** A reference DXF $INSUNITS header is metadata, not automatic geometric truth. Before comparing sample geometry, verify actual numeric units against independently read PDF witness-line dimensions and the user's explicit unit confirmation. The approved 520315-18_ss.dxf has a misleading inch header but actual mm numbers: DO NOT multiply/divide by 25.4. If a different sample's true units remain unresolved, FLAG and ask. Newly generated DXF still uses $INSUNITS=4.

- **REFERENCE_METADATA_NONBLOCKING:** `$INSUNITS` metadata alone never fails physical geometry once actual numeric units are proved from source/user/reference scale. Production exports still use mm metadata.
- EXACT printed PDF inputs never receive a comparison tolerance. Only absolute differences strictly <0.01 mm caused by internal precision/rounding in an already-correct DERIVED result can pass an arithmetic-only comparison with a reference DXF. Exactly 0.01 fails. This never waives feature/datum/topology/bend/manufacturing checks.
- **Reference DXF Comparison Check:** when a reference is active, compare feature coordinates and topology against it only after independent PDF interpretation. First apply the approved material-table automatic Laser R rule for eligible corners (`DRAWING_READING.md` §2.4); do not exclude matching DXF-only R0.5/R2 simply because the PDF omitted the callout. Only explicitly approved downstream shop-only differences may be excluded.
- Exact coincident duplicates in a user-approved sample are normalized for physical comparison and reported `REFERENCE_ANOMALY`; never promote duplicate entity count into feature quantity.
- If a sample/reference is introduced after production, output/audit reporting must preserve the frozen source-only status (`SOURCE_ONLY_SNAPSHOT`).
