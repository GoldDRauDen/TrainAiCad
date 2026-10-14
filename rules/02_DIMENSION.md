# 02 — DIMENSION & SOURCE EVIDENCE | Production rules V4.34

> Consolidated modules; original source path identifies section and preserves rule provenance. No guessed coordinates or dimensions.

<!-- BEGIN MODULE: skills/lispcad/core/DATUM_DIMENSION.md -->
## V4.34 typed witness node closure (2026-10-13)
For every **proved HOLE/SLOT member** in V4.34, declare `witness_required_feature_ids` and a `feature_witness_graph` for both X and Y. Every used dimension edge records a physical `from_node`/`to_node`, endpoint types (`OUTER_EDGE`, `HOLE_CENTER`, `SLOT_MIDPOINT`, `ARC_CENTER`, `TANGENT_POINT`, ...), signed axis/value, dimension kind, source page and a verifiable PDF crop/witness ref. `tools/dimension_witness.py` independently solves signed paths, rejects disconnected graphs/contradictory cycles, and cross-checks declared canonical CIRCLE coordinates. A claim `endpoint_verified=true` is not source proof by itself: source QA must inspect the crop and confirm the physical endpoints. 521013-21/059759 negative regression: taking 265 from the external RIGHT_EDGE rather than the RIGHT_HOLE_CENTER adds 10 mm to the group; sample/reference geometry cannot supply a missing witness. Old V4.31 jobs retain compatibility while V4.34 imposes the stronger evidence record.

# LISPCAD Core — Datum & Dimension Semantics

Source: approved V4.3 production baseline, with independently approved V4.10 source-origin/axis mapping. These rules apply across all topology and mode modules.

## V4.8 approved datum/feature-family regression

Regression 520709-07: for 039915, OD 30 minus local step 5 gives the external step at **25**, NOT 27.36 (Nobi-adjusted bend datum) minus 5 = 22.36; the bend zone still retains Nobi 2.64. For 039918 and PDF-mirrored 039919, printed diagonal 50 (not 100) is measured to the theoretical sharp point before R10; independently identify 2-M4 and 3-Ø5 hole families by source leaders. The correct original 039918 flattened local centers (173.2,110) and (224.2,54) are respectively M4→Ø3.3 and Ø5. These examples reinforce existing dimension-endpoint and family-isolation rules; they do not create new general coordinates.

## 4. Dimension Authority, Tolerance Rules & Nobi Logic

### 4.1 Dimension Precedence System
When dimension conflicts occur, strictly follow this hierarchy (higher overrides lower):
1. Latest Revision Note / Cloud
2. Red Handwritten Correction on Drawing
3. Explicit Numerical Callout
4. Detail View Callout
5. Section View Callout
6. Projection Alignment
7. Implied DXF Geometry
8. Visual Estimation

### 4.2 Datum Lock & Extension Line Integrity *(expanded V3.1 — anti-error safeguard)*
- To prevent feature displacement errors (such as misassociating extension lines across parallel dimension chains), notch/cutout/hole positions ($X$, $Y$) MUST be calculated strictly from the actual datum edge or datum feature proven by the dimension extension lines.
- **Never** add or subtract adjacent flange widths, hole-edge offsets, neighboring dimension values, or bounding-box offsets unless the drawing shows that they belong to one continuous dimension string.
- Every critical feature coordinate MUST be traceable as an explicit expression from a proven datum, e.g. `Y = 0 + 10 + 35 = 45`. If no valid trace exists, apply Section 4.4 instead of inferring the coordinate.

#### 4.2.1 Dimension-String Classification — MUST classify before arithmetic
Before using any dimension numerically, classify it as one of the following:

1. **Baseline / Common-Datum Dimension**: Multiple dimensions share the same extension-line origin. Values are measured independently from the common datum and MUST NOT be summed merely because they are drawn next to each other.
2. **Continuous Chain Dimension**: The end witness/extension line of one dimension is the proven start witness/extension line of the next. Only this type may be accumulated sequentially.
3. **Step / Local Feature Dimension**: A dimension defines the distance between two local contour levels, notch walls, hole centers, or other local features. It is not cumulative with a neighboring chain unless the extension lines explicitly connect the nodes.
4. **Overall Dimension**: The total width/height is primarily a closure check. It may validate a chain sum but MUST NOT be used to redistribute or invent missing intermediate dimensions.
5. **Ordinate / Coordinate Dimension**: A coordinate is measured directly from its stated zero datum; do not convert it into a chain unless the drawing explicitly defines one.

#### 4.2.2 Datum Graph Rules
- Treat extension-line endpoints as graph nodes and dimensions as graph edges. A coordinate is valid only when there is a connected, explicit path from the selected datum node to the target feature node.
- Parallel dimension strings at different offsets on the drawing are independent until a shared extension-line node is proven. Visual alignment alone is not connectivity.
- **Hole-center chains and contour/step chains must not be mixed** merely because they are nearby. A hole row offset (for example 10 mm from an edge) cannot become the origin for a separate 153 mm or 54 mm contour/feature dimension unless the extension lines prove the same origin.
- If two dimensions visually touch but their witness lines terminate on different geometry, classify them separately.
- Use the overall size only as a closure test: if `sum(chain segments) != overall`, mark the chain `FLAGGED` and re-read the extension lines; do not force-fit the numbers.

#### 4.2.2a V4.16 Face-First Dimension Ownership

