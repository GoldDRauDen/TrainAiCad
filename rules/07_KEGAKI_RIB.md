# 07 — KEGAKI / RIB / FORMING / WELD | Production rules V4.34

> Separate each manufacturing mark, rib, forming detail and source-evidenced weld location; never infer a source mark from copied DXF.

<!-- BEGIN MODULE: skills/lispcad/features/KEGAKI.md -->
# LISPCAD Feature — KEGAKI / locating marks

## Source-backed weld-site census closure

For KH851, load ../../../references/WELD_SITE_KEGAKI_CLOSURE.md.
Every independently proved weld site needs locating KEGAKI even without
an explicit printed marking callout. Validate parent/child identity,
host face, assembly witness, physical contact, local-to-flat transform,
and actual mark quantity. If datum/shape is customer-pending, keep
a scoped FLAG rather than emitting a fabricated RED production line.
The source/canonical weld-site gate independently checks this requirement.
Other customers retain the V4.27 source-cue and locating-function scope.


**V4.20 approved; V4.27 weld-cue scope approved.**

KEGAKI is an independent manufacturing family, not CUT/BEND/decoration. Production KEGAKI is Layer 0, Color 1 Red, LINE or proved LWPOLYLINE. Red supports identification but is not proof by itself.

Every mark needs function, host-face ownership, source/local datum and quantity. A formed-face mark follows that face through the same local-face -> flat transform. Fold-back must reproduce the intended physical locating position.

Do not join separate mark segments merely because they align in the flat. If the positioned component contacts separate faces/material regions with a gap/bend-clearance, keep the marks split.

## V4.27 barcode weld cue / locating requirement

`REVERSED_E_ABOVE_BARCODE` is the approved visual cue for a reversed-e mark immediately above a part barcode. When proved, record `WELD_REQUIRED_CUE` and scope it only to the code / detail cluster identified by that barcode. Do not propagate the cue to an adjacent barcode, neighboring code, or the whole sheet.

`WELD_REQUIRED_CUE` proves the welding process expectation for that scoped cluster; it is **not** itself KEGAKI geometry and does not supply a footprint, dimensions, datum, quantity, or host face.

- If a scoped welded child part (for example a RIB / gusset / support) cannot self-locate during fit-up, locating KEGAKI on the main part is required. The mark geometry must come from explicit source KEGAKI evidence or from a proved contact/locating function and host-face transform. If that locating geometry remains unresolved after source exhaustion, keep `KEGAKI = UNKNOWN` / FLAG the affected geometry; never silently omit it.
- If a specific KEGAKI instruction is present, treat that as an independent welding/locating instruction even when `REVERSED_E_ABOVE_BARCODE` is absent.
- If neither `REVERSED_E_ABOVE_BARCODE` nor a specific KEGAKI instruction is present for the scoped code/cluster, do not infer welding or add KEGAKI solely from the presence, shape, symmetry, or proximity of a RIB / gusset / support.
- A welded child that is already mechanically self-locating does not acquire invented KEGAKI geometry merely because the barcode weld cue is present.

The barcode cue changes process/routing evidence only. It never authorizes copying the full secondary-part contour as KEGAKI.

## HD4 PL1 / PL2
Do not add a KEGAKI outline to every secondary plate by symmetry. In the approved HD4 example, PL1 is located by the proved physical material edge and has no copied equivalent mark; PL2 is positioned inside the face and has a locating KEGAKI footprint. This is a function/source rule, not permission to invent a mark merely because a part appears interior.

## RIB locating marks
RIB KEGAKI is the contact/position footprint on the MAIN part after forming, not an automatic copy of the full RIB contour. It may be separated across multiple host faces. Verify by fold-back/contact.

RIB-part cancellation and main-part KEGAKI cancellation are independent decisions; do not delete the mark without its own source/revision scope.

Audit KEGAKI independently for count, host face, datum/transform, continuity/segmentation, Red property and fold-back locating function.
<!-- END MODULE: skills/lispcad/features/KEGAKI.md -->

---

<!-- BEGIN MODULE: skills/lispcad/features/RIB.md -->
# LISPCAD Feature — RIB routing

**V4.20 approved.**

A RIB with valid drawing/barcode/code, not cancelled/crossed out and not explicitly excluded is an independent manufacturing part and must be output/audited independently.

RIB locating KEGAKI belongs to the main part and is evaluated independently:
- it represents physical contact/position footprint after forming;
- it may span different formed faces and become separated segments in the flat;
- transform each segment with its owning face;
- fold-back must return the mark to the proved contact location.

Canceling a RIB does not automatically cancel its main-part locating KEGAKI. A separate source/revision instruction must cancel that mark.

Audit RIB CUT/HOLE geometry and main-part RIB KEGAKI as separate families.
<!-- END MODULE: skills/lispcad/features/RIB.md -->

---

<!-- BEGIN MODULE: skills/lispcad/features/FORMING_FEATURES.md -->
# LISPCAD Feature — Forming & Center Markings

Approved calibration 520924-19, 2026-09-25.

### 3.2 3D formed-feature mapping to 2D manufacturing

