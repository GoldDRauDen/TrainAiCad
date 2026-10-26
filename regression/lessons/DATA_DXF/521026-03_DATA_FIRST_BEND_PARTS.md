# 521026-03 — DATA first for bent and flat parts from several views (SỬA TOOLS directive 2026-10-26)

## FACT
- 8 codes, customer DXF DATA for every drawing (47408 R, 47409 L, 50053, 53034-0). The bent codes (26-063194/97/200/201) were first built with `bend:` + hole chains typed from the PDF (30, 70, 360, 520, P75…) and only checked against DATA afterwards: four holes differed from DATA by 0.005 mm (DATA 430.005 / 210.005 / 290.005; the typed chain made them 430 / 210 / 290).
- `data:` + `data_faces` took ONE view, so web view + plan view (solid holes = top flange, dashed circles = the hidden flange `4-Ø7 反対側`) could not be harvested; the 半月 (D-cut) hole is an arc + chord, a two-vertex closed loop that the builder refused; a slot's `axis` collided with the chain selector; `P75*7` had to be written as eight holes; PowerShell-written census files (UTF-8 BOM) were rejected.
- Directive: DATA is extracted whole and assembled; only rule-routed changes (tap pilot, Laser R, called R/C, Nobi, customer instruction) may differ, each in the ledger.

## ROOT_CAUSE
`AI_RULE_GAP` in tools (one view per part, no coordinate references, no flat multi-view route, 2-vertex loops, key collision, BOM). `AI_WORKFLOW_ERROR` in the job: the PDF-chain route was chosen for convenience and DATA used as a check, which silently snapped DATA ordinates to PDF nominals (DATA_DXF.md §3).

## LESSON
`data_views` (bent or flat): one dxf_assemble result per view with its own proved transform, `datum` members for the edges the views are read from, face ranges / origins / outline corners as `<member>.<start|end|min|max>.<x|y>` references (`START`/`END` = the chain's free edges); hidden-line circles are holes of the opposite face only when a PDF note scopes them. Cut-outs may be arc-closed two-vertex loops and take `pdf_size`; `repeat` for equal pitch; `chain:` selects a chain; input files may carry a BOM. Executable: `tools/data_part.py`, `tools/dxf_assemble.py`, `tests/test_data_views.py`, `tests/test_data_dcut.py`, `tests/test_slot_on_face.py`, `tests/test_repeat_holes.py`, `tests/test_bom_inputs.py`.
