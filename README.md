# TrainAiCad — DXF-first production (V4.7)

TrainAiCad is a user-calibrated CAD production skill repository, **not an automatic training environment**. Only user-approved rules enter the production skill. Begin with [AI_ENTRYPOINT.md](AI_ENTRYPOINT.md).

## Approved output mode (2026-09-26)

**Direct DXF is the default; AutoLISP is available only on explicit request.** For every eligible job, output **both** an individual `<JOB>_<CODE>.dxf` per production-PASS part and `<JOB>_ALL.dxf` containing each part exactly once in declared job-list order, top-to-bottom. Supply `<JOB>_MANIFEST.json` listing mapping, material, thickness, counts, individual bounding boxes and composite offsets. Minimum 10 mm *layout-only* clearance; this is not nesting or a machining allowance. Audit/reopen actual saved DXFs. Numeric-only, user-requested Magenta `_PREVIEW` files stay separate from production combined DXF.

**V4.7 changes output architecture ONLY.** All V4.6-approved manufacturing rules stay in force: PDF-first contour and datum graph, feature-family counts, mid-tolerance/Nobi/unfold, material Laser R, SUS430 process-specific routing, Cu/Brass t6 override, scoped POINT/CIRCLE and the ONE connected Green slit (three CAD primitives) of `055958`. Unresolved `055957` special-J and customer-unconfirmed dimensions remain FLAGGED. V4.3–V4.6 version snapshots are immutable and older superseded V4.3 R0.5/green Piasu assumptions do not override V4.6.

## Current modules and implementation

- [Portable current V4.7](skills/lispcad/portable/SKILL_LISPCAD_CURRENT.md), identical to [immutable V4.7 release](skills/lispcad/versions/V4.7/SKILL_LISPCAD_V4_7_PORTABLE.md). [Historical V4.6](skills/lispcad/versions/V4.6/SKILL_LISPCAD_V4_6_PORTABLE.md) preserved.
- `skills/lispcad/core/`: DRAWING_READING, DATUM_DIMENSION, VALIDATION, CAD_OUTPUT; load all before working.
- `skills/lispcad/{modes,topology,features}/`: load all applicable composable manufacturing rules.
- `references/`: full approved material, Nobi and metric-thread pilot tables.
- `regression/`: approved drawing cases and `export/DXF_DUAL_EXPORT.md` for dual-export.
- `tools/DXF_INPUT_SCHEMA.md` and `tools/export_dxf.py`: independently verified geometry interface and DXF serialization/read-back; `tests/test_export_dxf.py` uses synthetic input.

## Production sequence

Interpret the PDF independently, calculate manufacturing geometry once, and run real Section 5 validation BEFORE declaring canonical data PASS. Serialize identical data to the individual DXFs and translated composite, then verify the files and manifest. A reference DXF is calibration ground truth only after user declaration. Optional `c:DRAW` Lisp uses that SAME verified model if requested. A structural file audit or synthetic exporter test never substitutes for PDF-specific datum, material or geometric containment verification.

```bash
python -m pip install -r requirements.txt
python tools/export_dxf.py job.json out/
python -m pytest tests/ -q
```

New engineering lessons require separate direct user approval. GitHub is a portable storage for approved production skills, not a substitute for that review.
