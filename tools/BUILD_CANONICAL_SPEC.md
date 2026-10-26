# build_canonical spec (FLAT and single-axis BENT parts)

`python tools/run_job.py spec_A.yaml spec_B.yaml [box.job.json] OUT/` = `build_canonical.py` → `export_canonical_dxf.py` → reopen/verify → report table. One file per code is fine: files merge in the given (page-1) order; canonical job JSON (`tools/boxmet_job.py`, hand parts) joins as-is; `job_id` / `customer_code` must agree.
Examples: `examples/flat_minimal.yaml` (its generated `examples/flat_minimal.job.json` is kept in sync by a test), `examples/bend_minimal.yaml`.

Job level: `job_id`, optional `customer_code` (numeric, JOB STATISTICS) — its corner/hole policy from `data/customers.yaml` is applied to every part (e.g. KH768 sharp outside corners, KH712 C5, KH859 t≥19 corners FLAG).

## Part
| key | meaning |
|---|---|
| `code` | slip work number verbatim (`26-062931`) |
| `material`, `t` | as printed; Laser R and hole POINT/CIRCLE come from `tools/lookup.py` |
| `page` | PDF page cited by every witness edge |
| `envelope: [Ox, Oy]` | overall drawing/slip size; the nominal outline bbox must match (±0.5, `envelope_tol`) |
| `outline` | corners **counter-clockwise**; items below |
| `holes`, `slots` | features with their dimension chains |
| `flags` | Vietnamese FLAG lines → status PREVIEW, outline Magenta (only for a real unknown, `rules/OUTPUT.md` §5) |
| `jlj_edge` | `auto` (default) / `top` / `bottom` |

## Outline items
- `[x, y]` — AUTO: Laser R on a convex corner ≤90° (`MATERIAL_AUTO_R`, corner row AUTO_R); other corners stay sharp.
- `[x, y, {R: 3, group: R3, qty: 3, ev: "p2 R3-3"}]` / `{C: 10, ...}` — called R/C. One `group` per callout; `qty` is checked (`GROUP_COUNT_CLOSURE`).
- `outline: {circle: {center: [x, y], d: 100, ev}}` instead of a list — a round blank, saved as ONE CIRCLE (no corners, no bend).
- `[x, y, {SHARP: "lý do"}]` — sharp by the drawing; `[x, y, {FLAG: "nội dung"}]` — unresolved corner (FLAG, no auto R).
- `{vnotch: {start, pitch, count | x: [...], level, depth, angle: 90, inward: -1|1, axis: X|Y, qty, ev}}` — repeated V notches; list them in outline order. A mouth on an explicit corner merges with it.
- `{unotch: {at: [[x,y],...], inward: [ux,uy], width, depth, mouth: {C: 1, ev}, qty, ev}}` — open U notch; `depth` = mouth → semicircle center, R = width/2; the mouth R/C applies to every notch of the entry.

## Holes / slots
`{id, d, group, qty, ev, wx: [[value, TO_TYPE, "evidence", KIND?], ...], wy: [...], datum_x: 0, datum_y: 0, at?}` — the chain starts at the outer edge at `datum_x/datum_y`; the center is the sum (an `at` given is checked). Node types: `OUTER_EDGE`, `HOLE_CENTER`, `SLOT_MIDPOINT`, … (`tools/dimension_witness.py`). Slot: `{id, w, cd, axis: [1,0], ev, wx, wy}` → stadium, anchor `SLOT_MIDPOINT`.

Equal pitch: `repeat: {n: 8, step: 75, along: wx}` on a hole/slot = n copies (`H_1`..`H_n`, `qty` defaults to n), copy k adds (k-1) steps to the named chain (`wx|wy|wu|wv`), so `P75*7` is one entry.

Tap: `thread: M6` (or `M8x1` when the pitch is printed) instead of `d` → the pilot Ø from the table, same count and datum.

Hole keys for POINT: `piercing: true` (PIERCING scoped to this family by its leader) → ByLayer POINT; `piercing: true, through: true, stamp: "<scoped text quoting PIERCING + THROUGH HOLE>"` → Green POINT + `piercing_authorizations` (rules/HOLE_TAP.md §2). A hole with `d < t/2` or below the workbook minimum becomes a ByLayer POINT by itself. `d` is still given (witness chain); a Magenta/unknown lookup result is refused (draw by hand + FLAG).

