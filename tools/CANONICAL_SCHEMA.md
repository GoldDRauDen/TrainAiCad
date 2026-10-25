# Canonical job JSON (`"canonical_contract": "TrainAiCad-CANONICAL-V4.34"`)

Read only when a part cannot be written as a `tools/build_canonical.py` spec. `tools/export_canonical_dxf.py` is the only writer; every gate below runs there.

## Job, part and entities
Job: `{"canonical_contract": ..., "job_id": "<注番>", "customer_code": "851"|null, "parts": [...]}` in page-1 order (top to bottom in the composite). Part: slip `code`, `material` as printed, `thickness_mm`, `status: PASS|PREVIEW|VIEWS_ONLY|REVIEW`, `entities`, `source_groups`, `canonical_members`, eight `checks` (`contour_topology`, `datum`, `feature_count`, `unfold`, `containment`, `bend_domain`, `material_rules`, `slot_semantics`: PASS only when executed, else N/A/FLAGGED), optional `flags` (Vietnamese) and `dx_label` (true only when drawn from the inner face).
- **PASS:** one closed CCW `outer`, no flags. **PREVIEW:** `preview_reason: "numeric_only_known_topology"`, flags, a Magenta (6) estimated entity and an adjacent Magenta `TEXT` (`role: "estimated_note"`). **VIEWS_ONLY:** `preview_reason: "separate_source_views"`, flags, every non-TEXT entity carries a `view_id`, views ≥10 mm apart.
- Entities on Layer 0 with a unique `entity_id`: LWPOLYLINE `[[x,y,bulge],...]` (`outer` CCW; `cutout`/`slot` CW), CIRCLE (`hole`, effective cut radius), POINT (`ordinary_point` ByLayer; `through_piercing` Green 3), LINE/ARC (`kegaki` Red 1, `bend` DASHED pairs, Green `slit`/`relief`). Labels on `AI_META` are generated, never supplied. LWPOLYLINE is saved as LINE/ARC pieces (`<entity_id>:S0001`...).
- Each manufacturing callout is a `source_group` (`group_id`, `family`, `status` PROVED/FLAGGED/CANCELED, `qty`, `members`); each active member maps to exactly one `canonical_member` (`origin: SOURCE` + `source_member_id`, or `DERIVED_RULE` + `controlling_rule`) owning its `entity_ids`.

## Materials, surface and grain
The grade belongs in `material` exactly as printed; normalize using `data/material_aliases.yaml`, whose source rows are the user's Book1.xlsx `一覧表2026.07.30!A28:E48`. `HL` is a finish, not a new material family. Include optional part grain:
```json
"grain": {"is_hl": true, "direction_xy": [0,1], "evidence_ref": "PDF page 2/detail A/arrow"}
```
`direction_xy` is a signed 2-D vector in the SAME physical part-local canonical frame, not page X/Y. `evidence_ref` must identify what source establishes the direction. No proof means:
```json
"status":"REVIEW",
"review_reason":"HL_DIRECTION_UNPROVED",
"flags":["HL direction relative to the physical part not proved"],
"grain":{"is_hl":true,"direction_xy":null,"evidence_ref":null}
```
No estimated manufacturing curves are added for this attribute-only REVIEW. This status never emits an individual CUT DXF and causes `*_ALL_REVIEW_ONLY.dxf`.

## Typed dimension graph
All proved source HOLE/SLOT members must be declared in `witness_required_feature_ids`. Each member requires a target trace for **both X and Y** in `feature_witness_graph`:
```json
"witness_required_feature_ids":["M_HOLE_1"],
"feature_witness_graph":{
  "nodes":{"O":"OUTER_EDGE","HC":"HOLE_CENTER"},
  "edges":[
    {"from_node":"O","to_node":"HC","axis":"X","value_mm":10,"kind":"LOCAL",
     "proof":{"pdf_page":2,"evidence_ref":"p2/roi-10","endpoint_verified":true,
              "from_type":"OUTER_EDGE","to_type":"HOLE_CENTER"}}
  ],
  "targets":[
    {"feature_id":"M_HOLE_1","datum_node":"O","feature_node":"HC",
     "axis":"X","coordinate_mm":10,"datum_coordinate_mm":0,
     "datum_entity_id":"E_OUTER","entity_id":"E_HOLE_1"}
  ]
}
```
The example illustrates only X; a PASS demands Y too, with its own proven axis path. `coordinate_mm` is signed RELATIVE to the physical datum node; `datum_coordinate_mm` is that datum's coordinate in the canonical part-local frame, and `datum_entity_id` identifies its canonical physical geometry. The validator adds these values before comparing against the feature's canonical `CIRCLE.center` or `POINT.point`. The feature entity must belong to the source member named by `feature_id`; a valid dimension chain linked to a different member is rejected. Readers must supply actual PDF crop/view identity for independent QA.