Before unfolding any multi-face part, reconstruct each visible formed face as its own contour/feature model. Tag every used dimension by actual witness endpoints and assign it to one semantic graph: face contour, hole/slot center-or-size, bend/face transition, or another proved local feature.

- A hole/slot-center dimension never becomes a contour or bend-axis dimension merely because it is parallel, nearby, or numerically convenient.
- Finish each face's contour and feature graph from that face's own witnesses before joining adjacent faces and deducting Nobi.
- Projection alignment may identify the owning face but does not transfer dimension ownership across faces.
- Approved 044812/044813 regression: `25` is the center distance of two `9.5×R1.75` long holes on the `28×41` face; use `28 + 21 - 3.68 = 45.32` for the proved two-face flat contribution, not `25-3.68` as a contour/bend coordinate.

#### 4.2.2b Cross-part Assembly Datum Closure (approved 2026-10-13)

When a hole, slot, locating mark or other manufacturing feature has NO directly proved local coordinate but the PDF provides an assembly/installation view and related part dimensions, **try a source-backed ASSEMBLY_DATUM_GRAPH before numeric FLAG or VIEWS_ONLY**. Do not claim the dimension is missing merely because the child part's own flat lacks a coordinate.

1. Establish the PART_IDENTITY_GRAPH first: physical part code, host face, the related mating/support parts and actual view IDs. A shared assembly view is not a separate manufactured part.
2. Choose one physically proved assembly reference frame and independently prove both signed X and Y directions. For each used dimension record its *actual* witness endpoints, type (baseline/chain/local/ordinate/contact/assembly offset), sign, host-part identity and printed/approved evidence. Only join dimension paths through the **same physical node**, not paper proximity, shared numbers, nominal symmetry or sample/reference DXF.
3. Represent each relation as `target_axis - source_axis = signed_offset_mm`, with a source witness for the corresponding edge. A contact offset of zero requires positive evidence of the mating contact; mere proximity or a presumed flush fit is not a constraint. Across oriented/bent faces, prove the transform and physical attachment edge before adding its signed offset.
4. Solve the connected graph to express `feature - target_part_datum` as a signed sum; independently check every available alternate dimension path/cycle and the assembly fit. A contradicted or disconnected graph is **not** a 50%-confidence coordinate: retain the local FLAG and ask about the *missing physical relationship*.
5. Transform the assembly result to the feature's own physical face frame, then to the final flat through the routed face/bend rules. Run fold-back and hole count/diameter/host QA in the same frame. A mathematically correct assembly offset does not alone prove an unfolded feature location.
6. Retain feature ID, source dimension witnesses, source node and target node, `frame_id`, axis, signed formula, result, applicable face transform and any unresolved degrees of freedom. A later customer/sample DXF can challenge a solution but must not become its missing witness.

`tools/assembly_datum_solver.py` provides a deterministic, source-proof-gated graph solver for the arithmetic and cycle consistency. The L3 holistic guard independently recomputes any **declared** `assembly_indirect_candidates` from corresponding `assembly_datum_traces`, and fails incorrect/unattempted proof for production. **Source census must declare the candidates**; the tool cannot discover them by itself.

This procedure is conditional: do not create a fictitious assembly for standalone flat parts or override a genuinely explicit source feature dimension. The fixture `regression/datum/521013-04_059636_assembly_graph.json` tests this class of error only; its offsets are not general rules.

#### 4.2.3 Required Datum Trace Record
For every hole row, notch, step, or repeated feature pattern, retain a trace record containing: `axis`, `datum entity`, `dimension type`, `equation`, and `result`. This trace must be auditable in Stage 1 for any feature that was previously ambiguous or that disagrees with a reference DXF.

#### 4.2.4 Dimension Endpoint Identity — MUST NOT Borrow a Neighboring Endpoint
Every dimension endpoint/witness line must be tagged by the **actual geometry it terminates on** before arithmetic. At minimum distinguish: `OUTER_EDGE`, `CONTOUR_EDGE/STEP`, `HOLE_CENTER`, `CENTERLINE`, `THEORETICAL_SHARP_CORNER`, and `REFERENCE_DATUM`.

- Two parallel dimensions drawn beside each other may terminate on different targets even when they share the same axis or appear visually aligned. Never reuse the endpoint of a neighboring dimension without proving the witness line lands on the same node.
- A hole-center dimension and a contour-edge dimension are different graph edges even if their values are printed in the same local area.
- Example pattern: if one horizontal dimension is from a step to the **outer edge** and an adjacent dimension is between two **hole centers**, do not subtract both from the same right-side X coordinate.
- Example pattern: if vertical dimensions `389` and `404` terminate respectively at a hole center and a step ledge, they define two different Y nodes; they are not interchangeable.
- Record the endpoint identity in the datum trace whenever a crowded drawing contains multiple nearby extension lines.

#### 4.2.4.1 V4.32 Radius/notch depth endpoint semantics

For an edge-open notch or recess containing an arc/radius, classify whether a printed dimension terminates on the **physical deepest contour point**, the arc center, a tangent point, or another explicit witness node before converting it to geometry.

- `OVERALL_DEPTH` to the physical deepest point is not `CENTER_SETBACK`.
- If source proves radius `R` and overall depth `D` measured to the deepest arc point, then a same-axis center setback may be derived as `D - R`; do not copy `D` directly to the arc center.
- Conversely, if the witness proves the center location, do not silently reinterpret that center dimension as physical overall depth.
- Regression 521006-18 058649/058650: `R3` with source overall depth `8` gives center setback `5`; treating center setback as `8` creates wrong physical depth `11`. These values are regression evidence only.

