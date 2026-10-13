# DATA_GAP_FLAG_POLICY — nonblocking RAW DXF source-open evidence

## Scope and production decision

Applies only to source mode PDF_DATA_RAW and **only after actual source/PDF
manufacturing validation**. The raw DATA geometry may have an open edge or
a gap while the proved manufacturing result for a code is still PASS.

Do not create connecting CUT lines because a source gap exists.
Do not set LWPOLYLINE.closed=true solely to hide a missing DATA edge.
Do not treat small PDF/DATA numeric differences as permission to move,
snap or join DATA endpoints.

A raw open gap is a *source observation* and is not necessarily a defect in
the manufacturing CUT topology. Keep it visible without silently removing
it or making it a production cut.

## Classification: three exclusive proven cases

- NONCUT_SOURCE_OPEN: raw open endpoints belong only to drawing/projection/
  construction/thickness-display geometry and do not represent missing
  physical manufacturing CUT. Every raw source entity is still harvested.
- INTENTIONAL_OPEN_CUT: a source-proved process SLIT/RELIEF is intentionally
  open, with explicit manufacturing instruction; standalone CUT correctly
  retains its proved LINE/ARC and does not invent a closed shape.
- PROVED_MANUFACTURING_CLOSURE: the DATA boundary is physically open but
  a specific approved source witness or manufacturing rule *independently*
  proves the required production contour. Persist a PROVED scoped entry
  in manufacturing_change_ledger and a PDF/source closure witness.
  A simple closed=true assertion is never sufficient.

Unknown gap ownership, unproved closure, missing CUT segment, mismatch in
physical source/canonical projection, or lack of manufactured contour proof
is **BLOCKING REVIEW** under existing flags and no individual PASS CUT.

## Canonical JSON, warning vs blocking FLAG

The independent per-code ledger is data_gap_flags. This is a **nonblocking
SOURCE DATA FLAG**, separate from existing part.flags (blocking manufacturing
uncertainty). It does NOT set part.status to PREVIEW/VIEWS_ONLY.

For a nonblocking source gap, a proved PASS part must already have no
blocking flags and explicit PASS checks for topology, datums, feature counts,
containment and materials. The job must set source_mode=PDF_DATA_RAW.

Each data_gap_flags record requires:

- gap_id; classification; source_view_id; source_entity_ids
- source_endpoints: actual two RAW DATA endpoint coordinates in millimeters
- source_evidence; disposition_evidence
- raw_data_snapshot_ref; physical_data_baseline_ref; bidirectional_qa_ref
- source_to_part_transform: [a,b,c,d,tx,ty], source-backed rigid/reflected/
  uniform-scale transform from source view to part-local flat coordinates
- transform_evidence
- canonical_entity_ids (empty only for NONCUT_SOURCE_OPEN)

NONCUT_SOURCE_OPEN additionally requires source_role one of
DRAWING_ONLY, PROJECTION_ONLY, THICKNESS_REPRESENTATION, CONSTRUCTION,
and an empty canonical_entity_ids list.

INTENTIONAL_OPEN_CUT requires a manufactured LINE/ARC with role slit or
relief and manufacturing_instruction that proves the open cut.

PROVED_MANUFACTURING_CLOSURE requires canonical_entity_ids identifying
proved *closed* outer/cutout/slot contours and both closure_witness and
manufacturing_change_ledger_ref. The referenced manufactured change must
exist in the part's manufacturing_change_ledger with change_id,
status=PROVED, controlling_rule and its canonical_entity_ids.

Never use these fields to replace independent source physical-curve
extraction or PDF/source reprojection. The validation tool cannot inspect
the source PDF independently. A Reader that fabricates source_evidence
is still a process failure.

## Output

- All codes PASS, including nonblocking data_gap_flags: <JOB>_ALL.dxf.
- Mixed PASS + REVIEW: <JOB>_ALL_REVIEW_ONLY.dxf, as before.
- Composite: print each gap flag and mark its source-proved part-local
  location as Magenta on AI_META (non-cut, non-plot). The flag includes
  gap_id, code, and measured raw open gap. No CUT bridge is inserted.
- Each PASS code: parts_dxf/<CODE>.dxf remains clean LINE/ARC/CIRCLE only.
  No flag circle/text/preview source geometry is exported as CUT.
- Every code: geometry_json/<CODE>.json retains data_gap_flags,
  source_mode and customer_code for later local audit.
- Source/CUT geometry entities and XDATA read-back remain invariant.
  Nonblocking source gap flags do not erase blocking warnings.

The canonical geometric data model may retain proved bulged LWPOLYLINE, but
both the standalone PASS and the combined final DXF are emitted as physical
LINE/ARC/CIRCLE primitives. The combined exporter decomposes all Layer-0
polylines without faceting, preserves individual colors/linetypes, and audits
source entity -> serialized segment 1:N provenance. A source DATA gap warning
on AI_META must never create or alter manufactured CUT.