## Slot anchor witness
Each proved SLOT member requires a `slot_anchor_records` entry with `slot_id`, `entity_id`, `source_pdf_page`, `evidence_ref`, `witness_verified`, `anchor_point` (actual dimension target), `anchor_type` (SLOT_MIDPOINT/ARC_CENTER_1/ARC_CENTER_2/OUTER_TIP_1/OUTER_TIP_2), `axis_unit` (signed part-local vector), `width_mm`, `center_distance_mm`, `overall_length_mm`, `canonical_midpoint`. Code verifies the two semicircle bulges and compares their actual radii/centers and midpoint against the record; matching only a vertex-average midpoint is insufficient. Unknown anchor type => local FLAG/REVIEW, not a guessed center.

Every green `POINT` with role `through_piercing` needs a `piercing_authorizations` record linking `member_id`, `entity_id`, `source_pdf_page`, `evidence_ref`, and the source text in `stamp_text`. That same scoped stamp must contain English `PIERCING` and `THROUGH HOLE`; Japanese 通シ/貫通 or a thread-through callout does not qualify.

Every PASS part also checks each closed `CIRCLE` hole and closed slot/cutout against the proved outer material contour. The full boundary must fit inside the material region; a contained center alone is not enough.

## Bent-part source closure
If a PASS part has proved `BEND` source members, include `face_graph.faces` and `face_graph.bends`. Each face records `face_id`, `source_view`, `local_origin`, `local_axis_u`, `local_axis_v`, `contour_edge_ids`, `source_dimensions`, and `normal_orientation`. Each bend records `bend_id`, its `source_member_ids`, `face_A`/`face_B`, both physical shared-edge IDs, `edge_orientation`, `attachment_source_evidence`, `signed_angle_deg`, and `material_domain`. Every bend maps to exactly one `per_bend_witness_ledger` entry with matching `bend_id`/`source_group_id`, both `od_actual_mm` and `bend_pair_mm` values, `nobi_mm`, and `flat_mm`; the L3 guard independently checks arithmetic closure. A PASS with a missing or partial face graph or ledger is rejected.

## Bend-end junction evidence

For applicable bend ends, declare per-part `source_bend_end_site_ids` and matching `bend_end_junctions` (one record per site), plus `bend_end_source_edges` keyed by edge ID. The reader must discover all sites and inspect their PDF/DATA witnesses; the guard measures declared evidence, not unprovided drawings. An explicitly empty inventory has no applicable sites.

- Each source edge: `physical_edge_id`, common `frame_id`, `type:"LINE"`, `start:[x,y]`, `end:[x,y]`, and `proof:{source_pdf_page:...,evidence_ref:...,endpoint_verified:true}`; DATA may use `source_ref` instead of `source_pdf_page`. Coordinates are source-grounded in that physical frame, not distances between Nobi lines.
- Each proved site: `site_id`, `status:"PROVED"`, two existing `bend_ids`, `frame_id`, `flush_edge_id`, `web_edge_id`, unit `positive_axis`, `positive_axis_evidence_ref`, `included_angle_deg`, `S_mm`, `mechanism:"BEND_END_OFFSET_90"`, `decision:"NO_RELIEF"|"SLIT"`, `relief_member_ids:[]`. S is remeasured from both edges; numeric witness tolerance is1e-7mm, not a manufacturing step threshold. A positive S needs NO_RELIEF and no scoped relief geometry; nonpositive S needs SLIT with physical canonical owners.
- A generic required slit supplies `slit_construction:{actual_edge_id,side_edge_id,bend_id,inward_hint,side_void_normal,web_void_normal,evidence_ref}`. The edge IDs name proved `CANONICAL_FLAT` edges in `bend_end_source_edges`; evidence closes their source-to-flat mapping and inward/void sides. The actual edge retains the physical identity of `web_edge_id`; the two finite edges meet at the slit base. The controlled bend's canonical material-domain line proves bend direction. The guard rebuilds the existing connected slit rule from these witnesses, material and thickness, then checks the actual three Green LINE/ARC/LINE entities, t+0.2 actual-edge depth, R0.5 and lead. Missing or mismatched construction blocks save.
- `relief_member_ids` names proved canonical relief members with matching mechanism and site ownership; ordinary holes/contours cannot stand in for relief. Members and geometry carry `bend_end_site_id`, Green LINE/ARC relief roles (`slit`, `relief`, `bend_relief`); automatic relief, including non90 and derived relief-role geometry, cannot omit its inventory/owner. This prevents an empty decision list hiding a linked addition. Missing/duplicate inventory sites, wrong source frames, directions, S or owners block export. Explicit source slit features outside bend-end scope retain their existing source-group contract.
- A separately controlled site uses `decision:"SEPARATE_RULE"`, its mechanism and `special_rule_evidence_ref`. `OPPOSITE_FOLD_R_T` may draw its R = t relief hole inside the outer contour (ByLayer arc, R0.5 junctions, no Green entity): the relief member then owns the outer LWPOLYLINE (`entity_ids:[outer]`) and declares `outline_relief:{center,radius}`; the guard checks radius = t and that the polyline really contains that arc. `OPPOSITE_FOLD_R_T` additionally needs `intersection_edge_ids`: two proven finite source bend edges in the same physical frame, each with its owning `bend_id`, whose segments actually intersect. (`CROSSING_BEND` was removed 2026-10-20: a same-direction corner is an ordinary `BEND_END_OFFSET_90` site.) `BOXMET` needs a four-flange face-graph star whose central face owns both controlled bends. `CUSTOM_SOURCE_SLIT` needs a proved `SLIT_RELIEF` source group (`source_group_id`) owning its relief members. `NON_90_RELIEF` needs its non90 angle and `angle_evidence_ref`; the90-degree S decision is not applied to it. Each mechanism retains its own routed manufacturing gates.
- An unresolved site stays in the inventory with `status:"FLAGGED"`, `decision:"FLAGGED"` and no proved relief geometry; it cannot enter a PASS part or erase another proved face/feature. Use the existing local preview policy rather than fabricating a slit or downgrading a defensible whole flat to VIEWS_ONLY.

