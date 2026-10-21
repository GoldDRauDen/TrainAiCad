# LISPCAD Mode — Bend / Unfold

## Attachment and formed-profile OD before unfold

For every BEND, MULTI_FACE or unresolved bend candidate, execute `../../../references/FACE_GRAPH_UNFOLD_PROTOCOL.md` and `../../../references/BEND_ATTACHMENT_EDGE_OWNERSHIP.md` before production unfold. They own BEND_ATTACHMENT_EDGE_LOCKED, both physical shared edges, valid source evidence and the forbidden NEAREST_VIEW_EDGE shortcut. Apply `../../../references/FORMED_PROFILE_OD_MEASUREMENT.md` when formed geometry must establish OD_actual; a MEASUREMENT_CONSTRUCTION_VIEW is not CUT.

## V4.23 — mandatory per-bend witness ledger

In addition to the V4.19 FACE_GRAPH, every bend must close a `PER_BEND_WITNESS_LEDGER` before its double lines are accepted. Record ordered faces, controlling source witnesses, ID/OD semantics, every thickness term and where it is consumed, Nobi, sign, material domain and final pair coordinates. Enforce `THICKNESS_SINGLE_USE`: no thickness contribution may be silently consumed twice for the same transition.

Do not place a bend from total-flat closure alone. If a candidate bend pair differs from source/reference diagnosis by exactly ±t, treat that only as evidence of a possible thickness/datum ownership error and re-trace the ledger; do not auto-shift by t as a generic formula.

Source: approved V4.3 production baseline.

Load shared Nobi values from `../../../references/NOBI_TABLES.md`.

## V4.19 — Mandatory constraint-closed FACE_GRAPH before unfold

For **every bent/multi-face part**, load `../../../references/FACE_GRAPH_UNFOLD_PROTOCOL.md` before calculating production flat coordinates. The source-first graph must lock dimension witnesses/owners, feature host faces/local datums, ordered adjacency, signed bend orientation and actual material domains. `sum(OD)-sum(Nobi)` or a matching flat bbox is not a substitute for graph closure.

Close all G1–G7 graph/attachment/witness/ownership/order/sign/domain/constraint gates in FACE_GRAPH_UNFOLD_PROTOCOL. After unfold, FOLD_BACK_MATCH must reproduce the source and physical attachment edges before serialization; ambiguity follows the existing source-exhaustion and local FLAG/VIEWS_ONLY policy.

## V4.13 520315-18 — only nonduplicate approved additions

**INSIDE_VIEW assembled before proved reflection:** When source views prove they show inner faces, identify each face's datum, view direction and fold order. Apply the existing ID→OD, handwritten/table Nobi and local-face-to-flat rules, assemble the complete proved inside-face flat, and ONLY THEN reflect the assembled geometry when the intended target blank requires the proved axis. Compare hole center, actual M/Ø family and count IN THE SAME final frame; a left/right appearance in unmatched frames is not a hole error. Never mirror every bent part by default. User-approved 018297 is the regression for a false M3/Ø7 swap conclusion.

**Handwritten/table audit:** a legible scoped handwritten Nobi (`N_hand`) always draws, including bends marked J; record a differing compatible table value (same material, t, L, angle, surface) only as nonblocking `HANDWRITTEN_NOBI_DIFFERS_FROM_TABLE`.

**Exact printed inputs versus strictly <0.01 mm DERIVED comparison:** Continue rounding each calculated ID→OD offset to 0.01 before adding it to the actual printed ID and deducting the real Nobi. Read printed dimensions EXACTLY; the <0.01 mm threshold applies only to a representation/rounding difference when auditing ALREADY CORRECT derived quantities against a reference. Exactly 0.01 is not below threshold, and a wrong source input, datum, topology, feature class, or bend order fails regardless. Approved 018300: (797+0.26)+(24+0.26)-0.37=821.15 mm; 262+61.5-3.68=319.82 mm. Its previously measured reference bbox ~821.153 differs ~0.003 mm only in derived arithmetic.

