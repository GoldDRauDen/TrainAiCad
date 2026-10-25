# BEND_ACUTE — included angle ≤85° (85 inclusive)

Overrides the generic ID→OD tangent offset for that bend. Needs proved t, angle, both faces, free edges, inside surfaces and Rin (shop method HD.dxf: Rin 0.6 unless the drawing states another).

1. Inside-surface choice and each face direction `d_i` (free edge → bend) come from formed topology, never from matching a sample.
2. Offset both inside lines by Rin toward the curvature; their intersection is the centre C; `Rout = Rin + t`.
3. `OD_i` = free edge to the OUTSIDE envelope (外寸法), never the sharp intersection (交点):
   `python tools/acute_bend.py od --t T --angle A --rin RIN --inside a1 a2` (a_i = inside length from free edge to the sharp inside corner; `OD_i = a_i − Rin/tan(A/2) + Rin + t`).
4. Then Nobi: `L_flat = OD1 + OD2 − Nobi`; from face 1: line1 = `OD1 − Nobi`, line2 = `OD1`. No handwritten Nobi on a non-90° bend → `SPLIT_FLANGE_10MM` (`BEND.md` §6).
5. Unresolved angle/radius/face/normal sign → FLAG that bend; a sample may confirm, never supply, an OD.

Trace to keep: `view | face1 | face2 | t | angle | free edges | inside lines | Rin source | C | Rout | OD1 | OD2 | Nobi source | flat | line pair`.

Lessons: `regression/lessons/BEND/ACUTE_BEND_LT85_APPROVED.md` (fixture t3, 75°, Rin0.6 → OD 182.01 / 49.71; `tests/test_golden_formulas.py`), 520925-03 056135 (83.66°, t4.5, OD 121.93/56.90, handwritten Nobi 6.70).
