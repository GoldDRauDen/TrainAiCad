# 06 — HOLE / TAP / SLOT | Production rules V4.34

> Holes, pilots, threads, countersinks and straight/curved slots. Preserve per-material pilot/witness requirements.

<!-- BEGIN MODULE: skills/lispcad/features/HOLES_TAPS.md -->
# LISPCAD Feature — Holes / Taps / Piercing

2026-10-12 clarification: For a countersink/counterbore, only the proved through-opening/pilot is prospective laser CUT; never serialize machining-mouth diameter as a second CUT. See `references/COUNTERSINK_COUNTERBORE.md`. Fine-pitch threads only when pitch is explicitly proved; route `references/THREAD_FINE_PILOT_TABLE.md`. Even DATA-authority customer exceptions cannot waive physical hole identity/count/type/position checks. NC pierce paths and joints are deferred.



## V4.24 — universal DATA M* nominal-reference / pilot canonicalization

This applies to **every proved `M*` tap**, not only M6.

1. Lock the PDF/source thread identity `M<n>`, quantity, leader scope, host face and DATA feature cluster before converting geometry.
2. If that DATA cluster contains an independently identifiable concentric nominal thread reference circle/ring, classify it `THREAD_NOMINAL_REFERENCE` and compare its diameter against nominal `n` using the normal DATA<->PDF same-parameter gate: `Delta < 0.1 mm` passes; `Delta >= 0.1 mm` => `DATA_PDF_DIM_DIFF`. Exactly 0.1 mm flags.
3. A `THREAD_NOMINAL_REFERENCE` is semantic/reference geometry and **must not** become a second laser CUT. Do not compare the raw inner pre-hole/pilot diameter against nominal `n`; those are different physical parameters.
4. Preserve the DATA center, quantity, host-face ownership and raw pre-hole provenance. Unless the PDF explicitly specifies another effective cut diameter, serialize exactly one production hole using `THREAD_PILOT_TABLE.md` for the proved `M*`.
5. Example only: PDF M6 + DATA outer nominal Ø6 + inner/raw Ø5.1 => identity M6 is consistent and final production CUT is one Ø5.0 pilot. M4/M5/M8/etc. follow the same mechanism with their own table values.
6. If a DATA circle's nominal-reference role is ambiguous, FLAG that semantic assignment instead of choosing by proximity/size. If DATA has no proved nominal-reference entity, do not invent one merely to run the delta check.
7. Production QA fails if both nominal-reference and pilot circles survive as CUT, if raw pre-hole diameter is retained where the table controls the pilot, or if a nominal-reference `Delta >= 0.1 mm` is silently accepted.

Approved calibration 520924-19, 2026-09-25. Uses `../../../references/MATERIAL_RULES.md` (transcribed approved workbook) and `../../../references/THREAD_PILOT_TABLE.md`.

## 3.1 Cutting features
- A verified cut round hole is a `CIRCLE`. A tapped M feature uses the standard **pilot hole** diameter, not the nominal thread diameter, unless the drawing explicitly specifies another effective hole diameter. Countersink/counterbore cut geometry uses the proven through-hole/pilot opening; do not cut the countersink's outer diameter.
- Slots and polygonal cutouts follow the separate `SLOTS.md` module and topology rules. A POINT is NOT a small circle, and converting an M callout does not change the required feature count.
- Trace the arrow/leader/note scope before applying PIERCING. A large PIERCING label elsewhere on a sheet is not blanket authorization for every feature family.

## V4.12 unresolved circular-hole diameter gate — before numeric POINT/CIRCLE tests

When the source confirms a feature is a ROUND HOLE but its Ø is customer-pending, draw a source-supported, integer-rounded estimated **CIRCLE** on Layer `0`, Color `6` (Magenta) with adjacent `Ø? / CONFIRM DIAMETER` note and independent FLAG. Preserve separately proved centers, quantity and flat contour. Set PREVIEW / NO CUT. Do **not** apply `d<t/2` or capacity-based POINT rules using guessed Ø; those require a known effective diameter. Explicitly scoped PIERCING remains independently authoritative. Unknown round-hole identity or center follows V4.11 source-supported preview/VIEWS_ONLY and separate flags, not a fabricated verified hole.

## 3.3 Approved POINT / CIRCLE decision (first matching rule)

**L09:** For **SUS430**, apply **SUS, 他** rows to cut-hole minimum and 白ピアス capability, independently of SS/SUS430/BRASS Nobi. At t6 the inherited minimum hole threshold is t/2 and White Piercing is 〇 (capability only).

