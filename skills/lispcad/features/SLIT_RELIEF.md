# LISPCAD Feature — SLIT / bend relief routing

**V4.29 custom source-slit gate; V4.20 base formulas retained.**

## V4.29 — custom source-instructed slit

A printed/handwritten `スリット`, `SLIT`, or equivalent explicit slit instruction may define a **custom source-instructed slit**.

- This custom branch is instruction-driven. Do **not** add it merely because a bend exists, because a slit would be mechanically useful, or because a reference/sample contains one.
- The source value is drawing-specific. For example, `スリット 8` means the controlling explicit slit value for that scoped feature is 8 in that drawing. It does not establish a universal 8 mm rule.
- Read quantity, host edge/face, position, direction, and relation to BEND from the actual instruction, witnesses, leaders, and geometry. Such slits are often used around bend regions to reduce deformation, but that purpose does not prove that the slit lies at the bend center.
- Never hardcode a centerline or copy a reference-DXF coordinate into a new drawing.
- When the custom slit has an explicit controlling dimension, preserve it. Do not replace it with the generic `D90=t+0.2` or `D=t*sin(theta)` formulas below.
- If slit identity/scope is proved but a required numeric/position field remains unresolved, retain the feature and FLAG the unresolved field; do not silently drop `SLIT_RELIEF`.
- Load/close `references/SOURCE_MANUFACTURING_NOTE_CENSUS.md` for source-note provenance.

Existing same-direction corner retreat (`BEND_EDGE_RELIEF_90.md` section 9), opposite-fold `R=t`, `055958`, BOXMET and other separately-triggered relief mechanisms remain independent. This section does not require an explicit `スリット` note for those already-approved mechanisms and does not change their trigger/orientation rules.

## Base classification

First classify whether a source feature is ordinary CUT slot/notch, custom source slit, bend relief slit, BOXMET slit, lance, KEGAKI or another process. Similar appearance or Green color does not prove process identity.

## 90-degree bend slit

For the approved generic 90° bend-relief family, and only when that mechanism is actually the routed controlling mechanism rather than an explicit custom slit dimension, retain:

`D90 = t + 0.2 mm`.

## Bend angle greater than 90 degrees

For the approved >90° bend-relief family, with included physical bend angle `theta` satisfying `90° < theta < 180°`:

`D = t * sin(theta)`.

Equivalent reflex form: `D = t * abs(sin(phi))` when `phi = 360°-theta`.

Approved t=3.2 examples:
- 150° -> 1.600000 mm
- 130° -> 2.45134221798 mm
- 110° -> 3.00701638651 mm

The 150° value equals t/2 only because sin(150°)=0.5; do NOT generalize t/2. Exactly 90° uses the separate `t+0.2` rule when the generic 90° relief mechanism applies. Slit depth is not Nobi.

Preserve source-proved slit direction/connectivity and applicable local fillet/tangent construction. Do not universalize a local R0.5 unless the source/existing mechanism proves it. Green LINE/ARC geometry may be slit/relief; Green is supporting evidence only. A Green POINT with proved PIASU semantics is a different family.

QA: close source-note provenance when applicable, correct quantity/value/position/direction, correct mechanism/connectivity, no duplicate/coincident paths, no helper geometry in manufacturing CUT, correct BEND interaction, and saved-DXF physical read-back.


## Same-direction corner and opposite-fold construction

**Same-direction corner (replaces the old CROSSING_BEND mechanism, user 2026-10-20):** follow `../../../references/BEND_EDGE_RELIEF_90.md` section 9: the SHALLOWER flange retreats by `t` (depth differing by `>= 0.1 mm`; equal depth -> either, prefer the longer bend edge), then the normal step gate applies (`S=-t` -> slit `t + 0.2` + lead; the other end `S=+t` -> none). Never retreat the deeper flange (khuyết_t).

**Opposite-fold fixed-outside R=t relief** (approved calibration `055962`):
- When **two outer material edges actually intersect after step and bend-domain closure**, fold in different directions and require both outside dimensions unchanged, create `R=t` escape relief at that proved intersection. Different fold directions alone do not trigger it. A positive-step normal junction follows BEND_EDGE_RELIEF_90 Case A unless an independently proved specific mechanism controls; retain that mechanism's tangency/material-side proof.
- In `055962`, `t=2 mm` gives the two confirmed R2 reliefs. A separately observed R2 on an unbent corner is NOT automatically this relief.
- A proved connected LINE + local ARC + LINE relief is one operation, not three. A local R0.5 is not universal Laser R or a required slit radius. Approved 055958 method/count and independent pending fields remain in `../../../regression/features/520924-19_APPROVED.md`.

## BOXMET-style four-flange box routing

If the source proves a central/base rectangle with four adjacent bent flanges and BOXMET corner topology, load `../../../references/BOXMET_SLIT_RELIEF.md`. This reference decides which pair of flaps retreats by `t`, generates the four required slits, constructs the tangent `LINE + ARC R0.5 + LINE` geometry, and defines when the rule is not applicable. Do not omit a required BOXMET slit merely because the outer contour is already closed; do not auto-apply BOXMET slit logic to ordinary L/U/Z, single-flange/free-edge, non-crossing, or unrelated relief topology.
## One controlling mechanism per junction

Execute `../../../references/BEND_EDGE_RELIEF_90.md` §7 precedence: revision/cancellation or explicit custom slit first; proved topology-specific BOXMET/opposite-fold next; signed-offset 90-degree gate next; same-direction corner retreat (section 9 of BEND_EDGE_RELIEF_90) only chooses the recessed flange and then uses the signed-offset gate. Unknown size/sign/direction remains local FLAG. Depth alone never proves direction, scope or connectivity. The bend mode loads this owner before a final NO decision; the independent SLIT_RELIEF feature route also remains available for flat/custom source slits.
