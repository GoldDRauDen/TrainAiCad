# BEND — face graph, OD, Nobi, unfold (part_mode BEND / MULTI_FACE / UNKNOWN)

Triggers: `曲げ`, `ノビ`/`伸び`, `J`, `内R`, `外寸`, double dashed lines, L/U/Z/hat/box profiles, side/section views. Also always open `SLIT_RELIEF.md` before declaring SLIT_RELIEF = NO. Angle ≤85° → `BEND_ACUTE.md`.

## 1. Solve order (never start from a bbox or the desired flat)
`source views → witness graph → candidate faces → signed adjacency → attachment edge lock → OD_actual → constraint closure → unfold → feature transforms → bend-line clipping → fold-back → canonical`.
Shape labels (L, U, Z, hat, box, joggle) only propose candidates; witnesses, projections, bend callouts and sections prove them. Two graphs still possible after source exhaustion → draw the best-supported in Magenta, name the other.

**Tool first:** a chain along one axis (L, U, Z, hat, multi-bend) with full-width or simply notched faces → `bend:` block in the spec and `tools/run_job.py` (`tools/BUILD_CANONICAL_SPEC.md`): it looks up Nobi, places the line pairs, clips them to material, maps face-relative holes, draws `SPLIT_FLANGE_10MM` for a bend without Nobi, decides every bend-end junction (`SLIT_RELIEF.md` §3/§5) and writes the face graph + ledger. Two-axis parts: `chains:` (X and Y) in the same block. Still by hand: bends not at 90° that meet a step, R/C at a bend end, bent DATA parts.

Records per part (keep in the ledger file):
- FACE: id, view, local origin/axes, edges with stable ids, own dimensions.
- BEND: face_A + shared edge, face_B + shared edge, free edges, fold sign, angle, Rin/t, Nobi source, material domain.
- FEATURE: family, host face, local datum incl. physical edge id, local geometry.
- PER_BEND_WITNESS_LEDGER: ordered faces, both controlling witnesses, ID/OD meaning, every thickness/offset term and where it is consumed, Nobi, sign, domain, line1/line2.

## 2. Faces need bend evidence
- A slope, step, R/C or silhouette break is NOT a bend. New face only with positive evidence: bend/J/Nobi callout, section/side view with two planes, formed-edge/thickness lines, unique projection, authoritative DATA.
- One outline for an edge-on plate and a face-on ear proves neither: UNKNOWN, use function cues (a welded bar needs a face) and notes (三方曲げ), ask.
- SAME_FACE_FIRST: first try one planar face with a complex contour. Both models possible → unresolved.
- Lock the local bend domain: a flange may span only part of the width (521005-02: bend 555 long on a 1025 part). Bend lines only where material crosses the shared edge; split around notches, reliefs, voids.
- Theoretical-sharp overall vs physical R/C bbox: compare each to its own geometry; never sharpen the R to match a bbox.

## 3. Attachment edge lock
Prove `FACE_A.edge_i ⟷ BEND ⟷ FACE_B.edge_j` for every bend. Valid: formed/profile/section topology, view correspondence, witness connectivity, scoped bend notes, thickness/hidden lines (optional), DATA. Forbidden: `NEAREST_VIEW_EDGE`, paper proximity, "top edge is the bend", symmetry, whatever closes the flat, sample geometry. A wrong edge keeps the total length but reverses the flange and every feature measured from it (521006-18 058648). A whole-part 180° turn that keeps edge identities is equivalent. A formed/profile view used for measurement is a `MEASUREMENT_CONSTRUCTION_VIEW`, never CUT.

## 4. OD_actual (outside face contributions)
`L_flat = Σ OD_actual − Σ Nobi`, each OD physically proved.
- Measure along the owning face from its free edge to the outside bend envelope. Never use a bbox, an inside dimension as OD, the sharp intersection when the physical envelope controls, a sample coordinate, or a number from another feature row (a hole-row 30 is not a step height).
- A section dimension's extension lines show which face it touches → that face carries `+t`. Two plates joined by a U tab stay separate faces.
- Where the neighbour face is absent (notch), the wall sits at the face's OWN OD plane from its free end (first face x=OD1; last face x = total − OD_last = line1 of the last bend), never at the neighbour's OD (061138: 722.4−275 = 447.4).
- A tab width measured from the outer face includes t (30 + t); place it at line1_prev + d or line2_next − d.
- A flange/tab bent out of an edge locates that edge at its OUTER face plane (tangent + R + t): neck 304.0/305.8, not the printed 306.
- **Measure, do not read** when faces are only in a side/profile view plus a rotated auxiliary view: take OD from the DXF geometry; project orthogonally at the OD lines, keep the free-end side, rotate the auxiliary piece parallel to the chain, join at the in-between face OD, subtract Nobi; features come from the same rotated piece; a notch drawn in two views is one continuous cut. Self-check ≤0.02 mm against the DXF (521021-06: 410.8 −1.68− 20.8 −0.36− 175 → flat 604.56).
- `THICKNESS_SINGLE_USE`: a t or ID→OD offset already inside an outside extent is never added again. A bend pair off by exactly ±t means re-trace ownership — never an automatic shift.
- **Weld → bend special case** (a welded tab made from the same sheet; also any non-90° section whose dims stop at the plate end faces, so the OD is not formed): no weld site, no KEGAKI. `lookup.py leg --a A --b B --t T --angle θ --nobi N` (26-063295: 35/65, t6, 120° → 31.536 / 71.928, flat 98.544, lines 67.01/71.93). An OD the projection already forms is not redrawn. Build the outer-face intersection; OD = free end to it along the outer face. 90°: dimension to the mating plate's inner face → +t; standing plate set back by s → +s on the base face. ≠90°: draw both legs with t at the angle, extend the outer faces to their intersection, measure each leg (`d = angle − 90`: `OD1 = a − t·tan d`, `OD2 = b + t/cos d`, 26-062885: 28.942 / 56.093). Line positions rounded to 0.01.

