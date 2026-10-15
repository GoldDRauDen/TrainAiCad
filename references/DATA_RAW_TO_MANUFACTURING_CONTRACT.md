# Customer DATA — preservation, manufacturing and bidirectional QA

**Scope:** every `PDF_DATA_RAW` job. Approved preservation, census and manufacturing contracts remain one source of authority; this consolidation changes no formula or threshold. See `SOURCE_DATA_CLASSIFICATION.md` for source-mode selection and the independent job-family 646 missing-DATA gate.

## Authority and sequence

Customer DATA is the geometry/provenance authority; PDF controls code, material, thickness, view/face meaning, witnesses, scale, revision/handwriting, Nobi and manufacturing semantics. Never redraw existing DATA from PDF dimensions, bbox or screenshots.

`RAW_DATA_SNAPSHOT -> PHYSICAL_DATA_BASELINE -> PDF semantic lock -> SAME_PARAMETER_GATE -> MANUFACTURING_CHANGE_LEDGER -> MANUFACTURING_CANONICAL -> UNTOUCHED_DATA_INVARIANCE_CHECK -> source reprojection -> DXF save/read-back`.

## Complete harvest, classification and physical baseline

Before tolerance, Nobi, thread-pilot, R/C or other adjustment, harvest **every relevant DATA primitive/view/face**, freeze its geometry/provenance in immutable `RAW_DATA_SNAPSHOT`, and assign a semantic role:

- `PHYSICAL_CUT_OR_FACE_EDGE`
- `PHYSICAL_HOLE_SLOT_OR_FEATURE`
- `BEND_SUPPORT`
- `THICKNESS_REPRESENTATION`
- `HIDDEN_OR_PROJECTION_ONLY`
- `DIMENSION_HELPER_OR_CONSTRUCTION`
- `DUPLICATE_COINCIDENT`
- another explicitly proved physical/nonphysical role.

`RAW_DATA_SNAPSHOT_COMPLETE` requires complete source accounting before manufacturing. `100% DATA` does not require serializing title blocks, text/dimensions or drawing-only helpers. Exclude them only **after** classification; an exclusion must not hide unaccounted physical geometry. Paired side/section edges showing thickness may prove faces/witnesses but are not CUT without independent blank-boundary evidence.

`PHYSICAL_DATA_BASELINE_COMPLETE` requires source-supported physical CUT/face edges, holes/slots/features and bend support, retaining original coordinates/curves/host ownership before adjustment. Presence in DATA proves provenance, not manufacturing meaning.

Prove physical scale per PDF page/view, never one scale for every supplied file. A proved 1:2 view uses x2. Retain local face/view geometry and assemble only by proved translation, rotation, reflection or uniform source-scale conversion. Nobi changes placement between preserved faces; it is not permission to reconstruct the faces. Never force scale or infer a mirror to close numbers.

## Same physical parameter before change

First select the numeric customer-code policy from `CUSTOMER_CAD_RULES.yaml` under `CAD_CUSTOMER_POLICY.md`. No code or unlisted code uses general rules, without automatic REVIEW. `DATA_NO_DIM_COMPARE` bypasses only generic numeric PDF/DATA discrepancies; `PDF_PRIORITY` and `CONFIRM_CONFLICT` remain scoped to the conflicting physical parameter. Hole identity/count/M/Ø/location, topology, revisions, witnesses, membership, invariance and saved read-back remain mandatory. Numeric customer-code 646 is independent of job-family 646.

Run `SAME_PARAMETER_GATE` only after correct code/view/feature/datum/unit mapping, comparing the **same physical parameter**:

- General: `Delta < 0.1 mm` passes; `Delta >= 0.1 mm` gives `DATA_PDF_DIM_DIFF`. Exactly 0.1 flags.
- Explicit numeric KH433: `Delta < 1.0 mm` passes if topology/identity/count are unchanged; `Delta >= 1.0 mm` flags.

A passing gate never authorizes snapping to PDF nominal. Without a controlling manufacturing rule, retain the physical DATA geometry unchanged. A failed gate blocks automatic change of that local parameter: preserve DATA, FLAG, and continue unrelated proved geometry until higher-authority source/user evidence resolves the conflict. Different physical parameters are never compared, particularly raw pilot/pre-hole versus thread nominal.

## Rule-scoped manufacturing canonicalization

After complete source harvest and same-parameter closure, apply only active routed rules with proved scope: mid-tolerance/limit conversion, M* pilot conversion, explicit R/C, material Laser R, Nobi/bend placement or another approved manufacturing rule. Each changed physical member needs a local `MANUFACTURING_CHANGE_LEDGER` record:

`source_members, host_face, source_geometry_or_value, same_parameter_gate_status, controlling_rule, changed_scope, canonical_geometry_or_value, serialized_members`.

One changed corner/edge/diameter does not authorize refitting neighboring geometry.

