# CORNER_RC — explicit R/C and automatic Laser R (bo góc, vát)

Triggers: `R5`, `C2`, `n-R`, `n×m-R`, `面取り`, `角R`, `指示無き角部…`, rounded/chamfered corners, customer "sharp corner / ピン角" notes.

## 1. Every corner gets one ledger row (`tools/corner_ledger.py`)
`CALLED` (explicit R/C) · `AUTO_R` (shop Laser R) · `SHARP` (reason) · `FLAG`. Per corner, authority: revision/red correction → explicit PDF R/C (with its quantity) → customer corner rule → shop Laser R. A PDF R/C at one corner never stops auto R at other eligible corners.

## 2. Explicit R/C
- Lock the tuple `(R|C, value, quantity/scope, corner class, leader)` before geometry. C = straight chamfer (never an arc); R = true radius. Unclear glyph on a rotated callout → inspect context, else FLAG.
- Close each family's quantity first: find the targeted corner class (convex/concave), count rounded corners, then search other views. Per-view `n×C` calls are different corner sets (044841: 4+4+2 = 10×R5; replacing any with auto R0.5 is FAIL).
- Siblings of a called `n-` family drawn identically are CALLED (C1 at slot 1 → also slot 2).
- Semicircular notch/groove bottom whose width W is proved = R W/2; read `n×m-R` by source grouping (010421: width 6, `2×2-R` = 4×R3; `2×4-R1` = 8 mouth R1).
- Drawn R/C with no callout and no general note → `FLAG` row (keep the drawn shape as preview), never auto-rounded.
- A general note for uncalled corners (「指示無き角部はC0.5程度の面取り」) = the shop Laser R → AUTO_R, no FLAG.
- C beside a bend: see `BEND.md` §7.

## 3. Automatic Laser R (`python tools/lookup.py laser-r --material M --t T [--customer CODE]`)
- Only on corners drawn SHARP and uncalled; only convex outside corners ≤90° (material interior angle) unless the row says otherwise; never on holes/slots/inner notches; never on reliefs (`R=t` relief and slit R0.5 are not Laser R).
- SS t≥19: R3 on the OUTER perimeter only, including its concave corners; never on holes/slots. Customer sharp vs this R3 → draw the customer corner, FLAG, ask.
- SUS430: Laser R/holes from the SUS/他 rows. Cu/Brass: t≤6 R0.5, t>6 none.
- DATA jobs: a sharp DATA vertex does not suppress a required R; replace locally with a true tangent arc, record `DATA_AUTO_R_CANONICALIZATION`; explicit R/C still wins.
- Customer corner rules (e.g. 768, 859, 325, 412: outside corners sharp; 765: R3; 775: R0.3 when t≤4.5) are applied by `--customer`; drawn R/C still drawn as printed.
- A PDF-unmarked radius that no approved rule explains (only in a sample) is omitted only with user approval; otherwise source conflict/FLAG.

## 4. Geometry
Bake R into tangent points + bulge (`tan(sweep/4)`, 90° → 0.41421356, sign from the sweep); C as two offset vertices with bulge 0. Flat spec corner items: `[x,y]` (AUTO), `[x,y,{R|C: v, group, qty, ev}]`, `[x,y,{SHARP: "lý do"}]`, `[x,y,{FLAG: "…"}]`.

## Lessons
`regression/lessons/CORNER_RC/` — 520924-19 (workbook, 055955 two R2), 520801-04 (044841 10×R5), 520929-18 (C/R lock), 520217-26/27, 521023-16 (general note, sibling C1).
