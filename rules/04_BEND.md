# 04 — BEND & UNFOLD | Production rules V4.34

> Consolidated bend, face graph, NOBI and acute-bend rules; all independent engineering conditions remain effective.

<!-- BEGIN MODULE: skills/lispcad/modes/BEND_UNFOLD.md -->
# LISPCAD Mode — Bend / Unfold

## V4.32 — physical bend-edge attachment + formed-profile OD gate

For every `BEND`, `MULTI_FACE`, or unresolved bend candidate, load:

- `../../../references/BEND_ATTACHMENT_EDGE_OWNERSHIP.md`
- `../../../references/FORMED_PROFILE_OD_MEASUREMENT.md` when actual outside face length must be established from formed/profile geometry.

Before any production unfold, prove `BEND_ATTACHMENT_EDGE_LOCKED`: the exact physical edge of each adjacent face participating in each bend, not merely the face pair/order.

`NEAREST_VIEW_EDGE`, paper proximity, view-above/view-below assumptions and visual symmetry are forbidden attachment evidence. Thickness/hidden-line evidence is optional; formed/profile/side/section topology, projection/view correspondence, witness connectivity and other explicit source cues may prove the shared edge.

A formed/profile view used to reconstruct topology or measure outside length is a `MEASUREMENT_CONSTRUCTION_VIEW`, not automatic CUT geometry.

Production unfold is blocked until `TOPOLOGY_LOCKED`, `BEND_ATTACHMENT_EDGE_LOCKED`, `DIMENSION_WITNESS_LOCKED`, `FEATURE_OWNERSHIP_LOCKED`, `FACE_ORDER_LOCKED`, `BEND_SIGN_LOCKED`, `BEND_DOMAIN_LOCKED` and `CONSTRAINTS_CLOSED` pass. Fold-back must reproduce the same physical attachment edges and bent-face datum identities.

## V4.23 — mandatory per-bend witness ledger

In addition to the V4.19 FACE_GRAPH, every bend must close a `PER_BEND_WITNESS_LEDGER` before its double lines are accepted. Record ordered faces, controlling source witnesses, ID/OD semantics, every thickness term and where it is consumed, Nobi, sign, material domain and final pair coordinates. Enforce `THICKNESS_SINGLE_USE`: no thickness contribution may be silently consumed twice for the same transition.

Do not place a bend from total-flat closure alone. If a candidate bend pair differs from source/reference diagnosis by exactly ±t, treat that only as evidence of a possible thickness/datum ownership error and re-trace the ledger; do not auto-shift by t as a generic formula.

Source: approved V4.3 production baseline.

Load shared Nobi values from `../../../references/NOBI_TABLES.md`.

## V4.19 — Mandatory constraint-closed FACE_GRAPH before unfold

For **every bent/multi-face part**, load `../../../references/FACE_GRAPH_UNFOLD_PROTOCOL.md` before calculating production flat coordinates. The source-first graph must lock dimension witnesses/owners, feature host faces/local datums, ordered adjacency, signed bend orientation and actual material domains. `sum(OD)-sum(Nobi)` or a matching flat bbox is not a substitute for graph closure.

Production unfold is blocked until `TOPOLOGY_LOCKED`, `BEND_ATTACHMENT_EDGE_LOCKED`, `DIMENSION_WITNESS_LOCKED`, `FEATURE_OWNERSHIP_LOCKED`, `FACE_ORDER_LOCKED`, `BEND_SIGN_LOCKED`, `BEND_DOMAIN_LOCKED` and `CONSTRAINTS_CLOSED` pass. After unfold, `FOLD_BACK_MATCH` against source-proved formed constraints is mandatory before DXF serialization. If competing face graphs or attachment edges remain, use existing FLAG/VIEWS_ONLY policy rather than selecting by confidence.

## V4.13 520315-18 — only nonduplicate approved additions

**INSIDE_VIEW assembled before proved reflection:** When source views prove they show inner faces, identify each face's datum, view direction and fold order. Apply the existing ID→OD, handwritten/table Nobi and local-face-to-flat rules, assemble the complete proved inside-face flat, and ONLY THEN reflect the assembled geometry when the intended target blank requires the proved axis. Compare hole center, actual M/Ø family and count IN THE SAME final frame; a left/right appearance in unmatched frames is not a hole error. Never mirror every bent part by default. User-approved 018297 is the regression for a false M3/Ø7 swap conclusion.

**Handwritten/J mismatch audit:** Existing Rule 1 always draws with scoped legible N_hand, including bends marked J. Only if the approved table supplies a genuinely compatible N_table for the SAME material, thickness, bend length, angle and applicable surface state, record both and retain HANDWRITTEN_NOBI_DIFFERS_FROM_TABLE only as a nonblocking audit note if prescribed values differ. Do not borrow a 90° table row for a 165° bend; if the table has no match, never replace a proved handwritten Nobi with an OD fallback.

**Exact printed inputs versus strictly <0.01 mm DERIVED comparison:** Continue rounding each calculated ID→OD offset to 0.01 before adding it to the actual printed ID and deducting the real Nobi. Read printed dimensions EXACTLY; the <0.01 mm threshold applies only to a representation/rounding difference when auditing ALREADY CORRECT derived quantities against a reference. Exactly 0.01 is not below threshold, and a wrong source input, datum, topology, feature class, or bend order fails regardless. Approved 018300: (797+0.26)+(24+0.26)-0.37=821.15 mm; 262+61.5-3.68=319.82 mm. Its previously measured reference bbox ~821.153 differs ~0.003 mm only in derived arithmetic.

#### 4.2.6 Reference Dimensions Still Require a Proven Datum

Authoritative rule: `../core/DATUM_DIMENSION.md` §4.2.6. Interpret witness origins there; this BEND module must not copy or override it.

#### 4.2.7 Local-Face Datum → Global Flat Datum Mapping

Authoritative rule: `../core/DATUM_DIMENSION.md` §4.2.7; execute that proved local-face → global-flat coordinate transformation before any unfold output.

**V4.32 physical edge datum identity:** if the local datum is edge-based, retain the actual edge identity through the transform, e.g. `FACE_2.BEND_EDGE` or `FACE_2.FREE_EDGE`. Rotation/reflection may change coordinate direction but may not silently swap bend/free edge identity.

#### 4.2.8 Bend Sequence / Face Order Is Non-Commutative

Apply `../core/DATUM_DIMENSION.md` §4.2.8 for the canonical face-order rule. Additional bend-specific hard gates follow:

- Determine the ordered face sequence from the visible formed topology, bend callouts, section/detail views, and proven witness-line connectivity before calculating bend-line coordinates.
- Lock the physical attachment edge for every face transition under V4.32; correct face order with the wrong attached edge is still FAIL.
- Do not validate bend order merely because `sum(OD) - sum(Nobi)` matches the overall blank length.
- Double bend lines MUST be positioned from the ordered sequence in Section 4.7 and MUST exist only over material regions that actually cross that bend. For U-shaped, legged, stepped, or cut-away parts, split/trim bend lines around voids; never draw a bend line continuously through empty space.
- If two face orders or two physical attachment edges remain equally plausible after explicit trace exhaustion, STOP and ask the user. Magenta is not permission to choose an arbitrary bend order/edge.

### 4.6 ID-to-OD Conversion for Non-90° Bends
When dimensions are given as Inside Dimensions (ID), convert to Outside Dimensions (OD):

$$\text{Offset}_{raw} = t \times \tan\left(\frac{180^\circ - \text{Angle}}{2}\right)$$

**Mandatory rounding order:** round `Offset_raw` to the nearest `0.01 mm` **before** adding it to the ID or using it in any subsequent Nobi/flat-pattern arithmetic. Use ordinary decimal rounding at the hundredth place: inspect the thousandth digit; `0–4` rounds down and `5–9` rounds up.

$$\text{Offset} = \operatorname{Round}_{0.01}(\text{Offset}_{raw})$$

$$\text{OD} = \text{ID} + \text{Offset}$$

- Confirmed calibration example: for a `165°` bend with `t = 3.0 mm`, `Offset_raw = 3.0 × tan(7.5°) ≈ 0.39495...`, therefore **Offset = 0.39 mm**. Use `0.39`, not the unrounded value, in every following equation.
- Example (`135°` bend, `t = 3.0 mm`): `Offset_raw = 3.0 × tan(22.5°) ≈ 1.2426`, so **Offset = 1.24 mm**, then `OD = ID + 1.24 mm`.
- Do not apply this special intermediate rounding rule to unrelated explicit dimensions. It is specifically the ID→OD offset normalization step.
- V4.32: assign every ID→OD offset to the physical face contribution proved by the formed profile/attachment graph. Do not add the same offset again after an outside extent already includes it.

