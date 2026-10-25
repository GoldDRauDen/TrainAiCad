# 521016-13 sample audit lessons (user DUYỆT 2026-10-16)

Evidence only; not routed. Sample `17c8cd3b-521016-13_SS.dxf` was used to audit, never to supply parameters.

| Lesson | Enforcement (no new rule file) |
|---|---|
| Blank Oy<=100 & Ox>=1000 needs J/LJ POINT+TEXT h10 on top edge (Laser_SheetMetal) | `export_dxf.jlj_marks_check`; one line in `CAD_OUTPUT.md`; tests in `test_export_dxf.py` |
| Valid CW/CCW stadium slot was rejected; S-shape accepted | `slot_anchor.stadium_geometry` same-sign semicircle bulges; tests |
| Slot witness target could not use the slot polyline | `holistic_engineering_guard` accepts slot LWPOLYLINE via its anchor record midpoint; test |
| Step height read from a hole-row dimension (607/608 30 vs 25); OD +t on wrong face (605) | one bullet + one sentence in `FORMED_PROFILE_OD_MEASUREMENT.md` |
| Symbolic Ø3 markers; undimensioned same-family notch | two sentences in `REVIEW_PREVIEW_POLICY.md` |

Not enforced by code (visual reading cannot be gated): 611 chamfer count, 614 unfold derivation. Customer confirmation pending: 060607 three Ø7 holes.