#### 4.2.5 Contour Topology First — Dimensions Assign Coordinates, They Do Not Invent the Shape
Before solving numerical coordinates, trace the visible manufacturing boundary as an ordered topology: outer corners, protrusions, recesses, steps, notches, vertical/horizontal segments, chamfers, and radii.

- An overall width/height gives the bounding extent only. It does **not** imply that the part is a full rectangle over that entire extent.
- First establish which contour segments actually exist and how they connect; only then assign coordinates from dimensions.
- A local step can make the maximum width exist only over part of the height. Do not extend that maximum-width edge through a region where the drawing visibly steps inward.
- If the visible outline and the assumed rectangular base disagree, the visible outline wins subject to explicit dimensions/callouts.
- For complex stepped profiles, create an ordered contour trace such as `edge -> C -> vertical -> R -> ledge -> vertical ...` before converting it to LWPOLYLINE vertices/bulges.

#### 4.2.6 Reference Dimensions Still Require a Proven Datum
A parenthesized/reference dimension is **not automatically a coordinate from the global origin**. `Reference` means no mid-tolerance adjustment; its extension-line origin and target still control how the coordinate is calculated.

- If a reference value `(276.5)` is measured from a hole-center row at `Y=10`, then the target is `Y=10+276.5=286.5`, not `Y=276.5`.
- Apply Section 4.2 datum tracing exactly as for a normal dimension; only the tolerance treatment differs.
- **Formed-view reference dimensions are not flat-pattern dimensions by default.** A parenthesized/参考 overall shown on a bent Front/Side/Section view describes that formed view unless its witness lines explicitly belong to a Development/Flat Pattern view.
- Do NOT use a formed-view reference overall as the unfolded blank length merely because its numeric value is close to the expected flat length. Derive flat length from the proven ordered flange/body chain, ID→OD conversion where required, and Nobi deductions. Use the formed-view reference only for the geometry/view it actually dimensions.
- If a formed-view reference value conflicts with a fully proven unfold equation, classify the issue as `REFERENCE/FORMED-DIMENSION ERROR` or source conflict; do not force the flat equation to equal the reference value.

#### 4.2.7 Local-Face Datum → Global Flat Datum Mapping
Features dimensioned on a bent flange/face MUST be transformed from the **local face coordinate system** into the **global unfolded blank coordinate system** before verified global-flat coordinates are emitted.

1. Assign each formed face an ordered identity along the unfold path: `FACE_1 -> BEND_1 -> FACE_2 -> ...`.
2. Establish the flat start/end coordinates of that face from the sequential OD/Nobi equations in Section 4.7.
3. Preserve the dimension direction. If local coordinate `u` is measured from the face start datum, use `U_flat = FACE_START_flat + u`. If it is measured from the opposite/free edge, use `U_flat = FACE_END_flat - u`.
4. A feature coordinate printed on a formed face MUST NOT be copied directly as a global flat coordinate unless the face datum is proven to coincide with the global flat datum.
5. Record `face_id`, `local datum`, `local equation`, and `global flat equation` in the datum trace for holes/slots/notches that cross a bend mapping.

This rule applies independently on both axes. Projection alignment may identify which face a feature belongs to, but may not replace the required unfold transform.

#### 4.2.7.1 V4.32 Physical edge identity survives the transform

For any edge-based datum on a bent face, record the physical edge identity before unfold, for example `FACE_2.BEND_EDGE`, `FACE_2.FREE_EDGE`, `FACE_2.LEFT_EDGE`, or `FACE_2.RIGHT_EDGE`.

- The identity comes from the source-supported face graph and `BEND_ATTACHMENT_EDGE_LOCKED`, not from page direction or nearest-view proximity.
- Rotation/reflection/local-axis reversal may change the coordinate equation but must not silently swap `BEND_EDGE` with `FREE_EDGE`.
- Every feature positioned from such an edge must retain `face_id | physical datum edge id | local equation | attachment transform | global flat equation`.
- If the same local numeric coordinate can be obtained from two different edge identities, numeric equality does not close the ambiguity. The physical owner must still be proved.
- Fold-back must reproduce both the feature offset and the owning physical edge identity.

#### 4.2.7.2 V4.14 approved symmetry/explicit-edge-dimension precedence

If actual PDF geometry PROVES a symmetry axis and there is NO controlling outer-edge dimension for a repeated feature family, use that axis to construct the symmetric centers/positions and retain a datum trace. When the same feature family has an explicit physical outside-edge dimension, **DRAW ACCORDING TO THE PRINTED EDGE DIMENSION** even if a centerline is also shown. A printed axis that coexists with source-proved actual asymmetry or mutually inconsistent witnesses is a specific FLAG/question after fully tracing all source evidence; do not silently force visual symmetry. For features on bent faces, source-frame lock and the independent per-face local→global-flat transform remain mandatory. User-approved 010420 Q03 documents this priority.

#### 4.2.8 Bend Sequence / Face Order Is Non-Commutative
The total flat length equation may be numerically unchanged when two flange lengths are swapped, but **bend positions, feature transforms, and material topology are not**. Therefore:

- Determine the ordered face sequence from the visible formed topology, bend callouts, section/detail views, and proven witness-line connectivity before calculating bend-line coordinates.
- Do not validate bend order merely because `sum(OD) - sum(Nobi)` matches the overall blank length.
- Double bend lines MUST be positioned from the ordered sequence in Section 4.7 and MUST exist only over material regions that actually cross that bend. For U-shaped, legged, stepped, or cut-away parts, split/trim bend lines around voids; never draw a bend line continuously through empty space.
- If two face orders remain equally plausible after explicit trace exhaustion, STOP and ask the user. Magenta is not permission to choose an arbitrary bend order.

#### 4.2.9 Mandatory Source-Origin and Axis-Direction Lock (V4.10 — approved)

**Before converting any absolute/ordinate drawing dimensions into CAD coordinates, prove the SOURCE coordinate frame for EACH affected view.** Identify (a) the physical source origin O and the actual two edges/features that define it, (b) the direction of source +X and +Y from printed arrows, coordinate signs, dimension witness lines or explicit drawing annotations, (c) which actual material edge/feature becomes the TARGET CAD datum, and (d) the source-view-to-CAD orientation. Neither the paper/page upper-left corner nor a habitual DXF lower-left origin is evidence by itself. Never assume that a negative source ordinate means a negative CAD ordinate.

For an axis-aligned view with no X/Y exchange, let `(X0_cad,Y0_cad)` be the VERIFIED CAD coordinates of the drawing's source origin and `sx,sy ∈ {+1,-1}` represent the respective source-positive axis directions relative to CAD-positive right/up. Use the general explicit transform:

```
X_cad = X0_cad + sx * X_source
Y_cad = Y0_cad + sy * Y_source
```

Lock **both** source origin and each axis sign independently. When a source view is mirrored, rotated or exchanges X and Y, first prove the actual mapping from its view/face to the intended CAD face and apply the correctly oriented axis mapping; do not force this simple aligned-axis formula onto an unresolved view. Section 4.2.7 local-formed-face → global-flat unfolding is an ADDITIONAL transform after the source frame is established, not a substitute for it.

**Top-left source datum cases:** If the drawing's proven origin is at its material top-left, its explicitly dimensioned part height is `H`, and CAD Y=0 is the SAME material bottom edge, then `Y0_cad=H`. If source +Y points **up** and a hole is given as `Y_source=-d`, `Y_cad=H-d`; if source +Y points **down** and the hole is `Y_source=+d`, `Y_cad=H-d`. These are two equivalent physical layouts with DIFFERENT source signs; do not mix their conventions. Use `H` only when that height and both controlling top/bottom edges are actually proven for the SAME view/face; never use an arbitrary picture/image bounding box or a formed-view overall for a different flat face.

**Mandatory audit trace** for any ordinate-based feature family: source view/face ID, source origin's actual geometry, source +X/+Y directions, source signed X/Y of each family or row, target CAD datum, view transform (including any mirror/rotation), the explicit coordinate equations, and an independently dimensioned closure check where supplied. A row of repeated holes shares a Y result only when the source witness/ordinate data prove a common physical row. If origin or either needed axis direction is unproved after tracing all explicit drawing evidence, mark the affected coordinates FLAG and ask; keep independently proved source views separate rather than emitting guessed production coordinates. A visually plausible row or a matching total bbox is NOT evidence of a correct datum.

### 4.3 Mid-Tolerance Strategy (Tolerance Calculation)
For coordinates governed by asymmetric tolerances or limit dimensions, calculate the flat pattern feature position using the **Mid-Tolerance Value**:

$$X_{\text{mid}} = X_{\text{nominal}} + \frac{\text{Tolerance}_{\text{upper}} + \text{Tolerance}_{\text{lower}}}{2}$$

- **Example**: A dimension specified as $50.0^{+0.2}_{+0.1}\text{ mm}$ is computed as:
  $$X_{\text{mid}} = 50.0 + \frac{0.2 + 0.1}{2} = 50.15\text{ mm}$$
- **Symmetric Tolerances** ($\pm 0.1\text{ mm}$): Mid-tolerance equals nominal value.
- **Reference Dimensions** (参考 / marked as reference, no tolerance band): Do NOT apply mid-tolerance adjustment — use nominal value as-is (see Section 6, term "Reference").

### 4.4 Ambiguous, Unclear, or Missing Dimension Handling
- **Flag only after explicit-trace exhaustion**: A crowded/overlapping print is not automatically ambiguous. Before flagging, zoom/re-read the witness lines and test all explicit dimension paths, endpoint identities, feature diameters, feature counts, projection relationships, and overall closure. If the PDF contains a unique trace, use it; do not use Magenta as an escape from difficult dimension parsing.
- **Magenta is not permission to invent topology**: Use estimated/Magenta geometry only when the entity identity and contour/feature topology are already certain but a numeric dimension remains unreadable/ambiguous. If multiple topologies, feature types, bend orders, or physical attachment edges are possible, STOP and ask the user rather than fabricating a bounding rectangle, generic slot, or arbitrary flange order/edge.
- **Integer Value Enforcement applies only to estimated/assumed values**: Any truly estimated dimension MUST be rounded to the nearest integer (e.g., `256` or `258`, never `256.4`). Explicit dimensions and deterministic formula results (for example `182.70`, `159.26`, or a Nobi-derived bend coordinate) MUST retain their calculated precision and MUST NOT be rounded to an integer merely because another part of the same feature/part is flagged.
- **Known/unknown separation**: Flagging an unresolved feature does not authorize changing dimensions that are already proven. Keep all proven edges, lengths, hole sizes, and coordinates exact; isolate only the unresolved quantity/entity.
- **No bounding-box substitution**: A known overall width/height may be reported as a bounding extent, but MUST NOT be emitted as a closed rectangular outline unless the contour trace proves that all four rectangle edges actually exist.
- **Color Code 6 (Magenta)**: Assign DXF Group `(62 . 6)` to any line, circle, or polyline whose size/position was estimated or ambiguous.
- **Adjacent Text Annotation**: Add a `TEXT` entity on DXF Group `(62 . 6)` immediately adjacent to the ambiguous feature (e.g., `"(ESTIMATED GEOMETRY - CHECK DRAWING)"` or `"(M6 OR M8)"`).
<!-- END MODULE: skills/lispcad/core/DATUM_DIMENSION.md -->