## KEGAKI
`kegaki: [{id, group, qty, ev, lines: [[x0, y0, x1, y1], ...], circles: [{center: [x, y], d}]}]` → Red LINEs and ONE Red CIRCLE per round mark, family `KEGAKI`, one member per id (footprint from `tools/kegaki_footprint.py`, rules/KEGAKI.md).

## Cut-outs (rectangular opening, optional R corners)
`cutouts: [{id, rect: [x0, y0, x1, y1] | face, from, u: [a, b], v: [c, d] | vertices: [[x, y, bulge], ...], R: 10, group, qty, ev}]` (`vertices` = an exact CW loop, e.g. DATA) → one CW closed contour (4 tangent arcs when `R>0`), family `CUTOUT` (`qty` closes per `group`). `face/u/v` maps like a hole on a bent face (`u` along the face from its datum, `v` across from the flat edge). Refused: outside the material (CONTAINMENT), `R` > half the short side, overlapping a bend zone (bend lines must stop at the void: build by hand).

## Local FLAG (only the flagged entity is Magenta)
`flag: "nội dung"` on a hole / slot / cut-out (spec or DATA `members.<id>`) paints that entity Magenta and adds a `FLAG:` line at the right of the part; a corner `{R|C: v, FLAG: "…"}` paints only its arc/chamfer piece (`flag_segments`). `pdf_d`, `pdf_size`, `pdf_R`/`pdf_C` and `pdf_pos: [{from: <datum ref>, axis: x|y, pdf: n, label?}]` (one-entity member: |centre − datum| in the view frame against the PDF dimension) raise the flag themselves when Δ ≥ the customer threshold. A part-level `flags:` entry with no entity to point at (overall size, closure snap) still paints the whole outline.

## What the tool proves (checks it sets PASS)
contour_topology (closed, CCW, no self-intersection), datum (envelope + every witness chain), feature_count (group closure), containment (full boundary), material_rules (lookup). unfold/bend_domain N/A; slot_semantics PASS only with slots.
J/LJ: on the long straight edge (`rules/OUTPUT.md` §4); if the max-Y edge is notched/sloped and the min-Y edge is straight the part is rotated 180° (`canonical_rotation_deg`).
Check the shape against the drawing with `tools/overlay_check.py` (≥3 anchors, residual ≤1 mm).

## Bent part: `bend:` block (L / U / Z / hat / multi-bend chain along ONE axis)
```yaml
bend:
  axis: X                 # the face chain runs along flat X (bend lines vertical); Y = along flat Y
  width: 40               # proved width of every face (Nobi L and outline: auto); per-bend `L` overrides
  width_ev: "p6 web 40"   # needed for outline: auto (full-width rectangle)
  faces:                  # unfold order from the flat origin; od = proved outside length (rules/BEND.md §4)
    - {id: F1, od: 50, ev: "50 to the outer face"}
    - {id: F2, od: 64, ev: "62 + t"}
  bends:                  # one per face pair
    - {id: B1, angle: 90, sign: 1, nobi: 3.68, ev: "bend callout"}   # nobi only when handwritten; else table
```
- Nobi per bend from `lookup.nobi` (handwritten > 90° J table). A bend with no Nobi (`SPLIT_FLANGE_10MM`) is split: the body (largest ΣOD) and each other segment are built at their ODs, the segment drawn Magenta 10 mm away, no line pair, FLAG + PREVIEW. Needs `outline: auto`; every hole/slot/cut-out on a split part names its `face`.
- The tool derives line1/line2, the flat length, `face_graph`, `per_bend_witness_ledger`, the `BEND` groups and the DASHED lines clipped to the outline (one member per material interval).
- `outline: auto` = full-width rectangle; otherwise list the flat outline, where a point may be face-relative: `{face: F2, u: 10, v: 0, from: start|end, R: 2}`. Face start = the previous bend's line1 (the previous face's outer plane), face end = the next bend's line2; the first/last face are measured from their free edge.
- Holes/slots on a face: `{..., face: F3, from: start|end, wu: [[30, HOLE_CENTER, "ev"]], wv: [[10, HOLE_CENTER, "ev"]]}` (`wu` along the face, `wv` across from the flat edge v=0).
- A straight web edge that leaves the corner B slanted toward the web is accepted at a bend end (S read at B, lead offset from that edge, `rules/SLIT_RELIEF.md` §3).
- Bend lines run where both faces have material and stop at a perpendicular bend (its web-side line; opposite fold: line by line). Every bend end with a step is a junction (`rules/SLIT_RELIEF.md` §3): S = corner B − flange-side line toward the web; S ≤ 0 → Green slit `T+0.2−S` with lead and R0.5; written to `bend_end_junctions` for the guard.
- Two axes: `bend: {chains: [{axis: Y, faces, bends}, {axis: X, faces, bends, origin: 0}]}` — the shared web face has the same id in both chains (its OD per chain); `origin` = flat coordinate of the chain's first free edge; a face-relative point/hole/slot on the shared face adds `chain: X|Y` (`axis: X|Y` also works for points and holes; a slot's `axis` is its direction vector). Every bend meeting a perpendicular bend needs `fold: toward|away`; opposite folds get the R = t relief at the outline corner on the flange-side line intersection (list that corner in the outline). Bend `L` (or chain `width`) is the bend-edge length for the Nobi bracket.
- Refused (build that part as canonical JSON by hand): an outline corner inside a bend zone and its domain, R/C at a bend end, a step at a non-90° bend, a hole/slot overlapping a bend domain, a split flange with a shaped outline or two axes. A step at a bend end (flange narrower than the web) is built at any angle: S>0 no relief, S≤0 slit `T+0.2` (90°) / `t·sin θ` (>90°) past the flange-side line (`rules/SLIT_RELIEF.md` §3–4); ODs of a non-90° bend whose dims stop at the plate end faces come from `lookup.py leg`.

