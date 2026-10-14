# 03 — TOPOLOGY | Production rules V4.34

> Profile topology, face identity and flat-no-bend rules. Original module names are preserved as audit section IDs.

<!-- BEGIN MODULE: skills/lispcad/modes/FLAT_NO_BEND.md -->
# LISPCAD Mode — Flat / No Bend

## Scope

Use this mode when the drawing requires no bend-unfold calculation.

This module intentionally adds **no new manufacturing rule** beyond the approved core and applicable topology/feature modules. Do not import bend-specific Nobi, ID→OD, face-order, or unfold calculations unless the drawing explicitly requires them.

Always apply:
- `../core/DRAWING_READING.md`
- `../core/DATUM_DIMENSION.md`
- `../core/VALIDATION.md`
- `../core/CAD_OUTPUT.md`
<!-- END MODULE: skills/lispcad/modes/FLAT_NO_BEND.md -->

---

<!-- BEGIN MODULE: skills/lispcad/topology/L_PROFILE.md -->
# LISPCAD Topology — L Profile

## Scope

Use together with the applicable mode.

No L-profile-specific universal manufacturing rule has been approved yet. Apply the core rules, the selected bend/no-bend mode, and applicable feature modules.

Regression case `018263` remains evidence that an L/stepped visible contour must not be replaced by its bounding rectangle.
<!-- END MODULE: skills/lispcad/topology/L_PROFILE.md -->

---

<!-- BEGIN MODULE: skills/lispcad/topology/U_PROFILE.md -->
# LISPCAD Topology — U / Open-Center Profile

## Scope

Use together with the applicable mode.

This module currently adds no duplicate calculation rule. For U/open-center parts, apply the bend-line material-domain and containment rules from:
- `../core/VALIDATION.md`
- `../modes/BEND_UNFOLD.md` when bends are present.

No additional U-specific universal rule has been approved yet.
<!-- END MODULE: skills/lispcad/topology/U_PROFILE.md -->

---

<!-- BEGIN MODULE: skills/lispcad/topology/MULTI_FACE_PROFILE.md -->
# LISPCAD Topology — Multi-Face Profile

## Scope

Use for parts whose feature coordinates or bend positions depend on multiple formed faces.

The approved local-face → global-flat transform and non-commutative face-order rules are defined in `../modes/BEND_UNFOLD.md`. This topology module introduces no duplicate calculation rule.

No additional multi-face-specific universal rule has been approved yet.
<!-- END MODULE: skills/lispcad/topology/MULTI_FACE_PROFILE.md -->

---

<!-- BEGIN MODULE: skills/lispcad/topology/STEPPED_PROFILE.md -->
# LISPCAD Topology — Stepped / Notched Profile

Source: approved V4.3 production baseline.

The general contour-topology rule remains in `../core/DATUM_DIMENSION.md`.

### 4.9 Stepped / Notched Flanges *(restored from V1)*
For flanges stepping inward before joining the body:
- $Y_{\text{flange\_flat}} = L_{\text{flange\_nominal}} - N_y$
- $Y_{\text{bend}} = Y_{\text{flange\_flat}}$
- $Y_{\text{notch}} = Y_{\text{flange\_flat}} + L_{\text{notch\_gap}}$
- $Y_{\text{body\_flat}} = L_{\text{body\_nominal}}$ (untouched)
<!-- END MODULE: skills/lispcad/topology/STEPPED_PROFILE.md -->