### 4.6.2 V4.15 — Acute bend `<85°`: construct real radius, then measure outside OD

When the **proved included bend angle is strictly <85°**, this approved method takes precedence over using the generic §4.6 tangent-offset equation as the controlling OD construction for that bend.

1. Load `../../../references/ACUTE_BEND_LT85_METHOD.md` and the mandatory implementation contract `../../../references/ACUTE_BEND_LT85_FROM_SOURCE.md`.
2. Reconstruct both formed faces and their real free edges/inside surfaces from source evidence.
3. Apply the proved inside bend radius `Rin`; construct `Rout = Rin + t`.
4. Find the real bend center from the intersection of the two `Rin`-offset inside-face lines.
5. Measure `OD1` and `OD2` from the **physical outside envelope (外寸法)**. **Do not measure to the theoretical sharp intersection (交点).**
6. Only after both ODs are proved, apply the applicable Nobi: `L_flat = OD1 + OD2 - Nobi`. If unfolding starts from face 1, the double bend lines are `OD1-Nobi` and `OD1`.
7. A reference/proof DXF may confirm the independently reconstructed result but may never supply a PDF-missing OD or choose topology/normal signs.

Approved executable regression: `../../../regression/tools/check_acute_bend_lt85.py`; proof assets: `../../../regression/assets/acute_bend_lt85/`.

### 4.7 Nobi (Bend Allowance) Lookup Priority & Sequential Formulas

**2026-10-12 clarification:** If no defensible Nobi exists for a non-90° bend, preserve separate source/orthographic views under local REVIEW so the operator can assemble after customer confirmation. Never insert a 90° table value. KH646 is its own numeric customer-code route. Legible handwritten PDF Nobi overrides a differing table number with a nonblocking audit record.


1. **Handwritten Nobi on Drawing**: Highest priority. Use directly (e.g., `-4.8`, `135° -1.71`) regardless of J-symbol.
2. **No Handwritten Nobi + J-Symbol Present**: Look up Nobi from standard tables (Section 7.3) by Material, Thickness, Bend Length, and Angle — applying the Interpolation Rule in Section 4.8 when the exact value is not tabulated.
3. **No Handwritten Nobi + J-Symbol Absent**: Draw the affected flange as a separate piece detached from the main body, offset by a fixed `10 mm` gap for downstream reassembly. Set `is_flagged = true`.
4. **J-Symbol Present + No Table Match** (including out-of-range per Section 4.8): Maintain flat blank at Outside Dimension (OD) and draw bend line at OD design position. Set `is_flagged = true`.

#### Multi-Flange Sequential Coordinate Formulas (Axis from Origin 0)
For sequential flanges (`OD_1, OD_2, ..., OD_n`) with Nobi values (`N_1, N_2, ..., N_{n-1}`), first preserve the proven face order from Section 4.2.8. Any non-90° ID→OD offsets used inside the `OD_i` values MUST already be rounded to `0.01 mm` per Section 4.6 before these equations are evaluated:
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

### 4.8 Nobi Table Interpolation Rule (NEW — Conservative Round-Up, Shop-Practice Standard)
When the actual Thickness (`t`) or Bend Length (`L`) does **not** exactly match a row in Section 7.3, do **NOT** interpolate numerically. Instead:
- **Thickness mismatch**: Select the row with the **next higher tabulated t** (never round down). Rounding down risks selecting an undersized V-die opening for the actual material, risking cracking or improper die seating.
- **Bend Length mismatch**: Within the selected `t` row group, select the **next higher L bracket** (next larger V-die). This yields a conservative (larger) Nobi deduction, which errs toward tooling safety.
- **Out-of-Range**: If `t` or `L` exceeds the largest tabulated value for that material, do not guess. Set `is_flagged = true` and annotate `"OUT OF TABLE RANGE - CONFIRM NOBI WITH SHOP"` in Magenta (Color 6) per Section 4.4.
- This rule applies uniformly across all four material tables in Section 7.3.

### 4.10 Corner Reliefs — two distinct mechanisms (V4.4)

**Standard crossing-bend slit relief** (original V4.3 rule, only when two perpendicular bend lines cross):
- Retract longer edge by `t`; slit inward by `t + 0.2`; diagonal slit to bend-line intersection; read any drawing-specific offset or FLAG if unknown.

**Opposite-fold fixed-outside R=t relief** (approved calibration `055962`):
- When **two outer edges fold in different directions** and both outside dimensions must remain unchanged, create an `R=t` escape relief at their intersection without shortening either outside dimension. This is a distinct topology/operation from the standard slit relief and from material-table automatic laser fillets. Determine its exact tangency and retained-material side from the real bend/edge topology; if those are unclear, do not invent them.
- In `055962`, `t=2 mm` gives the two confirmed R2 reliefs. A separately observed R2 on an unbent corner is NOT automatically this relief.
- **`055958` (approved Q47/Q48): EXACTLY ONE standard Section 4.10 slit relief.** Its verified standalone DXF has three Green entities on Layer `0`, joined at endpoints: `LINE 55A` → `ARC 55B R0.5` → `LINE 55C`. Count **ONE connected machining feature**, NOT three reliefs. Its approved method is the existing crossing-bend slit rule (retract the longer edge by `t`, cut inward `t+0.2`, then diagonal to the proved bend intersection). The local `ARC R0.5` is **specific to this example**, not a mandatory arc for other slits or an automatic material-table Laser R. The old **slit method/count FLAG is RESOLVED**; customer-unconfirmed sizes and any independent datum/geometry FLAG remain. Never hardcode these reference coordinates as a universal construction.

#### 4.10.1 V4.16 BOXMET-style four-flange box routing

If the source proves a central/base rectangle with four adjacent bent flanges and BOXMET corner topology, load `../../../references/BOXMET_SLIT_RELIEF.md`. This reference decides which pair of flaps retreats by `t`, generates the four required slits, constructs the tangent `LINE + ARC R0.5 + LINE` geometry, and defines when the rule is not applicable. Do not omit a required BOXMET slit merely because the outer contour is already closed; do not auto-apply BOXMET slit logic to ordinary L/U/Z, single-flange/free-edge, non-crossing, or unrelated relief topology.

---
<!-- END MODULE: skills/lispcad/modes/BEND_UNFOLD.md -->

---

<!-- BEGIN MODULE: references/FACE_GRAPH_UNFOLD_PROTOCOL.md -->
# FACE_GRAPH_UNFOLD_PROTOCOL — V4.33 holistic challenge hardening over V4.32/V4.23/V4.19

## V4.32 — BEND_ATTACHMENT_EDGE_LOCKED

Before a bend may contribute to unfold, load `references/BEND_ATTACHMENT_EDGE_OWNERSHIP.md` and prove the exact physical connection:

`FACE_A.edge_i <-> physical BEND <-> FACE_B.edge_j`.

Face adjacency alone is insufficient. Retain both shared-edge identities, free-edge identities, attachment orientation/transform and source evidence. `NEAREST_VIEW_EDGE`, paper proximity, page-side assumptions and visual symmetry are forbidden as proof.

Thickness/hidden-line evidence is optional. Formed/profile/side/section topology, view correspondence, dimension/witness connectivity, bend notation and other explicit source cues may prove the connection.

When outside face length must be established from formed geometry, also load `references/FORMED_PROFILE_OD_MEASUREMENT.md`. A formed/profile drawing used to obtain topology or `OD_actual` is a `MEASUREMENT_CONSTRUCTION_VIEW`, not automatic manufacturing CUT geometry.

## V4.23 — PER_BEND_WITNESS_LEDGER and THICKNESS_SINGLE_USE

Before a bend may contribute final flat coordinates, retain an evidence-equivalent `PER_BEND_WITNESS_LEDGER` containing bend id, ordered adjacent faces, both controlling physical source witnesses, dimension semantics, each thickness term/offset and exactly where it is consumed, Nobi evidence/value, bend sign/orientation, material domain, derived double-line coordinates, and fold-back/source checks.