1. If the PDF explicitly applies `PIERCING + THROUGH HOLE` to a feature family: `POINT` on Layer 0, DXF color 3 (Green); Ø/M only in Stage 1 report, not CAD.
2. Else if the PDF applies `PIERCING`: `POINT` on Layer 0, ByLayer (no explicit color 3/6), regardless of the worksheet's `白ピアス 〇/×` or nominal diameter. That worksheet column is machine **capability**, NOT drawing intent; a `×` does not suppress the explicit PIERCING POINT or create a capacity-only FLAG.
3. Else, if the effective cut-hole diameter `d < t/2`: `POINT` ByLayer with **no capacity FLAG**. This holds even without a worksheet row. Strict inequality: `d = t/2` proceeds to the worksheet test.
4. Else look up the applicable material/thickness row of `references/MATERIAL_RULES.md` (the approved `Rule_Bo_R&Hole.xlsx` transcription). If `d` is below that row's inherited minimum hole diameter: `POINT` ByLayer, **no capacity FLAG** even without PIERCING. Otherwise draw `CIRCLE` ByLayer at the effective cut diameter.
5. If the worksheet cannot resolve the material/thickness/limit or the output type remains unproved and `d >= t/2`, use a **provisional `CIRCLE` Color 6 (Magenta) plus FLAG**; never assert production readiness. For a proved tapped `M*` callout, obtain provisional `d` from the approved thread pilot table (e.g. M4 Ø3.3, M5 Ø4.2, M6 Ø5.0), except where the PDF explicitly overrides it.

The precedence above is per **feature family**, never per whole sheet. No numeric capacity FLAG is warranted when a higher-priority explicit PIERCING or verified capability rule definitively selects POINT. Independent uncertainty about quantity, center coordinates, PDF legibility, handwritten instructions or customer approval **continues to require FLAG**. If feature identity/topology is unresolved, do not invent a hole or switch type merely to fill an output.

**Color contract:** all geometry Layer `0`; ordinary `POINT` ByLayer (DXF 62 omitted or 256); **only explicit PIERCING + THROUGH HOLE** produces a green **POINT** (62=3). A *provisional* feature is Color 6. Do not add redundant circle geometry or Ø/M labels around a POINT. Retain Ø/M and the conversion reason in the Stage 1 report.

## 3.4 Special J markings vs ordinary hole features

A printed `J` associated with a special POINT operation is **exceptional**, not a general feature inferred from an adjacent POINT or reference DXF. Only create that POINT/J set when the PDF has an applicable note/leader; when the mark is unreadable, flag it. This usage must be disambiguated from any bend/Nobi `J-symbol` described by the bend module; do not transfer a J operation between them. Calibration `055957`: the user confirms the PDF has a special J indication, but exact leader location is deferred; do not manufacture its geometry from the DXF alone.

## Verification and workflow

Trace separately the original callout count, verified effective diameters, POINT-vs-CIRCLE type, datum for every center, and every independent FLAG. Run material-domain containment on CIRCLE features. Preserve the part and keep a distinct shop report for all converted POINTs (source Ø/M, center, method/trigger).

### V4.14 approved boolean union for source-proven overlapping cut holes

When the actual source proves that hole/opening CUT REGIONS genuinely intersect to form ONE connected laser-cut void, compute the geometric Boolean union and output exactly ONE continuous closed CW internal boundary for the combined region (exact ARC/LINE arcs or correct bulged LWPOLYLINE). Do NOT output each contributing complete CIRCLE on top of the union or leave redundant interior overlapping toolpaths. Count and datum-trace every ORIGINAL callout-family member independently of the resulting one DXF closed contour; containment and topology validation are still mandatory. Mere tangential contact, separately specified machining, ambiguous topology or unproved overlap do not trigger automatic union; FLAG/ask. User-approved general case: 010447 has one `Ø28.5 + 4×Ø5.5` connected cut contour built from five contributed source cut regions, preserving four Ø5.5 nominal callout locations.
<!-- END MODULE: skills/lispcad/features/HOLES_TAPS.md -->

---

<!-- BEGIN MODULE: references/COUNTERSINK_COUNTERBORE.md -->
# Counterbore / 90° countersink through-hole references
Source: `伸び下穴経路一覧.xlsx`, sheet `皿ザグリ`. Values mm.

| Fastener | Through-hole Ø | Counterbore Ø | 90° countersink mouth Ø |
|---|---:|---:|---:|
| M3 | 3.4 | 6.5 | 6.4 |
| M4 | 4.5 | 8.0 | 8.4 |
| M5 | 5.5 | 9.5 | 10.4 |
| M6 | 6.6 | 11.0 | 12.5 |
| M8 | 9.0 | 14.0 | 16.5 |

