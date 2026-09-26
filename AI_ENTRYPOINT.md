# AI ENTRYPOINT — V4.7 DXF-first

Current production release is **V4.7 OUTPUT on the unchanged approved V4.6 ENGINEERING baseline**. Direct DXF is the default. Optional AutoLISP exists ONLY when the user expressly requests it. The existing lispcad module paths remain stable for backwards-compatible imports.

## Mandatory load order

1. Read ALL core files in `skills/lispcad/core/`: `DRAWING_READING.md`, `DATUM_DIMENSION.md`, `VALIDATION.md`, `CAD_OUTPUT.md`.
2. Inspect the actual PDF drawing/marked ROI before selecting specialized modules. Trace the real contour, explicit features and quantity callouts, and actual dimension extension-line endpoints BEFORE computing any coordinate. Lock barcode, material, thickness and applicable handwritten revisions.
3. Load `modes/FLAT_NO_BEND.md` or `modes/BEND_UNFOLD.md`; load ALL applicable topology and feature modules. A drawing may require multiple topology types.
4. Load material/Nobi/thread references where applicable. Keep every V4.6-approved rule: scoped PIERCING/POINT/CIRCLE; material-table Laser R; SUS430 SS Nobi versus SUS/他 laser R/hole rules; Cu/Brass t6; independently proven R=t relief and the `055958` ONE connected three-primitive slit.
5. Perform actual Section 5 PDF-semantic/manufacturing verification BEFORE marking canonical geometry PASS. A reference DXF can calibrate independently read PDF geometry ONLY when user-declared as ground truth; never borrow its hidden dimensions.
6. From ONE canonical checked part-local mm geometry model, deliver direct **individual** `<JOB>_<CODE>.dxf`, **combined** `<JOB>_ALL.dxf`, and `<JOB>_MANIFEST.json`. Combine translated copies of the identical individual geometry, ordered top-to-bottom by declared part order with at least 10 mm layout-only gap. Reopen/audit each actual DXF. Read `tools/DXF_INPUT_SCHEMA.md` and `regression/export/DXF_DUAL_EXPORT.md`.
7. Generate optional `c:DRAW` AutoLISP only by explicit request, from identical canonical geometry. Never silently substitute Lisp if DXF creation fails. Numeric-only user-requested FLAGGED Magenta previews stay in separate `_PREVIEW.dxf` files, never in production `_ALL.dxf`; critical unproved topology/type/bend order/material/datum blocks production export.

## Portability, approval and historical precedence

Current standalone file: `skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md`, identical to immutable `skills/lispcad/versions/V4.7/SKILL_LISPCAD_V4_7_PORTABLE.md`. Immutable **V4.6** and earlier V4.3–V4.5 are historical; do not modify snapshots. Older V4.3 blanket DXF-only-R0.5 omission and green-by-default Piasu are superseded by approved V4.4–V4.6 material/POINT rules. Historical regression documents that preserve obsolete assumptions cannot override active technical rules.

The user directly approved this V4.7 DXF output migration on 2026-09-26. That approval does NOT approve a new geometric/material lesson, alter regression source evidence or resolve the outstanding `055957` special-J and customer-unconfirmed dimensions. New lessons enter production only after separate direct user approval. GitHub stores portable production skills, not training state.
