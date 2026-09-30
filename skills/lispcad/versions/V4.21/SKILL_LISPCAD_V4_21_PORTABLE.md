# SKILL_LISPCAD V4.21 PORTABLE — Customer DATA Geometry Preservation Hard Gate

**Status:** CURRENT production release candidate, user-approved 2026-09-30.

## 0. Inheritance / mandatory base
V4.21 is an immutable delta release over V4.20. It does not replace, weaken or rewrite prior production rules.

Before using V4.21, read **all** of:
1. `skills/lispcad/versions/V4.20/SKILL_LISPCAD_V4_20_PORTABLE.md`
2. `references/SOURCE_DATA_CLASSIFICATION.md`
3. `references/PDF_DATA_RAW_GEOMETRY_PRESERVATION.md`
4. any other modules/references/regressions required by V4.20 for the actual drawing.

If a V4.21 statement conflicts with V4.20 only on the PDF+customer-DATA extraction behavior described below, V4.21 takes precedence. All Nobi, material, topology, BEND, KEGAKI, RIB, feature, output and QA rules not explicitly changed here remain V4.20.

## 1. Approved V4.21 production lesson
For **every job** where the customer supplies PDF/image plus corresponding customer DXF/CAD DATA:
- classify as `PDF_DATA_RAW` unless the user explicitly declares the DXF to be sample/approved/reference;
- customer DATA is the geometry authority;
- PDF is the semantic/control authority.

Existing DATA geometry must be **harvested, cleaned and preserved**, not reconstructed from PDF arithmetic, bbox, screenshot measurement or visual approximation.

## 2. Required workflow
1. Read PDF first to lock code/page mapping, physical scale, view/face semantics, witnesses/datums, revision/handwriting, Nobi and feature meaning.
2. Extract actual source primitives/curves from the corresponding DATA.
3. Remove frame/title/dimension/text/hidden/construction/thickness duplicates and unrelated views.
4. Preserve each retained face/view in source-local coordinates.
5. Assemble/unfold only by source-proved translation, rotation, reflection and physical scale conversion plus active bend/Nobi placement.
6. Do not redraw a face merely because its printed dimensions are known.
7. Canonicalize only when a PDF/manufacturing rule explicitly controls the production parameter; record each canonicalized element and its reason.
8. Run source reprojection before production PASS.

## 3. Source-reprojection hard gate
For every non-canonicalized face/feature:
- inverse-transform output geometry back to the extracted DATA source;
- residual may only be CAD serialization/numerical precision;
- measurable redraw drift is FAIL;
- DATA<->PDF customer delta thresholds are not redraw tolerances;
- bbox/flat-size closure alone is not proof of geometry fidelity.

CUT, HOLE/SLOT, BEND, KEGAKI and RIB remain independently audited under V4.20.

## 4. Drawing scale
Prove scale separately for each corresponding PDF page/view/DATA source. Do not force one scale across all attached DATA files. A proved 1:2 drawing is converted to physical geometry by x2 before assembly; that conversion is a source transform, not a redraw.

## 5. 646 DATA-required routing
Job family `646` is expected to include customer DATA by default.

If a 646 production job has no corresponding customer DATA:
- status `DATA_REQUIRED_MISSING`;
- ask the user for DATA;
- do not silently route to PDF_ONLY;
- do not generate production flat geometry until resolved.

Once DATA is present, 646 uses the same universal PDF_DATA_RAW rules as every other job.

## 6. Approved regression
Read `regression/qa/520930-03_V4_21_APPROVED.md`.

Case-specific values in that regression are assertions only and must never be reverse-fit into unrelated jobs.

## 7. Negative regression
FAIL if existing DATA geometry is redrawn from PDF dimensions; source endpoints/radii/centers are rounded without explicit canonicalization; per-page scale is ignored; unproved mirror/rotation is applied; small redraw drift is accepted under customer tolerance; or 646 proceeds PDF-only while required DATA is missing.
