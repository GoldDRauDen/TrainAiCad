# LISPCAD Mode — Bend / Unfold

Source: approved V4.3 production baseline.

Load shared Nobi values from `../../../references/NOBI_TABLES.md`.

#### 4.2.6 Reference Dimensions Still Require a Proven Datum
A parenthesized/reference dimension is **not automatically a coordinate from the global origin**. `Reference` means no mid-tolerance adjustment; its extension-line origin and target still control how the coordinate is calculated.

- If a reference value `(276.5)` is measured from a hole-center row at `Y=10`, then the target is `Y=10+276.5=286.5`, not `Y=276.5`.
- Apply Section 4.2 datum tracing exactly as for a normal dimension; only the tolerance treatment differs.
- **Formed-view reference dimensions are not flat-pattern dimensions by default.** A parenthesized/参考 overall shown on a bent Front/Side/Section view describes that formed view unless its witness lines explicitly belong to a Development/Flat Pattern view.
- Do NOT use a formed-view reference overall as the unfolded blank length merely because its numeric value is close to the expected flat length. Derive flat length from the proven ordered flange/body chain, ID→OD conversion where required, and Nobi deductions. Use the formed-view reference only for the geometry/view it actually dimensions.
- If a formed-view reference value conflicts with a fully proven unfold equation, classify the issue as `REFERENCE/FORMED-DIMENSION ERROR` or source conflict; do not force the flat equation to equal the reference value.

#### 4.2.7 Local-Face Datum → Global Flat Datum Mapping
Features dimensioned on a bent flange/face MUST be transformed from the **local face coordinate system** into the **global unfolded blank coordinate system** before AutoLISP coordinates are emitted.

1. Assign each formed face an ordered identity along the unfold path: `FACE_1 -> BEND_1 -> FACE_2 -> ...`.
2. Establish the flat start/end coordinates of that face from the sequential OD/Nobi equations in Section 4.7.
3. Preserve the dimension direction. If local coordinate `u` is measured from the face start datum, use `U_flat = FACE_START_flat + u`. If it is measured from the opposite/free edge, use `U_flat = FACE_END_flat - u`.
4. A feature coordinate printed on a formed face MUST NOT be copied directly as a global flat coordinate unless the face datum is proven to coincide with the global flat datum.
5. Record `face_id`, `local datum`, `local equation`, and `global flat equation` in the datum trace for holes/slots/notches that cross a bend mapping.

This rule applies independently on both axes. Projection alignment may identify which face a feature belongs to, but may not replace the required unfold transform.

#### 4.2.8 Bend Sequence / Face Order Is Non-Commutative
The total flat length equation may be numerically unchanged when two flange lengths are swapped, but **bend positions, feature transforms, and material topology are not**. Therefore:

- Determine the ordered face sequence from the visible formed topology, bend callouts, section/detail views, and proven witness-line connectivity before calculating bend-line coordinates.
- Do not validate bend order merely because `sum(OD) - sum(Nobi)` matches the overall blank length.
- Double bend lines MUST be positioned from the ordered sequence in Section 4.7 and MUST exist only over material regions that actually cross that bend. For U-shaped, legged, stepped, or cut-away parts, split/trim bend lines around voids; never draw a bend line continuously through empty space.
- If two face orders remain equally plausible after explicit trace exhaustion, STOP and ask the user. Magenta is not permission to choose an arbitrary bend order.

### 4.6 ID-to-OD Conversion for Non-90° Bends
When dimensions are given as Inside Dimensions (ID), convert to Outside Dimensions (OD):

$$\text{Offset}_{raw} = t \times \tan\left(\frac{180^\circ - \text{Angle}}{2}\right)$$

**Mandatory rounding order:** round `Offset_raw` to the nearest `0.01 mm` **before** adding it to the ID or using it in any subsequent Nobi/flat-pattern arithmetic. Use ordinary decimal rounding at the hundredth place: inspect the thousandth digit; `0–4` rounds down and `5–9` rounds up.

$$\text{Offset} = \operatorname{Round}_{0.01}(\text{Offset}_{raw})$$

$$\text{OD} = \text{ID} + \text{Offset}$$

