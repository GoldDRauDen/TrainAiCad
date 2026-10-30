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
- Every bend end: collinear edges → no corner → no slit. Otherwise, in the flat: **B** = the corner where the flange's side edge meets the web edge (the edge parallel to the bend); **S** = B − the flange-side bend line, positive toward the web (HD sample SUS t2: S 0 / −2 / +6).
  - `S > 0` → **no slit**. `S ≤ 0` → slit from B along the flange side toward the web, ending `T + 0.2` past the flange-side bend line: length `T + 0.2 − S` (t2: S 0 → 2.2, S −2 → 4.2).
  - The spec (`bend:` block) measures S and draws it from your outline; you prove the outline (web edge, flange width, retreat) from the source. A position you cannot prove → that edge FLAG, never a guessed S.
  - `python tools/lookup.py slit --material M --t T --S s` gives the decision, length and lead.
- A shoulder past the zone (wide ear behind a narrower neck): web = the face that continues beyond the bend end, S = shoulder − the other face's bend line toward the web (217.35 − 206.95 = +10.4) → no slit; the tool records the NO_RELIEF site.
- A free flange edge dimensioned to the outer plane (OD) sits at its face's `start`/`end` (`lookup.py unfold` → `faces`), ON the narrow face's side bend line: S = 0, so a slit at every such bend end (064687: 8 ends). Never retreat it by Nobi (S = +N → "no slit" is wrong).
- Fold sign changes and overlapping virtual-sharp dashed lines do not prove a physical crossing (521017-17).
- A web edge that leaves B slanted toward the web (not parallel to the bend) is the same corner: S is read at B, the lead uses that edge's own void normal offset LeadVal like the flange side (SS t3.2: 3|3 at the 115.02° corner).
- **Shape:** one Green connected `LINE + ARC R0.5 + LINE` (1 feature, 3 entities). Base B (above); short ray along the flange side toward the web, length `T+0.2−S`; lead end P = intersection of both edges offset toward the void by `LeadVal` (`lead_end_by_offset`; at 90° a 45° ray of LeadVal per axis, void side away from the flange); tangent arc R0.5. LeadVal from `data/lead_table.yaml` (`lookup.py slit`); hook rows (t≥19) or a t between rows → FLAG `LEAD_VALUE_UNPROVED`, nothing drawn. The exporter's guard rebuilds the slit with `tools/slit_geometry.py` from the declared edges. Lead is CAD geometry, not NC lead-in. The bend pair only touches B; trim a bend line only on a real interior intersection.

## 4. >90° bend relief
`90° < θ < 180°`: the §3 step gate decides first at every angle (S>0 → no relief; 26-063295: S +6.93 at 120° → none). S ≤ 0: slit from B, depth `D = t·sin θ` past the flange-side bend line (length D − S; lead and R0.5 as §3); `lookup.py slit --S s --angle θ` (t3.2 130°: 2.4513). Not t/2.

## 5. Two flanges at one corner
- **Same fold direction** (collide by t): the SHALLOWER flange (depth = OD perpendicular to its own bend line, difference ≥0.1 mm) retreats its end by t; equal depth → either, prefer the longer bend edge. Retreated end `S = −t` → §3 slit; the other end `S = +t` → none. Never retreat the deeper flange (leaves a `khuyết_t` notch). `python tools/lookup.py retreat --depth A B [--bend-len LA LB]`. Impossible retreat → assemble normally + FLAG.
- **Opposite fold directions** with two outer edges that really intersect after closure and both outside dimensions fixed → fixed-outside `R = t` relief at the intersection (055962: t2 → R2; 061247: R3.2 + R0.5 junctions). Different directions alone do not trigger it. Fold direction from all three views (solid = toward the viewer, dashed = away).
- Spec: two `chains` (X and Y) sharing the web, `fold: toward|away` on every bend that meets a perpendicular bend. The tool stops each bend line at the perpendicular bend's web-side line (opposite fold: line by line at the same-rank line), measures S at both flange ends (the retreated one gets the slit; a deeper flange retreating → FLAG khuyết_t) and replaces the outline corner at the flange-side line intersection with the R = t relief.

## 6. BOXMET (base rectangle L×W + four bent flanges meeting at the corners)
- Not for ordinary L/U/Z, single flanges or non-crossing bends. Do not omit a required slit because the outline already closes.
- Generator (retreat side, slit bases and signs, t+0.2, R0.5, Green): `python tools/boxmet_job.py --code 26-XXXXXX --L .. --W .. --H h1 h2 h3 h4 --T t --material M --N nobi --job-id <JOB> --out box.job.json`, then into `run_job.py` with the other codes. N is an input (handwritten > customer > table). Corners drawn rounded/chamfered without callout → refused (`BOXMET_CORNER_DRAWN_SHAPE_NOT_SHARP_FLAG`).
- Bend lines are interrupted only where the slit truly crosses their interior; endpoint contact keeps them continuous.

## 7. Check
Per junction: mechanism named once, S and T proved, depth/direction/connectivity right, bend domain clipped, saved DXF keeps the CUT/BEND interaction. `tools/bend_end_guard.py` (run by the exporter) re-measures S from the declared edge witnesses.

## Lessons
`regression/lessons/SLIT_RELIEF/` — HD_FLAT_STEP (S in the flat, slit length T+0.2−S, 061247/061248), 521005-05 (S matrix, 057873), 521005-13 (custom スリット 8), 521016-17 (lead shape), 521017-17 (S=+t no slit), 521019-05 (relief inventory, corner depth), 520801-04 / 520929-18 (BOXMET), 520924-19 055958/055962, SILT_GT90, 521026-03 (slanted web edge at a bend end), 521026-13 (S gate above 90°), 521028-17 (ear shoulder S), 521030-10 (flange edge on the OD plane: S=0 at all ends).