### DATA_TAP_NOMINAL_VALIDATION

For **every proved M***, lock thread identity, host face, quantity/centers and DATA cluster. Classify an independently identifiable concentric nominal ring as `THREAD_NOMINAL_REFERENCE`, and raw pilot as `THREAD_PREHOLE_SOURCE`. Apply the same-parameter/customer gate to the nominal reference against source M<n>, never to the pilot against n. Do not invent an absent reference ring or choose its role by size/proximity.

The nominal reference is non-cut; keep raw pre-hole provenance and serialize exactly one effective pilot under `HOLES_TAPS.md` and the applicable coarse/explicit-fine thread table, unless the PDF controls another effective diameter. M6 + nominal Ø6 + raw Ø5.1 becomes one Ø5.0 pilot; source quantities/centers/face ownership stay unchanged. A nominal-reference plus pilot as two CUTs, an uncontrolled raw pilot or an unaccepted nominal delta is FAIL.

### DATA_AUTO_R_CANONICALIZATION

A sharp DATA vertex does not suppress required material Laser R. At each otherwise uncalled eligible corner, apply `MATERIAL_RULES.md` with source R/C precedence and its specific SS t>=19 outer-perimeter/conflict scope. Retain source-corner provenance and exact local tangent replacement; do not refit adjoining curves. Record the changed entity as `MANUFACTURING_CANONICALIZED` with controlling rule and serialized members. An unlogged extra arc/hole is FAIL.

## Untouched invariance and representation equivalence

`UNTOUCHED_DATA_INVARIANCE_CHECK`: every physical member outside all approved `changed_scope` regions must remain physically identical after canonicalization **and actual saved-DXF read-back**, reversing only proved source/layout transforms. Endpoints, centers, radii, sweeps, straight/curved boundaries and feature locations must match within CAD numerical/serialization precision.

Any unapproved drift is `UNTOUCHED_DATA_INVARIANCE_FAIL`. The PDF/DATA threshold is **not a redraw tolerance**. Rounding/snapping, PDF redraw, bbox reconstruction, arbitrary tangent rebuilding or analytic simplification of unchanged curves fails.

LINE/ARC/CIRCLE and exact LWPOLYLINE/bulge encodings may be equivalent when physical curves and topology are identical. Prefer retaining primitives when simpler. Raw entity count and AutoCAD `OVERKILL` do not certify physical geometry.

## Independent completeness and fold-back

`SOURCE_PHYSICAL_TO_CANONICAL`: every active physical source family/curve has host/transform, retained/canonicalized/canceled status, quantity/value and canonical/serialized presence. No missing source geometry.

`CANONICAL_TO_SOURCE_PHYSICAL`: every manufacturing output primitive maps to physical source evidence or an explicitly logged canonicalization. No extra manufacturing geometry. Reprojecting only the AI-selected subset cannot satisfy either-direction completeness.

Close each family as `family, value/size, quantity, host_face, source members, canonical members, serialized members, cancellation/canonicalization status`. Count semantic operations separately from raw entities. Audit CUT, HOLE/SLOT, BEND, KEGAKI and RIB independently.

Each bend retains `PER_BEND_WITNESS_LEDGER`: bend ID, ordered faces, witnesses, ID/OD semantics, thickness terms/owners, Nobi, fold sign, material domain, pair coordinates and fold-back status. `THICKNESS_SINGLE_USE` means each thickness contribution has one owned use; a ±t residual diagnoses ownership and is never an automatic shift. Execute FACE_GRAPH, attachment/domain closure and fold-back under the routed bend rules.

For reference/direct audit only, normalize exact coincident/reversed duplicates for physical count comparisons; report `REFERENCE_ANOMALY` without changing the sample. A duplicated reference entity is not an extra manufacturing feature.

## PASS boundary

Require `RAW_DATA_SNAPSHOT_COMPLETE`, `PHYSICAL_DATA_BASELINE_COMPLETE`, `SAME_PARAMETER_GATE_CLOSED`, `MANUFACTURING_CHANGE_LEDGER_COMPLETE`, `UNTOUCHED_DATA_INVARIANCE_PASS`, `SOURCE_PHYSICAL_TO_CANONICAL_PASS`, `CANONICAL_TO_SOURCE_PHYSICAL_PASS`, `SOURCE_REPROJECTION_PASS` and `SAVED_DXF_READBACK_PASS`, with family/face/bend closure when applicable. Bbox, valid DXF, OVERKILL or sample resemblance cannot repair missing source members, unlogged changes or drift.

Approved numeric examples/assertions remain in `regression/qa/521001-20_V4_25_APPROVED.md`; census/bidirectional evidence in `regression/qa/521001-03_V4_23_APPROVED.md`; tap/auto-R evidence in `regression/qa/521001-13_V4_24_APPROVED.md`. They are not dimensions for a new job.