- Confirmed calibration example: for a `165°` bend with `t = 3.0 mm`, `Offset_raw = 3.0 × tan(7.5°) ≈ 0.39495...`, therefore **Offset = 0.39 mm**. Use `0.39`, not the unrounded value, in every following equation.
- Example (`135°` bend, `t = 3.0 mm`): `Offset_raw = 3.0 × tan(22.5°) ≈ 1.2426`, so `Offset = 1.24 mm`, then `OD = ID + 1.24 mm`.
- Do not apply this special intermediate rounding rule to unrelated explicit dimensions. It is specifically the ID→OD offset normalization step.

### 4.7 Nobi (Bend Allowance) Lookup Priority & Sequential Formulas
1. **Handwritten Nobi on Drawing**: Highest priority. Use directly (e.g., `-4.8`, `135° -1.71`) regardless of J-symbol.
2. **No Handwritten Nobi + J-Symbol Present**: Look up Nobi from standard tables (Section 7.3) by Material, Thickness, Bend Length, and Angle — applying the Interpolation Rule in Section 4.8 when the exact value is not tabulated.
3. **No Handwritten Nobi + J-Symbol Absent**: Draw the affected flange as a separate piece detached from the main body, offset by a fixed $10\text{ mm}$ gap for downstream reassembly. Set `is_flagged = true`.
4. **J-Symbol Present + No Table Match** (including out-of-range per Section 4.8): Maintain flat blank at Outside Dimension (OD) and draw bend line at OD design position. Set `is_flagged = true`.

#### Multi-Flange Sequential Coordinate Formulas (Axis from Origin 0)
For sequential flanges ($OD_1, OD_2, \dots, OD_n$) with Nobi values ($N_1, N_2, \dots, N_{n-1}$), first preserve the proven face order from Section 4.2.8. Any non-90° ID→OD offsets used inside the $OD_i$ values MUST already be rounded to `0.01 mm` per Section 4.6 before these equations are evaluated:
- **Total Unfolded Length**:
  $$L_{\text{total}} = \sum_{i=1}^{n} OD_i - \sum_{i=1}^{n-1} N_i$$
- **Exact Coordinates for Double Lines of Bend $k$**:
  - **Lower Line (Line 1 / Outer)**:
    $$Y_{\text{line1}} = \left(\sum_{i=1}^{k} OD_i\right) - \left(\sum_{i=1}^{k} N_i\right)$$
  - **Upper Line (Line 2 / Inner Datum)**:
    $$Y_{\text{line2}} = \left(\sum_{i=1}^{k} OD_i\right) - \left(\sum_{i=1}^{k-1} N_i\right)$$
  - **Distance between double lines**: $N_k$
- **Body Interior Preservation**: Main body interior dimensions ($B$) are **NEVER** reduced by Nobi. Nobi deductions exist strictly within the bend zone between parallel bend lines.

### 4.8 Nobi Table Interpolation Rule (NEW — Conservative Round-Up, Shop-Practice Standard)
When the actual Thickness ($t$) or Bend Length ($L$) does **not** exactly match a row in Section 7.3, **do NOT interpolate numerically**. Instead:
- **Thickness mismatch**: Select the row with the **next higher tabulated $t$** (never round down). Rounding down risks selecting an undersized V-die opening for the actual material, risking cracking or improper die seating.
- **Bend Length mismatch**: Within the selected $t$ row group, select the **next higher $L$ bracket** (next larger V-die). This yields a conservative (larger) Nobi deduction, which errs toward tooling safety.
- **Out-of-Range**: If $t$ or $L$ exceeds the largest tabulated value for that material, do **not** guess. Set `is_flagged = true` and annotate `"OUT OF TABLE RANGE - CONFIRM NOBI WITH SHOP"` in Magenta (Color 6) per Section 4.4.
- This rule applies uniformly across all four material tables in Section 7.3.

### 4.10 Corner Reliefs *(restored from V1)*
- **Intersection Only**: Create corner reliefs ONLY where two bend lines from perpendicular axes cross.
- **Geometry**: Retract longer edge by material thickness $t$, create slit inward by $t + 0.2$, and draw diagonal slit to bend line intersection.
- **Offset Value**: Read from drawing. If unspecified, record `offset = null` and flag missing dimensions per Section 4.4.

---
