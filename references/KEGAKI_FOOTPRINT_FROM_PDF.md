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

## 2b. Child standing on two faces of a bent host (521021-20)
- A thin strip in a plan view of an assembly (rib seen edge-on, 6 mm wide) is the child's FOOTPRINT, never a slit/cutout of the host. A cutout needs its own callout or dimensions on the host; do not infer one from a strip.
- When a rib stands on both the flange and the web of a bent host and its foot is adjacent to the bend with NO chamfer at the foot, the two contact zones are adjacent: draw ONE union outline that runs continuously across the bend line (closed rectangle, 4 red LINEs when no side lies on the contour).
- If the rib foot is chamfered, the contact zone is cut by the chamfer: do not apply this; follow the chamfer geometry or FLAG.
- Flat position of a web-face point = line1 + v, with v measured along the web from the OUTER plane of the flange (flange thickness included). Example 521021-20 (t9, line1 84.38): rib 150 on the web, v = 9 + 150 = 159 -> 84.38 + 159 = 243.38. The flange contact starts at (inner flange length 90) - (rib base 65) = 25 from the flange end.

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

## 8. Worked values (521021-20, KH851, plan-view frame, origin = part bbox min)
| Code | KEGAKI |
|---|---|
| 062288 (t9, bent, 314.38 x 75, flange end at top) | closed rectangle across the bend: x 34.5..40.5 (6 wide, centred), flat from flange end 25 .. 243.38; no cutout |
| 062289 | none (rib C, child) |
| 062291 | none (child of 062292) |
| 062292 (dx) | 2 LINEs y=22 and y=28, full width 22 (child centred on the 50 length) |
| 062293 (dx) | 2 LINEs x=30 and x=70, full depth 90 (tube 40, host_not_laser) |
| 062294 / 062295 | 2 LINEs x=95 and x=135, full depth 75 / 25 (tube 40 centred by 95+40+95) |
