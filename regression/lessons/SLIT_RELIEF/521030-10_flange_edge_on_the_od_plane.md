# 521030-10 26-064687/064688 — flange edge on the OD plane, S = 0 at all eight bend ends

**FACT.** SPHCP t1.6 hat (chain lip 26.6 – flange 62 – web 150 – flange 62 – lip 26.6, Nobi 2.64 handwritten, flat 316.64 × 275). Flanges 275 wide, web 155 (60 | 155 | 60), two 30 wide ear tabs flush with the web edges. First build put each flange's free edge one Nobi inside the formed edge (line2 / line1 − N), so S = +2.64 and the tool drew no slit. The user corrected it: no step (S = 0), every bend end (4 web ends + 4 ear ends) carries a slit.

**ROOT_CAUSE.** Coordinates were derived by hand from `lookup.py unfold` bend lines and the OD planes were mistaken for the flange-side lines. A face dimensioned outer plane to outer plane spans exactly its OD: face k = `[line1 of bend k−1, line2 of bend k]` (flange 62: 23.96 → 85.96). Its free edge at the formed edge is therefore ON the narrow neighbour's side bend line.

**LESSON.** Place a free flange edge at the face's `start`/`end` (now printed by `lookup.py unfold` as `faces`), S = 0, slit `T+0.2` at each such end. Never retreat by Nobi. Notch depth measured from the formed edge (25) is measured from that same edge (292.68 − 25 = 267.68).

**TOOL.** `bend_corner.end_step` took the first collinear run on the web-edge line (a tab edge at Y = 60) as the flange side edge and put a bogus slit (S −204) at the wrong corner while the real corner got none. It now takes the run nearest the bend zone; `tests/test_bend_end_collinear_tab.py` fixes the 8-slit result for the part and its mirror.
