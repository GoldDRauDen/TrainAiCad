# DATUM — dimension semantics and coordinates (L2, always)

Every coordinate is an explicit expression from a proved datum, e.g. `Y = 0 + 10 + 35 = 45`. No trace → FLAG (§6), never inference.

## 1. Classify each dimension before arithmetic
1. **Baseline** — shared extension-line origin; never summed.
2. **Chain** — end witness of one = start witness of the next; only this accumulates.
3. **Step/local** — between two local levels/walls/centers; not part of a neighbour chain unless witnesses connect.
4. **Overall** — closure check only; never redistributed into missing segments. `sum(chain) ≠ overall` → re-read, FLAG; never force-fit.
5. **Ordinate** — from its stated zero.

## 2. Datum graph
- Witness endpoints = nodes, dimensions = edges. A coordinate needs a connected path from the datum node. Visual alignment is not connectivity.
- Tag every endpoint by what it lands on: `OUTER_EDGE`, `CONTOUR_EDGE/STEP`, `HOLE_CENTER`, `SLOT_MIDPOINT`, `ARC_CENTER`, `CENTERLINE`, `THEORETICAL_SHARP_CORNER`, `REFERENCE_DATUM`. Never borrow a neighbour's endpoint.
- Hole-center chains and contour/step chains never mix. **Each hole family has its own string**; name the printed label on each witness step (521021-20: M8 200+15 → X15; M5 204+13 → X13, not 15).
- Notch with radius: overall depth to the deepest point ≠ center setback. `R` + overall depth `D` → center setback `D − R` (R3 + depth 8 → setback 5, not 8).
- Parenthesized/参考 dimension: no mid-tolerance, but its own extension-line datum still applies (`(276.5)` from a hole row at Y10 → Y286.5). A formed-view reference overall is NOT the flat length; derive the flat from the face chain.
- Symmetry: a proved axis with no outer-edge dimension → build symmetric; an explicit outer-edge dimension wins over a drawn centerline; contradictory → FLAG.
- Same-family undimensioned notch/step in a chain-dimensioned outline takes the dimensioned sibling's size (`DERIVED_FROM_SIBLING`); FLAG only if visibly different.

## 3. Contour topology first
Trace the ordered boundary (edge → C → vertical → R → ledge …) before numbers. An overall size gives the extent only, never a full rectangle; the visible outline wins. No bounding rectangle as a placeholder.

## 4. Source origin and axis lock (per view)
Prove origin O (two real edges) and the +X/+Y directions from arrows, signs or witnesses; paper corner or habitual lower-left is not evidence.
`X_cad = X0 + sx·X_src`, `Y_cad = Y0 + sy·Y_src`, `sx, sy ∈ {+1, −1}` proved separately. Top-left origin, height H proved on the same face, CAD Y=0 at the bottom: `Y_cad = H − d` (whether the source writes `−d` with +Y up or `+d` with +Y down). Example: `Y=−30` from a top-left origin on a 138 view → `Y=108`. Mirror/rotation/X-Y swap: prove the view→face mapping first. Unproved origin/axis → FLAG those coordinates.

## 5. Tolerance
Asymmetric/limit tolerance → mid value `X = nominal + (upper + lower)/2` (`50 +0.2/+0.1` → 50.15). Symmetric ± → nominal. Reference → nominal.

## 6. Unclear or missing
- FLAG only after re-reading every witness, endpoint, count, projection and closure; a crowded print is not ambiguous by itself.
- Magenta estimate only when topology/identity is certain and a number is unreadable. Competing topologies: draw the best-supported one in Magenta and name the alternative in the FLAG.
- Estimated values are integer-rounded; explicit and formula values keep full precision.
- Keep proved geometry exact; isolate only the unknown.

## 7. Witness graph in canonical JSON
Every proved HOLE/SLOT member carries X and Y witness edges (`from_node`/`to_node`, endpoint types, signed value, kind, page, crop ref); `tools/dimension_witness.py` solves them. `endpoint_verified=true` is not proof: the crop is. Bent faces: local face → flat transform in `BEND.md` §5.

## Lessons
`regression/lessons/DATUM/` — 520728-06 (top-left origin, H138), 520919-05 (chains), 520919-07 (endpoint identity, reference datum). Hole-family strings: 521021-20 (`KEGAKI/`).
