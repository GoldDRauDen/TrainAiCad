# KEGAKI_FOOTPRINT_FROM_PDF — compute the contact footprint from the PDF

**Scope:** KH851 (and any customer with a proved weld/contact site) stacked
plate assemblies such as A–B–C. Complements `WELD_SITE_KEGAKI_CLOSURE.md`
(census) with HOW to derive the mark geometry from the source views. Source:
job 521021-03, audited against the customer's sample (the sample is an audit
only; the source-only firewall is unchanged — every number below must be
traceable to a printed/derived PDF dimension).

## 1. Host: which part carries the mark
The mark is drawn on the LASER part that RECEIVES the contact: the other part's
**edge stands on this part's face and cannot locate itself** (hand-written
ケガキ in the PDF and/or the dimensioned VIEW confirm). 617: A's end on B →
mark on B; B's edge on C → mark on C. A has none. The child never draws its own
footprint. Host is NOT decided by letter order A/B/C. If the receiving face is a
purchased/non-laser part (tube, cap in tube) there is no DXF for that mark:
record `host_not_laser` in the census. If the host cannot be proved → FLAG.

## 2. Footprint = projection of the child's thickness edge on the host face
- Width: `t` for a square edge; `hypot(Δ, t)` for a slanted end whose two
  alternate lengths differ by Δ (117 vs 113.5, t6 → 6.946); `t / cos(tilt)` for a
  tilted child (t6, 12° → 6.14).
- Length: contact edge length − printed offset (B height 35, offset 5 → 30,
  starting at the part edge). Slanted contact edge: length of the slanted edge
  from the SHORTER alternate heights (95.7 / 90.3 over run 20 → 20.716), minus
  the offset 5 → 15.716 (≈15.72). The angle is a result, never a separate
  measurement and never a cos division of another angle.
- Position across: the printed offset in the view (5.5 from the base → y 5.5 to
  5.5 + 6.946; 13 from the side edge → right face of a 6.14 box 13 from the
  right edge).
- Alternate overall lengths: use the SHORTER for machining (KH851 J418; weld
  makes up the difference).
- Helpers and tests: `tools/kegaki_footprint.py`, `tests/test_kegaki_footprint.py`.

## 3. Single line
When the other boundary of the contact zone coincides with the part contour,
only the inner boundary is drawn, at `t_host − k` from the welded edge, where k
is the dimension shown in the view (062113: 6 − 4 = 2; 062024: 6 − 2 = 4).
It runs the full width of the part.

## 4. Drawing form (executable: `weld_kegaki_guard.check_kegaki_drawing_form`)
- RED LINE entities only (role kegaki, color 1).
- A boundary lying on the part contour is NOT drawn (`KEGAKI_ON_CONTOUR`): the
  rectangle of 062020/062021 is open on the part edge (3 LINEs).
- Touching/overlapping zones are drawn as ONE UNION outline, shared boundaries
  removed (`KEGAKI_DUPLICATE_SEGMENT`): 062027 tube 12.5..62.5 × 25..75 plus ribs
  37.5..43.5 × 75..100 and 0..25 = 10 LINEs; the tube outline is interrupted at the
  rib windows and each rib runs out to the plate edge.
- Never copy the whole child outline.

## 5. When to FLAG instead
Only when a number the formula needs is genuinely not in the PDF (offset,
contact length, host proof). "No dimension on the mark itself" is not a reason:
derive it from the views as above. Unresolved → local FLAG + Magenta, never RED.

## 6. Chain census (see WELD_SITE_KEGAKI_CLOSURE.md)
Every laser part in an A–B–C assembly view needs either weld sites or an
explicit `assembly_laser_partner_codes` + `no_weld_evidence` naming each partner
(`CHAIN_CENSUS_EMPTY`). A silent `sites=[]` is what dropped the 062113/062114/062024
marks in the first run of 521021-03.

## 7. Worked values (521021-03, local coordinates, origin = part bbox min)
| Code | KEGAKI |
|---|---|
| 062019 | none (A lands on B) |
| 062020 / 062021 (identical flat) | rectangle x 0..30, y 5.5..12.446, open on x=0 |
| 062113 / 062114 | LINE y=2, x 0..19 |
| 062023 | U open on the bottom edge: 6.14 wide × 15.716 deep, right face 13 from the right edge |
| 062024 | LINE y=4, x 0..22 |
| 062027 | 10 LINE union (tube + 2 ribs) |
| 062028 / 062029 | none |