---

<!-- BEGIN MODULE: references/SOURCE_MANUFACTURING_NOTE_CENSUS.md -->
# SOURCE_MANUFACTURING_NOTE_CENSUS — V4.29 source-instruction closure gate

**Approved:** 2026-10-05 from calibration/audit job `521005-13`.

## Purpose

Prevent a manufacturing feature from disappearing because its evidence is carried primarily by a printed/handwritten instruction rather than by visually prominent geometry.

This is an always-on source-reading gate. It adds no Nobi, material, tolerance, hole, slit-length, or bend-position formula.

## 1. SOURCE_MANUFACTURING_NOTE_CENSUS

Before final preliminary Feature Census, inspect every production-affecting Japanese/English printed note, handwritten note, revision note, leader, witness, and locally scoped instruction.

For every potentially production-affecting note retain an evidence-equivalent record:

`note_text | evidence_type | code_scope | target/leader/witness | candidate_family | quantity | explicit_value | location/direction evidence | resolution`

Allowed `resolution` states include:
- `ROUTED`
- `CANCELLED`
- `IRRELEVANT_TO_MANUFACTURING`
- `UNRESOLVED`

A note may not disappear merely because its feature is small, edge-open, visually similar to CUT geometry, or absent from OCR output.

## 2. SOURCE_NOTE_TO_FAMILY gate

A source instruction that proves or plausibly indicates a known manufacturing family must affect Feature Census before that family may be marked `NO`.

- Identity and scope proved -> route the family as `YES`.
- A manufacturing instruction exists but identity, scope, quantity, host, value, location, or direction remains materially unresolved -> route the relevant family as `UNKNOWN` until source exhaustion.
- `NO` is allowed only after applicable manufacturing notes have been resolved as cancelled, irrelevant to that family, or positively shown to belong elsewhere.

`UNKNOWN != NO`; unresolved notes must not be suppressed to avoid loading a route.

## 3. CUSTOM_SOURCE_SLIT

`スリット`, `SLIT`, or an equivalent explicit slit instruction can define a **custom source-instructed slit**.

Rules:

1. **Instruction required for this custom branch.** Do not create a custom anti-deformation slit merely because a bend exists, because a location looks mechanically useful, or because an approved sample has one.
2. The slit value is drawing-specific. `スリット 8` means the controlling explicit slit value for that scoped feature is `8` in that drawing; `8` is not a universal slit size.
3. Quantity, edge/host, position, direction, and relation to BEND come from source instruction/witness/geometry. Slits are often used near bend regions to reduce deformation, but that mechanical purpose does **not** prove a centerline location.
4. Never hardcode `BEND_CENTER -> SLIT`, and never copy coordinates from a reference DXF into a new drawing.
5. When an explicit source slit dimension controls the custom feature, preserve that value. Do not replace it with a generic relief formula such as `t+0.2` or `t*sin(theta)`.
6. If `スリット/SLIT` identity is proved but the exact construction remains incomplete, keep the feature routed and FLAG only the unresolved fields; do not delete the family.
7. Existing separately-triggered mechanisms such as crossing-bend relief, opposite-fold `R=t`, BOXMET slit/relief, or other approved relief families remain independent. This custom-instruction gate does not disable or redefine their trigger rules.

## 4. SOURCE_NOTE_FEATURE_COMPLETENESS

Before production PASS, close:

`SOURCE MANUFACTURING NOTES -> FEATURE CENSUS -> LOADED ROUTES -> CANONICAL FAMILY -> SERIALIZED DXF -> READ-BACK`

Any source-active manufacturing instruction that has no resolved family/output status is a production FAIL/FLAG.

For source-instructed custom slit, validate at minimum:
- source instruction scope;
- slit family identity;
- quantity when specified/proved;
- explicit size/value when specified;
- host edge/face and direction;
- source-proved relationship to BEND, if any;
- canonical representation;
- serialized physical geometry;
- saved-DXF read-back.

## 5. 521005-13 regression intent

For `058155` and `058156`, the source carries `スリット 8`; the approved sample confirms two edge-open slit features for each code. The job-specific value `8` and approved local coordinates belong only to that regression.

The generalized lesson is only:

**Do not lose an explicitly instructed manufacturing slit during source-note census/routing. Do not invent its size or position when the source does not specify them.**
<!-- END MODULE: references/SOURCE_MANUFACTURING_NOTE_CENSUS.md -->

---

<!-- BEGIN MODULE: references/SOURCE_FEATURE_GROUP_CLOSURE.md -->
# SOURCE_FEATURE_GROUP_CLOSURE — leader/callout group closure + reference parameter identity

**Status:** USER APPROVED 2026-10-05 from calibration job `521005-05`.

## Purpose