`THICKNESS_SINGLE_USE` is mandatory: a thickness term already consumed by ID→OD conversion, a proved outside-face extent, or another owned face-transition equation must not be added/subtracted again for the same bend placement. A bend-pair residual numerically equal to `+t` or `-t` is diagnostic evidence to re-trace witnesses/ownership; it is never a universal auto-fix.

A correct total flat length, outer bbox, or matching CUT contour cannot pass a bend with an unclosed ledger.

### G7B — BIDIRECTIONAL_SOURCE_CANONICAL_CLOSURE
For `PDF_DATA_RAW`, after source census and before FOLD_BACK_MATCH:
- `SOURCE_PHYSICAL_TO_CANONICAL`: every active physical source curve/family is represented or explicitly canonicalized/canceled;
- `CANONICAL_TO_SOURCE_PHYSICAL`: every manufacturing canonical curve has physical source provenance or a recorded canonicalization rule.
Missing source physical geometry or extra manufacturing geometry is FAIL even when selected geometry inverse-reprojects perfectly.


**Approved:** 2026-09-29 baseline; V4.32 hardening approved 2026-10-07 from calibration job 521006-18.  
**Scope:** every bent or multi-face sheet-metal part. This protocol adds no material, Nobi, thread, laser-R or acute-bend formula. It hardens how existing source evidence is converted into a unique formed model and then into a flat.

## 1. Core principle

Do **not** start a bent job from the desired flat contour, overall bbox, a familiar shape label such as U/Z/box, or the graphical edge nearest another view. First construct a source-supported formed-part model. Pattern recognition may propose a candidate topology, but only witness-owned dimensions, projection relationships, bend callouts, sections/details and explicit feature evidence may prove it.

The mandatory representation is a **constraint-closed signed FACE_GRAPH**:

- **FACE** = one material face with its own source/local frame and contour.
- **DIMENSION** = exact printed/derived value plus both witness endpoints, semantic family and owner.
- **FEATURE** = hole/slot/notch/R/C/KEGAKI/RIB/etc. with a mandatory host face and local datum.
- **BEND** = adjacency between exactly two faces, with both physical shared-edge identities, signed fold orientation, angle/radius/thickness/Nobi evidence and actual material domain.
- **TRANSFORM** = deterministic local-face → flat mapping derived only after the face graph and attachment edge are locked.

A production flat is forbidden while an active graph element lacks its required ownership/constraint fields.

## 2. Mandatory intermediate records

For every multi-face part retain an internal/evidence-equivalent record sufficient to reproduce these fields:

```text
FACE:
  face_id
  source_view / source ROI
  local_origin
  local_axis_u / local_axis_v
  contour_edges with stable edge identities
  source-proved face dimensions
  normal/orientation state

DIMENSION:
  dim_id
  value
  printed | derived | handwritten/revision
  witness_A
  witness_B
  semantic = FACE_CONTOUR | FEATURE_SIZE | FEATURE_POSITION |
             BEND_FACE_TRANSITION | OTHER_PROVED
  owner_face or owner_bend

FEATURE:
  feature_id
  family / size / quantity
  host_face
  local_datum including physical edge identity when edge-based
  local_geometry
  local_to_flat_transform

BEND:
  bend_id
  face_A
  face_A_shared_edge
  face_B
  face_B_shared_edge
  face_A_free_edge(s)
  face_B_free_edge(s)
  edge_orientation / attachment_transform
  attachment_source_evidence
  signed_angle / fold_sign
  Rin / t / Nobi evidence as applicable
  material_domain
  resulting double-line domain
```

A printed number may not remain an unowned scalar. A feature may not be represented first as an arbitrary final-DXF `(x,y)`; its host face/local datum must be proved first.

## 3. Hard gates G1–G9

### G1 — TOPOLOGY_LOCKED
All material faces required by the source are identified and their actual adjacency is established. Similar silhouette or a closing overall sum is not topology evidence.

### G1A — BEND_ATTACHMENT_EDGE_LOCKED
For every adjacency, prove the exact physical edge on each face that participates in the bend. A correct face pair with the wrong face edge is still wrong topology.

Required checks:
- `face_A_shared_edge` and `face_B_shared_edge` are explicit physical edge identities;
- free edges are distinguished from bend edges before transform;
- attachment orientation/rotation/reflection follows source evidence;
- no attachment is selected merely because its drawing edge is nearest another view;
- if two different edge attachments remain source-compatible after source exhaustion, the bend remains unresolved.

A whole-part rotation/reflection that preserves the same physical edge identities may be equivalent; page orientation by itself is not an error.

### G2 — DIMENSION_WITNESS_LOCKED
Every dimension used for contour, feature or bend construction has both witness endpoints and exactly one semantic owner. Hole/slot pitch cannot become a contour or bend distance.

### G3 — FEATURE_OWNERSHIP_LOCKED
Every manufacturing feature belongs to a proved face/local frame before unfold. Features transform with their face; they are not copied as global flat coordinates unless the source datum truly coincides with the flat datum. Edge-based datums must remain bound to the same physical edge identity through the attachment transform.

### G4 — FACE_ORDER_LOCKED
For each unfold path, preserve the ordered face chain. `sum(OD)-sum(Nobi)` may be identical for different face orders; identical total length does not validate bend positions or attachment-edge orientation.

### G5 — BEND_SIGN_LOCKED
Every bend has a source-supported sign/orientation. Track face normals or an equivalent signed state so U, Z/S, return, joggle, local channel and mixed-axis structures cannot collapse into the same unsigned 90° description.

### G6 — BEND_DOMAIN_LOCKED
A bend exists only where material actually crosses the shared edge. Split/trim double lines around reliefs, cutouts, steps and local flanges. Never extend BEND through voids merely to span the bbox.

### G7 — CONSTRAINTS_CLOSED
The chosen graph must be uniquely determined by source evidence. Required checks:
- no unresolved owner fields;
- no unanchored face translation/orientation DOF;
- no alternative face order, attachment-edge or bend-sign assignment that satisfies the same used constraints;
- all declared feature quantities and face dimensions close;
- every derived flat equation traces back to exact printed inputs and approved formulas.

If two materially different graphs remain possible after source exhaustion, production is blocked and the unresolved choice must be FLAGGED/asked. Confidence is not evidence.

### G7A — SOURCE_EXHAUSTED_BEFORE_VIEWS_ONLY

For `PDF_DATA_RAW`, `VIEWS_ONLY` is a production-blocking fallback only after **source exhaustion**, not a shortcut when unfolding is difficult.

Before `VIEWS_ONLY` may be selected:
- harvest every available relevant DATA view/face/primitive for that code;
- classify retained physical geometry versus drawing-only helpers/duplicates;
- complete the active manufacturing-family inventory and assign each detected family a host/status;
- attempt every source-supported FACE_GRAPH candidate through G1–G7 using the complete evidence set;
- record the specific unresolved degree of freedom, competing topology, attachment edge or missing evidence that remains after exhaustion.

Hard FAIL if `VIEWS_ONLY` is selected while relevant DATA remains unharvested/unclassified, because the first graph attempt failed, or merely because the unfold is complex. A later approved/reference DXF may diagnose a prior premature `VIEWS_ONLY`, but in NEW construction it still cannot supply hidden source dimensions.

### G7C — HOLISTIC_ENGINEERING_CHALLENGE

After the first G1-G7 solve, but before accepting an unresolved graph or canonicalizing a flat, run `references/HOLISTIC_ENGINEERING_CHALLENGE.md`.

For a bend/multi-face part, explicitly challenge:

- whether every relevant source view/DATA face has been consumed or classified;
- whether all source-supported attachment/order/sign candidates were actually tested;
- whether a shared bend-edge length has been reused as a whole face/blank extent without proof;
- whether handwritten/printed flat/Nobi arithmetic provides an independent closure not yet used;
- whether a local unresolved feature is being allowed to erase an otherwise unique graph.

If an anomaly remains, re-open the source. Do not call the graph source-ambiguous merely because the current solver has not solved it.

### G7D — COMPLETE VIEWS_ONLY FALLBACK

If G1-G7 remain genuinely unresolved only after G7A source exhaustion and G7C challenge, preserve every independently proved source-view member in the VIEWS_ONLY review output. Record the specific remaining DOF and blocker class. Missing source-view members is a hard `VIEWS_ONLY_SOURCE_VIEW_COMPLETENESS` failure.

