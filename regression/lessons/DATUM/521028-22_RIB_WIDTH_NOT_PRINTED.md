# 521028-22 — a rib's width is not the dimension that ends at a hole

Rule: `rules/DATUM.md` §2. Approved by the user (DUYỆT).

## FACT
- Bracket side view: 33 = hole centre line to the inner face of plate A (B end 50 + overhang 5 − A 12 = 43; hole at 10; 43 − 10 = 33). The rib has no dimension of its own.
- If the rib were 33 its end would sit on the hole line; zoomed in it is about 1 mm off (hard to see, easy to misread). Rib width stays unconfirmed (about 32): Magenta + FLAG.
- The slip size 100 x 33 was used as supporting proof, but slip sizes are only a plausibility check.

## ROOT_CAUSE
`AI_SOURCE_SEMANTICS_ERROR`: the endpoint of 33 was assigned to the nearest feature (the rib edge) by visual alignment, not by what it was derived from; the slip size then looked like confirmation.

## LESSON
1. A rib/child extent with no own dimension is never taken from a dimension ending at a hole or another feature line.
2. An extension line within about 1 mm of two features: name which one it touches at ≥900 dpi; otherwise estimate in Magenta and FLAG both candidates.