Prevent same-family features from being collapsed into one dimension graph, and prevent false PDF/reference conflicts caused by comparing different physical parameters or different witness frames.

This reference is always-on source parsing before final preliminary Feature Census. It adds no hole size, Nobi, material, tolerance, or slit formula.

## 1. FEATURE_FAMILY versus SOURCE_FEATURE_GROUP

A **FEATURE_FAMILY** is the manufacturing class such as `HOLE`, `TAP`, `SLOT_STRAIGHT`, `CHAMFER_FILLET`, `SLIT_RELIEF`, etc.

A **SOURCE_FEATURE_GROUP** is one source-scoped cluster controlled by its own callout/leader/quantity and dimension ownership. Two groups may have the same family and the same nominal size and still remain separate groups.

Required group record:

`group_id | family | source callout | quantity | leader/target scope | source view | host face | X witness graph | Y witness graph | local datum | size semantics | evidence status`

Do not merge source groups merely because they share:
- the same diameter/thread/slot size;
- a continuous or nearby X dimension string;
- visual alignment;
- projection proximity;
- a common family label;
- a convenient aggregate count.

### Group closure rule

Close each source group independently:

`leader/callout -> quantity -> feature size -> X witnesses -> Y witnesses -> datum -> host face -> canonical members`.

A dimension string may be shared by multiple groups only where the actual witness graph proves that shared ownership. A shared X chain does **not** authorize borrowing another group's Y chain, and vice versa.

`GROUP_COUNT_CLOSURE` is mandatory before aggregate family count closure. If the final total count is numerically correct but one source group is short and another is over-produced, the result is FAIL.

### 057862 regression intent

For calibration code `057862`, the source contains separate `2-Ø9` left, `6-Ø9`, and `2-Ø9` right source groups. They are the same broad HOLE/Ø9 family but have independent leader/quantity/dimension ownership. Those job-specific groups are regression evidence only; they do not establish universal coordinates.

## 2. DETAIL_VIEW_MAPPING

The paper location of a Detail/Section/Auxiliary view may be arbitrary. Its placement on the sheet is not a manufacturing coordinate.

Use the detail identifier/leader and projection/source mapping to bind the detail back to the actual physical target. Dimensions inside the detail retain their own witness endpoints and local feature ownership. Do not transfer the detail's page position into part geometry.

## 3. CUSTOMER_CONFIRMATION_PENDING boundary

A customer/sample/reference DXF does not automatically resolve a source value that is explicitly or genuinely `CUSTOMER_CONFIRMATION_PENDING`.

- Keep every independently proved geometry exact.
- Keep the unresolved source field locally FLAGGED.
- A TRAIN_REFERENCE may diagnose likely intent, but it may not promote the pending value into production authority unless the user/customer explicitly confirms that value or the active source authority itself resolves it.

Calibration examples `057861` and the `8-R5` corner family on `057864` remain local customer-confirmation cases; their sample geometry must not become a universal or silent source substitute.

## 4. SAME_PHYSICAL_PARAMETER_BEFORE_REFERENCE_CONFLICT

Before declaring a PDF/source value to conflict with customer DATA or an approved/sample/reference DXF, prove that both measurements describe the **same physical parameter**.

At minimum lock:

`code + source group + host face + physical witness A + physical witness B + dimension semantics + inside/outside state + source/local frame + units`.

Only after those fields match may a numeric difference be classified as an actual source/reference parameter conflict.

Do not compare:
- an inside bend dimension with a measurement from an outside/free edge;
- a formed-face local dimension with a global-flat coordinate;
- a hole-center distance with a contour-edge distance;
- a theoretical-sharp dimension with the trimmed physical R/C bbox;
- two visually similar values whose witness endpoints differ.

If parameter identity is not closed, re-trace the source/reference witnesses. Use `UNVERIFIED`/local FLAG as applicable; do not report `SOURCE_CONFLICT` merely because two numbers differ.

### 057865 regression intent

For calibration code `057865`, `10.5 / 8.5` are inside bend dimensions. A reference measurement of `10.0 / 8.0` taken from an outside edge is not the same physical parameter. The earlier comparison was an `AI_RULE_MISAPPLICATION`, not evidence that the source and sample disagreed.

## 5. Feature Census interaction

Before a family may be `NO`, first determine whether source leaders/callouts imply one or more unresolved source groups. A proved group makes the family `YES`; an apparent group with unresolved family/scope/quantity/host/datum makes the relevant family at least `UNKNOWN`.

For bent parts, if a bend-end/corner junction may require a relief decision but the signed bend-end offset has not yet been closed, retain `SLIT_RELIEF = UNKNOWN` until the routed 90-degree bend-end relief gate is evaluated. Do not require the literal word `SLIT` for topology-triggered relief mechanisms already approved elsewhere.

## 6. QA

Before production PASS:

- every active source group has a closed quantity and datum/witness record;
- no group borrows an unproved X/Y chain from another group;
- aggregate family count equals the sum of independently closed groups;
- Detail views map to their physical target rather than page position;
- customer-pending fields remain pending unless source/user authority resolves them;
- every claimed source/reference numeric conflict passes `SAME_PHYSICAL_PARAMETER_BEFORE_REFERENCE_CONFLICT`.
<!-- END MODULE: references/SOURCE_FEATURE_GROUP_CLOSURE.md -->

---

<!-- BEGIN MODULE: references/PART_IDENTITY_GRAPH.md -->
# PART_IDENTITY_GRAPH — V4.33