### G8 — FOLD_BACK_MATCH
After unfold, replay/fold the flat back through the signed graph (a deterministic 2.5D face graph is sufficient; a full B-rep is not required) and reproject/compare against the source-proved formed constraints.

At minimum verify:
- face dimensions and adjacency;
- **the same physical attachment edge on both adjacent faces**;
- relative face orientation/bend sign;
- formed outside dimensions that were used, including `OD_actual` when applicable;
- feature host face, quantity, local offsets and physical datum-edge identity;
- view silhouette/topology where source-proved;
- local channel/tab/flange placement;
- bend-domain ownership.

A flat bbox match, total length match, or visually similar silhouette cannot pass G8 when the attachment edge is reversed. The strict `<0.01 mm` residual rule remains limited to correctly derived numeric comparisons and never repairs wrong topology, witness or printed dimensions.

### G9 — DXF_READBACK_MATCH
Only after G1–G8 pass may production geometry be serialized. Re-open the saved DXF and audit CUT/HOLE/BEND/KEGAKI/RIB, properties, mm units and code mapping independently from the source-semantic gates.

## 4. Mandatory solve order

`SOURCE VIEWS → witness/semantic graph → candidate FACE_GRAPH → signed adjacency → BEND_ATTACHMENT_EDGE_LOCKED → formed-profile OD measurement when applicable → constraint closure → unfold → feature transforms → material-domain BEND trim → FOLD_BACK/reprojection → manufacturing QA → DXF → DXF read-back`.

Do not reorder this into `bbox → nearest edge → flat → try to explain views afterward`.

## 5. Candidate-shape recognition

Labels such as L, U, Z, hat, box, joggle, return flange, flexible bend or local channel are permitted only as candidate generators. They may help identify which formed topology must be tested, but they must not directly select bend order, attachment edge, sign, relief or feature placement. Test the candidate against G1–G8. Reject candidates that require borrowing a dimension from another face, ignore a witness, move a feature to another host face, swap a bend edge with a free edge, or leave a competing topology equally valid.

## 6. Reference DXF boundary

For NEW_PDF_TO_DXF, construct the graph independently from PDF/image source first. A customer-approved DXF may assert/audit the result afterward but may not fill missing source coordinates, choose a hidden face order/attachment edge or reverse-fit the graph.

For DIRECT_EXISTING_DXF_AUDIT, compare AI DXF ↔ approved sample first as required by the existing skill, then use PDF/source to diagnose the semantic root cause. Convert only the general cause into production rules; job-specific coordinates remain regression assertions.

A profile/formed view in a reference may be a `MEASUREMENT_CONSTRUCTION_VIEW`; Layer 0 membership alone does not prove manufacturing CUT semantics.

## 7. Production blocker policy

- G1–G7 unresolved **after G7A source exhaustion** but independently proved source views exist → `VIEWS_ONLY` / REVIEW ONLY. If relevant DATA has not been fully harvested/classified and closure attempts are incomplete, `VIEWS_ONLY` is not yet allowed.
- A unique graph exists but a local feature remains uncertain → preserve proved flat, Magenta/FLAG only the unresolved feature under existing V4.11 rules.
- Any G8 failure → production FAIL; fix the graph/transform, do not tune coordinates to the reference.
- G1–G9 PASS → eligible for normal production status, subject to all other material/Nobi/R/C/relief rules.

## 8. Regression intent

### 520929-25 — V4.19 baseline
- 056942 proves that the same total flat length can hide a wrong face order/BEND placement.
- 056956 proves that perpendicular/local flanges require an actual face graph and material-domain BEND clipping.
- 057042 proves that longitudinal Z/S bends and a local transverse channel require independent signed axes/domains and feature ownership.

### 521006-18 — V4.32 attachment-edge hardening
- 058648 proves that a correct adjacent face can still be attached by the wrong physical edge; nearest paper edge is not evidence.
- 058652 is the control that a 180-degree whole-part representation may remain physically equivalent after normalization.
- 058653/058655 prove the need to establish actual outside face contributions before Nobi.
- 058654 remains unresolved where source/customer confirmation is still pending.

Regression coordinates/numbers are calibration evidence only and must never become construction authority for another drawing.

See `regression/qa/520929-25_V4_19_APPROVED.md`, `regression/qa/521006-18_V4_32_APPROVED.md`, and their executable checks.
<!-- END MODULE: references/FACE_GRAPH_UNFOLD_PROTOCOL.md -->

---

<!-- BEGIN MODULE: references/FACE_CREATION_BEND_EVIDENCE.md -->
# FACE_CREATION_BEND_EVIDENCE — V4.28 topology anti-overclassification gate

**Approved:** 2026-10-05 from calibration/audit job `521005-02`.

## Purpose

Prevent over-classifying a complex 2D contour as multiple formed faces. This module adds no Nobi, material, thread, tolerance, or DATA/PDF numeric rule. It is loaded for `BEND`, `MULTI_FACE`, and `UNKNOWN` mode candidates before final FACE_GRAPH closure.

## 1. FACE_CREATION_REQUIRES_BEND_EVIDENCE

A contour direction change, slope, step, recess, protrusion, radius, chamfer, or silhouette break **does not by itself prove a bend or a new material face**.

Create a new FACE/BEND adjacency only when source evidence proves material changes plane/orientation. Acceptable evidence includes one or more mutually consistent items such as:

- explicit bend/J/Nobi callout attached to the transition;
- section/side/detail geometry that proves two adjacent material planes;
- thickness representation or formed-edge representation that proves a fold;
- projection/witness relationships that uniquely establish adjacent faces and a shared bend edge;
- customer DATA physical geometry when DATA is authoritative for source geometry;
- another explicit source cue that uniquely proves a formed transition.

Color, contour angle, slope, a step-looking silhouette, visual familiarity, bbox, or resemblance to a known U/Z/box profile is not enough.

## 2. SAME_FACE_FIRST candidate test

Before splitting a visible profile into multiple faces, first test whether the source can be represented as one planar face with a complex contour while preserving all proved witnesses, feature ownership, sections/details, and formed constraints.

- If the same-face model satisfies the source and no independent bend evidence exists at the contour break, retain one FACE.
- Split only where positive bend evidence requires it.
- If both same-face and multi-face models remain materially possible after source exhaustion, keep the topology unresolved; do not choose by confidence or visual familiarity.

This is an anti-overclassification gate, not a rule that all sloped/stepped geometry is flat.

## 3. LOCAL_BEND_DOMAIN_BEFORE_UNFOLD

After a bend is proved, lock the exact material domain that crosses it **before** using the bend in unfold arithmetic.

- A local flange may occupy only a sub-span of the part width/height.
- Do not extend the bend pair through neighboring material that remains on the main face.
- Bend line length/domain must come from the actual shared edge/material crossing, not from overall part bbox.
- Existing `BEND_DOMAIN_LOCKED` and material-void clipping remain mandatory downstream.

## 4. THEORETICAL_SHARP_CLOSURE_FOR_R_CONTOURS

When an overall or summary dimension refers to the theoretical sharp intersection of two source-proved straight edges that are physically trimmed by an explicit radius/chamfer, do not reject the source/reference merely because the physical bbox is smaller.

1. Preserve the explicit R/C physical contour.
2. Reconstruct the theoretical sharp intersection only when the source witnesses/extension geometry prove that semantic.
3. Compare the theoretical overall to the theoretical sharp point and the physical bbox to the actual R/C contour separately.
4. Never replace the physical R/C with a sharp corner solely to make bbox equal the theoretical dimension.

## 5. TRAIN_REFERENCE boundary

A sample/approved DXF may diagnose whether the PDF-derived topology candidate was over-classified, but it does not supply hidden construction dimensions for a new job. Compare physical geometry, then return to PDF/source evidence to identify the general cause.

## 6. Required validation record

For every proposed face boundary retain:

`boundary_id | source evidence | SAME_FACE_FIRST result | bend_proved YES/NO/UNKNOWN | shared-edge/material-domain | resulting FACE ids`

Production PASS is forbidden when a created FACE lacks positive bend evidence, or when a proved local bend has been expanded to a larger bbox-derived domain without source support.

## 7. 521005-02 regression intent

- `26-057867`: control case — one source-proved bend; simple full-width flange remains valid.
- `26-057869` / `26-057870`: local flange only; approved/reference bend pair spans 555 mm, not the whole 1025 mm part width. Complex neighboring contour remains on the main face.
- `26-057871` / `26-057872`: sloped outer contour is part of the same planar face; only the proved bottom flange becomes a new face. The R10-trimmed physical bbox is smaller than the theoretical-sharp overall, so bbox mismatch alone is not a source/reference error.

