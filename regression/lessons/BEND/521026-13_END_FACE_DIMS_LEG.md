# 521026-13 / 26-063295 — non-90° section dims that stop at the plate end faces (user DUYỆT 2026-10-26)

Rule: `rules/BEND.md` §4; executable `python tools/lookup.py leg`, `tests/test_lookup.py::test_leg_od_of_a_non90_bend_from_end_face_dims`.

## FACT
- Section of 26-063295: tab 35 (to the tab end face), plate 65 (along its outer face from the end-face corner), t6, 120°, Nobi 4.92. The job used 35 and 65 as ODs: flat 95.08, web edge at the bend line.
- HD: OD1 = 35 − 6·tan30° = 31.536, OD2 = 65 + 6/cos30° = 71.928, flat 98.544, bend lines 67.008 / 71.928, plate edge between the tabs at 65 (the plate's own length). Same family as 26-062885 (30 / 50, t6, 100° → 28.942 / 56.093).

## ROOT_CAUSE
`AI_RULE_MISAPPLICATION`: the weld → bend special case was read as "only for a weld". The section had no OD (both plates drawn with thickness), so the outer faces had to be extended to their intersection.

## LESSON
When the projection does not form the OD, draw the outer faces to their intersection: `OD1 = a − t·tan d`, `OD2 = b + t/cos d`, `d = angle − 90` (tool `lookup.py leg`). When the OD is already formed, do not redraw it.
