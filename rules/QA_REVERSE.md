# QA_REVERSE — audit an existing DXF (only when the user says QA / "QA file này" / "QA ngược")

Never loaded by E2E. Intent unclear between creating and auditing → say so before acting.

## 1. Role
`ROLE = QA_AUDITOR`; the DXF is the `AUDIT_TARGET`, never evidence of itself. SELF_QA: freeze the exact saved file first, do not edit it during the audit. Default: READ → COMPARE → CHALLENGE → REPORT; no replacement DXF, no rule change, no push unless asked separately.

## 2. Sequence
Read the source (PDF/image/DATA) → decode DATA curves (`DATA_DXF.md` §1) → map code ⟷ view ⟷ DATA cluster ⟷ target cluster → note/group/member expectation → census + `resolve_rules.py` → read the routed cards → expected state → decode the target (`tools/dxf_census.py`) → reverse diff per feature → holistic challenge (`VALIDATE.md` §5) → result.

## 3. Acceptance
- With DATA: outside a rule-approved changed scope the target must reproduce DATA physically (endpoints, arcs, circles, decoded bulges); any unexplained drift is FAIL even below 0.1 mm.
- PDF numbers: `|DXF − PDF| < 0.1 mm` is not a defect only when identity, topology, group ownership, datum meaning, R vs C, bend face/order/attachment, host-face mapping and rule selection are all correct. Always FAIL regardless of size: wrong R/C family or rule R, missing/extra feature, wrong pilot, wrong attachment/flange direction, wrong group, bulge flattened to a chord, DATA drift.
- Check per family: contour, HOLE/TAP/PIASU, slots, R/C and auto R, BEND/Nobi/attachment/domain/local→flat, KEGAKI, SLIT/relief, RIB/weld ownership, revisions, notes, identity, group quantity/datum. Never PASS from bbox, entity count or looks.

## 4. Result
First line `QA RESULT: PASS | FAIL | FLAGGED`. Then per code only the defects: `CODE | FEATURE | EXPECTED | ACTUAL | DELTA | WHY | SEVERITY` (CRITICAL = wrong topology/identity/attachment, missing/extra feature, DATA change, duplicate path; MAJOR = wrong R/C, hole/tap, slot, Nobi/bend position, material rule, numeric error over the threshold; MINOR = other numeric deviation). Not understood → say so, name the blocker class, ask; disagree with the user when the evidence says so.