Job-specific coordinates are regression evidence only and must never become generic construction coordinates.
<!-- END MODULE: references/FACE_CREATION_BEND_EVIDENCE.md -->

---

<!-- BEGIN MODULE: references/BEND_ATTACHMENT_EDGE_OWNERSHIP.md -->
# BEND_ATTACHMENT_EDGE_OWNERSHIP — V4.32 physical bend-edge attachment hard gate

**Approved:** 2026-10-07 from calibration/audit job `521006-18`.  
**Scope:** every `BEND`, `MULTI_FACE`, or unresolved bend candidate before production unfold.

## 1. Purpose

A correct face count or face order is not enough. Every bend must prove **which physical material edge of face A is joined to which physical material edge of face B**, and the orientation of that attachment.

The mandatory lock is:

`FACE_A.edge_i <-> physical BEND <-> FACE_B.edge_j`

This is `BEND_ATTACHMENT_EDGE_LOCKED`.

A wrong edge attachment can preserve the same total flat length while reversing a flange and moving every feature referenced from its bend/free edge. Therefore bend attachment is a topology gate, not a cosmetic orientation choice.

## 2. Required edge identities

Before unfold, retain an evidence-equivalent record containing at least:

```text
bend_id
face_A
face_A_shared_edge
face_B
face_B_shared_edge
face_A_free_edge(s)
face_B_free_edge(s)
edge_orientation / attachment_transform
source_evidence
alternative_attachment_state
```

`shared_edge` must identify the physical material edge on **both** faces. A generic statement such as `FACE_A adjacent to FACE_B` is insufficient.

## 3. Valid source evidence

Use mutually consistent source evidence. No single cue below is mandatory in every drawing.

Valid evidence may include:

- formed/profile/side/section geometry that proves the L/U/Z/joggle/return/flexible-bend topology;
- projection/view correspondence that identifies which physical edge of one face continues into another;
- dimension/witness connectivity tied to actual face edges;
- bend/J/angle/radius notation scoped to the transition;
- thickness or hidden-line representation **when present**;
- authoritative customer DATA geometry when applicable;
- another explicit source cue that uniquely proves the material connection.

Thickness/hidden lines are supporting evidence, not a prerequisite. When they are absent, formed-profile topology and view correspondence may be the controlling evidence.

## 4. Forbidden attachment shortcuts

The following do **not** prove a bend attachment edge:

- `NEAREST_VIEW_EDGE`;
- paper/page proximity between views;
- assuming the upper/lower/left/right paper edge is the bend edge;
- visual symmetry;
- choosing the attachment that makes the flat easiest to close;
- reference/sample geometry used to fill source-missing topology in a new construction job.

Never apply a drawing-specific lesson such as "always attach the top edge". The physical edge must be solved again for every source.

## 5. Measurement-construction views

A formed/profile view may be a `MEASUREMENT_CONSTRUCTION_VIEW`: source evidence used to prove topology, bend sign, edge attachment, or outside dimensions.

Such a view is **not manufacturing CUT geometry merely because it appears on Layer 0 or beside the flat in a reference DXF**. Output semantics remain controlled by the canonical manufacturing model.

## 6. Feature datum propagation

After `BEND_ATTACHMENT_EDGE_LOCKED`, local feature datums must retain physical edge identity, for example:

- `FACE_2.BEND_EDGE`
- `FACE_2.FREE_EDGE`
- `FACE_2.LEFT_EDGE`
- `FACE_2.RIGHT_EDGE`

If the attachment transform rotates or reflects the face, holes/cutouts/notches/chamfers transform with that face and keep their source-owned datum identity. `BEND_EDGE` and `FREE_EDGE` may never be swapped merely because the view is drawn nearer another view.

## 7. Ambiguity policy

If two different edge attachments remain source-compatible after source exhaustion, the bend is unresolved. Keep proved geometry local and use existing FLAG/VIEWS_ONLY policy. Do not choose by confidence or nearest-edge heuristics.

## 8. Regression intent

Job `521006-18` proves the mechanism:

- `058648`: the source/reference audit demonstrated a wrong flange reversal caused by attaching the graphical nearest edge rather than the physical shared bend edge. This is regression evidence only; its page orientation is not a universal rule.
- `058652`: a whole-part 180-degree representation can still be physically equivalent, so paper orientation alone is not an error.

See `regression/qa/521006-18_V4_32_APPROVED.md` and `regression/tools/check_521006_18_v432.py`.
<!-- END MODULE: references/BEND_ATTACHMENT_EDGE_OWNERSHIP.md -->

---

<!-- BEGIN MODULE: references/FORMED_PROFILE_OD_MEASUREMENT.md -->
# FORMED_PROFILE_OD_MEASUREMENT — V4.32 formed-profile outside-length contract

**Approved:** 2026-10-07 from calibration/audit job `521006-18`.  
**Scope:** bent/multi-face parts where flat arithmetic needs outside face lengths that are not already unambiguously supplied as usable OD values.

## 1. Purpose

A formed/profile/side view can be a **measurement construction** for the real bent part. It is used to reconstruct the material planes and measure the actual outside dimensions required for unfold.

Do not serialize a measurement construction as CUT merely because it is present in a source/reference DXF.

## 2. Required order

When applicable:

```text
SOURCE FORMED VIEWS
-> FACE_GRAPH + BEND_ATTACHMENT_EDGE_LOCKED
-> source dimensions/witness semantics
-> construct actual formed faces and bend transitions
-> establish outside material envelope
-> measure OD_actual for each ordered face contribution
-> assign each thickness/ID->OD term to exactly one owner
-> apply Nobi
-> unfold
-> fold-back / source reprojection
```

The general flat equation remains:

`L_flat = sum(OD_actual) - sum(Nobi)`

but the `OD_actual` terms must be physically proved.

## 3. Measuring OD_actual

Measure along the owning face direction between the physical source-defined free/boundary edge and the applicable outside bend envelope/tangent/formed boundary.

Do not substitute:

- a bbox extent;
- an inside dimension as if it were already outside;
- a theoretical sharp intersection when the physical outside envelope is the controlled endpoint;
- a reference/sample coordinate for a source-missing OD.

For non-90-degree bends, retain existing routed ID->OD and acute-bend rules. This module controls **ownership and measurement meaning**: offsets/thickness terms must land on the correct face contribution and must not be consumed twice.

## 4. THICKNESS_SINGLE_USE remains mandatory

If a thickness or ID->OD offset is already represented in a constructed outside extent, do not add it again during sequential flat arithmetic.

For every contribution retain:

`face_id | source witnesses | ID/OD semantic | thickness/offset owner | OD_actual | Nobi transition`.

## 5. Measurement view versus manufacturing view

Use explicit semantic states when needed:

- `SOURCE_VIEW`
- `MEASUREMENT_CONSTRUCTION_VIEW`
- `MANUFACTURING_GEOMETRY`

A measurement construction may support topology/OD/fold-back QA but does not become production geometry automatically.

## 6. Ambiguity and reference boundary

If source geometry cannot uniquely establish the outside envelope or the required OD term, keep the affected bend/flat locally unresolved. An approved/reference DXF may diagnose an AI error after comparison, but it cannot silently supply a missing parameter for a new drawing.

## 7. Regression intent

`521006-18` provides approved audit facts for the mechanism:

- `058653`: source/profile reconstruction requires actual outside contributions before Nobi; directly summing the apparent inside/formed numbers produces a short flat.
- `058655`: the same error occurs on a mixed 155-degree/90-degree chain.
- `058654`: customer-confirmation-pending geometry remains unresolved and must not be reverse-fit from the sample.

The numeric regression values are calibration assertions only, never construction values for another drawing.
<!-- END MODULE: references/FORMED_PROFILE_OD_MEASUREMENT.md -->

---

<!-- BEGIN MODULE: references/BEND_TOOLING_FEASIBILITY.md -->
# Bend-tooling minimum L/Z — manufacturing WARN only
Source: `伸び下穴経路一覧.xlsx` / `旭26-9-18` rows 8–9, 17–18 (SS), 28–29, 38–39, 49 (SUS), 62, 71 (AL), 81 (Cu).

