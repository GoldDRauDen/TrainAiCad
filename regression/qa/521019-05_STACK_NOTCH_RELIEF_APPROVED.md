# 521019-05 — projection reading, notch census, stacked plates, bend-end relief inventory

**Status:** USER APPROVED / PUSH 2026-10-19 (Project TrainAiCad, KH843, 7 codes, PDF only). All coordinates are per-part local frames, PDF orientation, origin = bottom-left of the flat.

## FACT -> ROOT_CAUSE

| Topic | FACT (coordinates) | ROOT_CAUSE of the earlier error |
|---|---|---|
| Projection / dx | 26-061249: 三角法 title block; in the top/bottom views the web is edge-on at the rear, flanges toward the viewer => main view = INNER face (dx). Tab at the LEFT end (thick edge-on line at the left end of both strips), on the TOP flange of the main view: x 0..36.2, y 127.5..157.5; 32.3 = 30 + t2.3; 3 R10 (2 right-end free-edge corners, 1 tab corner). | Tab placed at the right / full width from adjacency; projection method not applied. |
| Notch census | 061122: notch 50x100 at x 850..900, y 350..450, so bend and flange are 350 long. 061249: partial tab instead of a full flange. | Notches silently omitted instead of built / cancelled / FLAGged. |
| Notch wall at OD plane | 061138: x = 722.4 - 275 = 447.4 for y 350..540 (not 450). | Wall taken at the absent neighbour's OD. |
| C beside a bend | 061113: C50 chord (700,510)-(650,560) ends on the bend line, flange x 0..650; 4xC3 = 2 on the face free end + 2 on the flange. | C placed at the flange's far corner. |
| Stacked plates | 061137 (t2, Nobi 3.0) lies on 061122 (t2): bends x 748.62/751.62 (line2 = vertex of 061122's lower contour offset by t); flange OD = 338.97 (offset slanted edge); total 751.62+338.97-3.0 = 1087.59; whole bottom edge y=2 (x 0..1087.58); flange y 2..150. The yellow offset line is reference only. | PDF dimensions read as part dimensions, not assembled dimensions. |
| Bend-end relief inventory | Relief (S=0): 061113 (650,560); 061138 (447.4,350); 061137 (751.62,150). No relief: collinear ends 061113 (0,557.4-560), 061138 (447.4-450,0), 061137 (748.62-751.62,2), 061122 (896.4-900,0); and S>0 at 061122 (896.4-900,350). | KH843 note "no auto-SLIT" misapplied to BEND_END_OFFSET_90; ends not inventoried. |

## APPROVED LESSON (edited in place, one owner each)

1. `DRAWING_READING.md`: notch census states + projection reading.
2. `FORMED_PROFILE_OD_MEASUREMENT.md` §3: wall at the face's own OD plane; tab width includes t.
3. `CHAMFER_RADIUS.md`: C beside a bend ends on the bend line; per-view n-calls are different corner sets.
4. `ASSEMBLY_DATUM_CLOSURE.md`: stacked parts (assembled dimensions, unsaved reference line, retreat tA).
5. `BEND_EDGE_RELIEF_90.md`: notch shortens bend-edge length; per-end inventory (parallel -> no corner B).
6. `CUSTOMER_CAD_RULES.yaml` KH843: the no-auto-SLIT note covers the Nobi-centre slit only.

## REGRESSION_CASE

`tests/test_521019_05_lessons.py` (phrase pins + arithmetic + `connected_slit` geometry that reproduces the user's sample entity-for-entity).
