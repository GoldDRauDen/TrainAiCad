# WELD_TO_BEND_OUTER_INTERSECTION_OD — welded flange turned into a bend, OD from the outer-face intersection

**Approved:** 2026-10-23 by the user from job `521023-14`, part `26-062885` (guide `3058485f-062885HD.dxf`).
**Scope:** SPECIAL CASE. A flange/tab that the drawing shows as a separate welded piece (e.g. `B x2`) but that is made as a BEND of the same sheet. It does NOT replace the general rules of `FORMED_PROFILE_OD_MEASUREMENT.md` / `ORTHO_PROJECTION_OD_SEPARATION.md`; it is an extra route used only when the weld is converted to a bend.

## 1. Rule

1. **Weld becomes bend.** When the guide/user shows the welded piece as formed from the same sheet, the part is a bent part: no weld site exists, so no KEGAKI. Census: `sites=[]` with `no_weld_evidence` = "flange tab is integral (bent), not a welded child". Do not leave a FLAGGED KEGAKI site for it.
2. **Always construct the outer-face intersection; OD = free end to that intersection, measured along the outer face.** Printed numbers are added only as far as they already reach it:
   - Bend angle = 90 degrees and the dimensions already end at the outer-face intersection: sum them (minus Nobi).
   - 90 degrees, but a printed dimension stops at the INNER face of the mating plate: add t for that face (e.g. plate 30 standing on plate 50: `OD(30 face) = 30 + t`).
   - 90 degrees, but the standing plate is set back from the edge of the base plate by an offset `s` (not flush): add `s` to the base-plate face (e.g. `s=3`: `OD(50 face) = 50 + 3`, `OD(30 face) = 30 + t`).
   Every `+t` and `+s` term is single-use (`THICKNESS_SINGLE_USE`) and must be written with the face it belongs to. If the section does not show which face a dimension touches or where the offset is measured from, FLAG locally.
3. **Bend angle != 90 degrees.** Build the profile section: flange and leg, each of thickness t, at the bend angle (include any set-back offset). Extend the two OUTER face lines to their intersection point. Measure from each free end to that intersection (CYAN construction in the guide). These two lengths are the NEW OD terms:
   `L_flat = OD1 + OD2 - Nobi`.
4. Construction used by `26-062885` (flange 30 measured on the outer face from the free end to the flange far end; leg 50 measured along the leg outer face from the flange inner far corner to the leg free end; t=6; 100 degrees): with `d = angle - 90`,
   `OD1 = 30 - t*tan(d) = 28.942`, `OD2 = 50 + t/cos(d) = 56.093`.
   Always re-derive from the actual section view of the drawing in hand. If the dimensions do not touch the faces exactly this way, take the faces they really touch; if that is not determinable, FLAG locally.
5. **Positions after the OD is known.** Bend line 1 = `OD1 - Nobi`; bend line 2 = `OD1`. Draw the double dashed bend lines only where flange material exists (tab zones), not across a notch. A notch wall is placed at `W - leg_dimension` when the drawing states that leg dimension (here 50 -> 26.39); if the wall position is not clear, FLAG it.
6. **Rounding.** When the bend is drawn from the PDF, flat dimensions and line positions are rounded to 2 decimals (`W=76.3946 -> 76.39`, `20.302 -> 20.30`, `28.942 -> 28.94`). Keep 3 decimals for OD in the ledger.
7. Corners: Laser R2 on convex corners <= 90 degrees only (concave and 135-degree C20 chamfer corners stay sharp). J/LJ marks follow the existing `Laser_SheetMetal` rule on the long straight edge (blank X >= 1000, Y <= 100).

## 2. Not allowed

- Do not apply this route to an ordinary bend, only to the weld-to-bend conversion above.
- Do not copy `76.39`, `28.942`, `56.093`, `26.39` to another drawing; they are calibration values.
- Do not keep a KEGAKI site for a tab that has become a bend.

## 3. Regression fact (`521023-14`, `26-062885`, SPHCP/SS400 t6, KH 851)

- Length 1015, bend 100 degrees, Nobi 8.64 (handwritten), tabs 38 mm long at both ends, 939 notch between, 2-C20 at leg ends, 2-O10 at 10 from the free edge and 20 from the ends.
- `W = 28.942 + 56.093 - 8.64 = 76.39`; bend lines `20.3 / 28.94` in the 38 mm zones; notch wall 26.39; J/LJ at 30 from the leg-edge ends. Calibration only.
