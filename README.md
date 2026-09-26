# TrainAiCad — DXF-first production (V4.10)

TrainAiCad is a user-calibrated CAD production skill repository, **not an automatic training environment**. Only user-approved rules enter the production skill. Begin with [AI_ENTRYPOINT.md](AI_ENTRYPOINT.md).

## V4.8 approval — 520709-07 (2026-09-26)

The user approved one narrowly scoped manufacturing interpretation rule: a clearly struck-out COMPLETE hole-family callout with an unambiguous leader deletes all its holes even when obsolete circle symbols remain visible. Crossing out only tolerance/finish never automatically deletes holes; unclear scope requires a question. Regression 039915 requires an OD external-step datum (25, not 22.36); 039918/039919 require slope 50, correct printed M4/Ø5 groups and exact corrected reflection; 040006 requires deleting its entire 2-Ø8H7 group, preserving 6-M8 and 4-Ø9. See [approved regression](regression/datum/520709-07_APPROVED.md). V4.7 export and V4.6 engineering remain unchanged; V4.7 snapshot is preserved.

## Approved V4.10 drawing-origin and axis rule (2026-09-26)

The user **directly approved** the previously proposed source-frame lesson using original drawing `520728-06` code `043793` (page 4): the absolute coordinate origin is the part's **top-left**, its proven height is `138 mm`, and all three Ø7 holes on the source `Y=-30 mm` row are at target bottom-left DXF `Y=138-30=108 mm` (NOT `88 mm`). For EVERY future absolute/ordinate drawing, first prove the source origin's real material edge/feature, source +X/+Y direction, target CAD datum, and then transform signed source ordinates; the location cannot be inferred from page position or CAD habits. Different views/formed faces require independently proved frames. Ambiguous frames stay FLAGGED; reference DXF is calibration after PDF interpretation, not a missing-coordinate source. See [approved regression](regression/datum/520728-06_043793_TOP_LEFT_APPROVED.md), [core rule](skills/lispcad/core/DATUM_DIMENSION.md), [arithmetic helper](tools/datum_coordinates.py) and [tests](tests/test_datum_coordinates.py). This approval does NOT resolve customer-pending `043796` Z lengths, `043797` two Ø? or `043799` 165° Nobi.

## Approved V4.9 output mode (2026-09-26)

**One DXF total by default**, not one DXF per code. It includes every code in the page-1 order, top-to-bottom, as nonoverlapping clusters with >=10 mm layout-only clearance and the exact code visibly labeled on non-cut `AI_META`. No default external manifest or individual files. If any source Ø/Nobi/unfold datum is unresolved, the one output becomes `<JOB>_ALL_REVIEW_ONLY.dxf` including all part groups, separate proved source views if no safe flat is possible, Magenta estimated numeric features/FLAGs where authorized, and global **NO CUT** warning. A production `<JOB>_ALL.dxf` is possible only when ALL included codes independently PASS. Operators exclude `AI_META` labels from CAM cutting. Optional individual DXFs, manifest, legacy dual output and `c:DRAW` Lisp require explicit requests.

**Output-only change:** V4.9 leaves all V4.8 and earlier approved geometry/manufacturing rules intact: PDF-first contour/datum/count verification, Nobi, material Laser R, SUS430 process-specific routing, Cu/Brass t6, scoped POINT/CIRCLE, and confirmed 055958 single connected Green slit. A customer-uncertain value in 520728-06 remains a case-specific FLAG, not a new universal rule. V4.8 and V4.7 historical releases are immutable. See [V4.9 export regression](regression/export/DXF_SINGLE_COMPOSITE.md).

## Current modules and implementation

- [Portable current V4.10](skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md), identical to [immutable V4.10 release](skills/lispcad/versions/V4.10/SKILL_LISPCAD_V4_10_PORTABLE.md); [historical V4.9](skills/lispcad/versions/V4.9/SKILL_LISPCAD_V4_9_PORTABLE.md) preserved; [historical V4.8](skills/lispcad/versions/V4.8/SKILL_LISPCAD_V4_8_PORTABLE.md) preserved; [historical V4.7](skills/lispcad/versions/V4.7/SKILL_LISPCAD_V4_7_PORTABLE.md) preserved. [Historical V4.6](skills/lispcad/versions/V4.6/SKILL_LISPCAD_V4_6_PORTABLE.md) preserved.
- `skills/lispcad/core/`: DRAWING_READING, DATUM_DIMENSION, VALIDATION, CAD_OUTPUT; load all before working.
- `skills/lispcad/{modes,topology,features}/`: load all applicable composable manufacturing rules.
- `references/`: full approved material, Nobi and metric-thread pilot tables.
- `regression/`: approved drawing cases and `export/DXF_SINGLE_COMPOSITE.md` for approved V4.9 default (`export/DXF_DUAL_EXPORT.md` is historical legacy).
- `tools/DXF_INPUT_SCHEMA.md` and `tools/export_dxf.py`: independently verified geometry interface and DXF serialization/read-back; `tests/test_export_dxf.py` uses synthetic input.

## Production sequence

Interpret the PDF independently, calculate manufacturing geometry once, and run real Section 5 validation BEFORE declaring canonical data PASS. Serialize identical checked part-local data as translated clusters into ONE code-labeled top-down DXF, then verify its source-to-cluster equivalence, metadata labels and review status. Optional requested individual DXFs/manifest must use the SAME data. Prove the absolute drawing source origin/axis signs before calculating coordinates, as in V4.10's 043793 regression. A reference DXF is calibration ground truth only after user declaration. Optional `c:DRAW` Lisp uses that SAME verified model if requested. A structural file audit or synthetic exporter test never substitutes for PDF-specific datum, material or geometric containment verification.

```bash
python -m pip install -r requirements.txt
python tools/export_dxf.py job.json out/  # one labeled ALL.dxf or ALL_REVIEW_ONLY.dxf
python -m pytest tests/ -q
```

New engineering lessons require separate direct user approval. GitHub is a portable storage for approved production skills, not a substitute for that review.