**This is a feasibility check, not a CAD dimension rule.** Look up the **already selected physical V die** for each proved bend. A leg shorter than the listed `L_min`, or a comparable Z leg shorter than a printed `Z_min`, creates **WARN only** when PDF geometry is otherwise complete, not REVIEW or re-sized CUT. The dash means the original sheet does not supply the corresponding Z value, NOT zero. Never infer unknown values from adjacent material/rows; preserve source witness and tooling evidence.

| Material family | thickness t | selected V die | L_min (mm) | Z_min (mm) |
|---|---:|---|---:|---:|
| SS | 0.5 | V8 | 7.5 | 8.5 |
| SS | 0.8 | V8 | 7.5 | 8.8 |
| SS | 1 | V8 | 7.5 | 9 |
| SS | 1.2 | V8 | 7.5 | 9.2 |
| SS | 1.5 | V8 | 7.5 | 9.5 |
| SS | 1.6 | V8 | 7.5 | 9.6 |
| SS | 2 | V12 | 8.5 | 12.1 |
| SS | 2.3 | V12 | 8.5 | 12.7 |
| SS | 3 | V12 | 8.5 | 14.6 |
| SS | 3 | V18 | 12.8 | 17.6 |
| SS | 3 | V25 | 17.8 | 21.6 |
| SS | 3.2 | V18 | 12.8 | 18 |
| SS | 3.2 | V25 | 17.8 | 22 |
| SS | 4 | V18 | 12.8 | 19.6 |
| SS | 4.5 | V25 | 17.8 | 26 |
| SS | 4.5 | V32 | 22.7 | 30 |
| SS | 4.5 | V40 | 28.4 | 34 |
| SS | 5 | V25 | 17.8 | 28 |
| SS | 5 | V32 | 22.7 | 32 |
| SS | 5 | V40 | 28.4 | 36 |
| SS | 6 | V25 | 17.8 | 30 |
| SS | 6 | V32 | 22.7 | 34 |
| SS | 6 | V40 | 28.4 | 38 |
| SS | 9 | V40 | 28.4 | 44 |
| SS | 9 | V80 | 57 | - |
| SS | 12 | V80 | 57 | - |
| SUS | 0.5 | V8 | 7.5 | 8.5 |
| SUS | 0.8 | V8 | 7.5 | 8.8 |
| SUS | 1 | V8 | 7.5 | 9 |
| SUS | 1.2 | V8 | 7.5 | 9.2 |
| SUS | 1.5 | V8 | 7.5 | 9.5 |
| SUS | 2 | V12 | 8.5 | 12.1 |
| SUS | 2 | V18 | 12.8 | 15.6 |
| SUS | 2.5 | V12 | 8.5 | 13.6 |
| SUS | 2.5 | V18 | 12.8 | 16.6 |
| SUS | 2.5 | V25 | 17.8 | 20.6 |
| SUS | 3 | V12 | 8.5 | 14.6 |
| SUS | 3 | V18 | 12.8 | 17.6 |
| SUS | 3 | V25 | 17.8 | 21.6 |
| SUS | 3 | V40 | 28.4 | 29.6 |
| SUS | 4 | V18 | 12.8 | 19.6 |
| SUS | 4 | V25 | 17.8 | 23.6 |
| SUS | 4 | V40 | 28.4 | 31.6 |
| SUS | 4.5 | V18 | 12.8 | 20.6 |
| SUS | 5 | V25 | 17.8 | 25.6 |
| SUS | 5 | V32 | 22.7 | 29.6 |
| SUS | 5 | V40 | 28.4 | 33.6 |
| SUS | 6 | V32 | 22.7 | 34 |
| SUS | 6 | V40 | 28.4 | 38 |
| SUS | 8 | V40 | 28.4 | - |
| SUS | 8 | V80 | 57 | - |
| SUS | 9 | V80 | 57 | - |
| AL | 0.8 | V8 | 7.5 | - |
| AL | 1 | V8 | 7.5 | - |
| AL | 1.5 | V8 | 7.5 | - |
| AL | 2 | V12 | 8.5 | - |
| AL | 3 | V12 | 8.5 | - |
| AL | 3 | V18 | 12.8 | - |
| AL | 3 | V25 | 17.8 | - |
| AL | 4 | V18 | 12.8 | - |
| AL | 4 | V25 | 17.8 | - |
| AL | 4 | V32 | 22.7 | - |
| AL | 4 | V40 | 27.4 | - |
| AL | 5 | V25 | 17.8 | - |
| AL | 5 | V32 | 22.7 | - |
| AL | 5 | V40 | 28.4 | - |
| AL | 6 | V25 | 17.8 | - |
| AL | 6 | V32 | 22.7 | - |
| AL | 6 | V40 | 28.4 | - |
| AL | 8 | V40 | 28.4 | - |
| AL | 8 | V80 | 57 | - |
| AL | 9 | V40 | 28.4 | - |
| AL | 9 | V80 | 57 | - |
| AL | 10 | V80 | 57 | - |
| CU | 3 | V18 | 12.8 | - |

The SS t4.5 V18 special cell is `要確認` and has no automatic Nobi application; do not promote it to the standard V25 row. SUS430 uses the SS material group for Nobi/tooling; for Laser R and hole processing it still uses SUS/他. Customer 646 uses its dedicated tooling/profile `AIKOKU_646_NOBI.md`, never fallback to this shop sheet. An explicit PDF/tooling instruction controls the selected die; don't switch dies merely because a listed L/Z minimum is violated. Source sheet feasibility notes concerning maximum width/depth remain WARN, not hard geometric redesign.

If bend length/leg ownership is unproved, that is a *geometry or source-evidence* REVIEW independently of a machine-feasibility WARN. Never calculate Nobi or min-leg checks from CAD bounding boxes instead of the locked physical bend edge.
<!-- END MODULE: references/BEND_TOOLING_FEASIBILITY.md -->

---

<!-- BEGIN MODULE: references/NOBI_TABLES.md -->
# Nobi Allowance Reference Tables

## Approved 2026-10-12 recalibration from `旭26-9-18`
Use the existing TrainAiCad unfolding formulas, NOT a new bend algorithm. `SUS` without documented 2B/#1 uses **2B** by default; an explicit #1 on source overrides. SUS304 t3 L1801–2400 V40 2B **7.84** (was erroneous 8.54) and #1 **7.80**. A legible handwritten PDF Nobi is higher authority and any table mismatch is an audit record, not QA REVIEW. 旭 Nobi does NOT backfill missing values for numeric customer code 646. Machine min L/Z is nonblocking feasibility WARN when proved geometry is correct. NC operations are excluded.


Source: approved V4.3 Nobi values, with approved L09 material-routing clarification on 2026-09-25. **SUS430 uses SS/SUS430/BRASS Nobi ONLY; use workbook group SUS, 他 for Laser R, hole limits and White Piercing in `references/MATERIAL_RULES.md`. All Nobi numbers remain unchanged.**

### 7.3 Nobi Allowance Standards Tables *(fully restored from V1 — including the previously-dropped Copper table and all intermediate L-brackets)*

#### 1. SS, SUS430, BRASS ($R=0.6$ for $t \le 4.5$, $R=3.0$ for $t=5.0 \sim 9.0$, $R=6.0$ for $t=12.0$)

| $t$ (mm) | Bend Length $L$ (mm) | V-Die | Nobi Deduction (mm) |
| :--- | :--- | :--- | :--- |
| **0.5** | ~ 2400 | V8 | 1.36 |
| **0.8** | ~ 2400 | V8 | 1.68 |
| **1.0** | ~ 2400 | V8 | 1.90 |
| **1.2** | ~ 2400 | V8 | 2.14 |
| **1.5** | ~ 2400 | V8 | 2.54 |
| **1.6** | ~ 2400 | V8 | 2.64 |
| **2.0** | ~ 2400 | V12 | 3.44 |
| **2.3** | ~ 2400 | V12 | 3.80 |
| **3.0** | ~ 1000 | V12 | 4.66 |
| **3.0** | 1001 ~ 1900 | V18 | 5.28 |
| **3.0** | 1901 ~ 2400 | V25 | 5.98 |
| **3.2** | ~ 1800 | V18 | 5.50 |
| **3.2** | 1801 ~ 2400 | V25 | 5.72 |
| **4.0** | ~ 1200 | V18 | 6.42 |
| **4.5** | ~ 1200 | V25 | 7.76 |
| **4.5** | 1201 ~ 1600 | V32 | 8.10 |
| **4.5** | 1601 ~ 2300 | V40 | 8.48 |
| **5.0** | ~ 1000 | V25 | 8.32 |
| **5.0** | 1001 ~ 1300 | V32 | 9.04 |
| **5.0** | 1301 ~ 1600 | V40 | 9.86 |
| **6.0** | ~ 700 | V25 | 9.78 |
| **6.0** | 701 ~ 900 | V32 | 10.22 |
| **6.0** | 901 ~ 1150 | V40 | 10.94 |
| **9.0** | ~ 400 | V40 | 14.62 |
| **9.0** | 401 ~ 800 | V80 | 15.50 |
| **12.0**| ~ 550 | V80 | 20.48 |