Counterbore source Q6:S10; countersink Q25:S30. **Only** the proved effective through-hole/pilot becomes possible CAD CUT; the counterbore/countersink mouth is post-laser machining semantics, NOT a second laser CUT. Where diameter or countersink angle differs from the table, confirm machining parameters locally if they materially control the CAD output. The 170 mm drill-machine reach is advisory WARN. An in-house reamer may require nominal minus 0.1 mm under an applicable shop/customer instruction; never subtract 0.1 from all holes. No personal/contact data copied.
<!-- END MODULE: references/COUNTERSINK_COUNTERBORE.md -->

---

<!-- BEGIN MODULE: references/THREAD_PILOT_TABLE.md -->
# Thread Pilot Reference

Source: approved V4.3 production baseline.

### 7.1 Metric Thread Pilot Hole Diameters *(full table restored from V1)*
For laser cutting, threaded holes (marked `M*`) MUST be output as pilot holes using the standard diameters below:

| Thread | Pitch | Pilot Hole $\varnothing$ (mm) | Pilot Radius (mm) |
| :--- | :--- | :--- | :--- |
| **M1** | 0.25 | 0.75 | 0.375 |
| **M1.1** | 0.25 | 0.85 | 0.425 |
| **M1.2** | 0.25 | 0.95 | 0.475 |
| **M1.4** | 0.30 | 1.10 | 0.550 |
| **M1.6** | 0.35 | 1.25 | 0.625 |
| **M1.7** | 0.35 | 1.35 | 0.675 |
| **M1.8** | 0.35 | 1.45 | 0.725 |
| **M2** | 0.40 | 1.60 | 0.800 |
| **M2.2** | 0.45 | 1.75 | 0.875 |
| **M2.3** | 0.40 | 1.90 | 0.950 |
| **M2.5** | 0.45 | 2.10 | 1.050 |
| **M2.6** | 0.45 | 2.20 | 1.100 |
| **M3** | 0.50 | 2.50 | 1.250 |
| **M3.5** | 0.60 | 2.90 | 1.450 |
| **M4** | 0.70 | 3.30 | 1.650 |
| **M4.5** | 0.75 | 3.80 | 1.900 |
| **M5** | 0.80 | 4.20 | 2.100 |
| **M6** | 1.00 | 5.00 | 2.500 |
| **M7** | 1.00 | 6.00 | 3.000 |
| **M8** | 1.25 | 6.80 | 3.400 |
| **M9** | 1.20 | 7.80 | 3.900 |
| **M10** | 1.50 | 8.50 | 4.250 |
| **M11** | 1.50 | 9.50 | 4.750 |
| **M12** | 1.75 | 10.30 | 5.150 |
| **M14** | 2.00 | 12.00 | 6.000 |
| **M16** | 2.00 | 14.00 | 7.000 |
| **M18** | 2.50 | 15.50 | 7.750 |
| **M20** | 2.50 | 17.50 | 8.750 |
| **M22** | 2.50 | 19.50 | 9.750 |
| **M24** | 3.00 | 21.00 | 10.500 |
| **M27** | 3.00 | 24.00 | 12.000 |
| **M30** | 3.50 | 26.50 | 13.250 |
| **M33** | 3.50 | 29.50 | 14.750 |
| **M36** | 4.00 | 32.00 | 16.000 |
| **M39** | 4.00 | 35.00 | 17.500 |
| **M42** | 4.50 | 37.50 | 18.750 |
| **M45** | 4.50 | 40.50 | 20.250 |
| **M48** | 5.00 | 43.00 | 21.500 |
<!-- END MODULE: references/THREAD_PILOT_TABLE.md -->

---

<!-- BEGIN MODULE: references/THREAD_FINE_PILOT_TABLE.md -->
# Metric fine-pitch pilot drill diameters — CAD-only
Source: `伸び下穴経路一覧.xlsx` / `タップ下穴!A19:H45`, 2026-10-12 selected rule baseline. The existing `THREAD_PILOT_TABLE.md` stays standard pitch authority. Apply this table **only if source proves the explicit fine pitch**, e.g. M8×1.0; an unspecified M8 uses coarse pitch. A nut symbol alone does not prove a tap.

