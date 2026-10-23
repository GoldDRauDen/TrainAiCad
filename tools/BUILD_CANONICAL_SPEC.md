# build_canonical spec (FLAT, no bends)

`python tools/run_job.py spec.yaml OUT/` = `build_canonical.py` → `export_canonical_dxf.py` → reopen/verify → §11 table.
Example: `examples/flat_minimal.yaml` (its generated `examples/flat_minimal.job.json` is kept in sync by a test).
Bent parts stay on the BEND_UNFOLD route; this tool refuses `bends`.

## Part
| key | meaning |
|---|---|
| `code` | slip work number verbatim (`26-062931`) |
| `material`, `t` | as printed; Laser R and hole POINT/CIRCLE come from `tools/lookup.py` |
| `page` | PDF page cited by every witness edge |
| `envelope: [Ox, Oy]` | overall drawing/slip size; the nominal outline bbox must match (±0.5, `envelope_tol`) |
| `outline` | corners **counter-clockwise**; items below |
| `holes`, `slots` | features with their dimension chains |
| `flags` | Vietnamese FLAG lines → status PREVIEW, outline Magenta (only for a real unknown, `REVIEW_PREVIEW_POLICY.md`) |
| `jlj_edge` | `auto` (default) / `top` / `bottom` |

## Outline items
- `[x, y]` — AUTO: Laser R on a convex corner ≤90° (`MATERIAL_AUTO_R`, corner row AUTO_R); other corners stay sharp.
- `[x, y, {R: 3, group: R3, qty: 3, ev: "p2 R3-3"}]` / `{C: 10, ...}` — called R/C. One `group` per callout; `qty` is checked (`GROUP_COUNT_CLOSURE`).
- `[x, y, {SHARP: "lý do"}]` — sharp by the drawing; `[x, y, {FLAG: "nội dung"}]` — unresolved corner (FLAG, no auto R).
- `{vnotch: {start, pitch, count | x: [...], level, depth, angle: 90, inward: -1|1, axis: X|Y, qty, ev}}` — repeated V notches; list them in outline order. A mouth on an explicit corner merges with it.
- `{unotch: {at: [[x,y],...], inward: [ux,uy], width, depth, mouth: {C: 1, ev}, qty, ev}}` — open U notch; `depth` = mouth → semicircle center, R = width/2; the mouth R/C applies to every notch of the entry.

## Holes / slots
`{id, d, group, qty, ev, wx: [[value, TO_TYPE, "evidence", KIND?], ...], wy: [...], datum_x: 0, datum_y: 0, at?}` — the chain starts at the outer edge at `datum_x/datum_y`; the center is the sum (an `at` given is checked). Node types: `OUTER_EDGE`, `HOLE_CENTER`, `SLOT_MIDPOINT`, … (`tools/dimension_witness.py`). Slot: `{id, w, cd, axis: [1,0], ev, wx, wy}` → stadium, anchor `SLOT_MIDPOINT`.

## What the tool proves (checks it sets PASS)
contour_topology (closed, CCW, no self-intersection), datum (envelope + every witness chain), feature_count (group closure), containment (full boundary), material_rules (lookup). unfold/bend_domain N/A; slot_semantics PASS only with slots.
J/LJ: on the long straight edge (CAD_OUTPUT.md); if the max-Y edge is notched/sloped and the min-Y edge is straight the part is rotated 180° (`canonical_rotation_deg`).
Check the shape against the drawing with `tools/overlay_check.py` (≥3 anchors, residual ≤1 mm).
