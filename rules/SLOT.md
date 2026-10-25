# SLOT — straight and curved slots (長穴)

Triggers: `長穴`, `n-長穴`, stadium shapes, `R` on slot ends, arc-shaped slots.

## Straight slot
- Classify every length: `OVERALL_LENGTH` (tip to tip) or `CENTER_DISTANCE C` (= straight tangent length). Store `L_TOTAL = C + W` when C is given; `W` = width = end diameter; `L_TOTAL ≥ W`. Unproved meaning → FLAG, never guess from looks or a sample.
- Anchor: a position dimension may land on `SLOT_MIDPOINT`, `ARC_CENTER_1/2` or `OUTER_TIP_1/2`; midpoint→arc centre = C/2, midpoint→tip = L/2 along the signed slot axis. Never infer the anchor from shape or value (521013-21: W6.6, C7.5, a 3.75 shift is FAIL). Canonical `slot_anchor_records` are checked by `tools/slot_anchor.py`.
- Width/R come from the slot's own callout and witnesses, never a nearby number of another chain (520929-10: W9/R4.5, not 10/5).
- `4-R` aimed at the four ends of two stadium slots of W12 → four R6 ends. A bare `R` leader on the end of a width-dimensioned slot/open notch (`2-8.5`) = R W/2, no FLAG.
- Canonical: ONE closed CW LWPOLYLINE, two tangents + two bulges of magnitude 1, exact tangent points, no overlapping circles. Flat spec: `{id, w, cd, axis, ev, wx, wy}` → stadium.

## Curved (circular-arc) slot
Centreline radius Rc, width W, sweep θ → `Rout = Rc + W/2`, `Rin = Rc − W/2`, end caps `W/2`. Exactly ONE closed contour: outer arc + cap + inner arc reversed + cap. FAIL on helper centreline/circles, lens loops, duplicate arcs, open ends. Noisy DATA is cleaned to the one physical slot with provenance (056691: W6, Rc23.4, 60° → 26.4 / 20.4 / R3).

## Lessons
`regression/lessons/SLOT/` — 520929-10, 520928-20, 521013-21, 521023-16 (bare R).