## Export
Single PASS cut: rotate+translate the serialized cut copy only, preserving ARC radii/bulges converted to separate ARC, cut roles and XDATA provenance. Without HL orient bbox X>=Y; with **proved** HL align its physical grain to X. Composite remains in canonical source-readable orientation and is the default sole output, without JSON deliverables. Individual PASS cuts require explicit user request (`--individual-dxf`). Never mix downstream orientation into source witness arithmetic. All downstream semantic and saved-file gates remain in force.

## Negative gates
- `WITNESS_REQUIRED_FEATURE_MISSING`, `WITNESS_GRAPH_MISSING`
- `WITNESS_ENDPOINT_UNPROVED`, `DIMENSION_CHAIN_CONFLICT`, `DIMENSION_CHAIN_MISMATCH`
- `SLOT_ANCHOR_RECORD_MISSING`, `SLOT_ANCHOR_MISMATCH`, `SLOT_CANONICAL_MIDPOINT_MISMATCH`
- `HL_DIRECTION_UNPROVED`, `PART_ORIENTATION_MISMATCH`

The validity of an alleged PDF witness requires actual source QA; it is not established by self-consistent JSON alone. Source reference DXFs may challenge but never create or modify a witness.

## Same-direction corner witness and corner inventory

A `BEND_END_OFFSET_90` site at a same-direction box corner may carry `corner_retreat`:

```json
"corner_retreat": {"flange_ids": ["F4", "F5"], "depth_mm": {"F4": 30, "F5": 30},
                   "bend_edge_length_mm": {"F4": 265, "F5": 83.2},
                   "site_flange_id": "F5", "retreated_flange_id": "F5", "evidence_ref": "..."}
```

`tools/bend_end_guard.py` requires: depth-first choice (`BEND_END_CORNER_RETREAT_KHUYET_T` when the deeper flange retreats by mistake, depth tolerance 0.1 mm), `S_mm = -t` at the retreated flange's end and `S_mm = +t` at the other end (`BEND_END_CORNER_RETREAT_S_MISMATCH`), and evidence (`BEND_END_CORNER_RETREAT_UNPROVED`).

`corner_inventory` (see `tools/corner_guard.py`) is required as soon as any `MATERIAL_AUTO_R` member exists, and census-checked against every sharp convex corner `<= 90` degrees of an outer LWPOLYLINE:

```json
"corner_inventory": [{"corner_id": "C1", "point": [0, 0], "drawn_shape": "SHARP|ROUNDED|CHAMFERED|UNKNOWN",
  "decision": "CALLED|AUTO_R|FLAG|SHARP", "canonical_member_id": "...", "evidence_ref": "...",
  "no_auto_r_reason": "SHARP decision only"}]
```

A corner DRAWN rounded/chamfered without a callout must be `FLAG` (never `AUTO_R`); `AUTO_R` needs `drawn_shape: SHARP`. `python tools/ledger.py job.json` prints one Vietnamese row per corner and per bend end.

Census closure: `tools/bend_end_guard.py` also derives, from the part's own `face_graph` and bend lines, every pair of perpendicular bends that share a face and whose bend zones touch (distance <= max Nobi); each such pair must own a declared `bend_end_junctions` site (`BEND_END_CORNER_SITE_MISSING`, or `BEND_END_SITE_CENSUS_MISMATCH` for a PASS part with no inventory at all). `python tools/ledger.py job.json --draft` prints a `corner_inventory` skeleton (all FLAG / UNKNOWN) so no corner is skipped.