**Status:** USER APPROVED / PUSH 2026-10-07.

## 1. Scope

Use when one drawing/detail/DATA cluster contains multiple barcodes/codes, constituent marks such as ①/②, weld/assembly relationships, or multiple candidate manufacturing parts.

The purpose is to prevent assigning one whole view/DATA bundle to multiple part codes without evidence.

## 2. Required graph

Persist an evidence-equivalent mapping:

```text
BARCODE/CODE
<-> PART_ID / CONSTITUENT_ID
<-> SOURCE_VIEW(S)
<-> DATA_CLUSTER(S)
<-> MATERIAL / THICKNESS
<-> ASSEMBLY / WELD RELATION
```

Each edge requires source provenance.

A drawing can show an assembly and its child parts together; paper proximity does not merge them into one manufacturing part.

## 2A. Assembly datum ownership and indirect feature positions

When an assembly/installation view provides the only route to a child part's hole, slot or KEGAKI position, keep its shared **assembly-frame dimension witnesses** distinct from the child's physical manufacturing geometry. Before flagging that child feature as undimensioned:

- prove each participating barcode/part code, target feature, host face and related parent/child part;
- resolve physical assembly contact/attachment and witness identities, not proximity of views or nominal symmetry;
- hand the proved, signed relation graph to `skills/lispcad/core/DATUM_DIMENSION.md` §4.2.2b, then apply any required face-to-flat transform;
- audit each derived feature from the child's own datum with the source evidence and assembly-fit closure;
- retain unresolved physical relationships as local FLAG. Do not copy reference/sample coordinates or silently duplicate child contours under the parent code.

The graph solves *positions*, not part ownership; it cannot replace PART_IDENTITY_GRAPH or create a manufacturing feature not actually called out in the source.

## 2B. Welded parent/child contact ownership

For an assembly or A/B detail, identify which code owns the main
manufacturing sheet, which constituent is mounted/welded to it, and
which actual physical face hosts each proved contact. Preserve the
assembly-view ID and contact-site provenance in the independent
WELD_SITE_KEGAKI_CLOSURE ledger. A side-positioning view beside a
part is not ignorable merely because its curves are not CUT.
The KH851 customer exception requires marking proved weld sites even
if a KEGAKI callout is absent. Do not transfer the site to an
adjacent barcode solely by paper proximity.

## 3. Collision gate

Raise `PART_IDENTITY_COLLISION` when:

- two independent codes receive the same complete DATA/source-view bundle;
- a constituent marker is present but unowned;
- a view is assigned to a code only because it is nearest that barcode;
- material/thickness or explicit part identity conflicts with the proposed ownership;
- a welded child is dropped because its geometry appears inside an assembly drawing.

Shared assembly views are allowed only with an explicit shared-view role; manufacturing child geometry must still be separated by proved ownership.

## 4. Output behavior

If identity is unresolved but source views are identifiable, preserve the views under REVIEW ONLY and FLAG the ownership question. Do not duplicate the same manufacturing geometry under multiple codes as if each were independently solved.

If only one local ownership is unresolved, keep other proved parts/members executable.

## 5. Non-generalization

Constituent symbols, numbering style and weld notation identify candidate ownership structure only within the actual drawing. Do not hardcode a universal meaning for a particular circled number, page position or barcode order without source evidence.
<!-- END MODULE: references/PART_IDENTITY_GRAPH.md -->

---

<!-- BEGIN MODULE: references/HOLISTIC_ENGINEERING_CHALLENGE.md -->
# HOLISTIC_ENGINEERING_CHALLENGE — V4.33

**Status:** USER APPROVED / PUSH 2026-10-07.

## 1. Purpose

This is a pre-canonical engineering challenge. It does not replace feature-specific rules, FACE_GRAPH proof, source-member completeness, fold-back, or saved-DXF read-back.

Its purpose is to catch a different failure mode: the AI may build a self-consistent but incomplete or wrongly interpreted source model and then pass downstream checks against its own bad ledger.

The challenge asks whether the current interpretation is mechanically plausible and whether all available source evidence has actually been consumed before the job is allowed to proceed, downgrade to VIEWS_ONLY, or ask the customer.

## 2. Mandatory position in the flow

Run after the first source-based solve and routed feature checks, but before final canonical serialization:

```text
SOURCE
-> census / groups / members / identity
-> first solve
-> HOLISTIC_ENGINEERING_CHALLENGE
   -> anomaly? re-open source and re-solve
   -> no anomaly? continue
-> local FLAG or proved flat / justified VIEWS_ONLY
-> FINAL_ENGINEERING_SANITY_REVIEW
-> canonical
-> DXF
```

The challenge is source-first. A later sample/reference must not be used to retroactively make this stage appear solved.

## 3. Mandatory anomaly triggers

At minimum raise `ENGINEERING_ANOMALY_DETECTED` when any applicable condition is true:

