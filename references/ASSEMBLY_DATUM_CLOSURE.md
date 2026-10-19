# Cross-part assembly datum closure (loaded when multi_code_or_assembly is not NO)

Moved verbatim from `DATUM_DIMENSION.md` §4.2.2b.

#### 4.2.2b Cross-part Assembly Datum Closure (approved 2026-10-13)

When a hole, slot, locating mark or other manufacturing feature has NO directly proved local coordinate but the PDF provides an assembly/installation view and related part dimensions, **try a source-backed ASSEMBLY_DATUM_GRAPH before numeric FLAG or VIEWS_ONLY**. Do not claim the dimension is missing merely because the child part's own flat lacks a coordinate.

1. Establish the PART_IDENTITY_GRAPH first: physical part code, host face, the related mating/support parts and actual view IDs. A shared assembly view is not a separate manufactured part.
2. Choose one physically proved assembly reference frame and independently prove both signed X and Y directions. For each used dimension record its *actual* witness endpoints, type (baseline/chain/local/ordinate/contact/assembly offset), sign, host-part identity and printed/approved evidence. Only join dimension paths through the **same physical node**, not paper proximity, shared numbers, nominal symmetry or sample/reference DXF.
3. Represent each relation as `target_axis - source_axis = signed_offset_mm`, with a source witness for the corresponding edge. A contact offset of zero requires positive evidence of the mating contact; mere proximity or a presumed flush fit is not a constraint. Across oriented/bent faces, prove the transform and physical attachment edge before adding its signed offset.
4. Solve the connected graph to express `feature - target_part_datum` as a signed sum; independently check every available alternate dimension path/cycle and the assembly fit. A contradicted or disconnected graph is **not** a 50%-confidence coordinate: retain the local FLAG and ask about the *missing physical relationship*.
5. Transform the assembly result to the feature's own physical face frame, then to the final flat through the routed face/bend rules. Run fold-back and hole count/diameter/host QA in the same frame. A mathematically correct assembly offset does not alone prove an unfolded feature location.
6. Retain feature ID, source dimension witnesses, source node and target node, `frame_id`, axis, signed formula, result, applicable face transform and any unresolved degrees of freedom. A later customer/sample DXF can challenge a solution but must not become its missing witness.

`tools/assembly_datum_solver.py` provides a deterministic, source-proof-gated graph solver for the arithmetic and cycle consistency. The L3 holistic guard independently recomputes any **declared** `assembly_indirect_candidates` from corresponding `assembly_datum_traces`, and fails incorrect/unattempted proof for production. **Source census must declare the candidates**; the tool cannot discover them by itself.

**Stacked parts:** printed dimensions are assembled dimensions. Only when the source/user states that part B sits on part A: offset A's relevant contour inward by tA as an UNSAVED reference line; B's bend line and flange size derive from that line; B's edge facing A retreats by tA so the assembled height stays as printed. Never write the reference line to the DXF.

This procedure is conditional: do not create a fictitious assembly for standalone flat parts or override a genuinely explicit source feature dimension. The fixture `regression/datum/521013-04_059636_assembly_graph.json` tests this class of error only; its offsets are not general rules.