#### 2. Stainless Steel (SUS Except SUS430) ($R=0.6$ for $t \le 5.0$, $R=3.0$ for $t=6.0 \sim 8.0$)

| $t$ (mm) | Bend Length $L$ (mm) | V-Die | Nobi 2B (mm) | Nobi #1 (mm) |
| :--- | :--- | :--- | :--- | :--- |
| **0.5** | ~ 2400 | V8 | 1.36 | - |
| **0.8** | ~ 2400 | V8 | 1.82 | 1.74 |
| **1.0** | ~ 2400 | V8 | 2.14 | 1.94 |
| **1.2** | ~ 2400 | V8 | 2.32 | 2.18 |
| **1.5** | ~ 2400 | V8 | 2.64 | 2.54 |
| **2.0** | ~ 1300 | V12 | 3.68 | 3.50 |
| **2.0** | 1301 ~ 2400 | V18 | 4.00 | 4.18 |
| **2.5** | ~ 1300 | V12 | 4.24 | 4.08 |
| **2.5** | 1301 ~ 2000 | V18 | 5.06 | 4.78 |
| **2.5** | 2001 ~ 2400 | V25 | 5.84 | 5.52 |
| **3.0** | ~ 750 | V12 | 4.80 | 4.68 |
| **3.0** | 751 ~ 1250 | V18 | 5.64 | 5.36 |
| **3.0** | 1251 ~ 1800 | V25 | 6.46 | 6.10 |
| **3.0** | 1801 ~ 2400 | V40 | 7.84 | 7.80 |
| **4.0** | ~ 650 | V18 | 6.78 | 6.50 |
| **4.0** | 651 ~ 1000 | V25 | 7.66 | 7.28 |
| **4.0** | 1001 ~ 1650 | V40 | 8.44 | 8.90 |
| **4.5** | ~ 550 | V18 | 7.30 | 7.30 |
| **5.0** | ~ 550 | V25 | 8.82 | 8.46 |
| **5.0** | ~ 750 | V32 | 9.68 | 9.18 |
| **5.0** | 751 ~ 1000 | V40 | 10.74 | 10.06 |
| **6.0** | ~ 500 | V32 | 10.72 | 9.82 |
| **6.0** | 501 ~ 650 | V40 | 11.88 | 10.12 |
| **8.0** | ~ 350 | V40 | 14.06 | 13.50 |
| **8.0** | 351 ~ 700 | V80 | 19.46 | 16.94 |
| **9.0** | ~ 550 | V80 | 20.54 | 18.08 |

#### 3. Aluminum (AL) ($R=0.6$ for $t \le 4.0$, $R=3.0$ for $t \ge 5.0$)

| $t$ (mm) | Bend Length $L$ (mm) | V-Die | Nobi Deduction (mm) |
| :--- | :--- | :--- | :--- |
| **0.8** | ~ 2400 | V8 | 1.84 |
| **1.0** | ~ 2400 | V8 | 1.90 |
| **1.5** | ~ 2400 | V8 | 2.40 |
| **2.0** | ~ 2400 | V12 | 3.20 |
| **3.0** | ~ 1200 | V12 | 4.56 |
| **3.0** | ~ 1900 | V18 | 4.78 |
| **3.0** | 1901 ~ 2400 | V25 | Confirm |
| **4.0** | ~ 1200 | V18 | 6.10 |
| **4.0** | 1201 ~ 1700 | V25 | 6.42 |
| **4.0** | 1701 ~ 2000 | V32 | 6.84 |
| **4.0** | 2001 ~ 2400 | V40 | 7.40 |
| **5.0** | ~ 1000 | V25 | 8.26 |
| **5.0** | 1001 ~ 1300 | V32 | 8.44 |
| **5.0** | 1301 ~ 1600 | V40 | 8.74 |
| **6.0** | ~ 700 | V25 | 9.62 |
| **6.0** | 701 ~ 900 | V32 | 9.80 |
| **6.0** | 901 ~ 1150 | V40 | 10.06 |
| **8.0** | ~ 650 | V40 | 12.78 |
| **8.0** | 651 ~ 800 | V80 | 14.90 |
| **9.0** | ~ 400 | V40 | 14.12 |
| **9.0** | 401 ~ 800 | V80 | 16.20 |
| **10.0**| ~ 800 | V80 | 17.52 |

#### 4. Copper (Cu) *(restored — was missing from V2 entirely)*

| $t$ (mm) | Bend Length $L$ (mm) | V-Die | Nobi Deduction (mm) |
| :--- | :--- | :--- | :--- |
| **3.0** | ~ 1900 | V18 | 5.10 |

> **Note (`3.0mm / 1901~2400 / V25` for Aluminum, row above)**: Source table marks this cell `Confirm` — no numeric Nobi value available. Per Section 4.7 Rule 4 (No Table Match), treat as `is_flagged = true` and maintain flat blank at OD.

---
<!-- END MODULE: references/NOBI_TABLES.md -->

---

<!-- BEGIN MODULE: references/ACUTE_BEND_LT85_METHOD.md -->
# ACUTE_BEND_LT85_METHOD — Approved production reference

**Status:** USER APPROVED on 2026-09-28.  
**Scope:** Sheet-metal bends whose included bend angle is **strictly `<85°`**, when the drawing/approved shop method requires the acute-bend outside-dimension construction demonstrated by `HD.dxf`.

## 0. Implementation requirement — derive from source, not answer

Before using this rule in production or regression, read `ACUTE_BEND_LT85_FROM_SOURCE.md`.

A valid implementation must execute the complete chain:

`source formed faces → identify free edges/inside surfaces → offset each inside surface by Rin → intersect offsets to get C → Rout=Rin+t → outside-envelope support measurement → OD1/OD2 → Nobi → flat/bend pair`

The approved OD numbers are **outputs/assertions only**. They must never be treated as source dimensions or fed back into construction.

## 1. Trigger and precedence

Apply this rule only when all of the following are true:

1. The real bend included angle is **<85°**.
2. The formed geometry and thickness are proved.
3. The applicable inside bend radius is proved by the approved shop method/drawing; for the approved regression below `Rin=0.6 mm`.
4. The bend is being converted to flat length using outside dimensions and Nobi.

If angle, thickness, radius, face identity, or free-edge datum is unresolved, FLAG instead of inventing an OD.

This rule is **not** the same as the existing generic §4.6 ID→OD tangent-offset formula. For this acute case, the controlling method is geometric construction of the real rounded bend followed by measurement of the two **外寸法 (outside dimensions)**.

## 2. Mandatory construction

For each affected bend:

1. Reconstruct the two formed faces from exact PDF dimensions/witnesses.
2. Replace the theoretical sharp intersection with the proved **inside bend radius `Rin`**.
3. Construct the outer surface with  
   `Rout = Rin + t`.
4. Preserve the real free edges and face directions.
5. **Do not use the theoretical sharp-line intersection as the OD datum.**
6. Measure the two physical outside dimensions from the real outer envelope after the bend radius has been constructed:
   - `OD1`: outside dimension of face 1.
   - `OD2`: outside dimension of face 2.
7. Use the applicable Nobi:
   `L_flat = OD1 + OD2 - Nobi`.
8. If unfolding from face 1:
   - `BEND_LINE_1 = OD1 - Nobi`
   - `BEND_LINE_2 = OD1`
   - separation = `Nobi`.
9. Clip the double bend lines to the actual material width crossing that bend.

## 3. Prohibited shortcuts

FAIL if the AI:
- extends the straight faces to a theoretical sharp corner and measures to that intersection;
- copies OD values from a reference DXF when they can be reconstructed from the PDF/shop method;
- treats a reference DXF as the source of missing PDF dimensions;
- substitutes the generic non-90° tangent-offset formula for this approved `<85°` geometric outside-envelope method;
- rounds printed source dimensions before construction;
- places bend lines through voids or beyond the material region.

