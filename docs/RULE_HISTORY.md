# Rule History (archived, not routed)

Verbatim archive of rule blocks removed from routed files. The Router does NOT load this file, and it is NOT production authority. It keeps provenance only. Restoring any block into a routed file requires explicit user approval (`DUYỆT`), per `AGENTS.md`.

## Archived from skills/lispcad/core/DRAWING_READING.md

## V4.7 DXF-first output mode (approved 2026-09-26)
After executing ALL approved V4.6 drawing/material rules and real geometric verification, build ONE checked canonical part-local model. The same coordinates generate direct individual and combined DXFs and optional request-only Lisp; never independently recalculate for either. See `CAD_OUTPUT.md`. Critical missing source evidence blocks production; numeric-only uncertainty on proved topology can be Magenta non-production PREVIEW only on request. No V4.6 engineering lesson is changed by this output migration.

## Archived from skills/lispcad/core/VALIDATION.md

## Historical V4.7 saved-DXF dual-export audit (explicit-request legacy only)
Before declaring the canonical model PASS, actually execute every preceding V4.6 PDF-semantic, source/material, true contour topology, datum, feature-count, containment and bend-domain check. A serializer's structural validations cannot prove these engineering facts.
Under explicit-request **legacy V4.7 dual export** only, for EACH individual and combined DXF reopen the SAVED file and audit: real mm DXF, Layer 0 only, correct V4.6 entity/linetype/color/POINT/CIRCLE and bulges, geometry/count against the canonical source, no extra code-label TEXT. Combined drawing MUST contain exactly one translated copy of each production-PASS part, in explicitly declared code order descending Y, separated by at least 10 mm layout-only bbox clearance; record/check all offsets in the manifest. Keep numeric-only user-requested Magenta _PREVIEW outside production _ALL.dxf and do not mark preview PASS. Unknown topology/type/bend/material/datum blocks export. Count the `055958` Green LINE+ARC+LINE as ONE slit operation, not three.
