# REFERENCE — sample / approved DXF present (TRAIN_REFERENCE, DIRECT_EXISTING_DXF_AUDIT, reference_present ≠ NO)

A sample may verify or teach; it never supplies a missing source fact.

## 1. Firewall
- Before opening any sample, freeze `SOURCE_ONLY_SNAPSHOT` (census, groups/members, identity graph, face-graph state, witness ownership, output status, unresolved objects, claims with provenance). Customer DXF DATA is not a sample and is decoded normally.
- After exposure, statuses: `SOURCE_ONLY_SOLVED`, `SOURCE_ONLY_UNRESOLVED`, `REFERENCE_ASSISTED_UNDERSTANDING`, `REFERENCE_CONFLICT`, `CUSTOMER_CONFIRMATION_PENDING`. A claim unresolved before exposure becomes PROVED only with new non-reference evidence; otherwise `POST_REFERENCE_SOURCE_REWRITE` (`tools/reference_exposure_guard.py`). A session that has seen the sample cannot claim a blind solve.
- Sample geometry marked FLAG/Magenta/pending = `CUSTOMER_CONFIRMATION_PENDING`: never fills a dimension, never becomes production geometry or a rule.

## 2. Calibration (new solve, then compare)
1. Solve from the PDF alone. 2. Compare with the sample: positions, sizes, topology, holes/slots, R/C, flat extent, bend pairs and clipping, code mapping. 3. Name each mismatch: `DATUM`, `CHAIN/BASELINE`, `STEP DIMENSION`, `FEATURE TYPE`, `FEATURE-COUNT`, `C/R TOPOLOGY`, `REFERENCE/FORMED-DIMENSION`, `UNFOLD TRANSFORM`, `BEND-SEQUENCE`, `CONTAINMENT`, `CODE/SCHEMA`, `MISSING/AMBIGUOUS PDF DIMENSION`, `DXF-ONLY SHOP FEATURE`. 4. Only the general cause becomes a proposed lesson (FACT → ROOT_CAUSE → LESSON) in the report; coordinates stay job evidence.
- A sample difference the PDF cannot support is a production-CAD adjustment or conflict → ask; never taught silently. A newer revision on the PDF is still reported.
- Apply the shop Laser R before comparing: matching DXF-only R0.5/R2 is expected.

## 3. Direct audit of an existing AI DXF
Compare the two DXFs first (`tools/dxf_census.py` on both gives parts top-to-bottom; proved code clusters, proved units, layout translation removed): outer/inner boundaries, each hole family (type, Ø, qty, coordinates), R/C, flat extent, each bend pair and its clipping. ARC+LINE ≡ exact bulged polyline. Report MATCH / PARTIAL / DIFF per code, protect MATCHed parts, then use the PDF to explain each error.

## 4. Numbers
- Sample `$INSUNITS` is metadata: verify units against PDF dimensions (520315-18_ss.dxf says inch but is mm — never ×25.4). Output always mm.
- Exact printed inputs get no tolerance; only derived values may differ by strictly < 0.01 mm.
- Exact duplicate sample entities → normalise for counting, report `REFERENCE_ANOMALY`.

## Lessons
`regression/lessons/REFERENCE/` — 520217-26 (direct audit), 520315-18 (units), 521007-07 (firewall), 521016-13 (sample audit), 520925-03 (reference-assisted).
