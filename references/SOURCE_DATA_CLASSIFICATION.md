# SOURCE_DATA_CLASSIFICATION — V4.25 repo-direct source routing

## Source relationship classes and mode loads (moved from AI_ENTRYPOINT.md §6)

Classify exactly one source relationship using this section:
- `PDF_ONLY`
- `PDF_DATA_RAW`
- `TRAIN_REFERENCE`
- `DIRECT_EXISTING_DXF_AUDIT`

For `PDF_DATA_RAW`, the router loads `references/DATA_RAW_TO_MANUFACTURING_CONTRACT.md`. Customer DATA supplies physical geometry; PDF controls semantics, dimensions, revisions and manufacturing meaning under the approved rules.

V4.25 requires `RAW_DATA_SNAPSHOT`, `PHYSICAL_DATA_BASELINE`, `SAME_PARAMETER_GATE`, `MANUFACTURING_CHANGE_LEDGER` and `UNTOUCHED_DATA_INVARIANCE_CHECK`. V4.26 additionally requires decoded physical LINE/ARC/CIRCLE preservation for bulged polylines.

For reference/sample calibration of a new/source-only solve, freeze `SOURCE_ONLY_SNAPSHOT` before exposing or decoding the sample/reference geometry; customer DXF DATA remains source-authoritative and is decoded normally. After freeze, compare physical reference geometry without reverse-fitting the source interpretation. DIRECT_EXISTING_DXF_AUDIT may compare existing AI DXF ↔ sample as required by that audit mode, but any later claim about what the original source alone established remains bounded by the frozen/pre-existing source evidence. V4.30 additionally requires same-physical-parameter identity before a numeric source/reference conflict is declared.


## Customer policy and DATA contract

Select numeric customer-code exceptions under `CAD_CUSTOMER_POLICY.md`; do not confuse a numeric customer with job-family 646. Every `PDF_DATA_RAW` job must execute `DATA_RAW_TO_MANUFACTURING_CONTRACT.md` for complete harvest/classification, RAW_DATA_SNAPSHOT, PHYSICAL_DATA_BASELINE, SAME_PARAMETER_GATE, MANUFACTURING_CHANGE_LEDGER, unchanged DATA invariance and bidirectional/source reprojection. Its customer thresholds never permit redraw drift.

## 1. Four source relationships

### PDF_ONLY
PDF/image is the source geometry. During explicit training/calibration workflows, absence of an unprovided DATA DXF is not a reason to ask whether one exists; continue from PDF. In ordinary production, if a page visibly carries a boxed/stamped `DATA` mark but its CAD DATA is absent, report `DATA_EXPECTED_MISSING` when the current task requires that DATA.

### PDF_DATA_RAW
Use when customer CAD/DXF is supplied together with the corresponding PDF/page. A boxed/stamped `DATA` mark on the PDF is evidence that CAD DATA exists for that page. PDF + DXF supplied together defaults to `PDF_DATA_RAW` unless the user explicitly declares the DXF to be a clean/sample/approved/training reference.

DATA supplies physical source geometry; PDF supplies semantic/manufacturing control. Execute `DATA_RAW_TO_MANUFACTURING_CONTRACT.md` before canonicalization and saved-DXF QA. Do not redraw existing DATA or call an AI-selected subset a complete census.

### TRAIN_REFERENCE
User explicitly declares the DXF as sample, clean/extracted drawing, approved/ground-truth CAD or training comparison artifact. It is audit/calibration evidence, not raw DATA for direct extraction. For NEW construction, interpret source independently first.

### DIRECT_EXISTING_DXF_AUDIT
When evaluating an already-exported AI DXF against an approved reference, compare those two DXFs first in proved physical units/orientation, report MATCH/PARTIAL/DIFF per code, then use PDF/source to diagnose causes.

## DATA comparison and canonicalization

The DATA contract owns same-physical-parameter comparison, customer policy, local manufacturing changes and untouched invariance. General `Delta < 0.1 mm` passes and `Delta >= 0.1 mm` flags; explicitly identified KH433 uses 1.0 mm instead. Exactly 0.1 mm FLAGS under general rules. Numeric allowance never waives topology, feature identity/count, source ownership or unchanged-curve preservation.

## 4. V4.21 646 DATA-required routing
For production job family `646`, corresponding customer DATA is expected by default. If it is absent: status `DATA_REQUIRED_MISSING`; ask for DATA; do not silently downgrade to `PDF_ONLY`; do not generate production geometry until resolved. Once DATA is present, the same universal PDF_DATA_RAW geometry-preservation rules apply as for every other job.