- source contains substantial physical DATA or multiple proved source views while the persisted proved-source-member inventory is empty or implausibly small;
- a source feature family is YES/UNKNOWN but no corresponding source group/member or explicit drawing-only/canceled classification exists;
- a printed/handwritten flat arithmetic or Nobi chain closes a meaningful part dimension while the part is downgraded directly to VIEWS_ONLY without testing the corresponding formed topology;
- relevant source views/faces/primitives were harvested but have no downstream role and no explicit drawing-only/duplicate/helper classification;
- two declared part codes or constituent identifiers are assigned the same whole source bundle without proved shared-assembly scope;
- a dimension classified as a shared bend-edge length is also used as a whole face/blank extent without same-physical-parameter proof;
- a local unresolved feature causes the whole part to become VIEWS_ONLY even though a defensible flat exists independently;
- VIEWS_ONLY is selected before every source-supported FACE_GRAPH candidate has been tested through the routed constraints;
- the output is materially simpler than the source inventory without a member-by-member explanation;
- a PASS depends only on ledger self-equality while upstream census/inventory/ledger cardinalities or ownership disagree.
- source assembly/welding views were available but no independent weld-site inventory or explicit negative disposition exists, or a proved KH851 weld site has no corresponding KEGAKI member/local FLAG.

An anomaly is not proof that a particular alternative answer is correct. It is a mandatory reason to re-open the source and test the interpretation.

## 3A. Assembly-derived feature-position challenge

For assemblies, a hole, slot or KEGAKI whose local drawing lacks a direct coordinate is not automatically source-ambiguous. If related source assembly views and other parts' positions can provide a physical dimension path, record an `assembly_indirect_candidate` and attempt the §4.2.2b ASSEMBLY_DATUM_GRAPH before leaving that member FLAGGED/VIEWS_ONLY.

Retain the candidate in `assembly_indirect_candidates` and a `assembly_datum_traces` entry including source-backed constraint graph, witness nodes, source frame, computed offset or specific failed constraint and status. The L3 source/canonical guard must recompute a declared proved offset and reject fabricated `PASS`, inconsistent cycles, unsupported attachment or a derived coordinate left FLAGGED. If no source-proved path exists, preserve the feature FLAG and ask for the missing mate/witness datum.

No assembly evidence means no extra constraint: the existing direct datum and single-part workflow remains unchanged.

## 4. Unresolved-cause analysis

Before a part may remain unresolved, persist an evidence-equivalent record:

```text
UNRESOLVED_OBJECT
CANDIDATES
EVIDENCE_USED
EVIDENCE_NOT_YET_USED
CONSTRAINT_RESULT_PER_CANDIDATE
TRUE_REMAINING_DOF
BLOCKER_CLASS
```

For bent/multi-face parts, candidate attachment/order/sign hypotheses must be tested against all applicable formed/profile topology, view correspondence, dimension witnesses, DATA physical curves, feature ownership, handwritten arithmetic and fold-back constraints.

Do not write only "bend unclear", "attachment unknown", or "complex part".

## 5. Blocker vocabulary

Use the most specific class supported by evidence:

- `TRUE_SOURCE_AMBIGUITY`: two or more materially different interpretations remain source-compatible after source exhaustion.
- `AI_INTERPRETATION_GAP`: source evidence exists but the current solver has not established a unique solution; do not blame the source.
- `SOURCE_MEMBER_CENSUS_GAP`: relevant source geometry/families have not been fully harvested/classified.
- `PART_IDENTITY_GAP`: barcode/code/constituent/view/DATA ownership is unresolved.
- `GEOMETRY_DECODE_GAP`: source physical curves exist but decoding/classification is incomplete.
- `ROUTING_COVERAGE_GAP`: a detected family has no current repo route.
- `CUSTOMER_CONFIRMATION_PENDING`: the source/user explicitly leaves a field pending.

`AI_INTERPRETATION_GAP` is not interchangeable with `TRUE_SOURCE_AMBIGUITY`.

## 6. VIEWS_ONLY is a last executable fallback, not a text-only stop

If no defensible flat exists after source exhaustion and this challenge, but independently proved source/orthographic views exist, execute the current DRAW -> FLAG -> CONFIRM policy:

- redraw/preserve every independently proved source-view member needed to represent the unresolved part;
- preserve physical customer-DATA curves instead of replacing them with simplified analytic lookalikes;
- keep views as separate labeled subgroups under the correct code;
- include all proved holes/slots/R/C/marks represented in those source views;
- mark only the unresolved relationship/topology/dimension as FLAGGED;
- set part status VIEWS_ONLY and whole composite REVIEW ONLY — NO CUT.

Hard fail `VIEWS_ONLY_SOURCE_VIEW_COMPLETENESS` when proved source-view members are omitted from the VIEWS_ONLY canonical representation.

## 7. Local uncertainty stays local

When a unique flat is proved but one relief, hole, slit, datum or other feature remains unresolved, retain the proved flat and proved members. FLAG/PREVIEW only the unresolved local member.

Do not use one local uncertainty to downgrade the whole part to VIEWS_ONLY.

## 8. Final engineering sanity review

Immediately before canonical serialization, ask again:

- Does every source physical/view member have a downstream role?
- Does every used dimension/note/Nobi have a semantic owner?
- Is any source view silently unused?
- Are any two codes suspiciously sharing the same complete source bundle?
- Is any shared bend-edge dimension being used as an unrelated face/blank extent?
- Is any output unexpectedly simple compared with the source inventory?
- Is any VIEWS_ONLY status still carrying an untested source-supported candidate?
- Is any PASS merely self-consistent with an incomplete ledger?

Any affirmative result returns the job to source interpretation; it does not authorize guessing.

## 9. Non-generalization

This gate creates no drawing-specific geometry, no new Nobi formula, and no rule that a complex drawing must have a complex flat. It only requires evidence accounting, challenge/re-solve behavior and an executable source-view fallback when the flat truly remains unresolved.
<!-- END MODULE: references/HOLISTIC_ENGINEERING_CHALLENGE.md -->
