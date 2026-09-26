# TrainAiCad V4.7 canonical geometry → direct DXF

The serializer accepts **only already verified** per-part geometry. Read AI_ENTRYPOINT.md and current V4.7 portable skill (which retains ALL approved V4.6 engineering rules) first. The writer does not interpret PDFs and cannot establish unknown witness-line datums, independent Nobi, material correctness, full manufacturing containment or ground-truth equivalence.

## Input JSON

Job: `{"job_id":"JOB","parts":[PART_1, PART_2, ...]}`, ordered by the explicitly declared part/job-list order. Part requires unique ASCII `code`, `material`, positive `thickness_mm`, `status:"PASS"|"PREVIEW"`, `entities` and `checks` with eight keys: `contour_topology`, `datum`, `feature_count`, `unfold`, `containment`, `bend_domain`, `material_rules`, `slot_semantics`. Values are independently executed `PASS` or genuinely inapplicable `N/A`. For production, topology/datum/count/containment/material must PASS; absent evidence cannot be replaced with a synthetic assertion.

### Synthetic example (NOT a real approved drawing)

```json
{"job_id":"EXAMPLE","parts":[
  {"code":"PART001","material":"SS","thickness_mm":2.0,"status":"PASS",
   "checks":{"contour_topology":"PASS","datum":"PASS","feature_count":"PASS",
             "unfold":"N/A","containment":"PASS","bend_domain":"N/A",
             "material_rules":"PASS","slot_semantics":"N/A"},
   "entities":[
     {"type":"LWPOLYLINE","role":"outer","closed":true,
      "vertices":[[0,0,0],[60,0,0],[60,30,0],[0,30,0]]},
     {"type":"CIRCLE","role":"hole","center":[30,15],"radius":3.5}
   ]
  }
]}
```

Entity input:
- `LWPOLYLINE` outer/cutout/slot: closed vertices `[x,y,bulge]`, one true polyline per proven material boundary/cutout/slot. Omit repeated last vertex. Use true CCW exterior and CW interior arcs. Slot uses proof of `L_TOTAL` and `W` before deriving bulges.
- `CIRCLE` hole: center `[x,y]`, positive *radius*. Effective cut diameter is decided by V4.6 material/POINT/pilot rules upstream.
- `POINT`: `point:[x,y]`; ordinary `role:"ordinary_point"` ByLayer; PDF-scoped PIERCING+THROUGH HOLE `role:"through_piercing","color":3`.
- `LINE`: `start:[x,y],end:[x,y]`, `role:"bend"` needs `linetype:"DASHED"`, `role:"kegaki"` needs `color:1`. `ARC`: `center`, `radius`, `start_angle`, `end_angle` degrees. Green slit color 3 only with actual feature evidence.
- All entities Layer 0; ByLayer color 256 or omitted, otherwise only current approved Red 1, Green 3, Magenta 6. Magenta only for numeric-only preview. `TEXT` requires `role:"estimated_note","color":6` and is forbidden in production file.

Preview: `status:"PREVIEW", preview_reason:"numeric_only_known_topology", flags:["..."]`, some Magenta `role:"estimated"` geometry AND an adjacent Magenta TEXT. Unknown topology/feature/bend order/critical datum/material BLOCKS preview as well as production.

## Usage

```bash
python -m pip install -r requirements.txt
python tools/export_dxf.py job.json output/ --gap-mm 10
python -m pytest tests/ -q
```

Expected deliverables for approved parts: `JOB_CODE.dxf` for each code, `JOB_ALL.dxf` composite top-to-bottom with >=10 mm **layout-only** gap and `JOB_MANIFEST.json` with per-part counts, local bounding boxes and placement translations. Preview files have `_PREVIEW.dxf` / `_PREVIEW_ALL.dxf` and never enter production `_ALL.dxf`. Reopen each DXF after serialization; structural tests do not replace V4.6 upstream drawing-specific checks.