## DATA part (customer DXF, flat)
`{code, material, t, page, data: assembled.json, envelope: [W, H], members: {<member id>: {ev, group, qty, pdf_d | thread | d + piercing/through/stamp}}, corners: [{at: [x, y], SHARP | FLAG | R | C, ev}]}` — `data` is the `tools/dxf_assemble.py` output (relative to the spec). The outline, holes, slots, cut-outs and KEGAKI come from DATA (coordinates kept, witnesses = DATA ordinates); every non-outline member needs its PDF meaning; `qty` closes against DATA. `envelope` and `pdf_d` are DATA/PDF gates (customer `data_pdf_policy` / `data_pdf_tolerance_mm`). Sharp DATA corners get Laser R like any outline (`corners` overrides); every change is listed in `manufacturing_change_ledger`. DATA bend lines are refused. Bent part: add the `bend:` block, `outline`, `envelope` and `data_faces: [{face, from: start|end, at, to}]` (+ `data_v` if the view's bottom edge is not the flat edge): each feature goes onto the face whose view range [at, to] holds it, measured from that face's datum (start = previous bend's line1 or the first free edge; end = next bend's line2 or the last free edge); middle-face spans are gated against the OD. `data_face: W` = the whole view is face W from its start. Several views: `data_views: [{data: view.json, origin: <ref>, width: <ref>, data_faces: [{face, from, at: <ref>, to: <ref>}], members: {...}}]` + `outline` of `[x, y, opts]` where x/y are numbers, `START`/`END` (chain free edges) or `<datum member>.<start|end|min|max>.<x|y>`; a view that runs against the chain is assembled mirrored (`mirror_x` + `rotate_deg: 180` = a y mirror). Scalars: `ZERO`, `<m>.length`, `<m>.radius` (an ARC datum), `<m>.leg` (a 45° chamfer line), `{span: [ref, ref]}` = |ref - ref| in one view, `{hypot: [scalar, ...]}` = √Σ² (a slanted length from its dx/dy spans); they fill outline coordinates, `R`/`C` of a corner (`pdf_R`/`pdf_C` gate them), `od` and `bend.width`; a point's `pdf: [x, y]` is its PDF nominal for the closure tie-break. A FLAT part (no `bend:`) uses the same `data_views` with `origin: [x ref, y ref]` (the flat X=0/Y=0 edges; a view only translated, turn it in `dxf_assemble`), outline refs and features; `START`/`END` need a chain. Cut-out members take `pdf_size: [w, h]` (same-parameter gate) and `pdf_label` folds identical DATA_PDF_DIM_DIFF lines. Module: `tools/data_part.py`.
