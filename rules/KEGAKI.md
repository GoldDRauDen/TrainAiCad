# KEGAKI — locating marks, weld sites, RIB, formed marks (ケガキ)

Triggers: `ケガキ`, `罫書`, reversed-e mark above a barcode, welded child (RIB, gusset, support, tube, plate), assembly views A/B/C, `溶接`, customer 851, emboss/louver/dimple/half-shear/curl/lance marks.

## 1. When a mark is required
- Customer **KH851**: every proved weld/contact site needs a KEGAKI on the axes the plates' own edges leave free (§3), even with no printed mark callout.
- Other customers: a specific KEGAKI instruction, or a proved `REVERSED_E_ABOVE_BARCODE → WELD_REQUIRED_CUE` (scoped to that barcode's code/cluster only) plus a child that cannot self-locate. A RIB/support alone never proves welding; a self-locating child gets no mark.
- The cue proves the process only; geometry still needs a proved contact/footprint. Unresolved location → `KEGAKI = UNKNOWN` + local FLAG (Magenta or FLAGGED_NO_GEOMETRY, never Red), part PREVIEW. Never NO for a required site.
- A welded tab that is actually bent from the same sheet has no weld site (`BEND.md` §4).

## 2. Weld-site census (before routing; `tools/weld_kegaki_guard.py` checks it)
Per code: `part_code`, `customer_code`, `source_assembly_view_ids`, `source_weld_site_ids`, `weld_site_census` {source_evidence, inspected views, sites[], no_weld_evidence}. Each site: id, PROVED/FLAGGED, parent_code, child id, view, host face, mark status, mark member ids, datum evidence. N stacked parts → ≥ N−1 contact pairs. KH851 with assembly views and `sites=[]` needs `assembly_laser_partner_codes` and a `no_weld_evidence` naming each partner (`CHAIN_CENSUS_EMPTY`).

## 3. Host and footprint (from the PDF views)
- Host = the LASER part that RECEIVES the contact (the other part's edge stands on its face and cannot locate itself). Not by letter order. Non-laser host (purchased tube) → `host_not_laser`, no DXF mark. The child never draws its own footprint.
- Footprint = projection of the child's thickness edge on the host face. Width `t` (square edge); `hypot(Δ, t)` for a slanted end with alternate lengths differing by Δ (t6, 117/113.5 → 6.946); `t/cos(tilt)` for a tilted child (t6, 12° → 6.14). Length = contact edge length − printed offset; slanted edge length from the SHORTER alternate heights (KH851 uses the shorter of alternate overall lengths). Position from the printed offsets. Numbers: `python tools/lookup.py kegaki --t T [--slant-delta d | --tilt a] [--edge L --offset o] [--run r --short a b] [--host-t th --k k]`; drawn with the spec `kegaki:` lines.
- A thin strip in an assembly plan view is the child's footprint, never a host slit/cutout without its own callout.
- Child standing on two faces of a bent host, foot adjacent to the bend, no chamfer at the foot → ONE closed union outline running across the bend line; with a chamfer follow it or FLAG. Web-face flat position = line1 + v, v measured from the flange OUTER plane (521021-20: 84.38 + 9 + 150 = 243.38).
- Boundary coinciding with the part contour → only the inner line, at `t_host − k` from the welded edge, full width (062113: 6 − 4 = 2).
- Per axis: edges that already fix X and Y (flush edge, face contact) → no line. Plates crossing mid-length each carry the other's position along itself. A child set back from the edge is not located by it (inner line above).
- "No dimension on the mark" is not a FLAG reason; FLAG only when a needed number is truly absent from the PDF.

## 4. Drawing form
RED (62=1) LINE, Layer 0, role kegaki; a round mark (bar/tube end) is ONE CIRCLE (tube: outer ring only), spec `circles:`. No line on the part contour (`KEGAKI_ON_CONTOUR`); touching zones drawn as ONE union outline, no segment inside it (`KEGAKI_DUPLICATE_SEGMENT`); never the full child outline. Marks on a formed face follow that face's local→flat transform and must fold back to the contact. Separate faces/regions with a gap stay split. The KEGAKI face is the OUTER face (`OUTPUT.md` §6).

## 5. RIB and formed marks
A RIB with its own code is an independent part; its CUT and the main part's locating mark are separate families; cancelling one never cancels the other. Formed-feature reference marks (louver, emboss, dimple, half shear, hem, curl, lance) = Red LINE when the drawing requires them; respect `※ケガキ不可` (Cu/Brass t≥6). HD4: PL1 located by the material edge (no mark), PL2 inside the face (mark) — function decides, not symmetry.

## Lessons
`regression/lessons/KEGAKI/` — 521005-01 (weld cue), 521013-12 (KH851), 521019-13 (outer face), 521021-03 / 521021-20 (footprints, across the bend), 520925-03 HD1 (B-side footprints), 520929-10, HD4, 521026-13 (round marks, one circle), 521028-22 (marks only on free axes, union).
