# ORTHO_PROJECTION_OD_SEPARATION — measure OD from the DXF, cut by projection, rotate, join

**Approved:** 2026-10-21 by the user from job `521021-06`, part `26-062103` (guide `26-062103_hd_tach.dxf`).
**Scope:** a bent part whose faces are only visible in a side/profile view plus an auxiliary view that is rotated on the sheet (slanted face, non-90 bend, formed face drawn in true shape). Complements `FORMED_PROFILE_OD_MEASUREMENT.md` (ownership of OD terms) and `BEND_DATUM_MAPPING.md`.

## 1. Rule

1. **Measure, do not read.** Every outside dimension (OD) that feeds the flat is measured from the DXF geometry of the profile/side view (point-to-point along the owning face, from the free edge to the outer corner). A printed number such as `410`, `175` or `306` is only a cross-check. "The drawing does not say inside or outside" is never a reason for FLAG/PREVIEW while the DXF geometry can be measured.
2. **Project orthogonally at the OD lines.** From the outer corner of the profile view, draw the perpendicular projection line into the other view (top/plan view or the auxiliary view). It cuts each face exactly at its OD plane. Keep the part on the free-end side of the cut; discard the rest.
3. **Rotate the auxiliary view.** Rotate the cut piece about its own angle (here 33 degrees) until its length axis is parallel to the chain axis. A rotated auxiliary view is true shape; "not a 90-degree projection" is not a reason to skip it.
4. **Join with offset.** Place the next piece at the OD distance of the face in between (here the vertical face 20.8: plate OD end, +20.8, panel OD base line), then subtract the sum of the Nobi values (`1.68 + 0.36`). The panel OD base line therefore lands on `line1` of the last bend (`410.8 + 20.8 - 2.04 = 429.56`). Panel coordinates are `u` (along the face from its OD base line) and `v` (across); flat `X = line1 + u`.
5. **Features come from the same measurement.** Slots, holes, notches, slits and tabs are taken from the cut and rotated piece, not retyped from rounded dimensions. A tab/flange bent out of an edge is positioned at its OUTER face plane (neck lines show tangent and outer plane: for R1 and t0.8 the neck is `304.0 / 305.8`, so the OD edge is 305.8, not the printed 306); flat tip = `OD_edge + flange_OD - Nobi` (`305.8 + 19.0 - 1.68 = 323.12`).
6. **Gap geometry is continuous through the join.** A notch drawn in two views is one cut: it runs through the plate, the intermediate face and into the next face up to its closed end (`26-062103`: gap 146 from the plate end through the 20.8 face to the R10 bottom 120 from the free edge); bend lines are split into one segment per leg.

## 2. Self-check before export

- Every dimension used in the builder is either a direct DXF measurement or an arithmetic result written with its formula. Hand-rounded numbers (306, 92, 238 ...) are compared with the DXF; tolerance 0.02 mm.
- Compare the final holes, arcs and straight ends with the separated/rotated source geometry. A mismatch is an error to fix, not a rounding to accept.
- Do not write "unclear" for something that exists in the DXF; say which entity was not found.

## 3. Regression facts (`521021-06`, `26-062103`, SPCC t0.8, KH 646)

- Chain `410.8 -(90 deg, 1.68)- 20.8 -(147 deg, handwritten 0.36)- 175.0`: flat 604.56; bend 1 lines 409.12/410.8; bend 2 lines 429.56/429.92.
- Widths: prongs 92 and 81 (68 at the bend end), gap 146, face/panel 306, tab outer plane 305.8.
- Tab: 13 wide, 19.0 outside height, Ø7 at 7.08 from the tip, two 1.0 slits 4.7 deep (R0.5 bottoms, R2 outside corners): flat tip 323.12.