| Explicit thread × pitch | Effective pilot Ø mm |
|---|---:|
| M1×0.2 | 0.8 |
| M1.1×0.2 | 0.9 |
| M1.2×0.2 | 1 |
| M1.4×0.2 | 1.2 |
| M1.6×0.2 | 1.4 |
| M1.8×0.2 | 1.6 |
| M2×0.25 | 1.75 |
| M2.2×0.25 | 1.95 |
| M2.5×0.35 | 2.2 |
| M3×0.35 | 2.7 |
| M3.5×0.35 | 3.2 |
| M4×0.5 | 3.5 |
| M4.5×0.5 | 4 |
| M5×0.5 | 4.5 |
| M5.5×0.5 | 5 |
| M6×0.75 | 5.3 |
| M7×0.75 | 6.3 |
| M8×1 | 7 |
| M8×0.75 | 7.3 |
| M9×1 | 8 |
| M9×0.75 | 8.3 |
| M10×1.25 | 8.8 |
| M10×1 | 9 |
| M10×0.75 | 9.3 |
| M11×1 | 10 |
| M11×0.75 | 10.3 |
| M12×1.5 | 10.5 |
| M12×1.25 | 10.8 |
| M12×1 | 11 |
| M14×1.5 | 12.5 |
| M14×1 | 13 |
| M15×1.5 | 13.5 |
| M15×1 | 14 |
| M16×1.5 | 14.5 |
| M16×1 | 15 |
| M17×1.5 | 15.5 |
| M17×1 | 16 |
| M18×2 | 16 |
| M18×1.5 | 16.5 |
| M18×1 | 17 |
| M20×2 | 18 |
| M20×1.5 | 18.5 |
| M20×1 | 19 |
| M22×2 | 20 |
| M22×1.5 | 20.5 |
| M22×1 | 21 |
| M24×2 | 22 |
| M24×1.5 | 22.5 |
| M24×1 | 23 |
| M25×2 | 23 |
| M25×1.5 | 23.5 |
| M25×1 | 24 |
| M26×1.5 | 24.5 |
| M27×2 | 25 |
| M27×1.5 | 25.5 |
| M27×1 | 26 |
| M28×2 | 26 |
| M28×1.5 | 26.5 |
| M28×1 | 27 |
| M30×3 | 27 |
| M30×2 | 28 |
| M30×1.5 | 28.5 |
| M30×1 | 29 |
| M32×2 | 30 |
| M32×1.5 | 30.5 |
| M33×3 | 30 |
| M33×2 | 31 |
| M33×1.5 | 31.5 |
| M35×1.5 | 33.5 |
| M36×3 | 33 |
| M36×2 | 34 |
| M36×1.5 | 34.5 |
| M38×1.5 | 36.6 |
| M39×3 | 36 |
| M39×2 | 37 |
| M39×1.5 | 37.5 |
| M40×3 | 37 |
| M40×2 | 38 |
| M40×1.5 | 38.5 |
| M42×4 | 38 |
| M42×3 | 39 |
| M42×2 | 40 |
| M42×1.5 | 40.5 |
| M45×4 | 41 |
| M45×3 | 42 |
| M45×2 | 43 |
| M45×1.5 | 43.5 |
| M48×4 | 44 |
| M48×3 | 45 |
| M48×2 | 46 |
| M48×1.5 | 46.5 |
| M50×3 | 47 |
| M50×2 | 48 |
| M50×1.5 | 48.5 |

Generic coarse M2×0.4 stays Ø1.6; Ø1.7 is only a proved tool-breakage operation exception. Generic coarse M12×1.75 stays Ø10.3; Ø8 is only for the source-specified outside process. Source worksheet gives M38×1.5 Ø36.6: preserve this exact source value rather than 'correcting' it without confirmation. Each proved M feature creates exactly one physical pilot CUT/POINT subject to material capacity; nominal reference is non-cut geometry.
<!-- END MODULE: references/THREAD_FINE_PILOT_TABLE.md -->

---

<!-- BEGIN MODULE: skills/lispcad/features/SLOTS.md -->
## V4.34 slot *position anchor* (2026-10-13)
The source dimension may locate `SLOT_MIDPOINT`, `ARC_CENTER_1/2`, `OUTER_TIP_1/2`, or another explicitly proven witness point. The midpoint is distinct from either semicircular center and from either extreme outside tip. With width W and semicircle-center separation C, total length L=C+W; midpoint-to-arc-center=C/2, midpoint-to-extreme=L/2 **along the signed slot-axis unit vector**. Never infer an anchor type from slot shape alone, from a reference DXF, or from the dimension value. V4.34 `slot_anchor_records` bind per-slot member ID, source PDF witness/ref, canonical midpoint, width/C/L, signed axis, and canonical slot entity ID; `tools/slot_anchor.py` and source/geometry cross-check reject inconsistencies. Regression 521013-21: W6.6, C7.5, a 3.75 mm shift of the midpoint is FAIL. This augments, not replaces, the preexisting overall-vs-center-distance slot *size* classification.

