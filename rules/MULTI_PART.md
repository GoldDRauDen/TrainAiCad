# MULTI_PART — part identity and assembly datums (multi_code_or_assembly ≠ NO)

Triggers: several barcodes/codes on one view, constituent marks ①②, A/B/C assembly views, weld relations, one DATA cluster for several codes, a feature with no local dimension but an installation view.

## 1. Identity graph
`BARCODE/CODE ⟷ PART/CONSTITUENT ⟷ SOURCE VIEW(S) ⟷ DATA CLUSTER(S) ⟷ material/t ⟷ assembly/weld relation`, each edge with evidence. Paper proximity never merges or assigns. `PART_IDENTITY_COLLISION` when two codes get the same complete bundle, a constituent is unowned, a view is assigned only by nearness, material/t conflict, or a welded child disappears inside an assembly view. Shared assembly views are allowed only with an explicit shared role. Unresolved ownership → views under REVIEW with a FLAG; never the same geometry duplicated under two codes. Other proved parts stay executable.

## 2. Assembly datum closure (before FLAG/VIEWS_ONLY for a feature with no local coordinate)
1. Identity first: target part, host face, mating/support parts, view ids.
2. One proved assembly frame with both signed axes; each used dimension with its real witness endpoints, type and host part. Join paths only through the same physical node.
3. Each relation `target_axis − source_axis = signed_offset` with evidence; a zero contact offset needs positive contact evidence.
4. Solve with `python tools/assembly_datum_solver.py graph.json <datum_node> <feature_node> --axis X|Y`; check alternate paths/cycles. Contradicted/disconnected → keep the FLAG and ask for the missing physical relation.
5. Transform the result to the feature's face, then to the flat (`BEND.md` §5); QA in the same frame.
6. Declare candidates in `assembly_indirect_candidates` + `assembly_datum_traces`; the L3 guard recomputes them.
Standalone flat parts never get a fictitious assembly.

## 3. Stacked plates
Printed dimensions are assembled dimensions. When B sits on A: offset A's contour by tA as an unsaved reference; B's bend line/flange derive from it; B's edge facing A retreats tA (061137 on 061122).

## Lessons
`regression/lessons/MULTI_PART/` — 521013-04 059636 (assembly graph fixture `regression/fixtures/521013-04_059636_assembly_graph.json`), 521007-07 (identity collision), 521019-05 (stacked).
