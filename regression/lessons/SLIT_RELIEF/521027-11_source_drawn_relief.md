# 521027-11 26-063377 — box corners already drawn by the DATA (3.5 x 3.5 void, R1): no slit

**FACT.** SPCC t1.2 tray (base 280 x 65, four flaps 73, Nobi 2.14 handwritten, flat 421.72 x 206.72). The customer DATA draws at every box corner a square void 3.5 x 3.5 (outer dims) with R1 on its inner corner in the base, in the end flap (69.5 left to the free edge) and in the long wall (end set back by t), plus callouts 4-R1, 2x2-R1, (2-R1) and the note `A部4ヶ所角は球面状にR取り(R1)のこと 手仕上げ`. First build ran `boxmet_job.py` (census BOXMET stayed UNKNOWN), drew four Green slits and called the note hand finishing. The user corrected twice: the note is DATA used for cutting, build the corner as drawn, no slit.

**ROOT_CAUSE.** No rule said a drawn relief is the junction mechanism; `CENSUS.md` triggered BOXMET on "base + four flanges" alone. The spec tool refused a relief overlapping a bend zone ("build by hand") and `bend_end_guard` only knew BOXMET / `OPPOSITE_FOLD_R_T` / `CUSTOM_SOURCE_SLIT`, so the hand-built part fell to PREVIEW.

**LESSON.** Per bend end and box corner record `relief drawn` (PDF and DATA) before any slit. Drawn → `SOURCE_DRAWN_RELIEF`: the outline carries the relief, bend lines stop at it, no Green entity. Slit only when none is drawn and the gate requires it. A slit that starts at the intersection of two outer edges carries the lead (offset LeadVal, SUS t6 → 6|6, R0.5).

**TOOL.** `bend_end_guard` accepts `SOURCE_DRAWN_RELIEF` (source group, SOURCE members, `relief_point` in the void, bend lines outside it, no second relief) and checks the lead of a custom slit at an edge intersection; `slit_geometry.custom_slit_at_intersection`; `boxmet_job --drawn-corners RELIEF` refuses; `tests/test_source_drawn_relief.py`.
