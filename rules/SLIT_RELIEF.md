# SLIT_RELIEF — slits and bend reliefs (rạch / スリット)

Triggers: `スリット`, `SLIT`, Green LINE/ARC near a bend end, box corners, flanges meeting at a corner, a web edge flush with or recessed from a bend line. Loaded for every bent part.

## 0. Classify first
Ordinary CUT notch/slot, custom source slit, bend-relief slit, BOXMET slit, lance, KEGAKI or other. Green colour supports but never proves identity.

## 1. Custom source slit (instruction-driven)
Only from a printed/handwritten `スリット` / `SLIT`. Value, quantity, host edge, position, direction and relation to the bend come from that instruction and its witnesses (`スリット 8` = 8 in that drawing only). Never added because a bend exists, never placed at the bend centre by habit, never copied from a sample. An explicit slit value is never replaced by `t+0.2` or `t·sin θ`. Identity proved but a field unknown → keep the slit, FLAG the field.

## 2. Precedence at one junction (exactly one mechanism)
1. revision/cancellation or custom source slit; 2. BOXMET or opposite-fold `R=t` when their topology is proved; 3. bend-end offset gate §3; same-direction corner retreat §5 only picks the recessed flange, then §3 applies. Never two reliefs at one junction.

## 3. 90° bend-end offset gate (`BEND_END_OFFSET_90`)
- Bend-edge length = the real shared material edge, clipped to voids; a notch at the bend end shortens it (057873: 248 and 2×50).
- Inventory EVERY bend end: collinear/parallel edges → no corner B → no slit; a wall/chamfer ending at the bend end forms corner B → measure the signed step **S** between the flush (virtual-sharp) reference and the actual neighbouring web edge, in one physical frame, from source witnesses.
  - `S > 0` (protrudes, including S = t) → **no slit**.
  - `S = 0` (flush) → slit depth `T + 0.2` from the actual edge.
  - `S < 0` (recessed) → `T + 0.2` from the actual recessed edge (= `|S| + T + 0.2` from the reference).
  - S unproved → `SLIT_RELIEF = UNKNOWN` + local FLAG; never guess.
  - t=2: S −2 → 2.2 (4.2 from reference); S 0 → 2.2; S +1, +1.5, +2 → none (`tools/slit_geometry.py`: `slit_depth_from_actual_edge(S, T)`).
- Fold sign changes and overlapping virtual-sharp dashed lines do not prove a physical crossing (521017-17).
- **Shape:** one Green connected `LINE + ARC R0.5 + LINE` (1 feature, 3 entities). Base B = corner of web edge and flange side line; short ray perpendicular to the bend line, pointing inward (`slit_dir_from_bend`), length `T+0.2`; lead end P = intersection of both edges offset toward the void by `LeadVal` (`lead_end_by_offset`; at 90° a 45° ray of LeadVal per axis, void side away from the flange); tangent arc R0.5. `LeadVal = slit_geometry.lead_val(material, t)` from `data/lead_table.yaml`; hook rows (t≥19) or a t between rows → FLAG `LEAD_VALUE_UNPROVED`, nothing drawn. Construct with `slit_geometry.connected_slit(B, S, D, slit_len)`. Lead is CAD geometry, not NC lead-in. The bend pair only touches B; trim a bend line only on a real interior intersection.

## 4. >90° bend relief
`90° < θ < 180°`: depth `D = t·sin θ` (`slit_geometry.slit_depth_gt90`; t3.2: 150° 1.6, 130° 2.4513, 110° 3.0070). Not t/2 in general. Exactly 90° uses §3.

## 5. Two flanges at one corner
- **Same fold direction** (collide by t): the SHALLOWER flange (depth = OD perpendicular to its own bend line, difference ≥0.1 mm) retreats its end by t; equal depth → either, prefer the longer bend edge. Retreated end `S = −t` → §3 slit; the other end `S = +t` → none. Never retreat the deeper flange (leaves a `khuyết_t` notch). `tools/corner_retreat.py choose_retreat`. Impossible retreat → assemble normally + FLAG.
- **Opposite fold directions** with two outer edges that really intersect after closure and both outside dimensions fixed → fixed-outside `R = t` relief at the intersection (055962: t2 → R2). Different directions alone do not trigger it. Fold direction from all three views (solid = toward the viewer, dashed = away).

## 6. BOXMET (base rectangle L×W + four bent flanges meeting at the corners)
- Not for ordinary L/U/Z, single flanges or non-crossing bends. Do not omit a required slit because the outline already closes.
- L ≥ W: bottom/top flaps retreat t, slit bases `(t,0) (L−t,0) (L−t,W) (t,W)`; W > L: right/left retreat, bases `(L,t) (L,W−t) (0,W−t) (0,t)`. Local signs (+X right, +Y up), case A: BL S(0,+1) D(−Lv,−Lv); BR S(0,+1) D(+Lv,−Lv); TR S(0,−1) D(+Lv,+Lv); TL S(0,−1) D(−Lv,+Lv); case B: BR S(−1,0) D(+Lv,−Lv); TR S(−1,0) D(+Lv,+Lv); TL S(+1,0) D(−Lv,+Lv); BL S(+1,0) D(−Lv,−Lv). SlitLen `t+0.2`, R0.5, Green, Layer 0.
- Generator: `python tools/boxmet_job.py --code 26-XXXXXX --L .. --W .. --H h1 h2 h3 h4 --T t --material M --N nobi --out job.json` then `export_canonical_dxf.py`. N is an input (handwritten > customer > table). Corners drawn rounded/chamfered without callout → refused (`BOXMET_CORNER_DRAWN_SHAPE_NOT_SHARP_FLAG`).
- Bend lines are interrupted only where the slit truly crosses their interior; endpoint contact keeps them continuous.

## 7. Check
Per junction: mechanism named once, S and T proved, depth/direction/connectivity right, bend domain clipped, saved DXF keeps the CUT/BEND interaction. `tools/bend_end_guard.py` (run by the exporter) re-measures S from the declared edge witnesses.

## Lessons
`regression/lessons/SLIT_RELIEF/` — 521005-05 (S matrix, 057873), 521005-13 (custom スリット 8), 521016-17 (lead shape), 521017-17 (S=+t no slit), 521019-05 (relief inventory, corner depth), 520801-04 / 520929-18 (BOXMET), 520924-19 055958/055962, SILT_GT90.