## 5. Feature transform, order, frame
- Each face's contour and features from its own witnesses first; a hole pitch never becomes a contour/bend distance.
- `U_flat = FACE_START + u` (measured from the face start) or `FACE_END − u` (from the free/opposite edge); both axes independent. Edge-based datums keep their physical id (`FACE_2.BEND_EDGE` ≠ `FACE_2.FREE_EDGE`) through rotation/reflection.
- Face order is non-commutative: an equal Σ does not prove order. Prove it from formed topology/callouts/witnesses.
- Canonical flat frame = orientation of the primary/plan view (521021-20: length along Y, hole end at the bottom).
- Inside views: assemble the proved inside-face flat first, reflect only when the target blank needs it; compare holes in the same final frame (018297).
- Stacked plates (B sits on A): `MULTI_PART.md` §3.

## 6. Nobi (`python tools/lookup.py nobi --material <printed> --t <t> --L <bend edge length> --angle <A> [--surface "#1"] [--handwritten N] [--no-j] [--customer <code>]`)
Your inputs: the printed material/surface (SUS 2B unless `#1` is printed), t, L = the locked physical shared edge (never a bbox), the angle, a legible handwritten Nobi scoped to that bend (it wins at any angle, J or not), whether J is printed, the customer. The tool picks the table (KH646 its own) and returns the value or `SPLIT_FLANGE_10MM` + `flag_vi` (non-90° without handwriting, no J, t/L not tabulated, `Confirm`).
`SPLIT_FLANGE_10MM`: main body and flange each at their proved OD, the flange a separate closed Magenta piece 10 mm away along the unfold direction in the same cluster, no bend line for that bend, every other feature drawn, PREVIEW. The spec builds it (`outline: auto`); shaped outlines by hand. Never drop the code.

## 7. ID → OD and unfold arithmetic
- Non-90° inside dimension: `python tools/lookup.py idod --t T --angle A` → offset = round₀.₀₁(t·tan((180−A)/2)) FIRST, then `OD = ID + offset` (165°/t3 → 0.39; 135°/t3 → 1.24). Assign each offset to the face the formed profile proves; never twice.
- `python tools/lookup.py unfold --od OD1 … ODn --nobi N1 … Nn-1` (the `bend:` block does this): total `ΣOD − ΣN`, bend k line pair spaced N_k. The body interior is never reduced by Nobi.
- Printed inputs are exact. `<0.01 mm` applies only to auditing an already-correct derived value against a reference (018300: (797+0.26)+(24+0.26)−0.37 = 821.15).
- Stepped/notched flange: `Y_flange_flat = L_flange − N`, `Y_bend = Y_flange_flat`, `Y_notch = Y_flange_flat + gap`, body untouched.
- C beside a bend: a C called on a main-face corner meeting the bend line ends ON the bend line; a C in the flange view sits on the flange's free corner.

## 8. Fold-back before export
Replay the flat through the signed graph: face sizes, adjacency, the SAME attachment edges, signs, used ODs, feature hosts/offsets/edge ids, local channels/tabs, bend domains. A matching bbox or total never passes a reversed attachment.

## 9. Tooling (WARN only)
Leg shorter than the selected V die's L_min/Z_min (`python tools/lookup.py tooling --material M --t T`) → WARN, never resize. SS t4.5 V18 is `要確認`.

## Lessons
`regression/lessons/BEND/` — 520929-25 (order/domain/Z), 521005-02 (face evidence, local domain), 521006-18 (attachment edge, formed OD), 521016-13 (step from hole row), 521019-05 (projection, notch wall, stacked, C at bend), 521021-06 (ortho OD), 521023-14 (weld→bend), 521026-13 (end-face dims, leg), 520315-18 (inside view), 520925-03 HD1, 520317-09, 521030-10 (ear vs plate), 521030-03 (mid-leg chamfer).