#### 4.2.6 Reference Dimensions Still Require a Proven Datum

Authoritative rule: `../core/DATUM_DIMENSION.md` §4.2.6. Interpret witness origins there; this BEND module must not copy or override it.

#### 4.2.7 Local-Face Datum → Global Flat Datum Mapping

Authoritative rule: `../../../references/BEND_DATUM_MAPPING.md` §4.2.7; execute that proved local-face → global-flat coordinate transformation before any unfold output.

Physical edge identity (`FACE_2.BEND_EDGE` vs `FACE_2.FREE_EDGE`) survives the transform: §4.2.7.1 there.

#### 4.2.8 Bend Sequence / Face Order Is Non-Commutative

Apply `../../../references/BEND_DATUM_MAPPING.md` §4.2.8 (face order from formed topology, callouts and witnesses; a closing `sum(OD) - sum(Nobi)` never proves order; bend lines only over material; competing orders drawn per `REVIEW_PREVIEW_POLICY.md` §3). Bend-specific addition: lock the physical attachment edge for every face transition (V4.32); a correct face order with the wrong attached edge is still FAIL.

### 4.6 ID-to-OD Conversion for Non-90° Bends
When dimensions are given as Inside Dimensions (ID), convert to Outside Dimensions (OD). Compute with `python tools/lookup.py idod --t <t> --angle <A>` (rounds the offset first; ≤85° is routed to §4.6.2):

$$\text{Offset}_{raw} = t \times \tan\left(\frac{180^\circ - \text{Angle}}{2}\right)$$

**Mandatory rounding order:** round `Offset_raw` to the nearest `0.01 mm` **before** adding it to the ID or using it in any subsequent Nobi/flat-pattern arithmetic. Use ordinary decimal rounding at the hundredth place: inspect the thousandth digit; `0–4` rounds down and `5–9` rounds up.

$$\text{Offset} = \operatorname{Round}_{0.01}(\text{Offset}_{raw})$$

$$\text{OD} = \text{ID} + \text{Offset}$$

- Confirmed calibration example: for a `165°` bend with `t = 3.0 mm`, `Offset_raw = 3.0 × tan(7.5°) ≈ 0.39495...`, therefore **Offset = 0.39 mm**. Use `0.39`, not the unrounded value, in every following equation.
- Example (`135°` bend, `t = 3.0 mm`): `Offset_raw = 3.0 × tan(22.5°) ≈ 1.2426`, so **Offset = 1.24 mm**, then `OD = ID + 1.24 mm`.
- Do not apply this special intermediate rounding rule to unrelated explicit dimensions. It is specifically the ID→OD offset normalization step.
- V4.32: assign every ID→OD offset to the physical face contribution proved by the formed profile/attachment graph. Do not add the same offset again after an outside extent already includes it.

### 4.6.2 V4.15 — Acute bend `≤85°`: construct real radius, then measure outside OD

When the **proved included bend angle is ≤85° (85° inclusive)**, this approved method takes precedence over using the generic §4.6 tangent-offset equation as the controlling OD construction for that bend.

1. Load the complete construction/implementation contract `../../../references/ACUTE_BEND_LT85_FROM_SOURCE.md`.
2. Reconstruct both formed faces and their real free edges/inside surfaces from source evidence.
3. Apply the proved inside bend radius `Rin`; construct `Rout = Rin + t`.
4. Find the real bend center from the intersection of the two `Rin`-offset inside-face lines.
5. Measure `OD1` and `OD2` from the **physical outside envelope (外寸法)**. **Do not measure to the theoretical sharp intersection (交点).**
6. Only after both ODs are proved, apply the applicable Nobi: `L_flat = OD1 + OD2 - Nobi`. If unfolding starts from face 1, the double bend lines are `OD1-Nobi` and `OD1`.
7. A reference/proof DXF may confirm the independently reconstructed result but may never supply a PDF-missing OD or choose topology/normal signs.

