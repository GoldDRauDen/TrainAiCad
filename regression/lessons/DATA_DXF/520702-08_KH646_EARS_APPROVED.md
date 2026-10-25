# 520702-08 / 26-038384 — KH646 plan view with ears and web; slip size is not proof (approved 2026-10-25)

Rule: `rules/DATA_DXF.md` §1 step 5. Tool: `tools/data_part.py` (`data_faces`). Test: `tests/test_data_part.py`.
Source (user, local): `template/DataKH646/SX-4A69433-C1A-05.dxf` + `520702-08-646.pdf` p2 (SPCC t2.3, 1:3).

**FACT:** the plan view is 640 x 40 with a 2-Ø5 note `あける` (drill/open) at 5 from each end. The user confirmed the
Ø5 holes are on the two ears. The profile is a U (legs 50.2 inside, web 611.4 inside) with ears turned out at the top
(12 inside); the handwritten check is 640 + 4.6 + 54.8 + 54.8 − 4.62 × 4 = 735.72 = the slip size.

**ROOT_CAUSE:** the first reading took a 2-bend U (legs 52.5, web 640): its flat 735.76 sat 0.04 from the slip, so
it looked right, and the Ø5 fell into a bend zone. Only one face per DATA view could be mapped.

**LESSON:** read every face OD from the profile (ears 14.3, legs 54.8, web 616) before trusting a flat; a flat close to
the slip size proves nothing. One plan view can show several flat faces: map each with its own datum (ears from their
tips, web from the legs' outer faces) via `data_faces`.
