# Bend / multi-face datum mapping (loaded for BEND and MULTI_FACE)

Moved verbatim from `DATUM_DIMENSION.md` (section numbers kept). Source-frame lock §4.2.9 and symmetry precedence §4.2.7.2 stay in `DATUM_DIMENSION.md`.

#### 4.2.2a V4.16 Face-First Dimension Ownership

Before unfolding any multi-face part, reconstruct each visible formed face as its own contour/feature model. Tag every used dimension by actual witness endpoints and assign it to one semantic graph: face contour, hole/slot center-or-size, bend/face transition, or another proved local feature.

- A hole/slot-center dimension never becomes a contour or bend-axis dimension merely because it is parallel, nearby, or numerically convenient.
- Finish each face's contour and feature graph from that face's own witnesses before joining adjacent faces and deducting Nobi.
- Projection alignment may identify the owning face but does not transfer dimension ownership across faces.

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

#### 4.2.8 Bend Sequence / Face Order Is Non-Commutative
The total flat length equation may be numerically unchanged when two flange lengths are swapped, but **bend positions, feature transforms, and material topology are not**. Therefore:

- Determine the ordered face sequence from the visible formed topology, bend callouts, section/detail views, and proven witness-line connectivity before calculating bend-line coordinates.
- Do not validate bend order merely because `sum(OD) - sum(Nobi)` matches the overall blank length.
- Double bend lines MUST be positioned from the ordered sequence in Section 4.7 and MUST exist only over material regions that actually cross that bend. For U-shaped, legged, stepped, or cut-away parts, split/trim bend lines around voids; never draw a bend line continuously through empty space.
- If two face orders remain equally plausible after explicit trace exhaustion, STOP and ask the user. Magenta is not permission to choose an arbitrary bend order.
