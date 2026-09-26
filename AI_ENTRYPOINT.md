# AI ENTRYPOINT — V4.9 single-composite DXF approved output on V4.8 engineering

Current production release is **V4.9**. It changes ONLY the output default to ONE code-labeled top-to-bottom composite DXF, preserving every V4.8 hole-cancellation and PDF-grounded regression and earlier approved manufacturing rule. Direct DXF remains the default. Optional AutoLISP exists ONLY when the user expressly requests it. The existing lispcad module paths remain stable for backwards-compatible imports.

## Mandatory load order

1. Read ALL core files in `skills/lispcad/core/`: `DRAWING_READING.md`, `DATUM_DIMENSION.md`, `VALIDATION.md`, `CAD_OUTPUT.md`.
2. Inspect the actual PDF drawing/marked ROI before selecting specialized modules. Trace the real contour, explicit features and quantity callouts, and actual dimension extension-line endpoints BEFORE computing any coordinate. Lock barcode, material, thickness and applicable handwritten revisions.
3. Apply V4.8 full-family crossed-out callout scope: delete every hole only if the entire callout and target leader unambiguously cancel the group; a partial H7/finish strike-through or unclear leader requires clarification. Record source canceled quantity and verify ZERO residual entities; preserve neighboring active families. Read regression/datum/520709-07_APPROVED.md.
4. Load `modes/FLAT_NO_BEND.md` or `modes/BEND_UNFOLD.md`; load ALL applicable topology and feature modules. A drawing may require multiple topology types.
5. Load material/Nobi/thread references where applicable. Keep every V4.6-approved rule: scoped PIERCING/POINT/CIRCLE; material-table Laser R; SUS430 SS Nobi versus SUS/他 laser R/hole rules; Cu/Brass t6; independently proven R=t relief and the `055958` ONE connected three-primitive slit.
5. Perform actual Section 5 PDF-semantic/manufacturing verification BEFORE marking canonical geometry PASS. A reference DXF can calibrate independently read PDF geometry ONLY when user-declared as ground truth; never borrow its hidden dimensions.
6. From ONE canonical checked part-local mm geometry model, deliver **ONE** composite DXF containing EVERY code in the page-1 order top-to-bottom, each cluster labeled with its exact code on non-cut `AI_META`, >=10 mm layout-only gap. If ANY code remains PREVIEW/VIEWS_ONLY/FLAG, emit only `<JOB>_ALL_REVIEW_ONLY.dxf` and global NO CUT warning; proved orthographic views remain separate in that code's cluster. Otherwise emit `<JOB>_ALL.dxf`. Reopen/audit that file and internal per-code mapping. Individual DXFs and external manifest only when explicitly requested. Read `tools/DXF_INPUT_SCHEMA.md` and `regression/export/DXF_SINGLE_COMPOSITE.md`.
7. Optional `c:DRAW` AutoLISP only by explicit request, from identical canonical geometry. Never silently substitute Lisp. Numeric-only user-authorized Magenta estimates may be included only in a global `REVIEW_ONLY - NO CUT` DXF with adjacent FLAG; unknown unfold dimensions/order may yield separate *proved source views*, NOT an invented flat. Ambiguous source-view identity/code mapping blocks all export.

## Portability, approval and historical precedence

Current standalone file: `skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md`, identical to immutable `skills/lispcad/versions/V4.9/SKILL_LISPCAD_V4_9_PORTABLE.md`. Immutable **V4.8, V4.7, V4.6** and earlier V4.3–V4.5 are historical; do not modify snapshots. Older V4.3 blanket DXF-only-R0.5 omission and green-by-default Piasu are superseded by approved V4.4–V4.6 material/POINT rules. Historical regression documents that preserve obsolete assumptions cannot override active technical rules.

The user directly approved this V4.7 DXF output migration on 2026-09-26. That approval does NOT approve a new geometric/material lesson, alter regression source evidence or resolve the outstanding `055957` special-J and customer-unconfirmed dimensions. New lessons enter production only after separate direct user approval. GitHub stores portable production skills, not training state.

The user separately approved ALL 520709-07 regression cases plus the explicit whole-group strike-through cancellation rule on 2026-09-26. This V4.8 approval does not endorse the original nine-code DXF export or certify unexecuted corrected DXF deliverables.

The user directly approved the V4.9 **single-composite code-labeled export** on 2026-09-26. This does not approve a new datum/manufacturing lesson: unresolved 520728-06 customer Ø/Nobi/Z-fold lengths remain FLAGGED, and the separate top-left datum lesson proposal remains unapproved.
