# DATA_DXF — customer DXF DATA (source class PDF_DATA_RAW; also any DXF used as evidence)

DATA = physical geometry and provenance. PDF = code, material, t, view/face meaning, witnesses, scale, revisions, Nobi, manufacturing semantics. Never redraw existing DATA from PDF numbers, bbox or screenshots.

## 1. Decode before anything
Every POLYLINE/LWPOLYLINE segment uses its START vertex bulge: `b = 0` LINE; `b ≠ 0` ARC (`θ = 4·atan b`, `R = c(1+b²)/(4|b|)`); closed polylines include the last→first segment; INSERT/blocks via their transform. ezdxf `virtual_entities()` gives exact pieces. Equal X/Y vertex offsets with a bulge are an R, not a C (`|b| = 0.41421356` = quarter circle). Unsupported curve → UNKNOWN/FLAG, never flattened. Unaccounted bulge → no PASS. `python tools/dxf_census.py data.dxf [--out decoded.json]` decodes everything and lists parts top-to-bottom with holes by Ø, arc radii and colours.

Customer DATA is usually a whole drawing sheet (frame, title block, several views, iso, exploded dimensions/text; KH646 is always a CATIA sheet). `python tools/dxf_digest.py data.dxf --out digest.json [--png v.png]` gives every primitive an id and one home (view / `B_*` bucket, nothing dropped); layer, colour and linetype are hints only. Pick views by id, prove scale/rotation/mirror per view, then `python tools/dxf_assemble.py digest.json plan.json --out assembled.json`: it copies the numbers, changes only layer/colour/linetype, demands a reason for every excluded piece, and re-checks the result against the source both ways. Never retype DATA coordinates.

## 2. Harvest and classify (RAW_DATA_SNAPSHOT, frozen)
Every relevant primitive gets a role: `PHYSICAL_CUT_OR_FACE_EDGE`, `PHYSICAL_HOLE_SLOT_OR_FEATURE`, `BEND_SUPPORT`, `THICKNESS_REPRESENTATION`, `HIDDEN_OR_PROJECTION_ONLY`, `DIMENSION_HELPER_OR_CONSTRUCTION`, `DUPLICATE_COINCIDENT`. Thickness side lines prove faces, never CUT. Exclude title blocks/text/helpers only after classification. Prove the scale per page/view (a 1:2 view → ×2); assemble faces only by proved translation/rotation/reflection/uniform scale; Nobi moves faces, never rebuilds them.

## 3. Same parameter, then change
- Compare a PDF value with DATA only for the same physical parameter. General: `Δ < 0.1` pass, `Δ ≥ 0.1` → `DATA_PDF_DIM_DIFF` (exactly 0.1 flags). KH433: 1.0 instead. A pass never snaps DATA to the PDF nominal; a fail preserves DATA + FLAG.
- Customer policies (from `data/customers.yaml`): `DATA_NO_DIM_COMPARE` skips only the numeric gate; `PDF_PRIORITY` lets the PDF control the conflicting parameter; `CONFIRM_CONFLICT` → local REVIEW. None waives hole count/type/M/Ø/position, topology, revisions or read-back.
- Allowed changes only by a routed rule with proved scope (mid-tolerance, M pilot, explicit R/C, Laser R, Nobi placement); each in a `MANUFACTURING_CHANGE_LEDGER` row: source members, host face, old value, gate status, rule, changed scope, new geometry.
- Taps: nominal ring is non-cut, one pilot (`HOLE_TAP.md` §1). Sharp DATA corner + eligible Laser R → local tangent arc (`CORNER_RC.md` §3).

## 4. Invariance and completeness
- `UNTOUCHED_DATA_INVARIANCE_CHECK`: everything outside the changed scopes is physically identical after canonical AND saved-DXF read-back (endpoints, centres, radii, sweeps). The 0.1 threshold is not a redraw tolerance. LINE/ARC vs exact bulged polyline is equivalent; entity counts and OVERKILL prove nothing.
- Both directions: every active physical source curve/family is in canonical (or logged/cancelled), and every manufacturing output maps to DATA or a logged change. Family closure: value, qty, host, source/canonical/serialized members.
- VIEWS_ONLY only after every DATA view/face/primitive was harvested and every face-graph candidate tried.
- Reference/audit only: normalise exact duplicate entities for counting, report `REFERENCE_ANOMALY`.

## Lessons
`regression/lessons/DATA_DXF/` — 520930-03 (preservation), 521001-03 (census, bidirectional), 521001-13 (DATA tap / auto R), 521001-19 (bulge), 521001-20 (DATA first), 520928-20, 520930-10, 520702-08 (digest/assemble).