## 4. Approved TEST regression

Source: `ACUTE_BEND_LT85_SOURCE_FIXTURE.dxf`; method evidence: `HD.dxf`.

- Included bend angle: **75°**
- Thickness: **3.0 mm**
- `Rin = 0.6 mm`
- `Rout = Rin + t = 3.6 mm`

Approved reconstructed outside dimensions:

- **OD1 = 182.014217 mm → report 182.01 mm**
- **OD2 = 49.712236 mm → report 49.71 mm**

The generated proof file `ACUTE_BEND_LT85_OD_PROOF.dxf` contains the rounded bend and the two OD dimensions as non-cut annotation. A future AI should be able to recreate the same two physical OD values from `ACUTE_BEND_LT85_SOURCE_FIXTURE.dxf` using this method.

## 5. Reference-audit behavior

When a user-approved DXF sample is also supplied:

- Derive OD1/OD2 independently from the PDF/shop method first.
- Then compare with the approved sample.
- A matching sample confirms the interpretation; it does not become the hidden dimension source.
- Report a conflict if the sample geometry cannot be reconciled with the proved formed geometry/radius/Nobi.

## 6. Regression assets

- `regression/assets/acute_bend_lt85/TEST.dxf` — independent test geometry.
- `regression/assets/acute_bend_lt85/TEST_OD_MINH_HOA.dxf` — generated proof geometry.

## Repository provenance

Original approved source hashes and the normalization boundary are recorded in `regression/assets/acute_bend_lt85/README.md`. The compact fixture preserves physical formed geometry but deliberately does not preserve irrelevant raw DXF entity packaging.
<!-- END MODULE: references/ACUTE_BEND_LT85_METHOD.md -->

---

<!-- BEGIN MODULE: references/ACUTE_BEND_LT85_FROM_SOURCE.md -->
# ACUTE_BEND_LT85_FROM_SOURCE — Implementation contract

**Purpose:** Make the `<85°` acute-bend method reproducible by another AI **from source geometry**, without reading the approved OD answers from the proof DXF.

This document is the implementation companion to `ACUTE_BEND_LT85_METHOD.md`.

---

## 1. Inputs that MUST exist before calculation

For one acute bend, lock these source facts first:

- `t`: sheet thickness.
- `alpha`: included bend angle, with this rule triggered only when `alpha < 85°`.
- `FACE_1`, `FACE_2`: the two formed sheet faces.
- `FREE_EDGE_1`, `FREE_EDGE_2`: the physical free-end planes of those faces.
- `INNER_FACE_1`, `INNER_FACE_2`: the two real inside-surface straight lines before inserting the bend radius.
- `Rin`: applicable inside bend radius from the approved tooling/shop rule or explicit drawing.
- `Nobi`: applicable handwritten/table bend deduction, only needed **after** OD1/OD2 are derived.

Do not start from an approved reference DXF OD value. A reference DXF is comparison evidence only.

For the approved `ACUTE_BEND_LT85_SOURCE_FIXTURE.dxf` regression, source geometry itself proves:
- two rectangular formed faces;
- face lengths `180 mm` and `50 mm`;
- `t=3 mm`;
- angle between the two face directions = `75°`.

`Rin=0.6 mm` comes from the approved acute-bend shop method (`HD.dxf`), not from an invented measurement of `ACUTE_BEND_LT85_SOURCE_FIXTURE.dxf`.

---

## 2. Source-topology lock

Treat each formed face as a thickness-bearing strip, not as one centerline.

For each face identify:

- the two long parallel surfaces;
- the free-end short edge;
- which long surface is the **inside bend surface**;
- the unit direction vector `d_i` pointing **from its free edge toward the bend**.

The inside-surface choice is a topology decision. In the regression fixture, the inside surface of each face is the long face closest to the body/interior wedge of the other face. A future drawing must establish this from the actual formed topology/views; do not choose a side merely to match the reference answer.

---

## 3. Construct the real bend center — no sharp-intersection shortcut

Let `L1` and `L2` be the two proved inside-surface lines.

For each line construct a parallel line offset by exactly `Rin` **toward the center of curvature**.

In vector form:

- Let `n1`, `n2` be unit normals from `L1`, `L2` toward the bend center.
- Pick any points `p1 ∈ L1`, `p2 ∈ L2`.
- Offset lines are:

`L1_R: p = p1 + Rin*n1 + s*d1`

`L2_R: p = p2 + Rin*n2 + u*d2`

The bend center is their intersection:

`C = L1_R ∩ L2_R`

Validation before continuing:

- perpendicular distance `dist(C,L1) = Rin`;
- perpendicular distance `dist(C,L2) = Rin`;
- center lies on the topology-proved curvature side of both faces.

If the sign of either normal is unresolved, STOP/FLAG that bend. Do not select the candidate that merely reproduces the sample.

---

## 4. Construct outer radius

The physical outer bend radius is:

`Rout = Rin + t`

This gives two concentric arcs:

- inside arc: center `C`, radius `Rin`;
- outside arc: center `C`, radius `Rout`.

Tangency to the straight faces must be exact. The old theoretical sharp intersection is no longer a measurement datum.

---

## 5. Measure OD1 and OD2 from the outside envelope

For each face `i`:

- `d_i`: unit direction from free edge toward bend.
- `q_i`: any point on the corresponding physical free-edge plane.
- The outer bend circle's furthest support point in direction `d_i` has scalar coordinate:

`S_i = dot(C, d_i) + Rout`

- The free-edge plane has scalar coordinate:

`F_i = dot(q_i, d_i)`

Therefore the physical outside dimension is:

`OD_i = S_i - F_i`

So:

`OD1 = dot(C,d1) + Rout - dot(q1,d1)`

`OD2 = dot(C,d2) + Rout - dot(q2,d2)`

This is the portable mathematical statement of **外寸法を出す。（交点ではない）**: measure the real outside envelope, not the theoretical line intersection.

---

## 6. Only after OD is proved: unfold using Nobi

For a two-face bend:

`L_flat = OD1 + OD2 - Nobi`

If the flat origin starts at `FREE_EDGE_1`, then:

`BEND_LINE_1 = OD1 - Nobi`

`BEND_LINE_2 = OD1`

and:

`BEND_LINE_2 - BEND_LINE_1 = Nobi`

Trim both bend lines to the actual material domain.

---

## 7. Fully reproducible TEST regression from raw geometry

`ACUTE_BEND_LT85_SOURCE_FIXTURE.dxf` contains:

### Face 1
A `180 × 3` vertical rectangular strip.

### Face 2
A `50 × 3` rectangular strip inclined so the included face angle is `75°`.

The regression runner must derive those dimensions from geometry. The following output values are **assertions only**, never input values:

- expected `t = 3.0`
- expected face lengths = `180.0`, `50.0`
- expected included angle = `75.0°`
- method input `Rin = 0.6`
- therefore `Rout = 3.6`

After constructing the offset-line intersection `C` and evaluating the outside-envelope equations:

- `OD1 = 182.014217199... mm`
- `OD2 = 49.712236235... mm`

Report:
- `OD1 = 182.01 mm`
- `OD2 = 49.71 mm`

The script `regression/tools/check_acute_bend_lt85.py` implements this chain. It reads the normalized source fixture, derives both face strips/thickness/angle, constructs `C`, calculates the two ODs, then compares them against the approved outputs. It does not read the proof DXF.

---

## 8. Mandatory audit trace for production use

For every future `<85°` bend record:

`source_view | face_1 | face_2 | t | alpha | free_edge_1 | free_edge_2 | inner_line_1 | inner_line_2 | Rin source | center construction | Rout | OD1 | OD2 | Nobi source | flat | bend pair`

This trace is what lets another AI or engineer verify the result without needing the original conversation.

---

## 9. Anti-cheating regression rule

A regression run is invalid if it:

- reads `182.014217` or `49.712236` from `ACUTE_BEND_LT85_OD_PROOF.dxf`;
- uses those values as constants in the geometric calculation;
- reverse-fits `Rin` from the approved outputs;
- chooses inner-face/normal signs solely because they minimize residual against the answer.

The approved OD values may appear only in the **final assertion/comparison block**.
<!-- END MODULE: references/ACUTE_BEND_LT85_FROM_SOURCE.md -->