# LISPCAD Feature — Slots

Source: approved V4.3 production baseline.

- **Slots / Oblong Holes**: Constructed as single closed `LWPOLYLINE`s with two straight segments and two semi-circular bulges (`bulge = 1.0`).
- **Slot Dimension Semantics — mandatory**: Before creating a slot, classify every length value as `OVERALL_LENGTH` (extreme end to extreme end) or `CENTER_DISTANCE / STRAIGHT_TANGENT_LENGTH` (center-to-center distance between the two semicircular ends; numerically equal to the straight tangent segment length for a stadium slot). Do not pass an unclassified value into a slot helper.
- The canonical direct-DXF slot uses overall `L_TOTAL` and end width `W` for a SINGLE closed Layer-0 LWPOLYLINE with two straight tangent segments and two true semicircular bulges; optional AutoLISP retains its existing spec: `(SLOTX L_TOTAL W)` or `(SLOTY L_TOTAL W)`, where `W` is slot width / end-circle diameter and `L_TOTAL >= W`. If the drawing gives center distance `C`, convert explicitly as `L_TOTAL = C + W` before storing or drawing the slot.
- If witness lines do not prove whether the printed slot length is overall or center-distance/tangent length, apply Section 4.4; do not guess from appearance or from a reference DXF.
- **V4.12 count-only n-R with proved slot width:** If `4-R` clearly targets FOUR semicircular ends of TWO depicted stadium slots with width `W=12`, each end has `R=W/2=6`. Build exactly four R6 semicircular ends (two per slot), not four slots or an unanswered radius. Generalize ONLY when slot identity, semicircular ends, leader count and dimensioned width are independently proved. Otherwise retain normal topology/size FLAG. Preserve independent slot overall-versus-center-distance semantics.


#### 8.4.1 Canonical Slot Spec — No Ambiguous `len` Parameter
Inside `HOLES`, slots MUST use one of these canonical forms:

```lisp
(x y (SLOTX L_TOTAL W))
(x y (SLOTY L_TOTAL W))
```

- `L_TOTAL` = total end-to-end slot length.
- `W` = slot width and diameter of each semicircular end.
- Internal helper geometry must use center offset `(L_TOTAL - W) / 2`.
- If the drawing supplies center-to-center / tangent length `C`, convert before storage: `L_TOTAL = C + W`.
- Reject/flag any slot where `L_TOTAL < W`, or where source length semantics are not proven.
- Do not use a generic helper argument named only `len` unless the function contract explicitly states `len = L_TOTAL`; ambiguous helper semantics are prohibited.

---


**V4.7 DXF default:** serialize each proved inner slot as exactly ONE closed CW `LWPOLYLINE` with semicircular bulge magnitude `1`, original proven `L_TOTAL`/`W`, exact tangent points and no faceted approximations, overlapping circles or independent calculations for composite output. The legacy `SLOTX`/`SLOTY` contract is request-only Lisp and must consume the same canonical derived geometry. Validate real containment, count and source length classification before production DXF.
<!-- END MODULE: skills/lispcad/features/SLOTS.md -->

---

<!-- BEGIN MODULE: skills/lispcad/features/CURVED_SLOT.md -->
# LISPCAD Feature — Curved / circular-arc slot

**V4.20 approved.**

Use when the slot center path is a circular arc rather than a straight stadium.

If source proves centerline radius `Rc`, slot width `W` and sweep `theta`:
- `Rout = Rc + W/2`
- `Rin = Rc - W/2`
- `Rcap = W/2`

Final boundary is one outer arc + one tangent end cap + the inner arc in reverse + the second tangent end cap. Exact ARC geometry or exact closed bulged LWPOLYLINE is acceptable.

**Hard gate:** final manufacturing feature is exactly ONE closed internal CUT contour.

FAIL on slot centerline/helper circle in CUT, duplicate/overlapping arcs, second lens-shaped loop, crossing arcs, open endpoints or coincident redundant toolpaths.

Raw customer DATA may contain noisy/exploded/projected geometry; clean it to the one physical slot while preserving DATA provenance and PDF-controlled parameters.

Regression 056691/056692: W6, Rc23.4, sweep 60° -> Rout26.4, Rin20.4, end caps R3. Lens-like overlapping output is FAIL.
<!-- END MODULE: skills/lispcad/features/CURVED_SLOT.md -->