Approved executable regression: `../../../regression/tools/check_acute_bend_lt85.py`; proof assets: `../../../regression/assets/acute_bend_lt85/`.

### 4.7 Nobi lookup and missing-Nobi fallback

Per bend run `python tools/lookup.py nobi --material <printed grade> --t <t> --L <bend length> --angle <included angle> [--surface "#1"] [--handwritten <N>] [--no-j] [--customer <numeric code>]`. It applies the order below and returns either `nobi` or `action: SPLIT_FLANGE_10MM` with the Vietnamese FLAG text. Without Python apply the same order to `references/NOBI_TABLES.md` by hand.

1. **Handwritten Nobi** legibly scoped to that bend: use it at any angle, J or no J (e.g. `-4.8`, `135° -1.71`). A differing table value is only a nonblocking audit note.
2. **90° bend (±0.5°) with J:** table by material group, the **exact** tabulated `t`, and the L bracket (`~ X` after a previous row means previous upper bound < L ≤ X). Numeric customer `646` uses `AIKOKU_646_NOBI.md` only. SUS uses 2B unless the source states #1.
3. **Everything else -> `SPLIT_FLANGE_10MM` + FLAG + status REVIEW:** non-90° bend without handwritten Nobi (never borrow a 90° row); J absent; `t` not exactly tabulated (no next-higher-row substitution); L outside the table; a `Confirm` cell; KH646 without a match (no fallback to the general table).

`SPLIT_FLANGE_10MM`: keep the main body and the affected flange each at its proved OD, draw the flange as a separate closed piece 10 mm away along the unfold direction inside the same code cluster, no bend line for that bend, all other proved features drawn. Never drop the code or stop the job.

#### Multi-Flange Sequential Coordinate Formulas (Axis from Origin 0)
For sequential flanges (`OD_1, OD_2, ..., OD_n`) with Nobi values (`N_1, N_2, ..., N_{n-1}`), first preserve the proven face order from §4.2.8. Any non-90° ID→OD offsets used inside the `OD_i` values MUST already be rounded to `0.01 mm` per §4.6. Compute with `python tools/lookup.py unfold --od OD_1 ... OD_n --nobi N_1 ... N_n-1`:
- **Total Unfolded Length**:
  $$L_{\text{total}} = \sum_{i=1}^{n} OD_i - \sum_{i=1}^{n-1} N_i$$
- **Exact Coordinates for Double Lines of Bend k**:
  - **Lower Line (Line 1 / Outer)**:
    $$Y_{\text{line1}} = \left(\sum_{i=1}^{k} OD_i\right) - \left(\sum_{i=1}^{k} N_i\right)$$
  - **Upper Line (Line 2 / Inner Datum)**:
    $$Y_{\text{line2}} = \left(\sum_{i=1}^{k} OD_i\right) - \left(\sum_{i=1}^{k-1} N_i\right)$$
  - **Distance between double lines**: `N_k`
- **Body Interior Preservation**: Main body interior dimensions (`B`) are **NEVER** reduced by Nobi. Nobi deductions exist strictly within the bend zone between parallel bend lines.
- **V4.32 OD provenance:** each `OD_i` must retain its source/formed-profile witnesses and thickness/offset owner. A numerically closing total does not validate a wrong OD owner or reversed attachment edge.

### Relief selection before unfold

Before declaring `SLIT_RELIEF=NO`, inspect each proved bend junction under `../features/SLIT_RELIEF.md`. It owns same-direction corner retreat (depth-first) and opposite-fold fixed-outside R=t construction, and routes custom, signed-offset 90-degree and BOXMET mechanisms. BEND/MULTI_FACE/UNKNOWN mode loads this feature owner even when the preliminary relief census says NO: recheck and reroute if the source proves relief. No duplicate mechanism at one junction.
