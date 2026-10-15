# TrainAiCad Canonical Input Schema — V4.34 (compatible V4.31 reader)

New jobs use `"canonical_contract": "TrainAiCad-CANONICAL-V4.34"`. Previously approved `TrainAiCad-CANONICAL-V4.31` jobs remain valid without converting saved ledgers. All V4.31 source-member ownership, exact XDATA Entity IDs, cut-contour rules, closure and review-only filename rules remain mandatory.

## Materials, surface and grain
The grade belongs in `material` exactly as printed; normalize using `references/MATERIAL_ALIASES.yaml`, whose source rows are the user's Book1.xlsx `一覧表2026.07.30!A28:E48`. `HL` is a finish, not a new material family. Include optional part grain:
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
The example illustrates only X; real V4.34 PASS demands Y too, with its own proven axis path. `coordinate_mm` is signed RELATIVE to the physical datum node; `datum_coordinate_mm` is that datum's coordinate in the canonical part-local frame, and `datum_entity_id` identifies its canonical physical geometry. The validator adds these values before comparing against the feature's canonical `CIRCLE.center` or `POINT.point`. The feature entity must belong to the source member named by `feature_id`; a valid dimension chain linked to a different member is rejected. Readers must supply actual PDF crop/view identity for independent QA.

## Slot anchor witness
Each proved SLOT member requires a `slot_anchor_records` entry with `slot_id`, `entity_id`, `source_pdf_page`, `evidence_ref`, `witness_verified`, `anchor_point` (actual dimension target), `anchor_type` (SLOT_MIDPOINT/ARC_CENTER_1/ARC_CENTER_2/OUTER_TIP_1/OUTER_TIP_2), `axis_unit` (signed part-local vector), `width_mm`, `center_distance_mm`, `overall_length_mm`, `canonical_midpoint`. Code verifies the two semicircle bulges and compares their actual radii/centers and midpoint against the record; matching only a vertex-average midpoint is insufficient. Unknown anchor type => local FLAG/REVIEW, not a guessed center.

Every green `POINT` with role `through_piercing` needs a `piercing_authorizations` record linking `member_id`, `entity_id`, `source_pdf_page`, `evidence_ref`, and the source text in `stamp_text`. That same scoped stamp must contain English `PIERCING` and `THROUGH HOLE`; Japanese 通シ/貫通 or a thread-through callout does not qualify.

Every PASS part also checks each closed `CIRCLE` hole and closed slot/cutout against the proved outer material contour. The full boundary must fit inside the material region; a contained center alone is not enough.

## Bent-part source closure
If a PASS part has proved `BEND` source members, include `face_graph.faces` and `face_graph.bends`. Each face records `face_id`, `source_view`, `local_origin`, `local_axis_u`, `local_axis_v`, `contour_edge_ids`, `source_dimensions`, and `normal_orientation`. Each bend records `bend_id`, its `source_member_ids`, `face_A`/`face_B`, both physical shared-edge IDs, `edge_orientation`, `attachment_source_evidence`, `signed_angle_deg`, and `material_domain`. Every bend maps to exactly one `per_bend_witness_ledger` entry with matching `bend_id`/`source_group_id`, both `od_actual_mm` and `bend_pair_mm` values, `nobi_mm`, and `flat_mm`; the L3 guard independently checks arithmetic closure. A PASS with a missing or partial face graph or ledger is rejected.

## Export
Single PASS cut: rotate+translate the serialized cut copy only, preserving ARC radii/bulges converted to separate ARC, cut roles and XDATA provenance. Without HL orient bbox X>=Y; with **proved** HL align its physical grain to X. Composite remains in canonical source-readable orientation and may be requested alone with `--composite-only`. Never mix downstream orientation into source witness arithmetic. All downstream semantic and saved-file gates remain in force.

## Negative gates
- `WITNESS_REQUIRED_FEATURE_MISSING`, `WITNESS_GRAPH_MISSING`
- `WITNESS_ENDPOINT_UNPROVED`, `DIMENSION_CHAIN_CONFLICT`, `DIMENSION_CHAIN_MISMATCH`
- `SLOT_ANCHOR_RECORD_MISSING`, `SLOT_ANCHOR_MISMATCH`, `SLOT_CANONICAL_MIDPOINT_MISMATCH`
- `HL_DIRECTION_UNPROVED`, `PART_ORIENTATION_MISMATCH`

The validity of an alleged PDF witness requires actual source QA; it is not established by self-consistent JSON alone. Source reference DXFs may challenge but never create or modify a witness.