- `Kegaki` / formed reference and explicitly required marking lines: Layer 0, Color 1 (Red), `LINE` or explicit `LWPOLYLINE` as the applicable drawing requires. Features include louver, emboss, dimple outline, rib, gusset, bridge, half shear, hem, curl and lance marks. Respect restrictions such as `※ケガキ不可` where listed by the material table.
- Manufacturing center `POINT`: Layer 0, **ByLayer by default**. Only a PDF-scoped **PIERCING + THROUGH HOLE** center is Color 3 (Green). Explicit PIERCING *without* THROUGH HOLE and material-capacity POINTs remain ByLayer. A provisional estimated center/type is Color 6 (Magenta) with an independent FLAG.
- Relief slits and other LINE geometry whose color is explicitly specified Green retain their LINE-specific legend; this does not permit arbitrary green POINTs. Do not create a circle of radius 0.5 to stand in for an AutoCAD `POINT` when the source requires POINT.
- The unusual `J`/POINT set requires an applicable explicit PDF J indication. It is not a universal shop feature and is not inferred merely because the reference DXF contains a J.
<!-- END MODULE: skills/lispcad/features/FORMING_FEATURES.md -->

---

<!-- BEGIN MODULE: references/WELD_SITE_KEGAKI_CLOSURE.md -->
# WELD_SITE_KEGAKI_CLOSURE — source-first hard gate

**Scope:** source-proved or source-suspected weld/assembly contact, with
**KH 851** as the customer-scoped mandatory marking exception. This is a
completeness check, not a geometric formula.

## Source authority before CAD output

1. Read numeric customer code from JOB STATISTICS, never a barcode suffix
   or Japanese name. KH 851 requires KEGAKI at every proved weld site
   even if no marking callout appears in the drawing (catalog J418).
2. Independently harvest all source assembly views, A/B or parent/child
   identities, physical weld/contact sites and installation witnesses
   BEFORE drawing marking coordinates.
3. Identify main/parent as the sheet being marked and child as the mounted
   part, including the actual physical host face. Never merge an assembly
   view into CUT, or copy the entire child outline as locating marks.
4. Solve each contact/mark with source dimensions, projection and
   physical face/attachment transforms; folded geometry must fold back
   to the same weld site.
5. If a required KEGAKI location remains unresolved, preserve a local
   source/canonical FLAG and mark the part REVIEW. No fabricated RED line.

V4.27 remains active for other customers: source-scoped weld cue plus a
non-self-locating child requires KEGAKI. A generic RIB/support does not
alone prove welding; self-locating pieces without a source/customer rule
do not acquire automatic marks. KH851 overrides only the need for a
printed marking callout once a physical weld site is proved.

## Independent source-census ledger

Persist per code before feature routing:

- part_code: the part's exact barcode/identity (e.g. 059685)
- customer_code: numeric ID from job statistics (e.g. 851)
- source_assembly_view_ids: all relevant views, including side A/B views
- source_weld_site_ids: independent welded-contact/site inventory
- weld_site_census: source_evidence, inspected_assembly_view_ids,
  sites, and no_weld_evidence if sites is empty

Each site retains weld_site_id, status (PROVED/FLAGGED), parent_code,
child_part_id, assembly_view_id, source_evidence, host_face for proved
sites, mark_status (PROVED/FLAGGED) for required marks, mark_member_ids
and source-backed datum_evidence for proved marks. Unresolved fields
are written to unresolved_fields. Other customers may require marks
from mark_required_by_source or a proved weld_required_cue with
self_locating=false. Non-required cases need not_required_evidence.

The two independent source inventories MUST agree with the weld-site
census. No-weld disposition requires an explicit source-grounded reason;
an empty list is not enough. A closed ledger does not prove that the
Reader actually inspected the PDF: independent source/holistic QA must
still check all views, dimensions and weld/contact evidence.

### Manufacturing mark provenance

A proved marking must have a host-face datum/witness expression and real
KEGAKI source-backed canonical members. Manufacturing mark entities
are RED (DXF color 1), role kegaki, LINE or source-proved LWPOLYLINE.
Unconfirmed marks remain FLAGGED_NO_GEOMETRY or an explicit Magenta
preview/source-view (never RED or CUT). Any missing required mark is FAIL.

Do not borrow missing dimensions or coordinates from a sample/reference:
the source-only reference firewall remains mandatory.

## Executable gates

- Router: tools/resolve_rules.py checks a complete independent source
  weld inventory for KH 851 and refuses KEGAKI=NO on required sites.
- Canonical: tools/canonical_contract.py calls the new
  tools/weld_kegaki_guard.py before exporting, ensuring every required
  weld site has a real KEGAKI source+canonical member and proved RED
  geometry, or a local REVIEW/FLAG. Canonical entity IDs/read-back remain.
- Holistic QA: compare actual source assembly views and part identities
  with the inventory. Ledger self-equality is never sufficient when
  the real source contains an unharvested weld feature.

## Regression targets (521013-12)

- 059685: A-B installation/weld to KEGAKI is required under KH851
  without an explicit mark callout; omitted group must FAIL.
- 059676 and 059678: classify separate contacts/mark groups by
  source witness and part identity, not by copying sample U-shapes.
- 059683: user's red 14 mm dimension is CUSTOMER_CONFIRMATION_PENDING,
  not production geometry, even if the DXF sample contains Magenta.
- For other customers, genuinely self-locating contacts with no source
  marking obligation must not automatically receive KEGAKI.

Synthetic regression geometry exercises these gates but is NOT an
independent CAD solution of the user's PDF.

This change does not alter Nobi, R/C, source hierarchy, other customer
rule data, or the TrainAiCad-CANONICAL-V4.31 schema version.
<!-- END MODULE: references/WELD_SITE_KEGAKI_CLOSURE.md -->
