# 521023-09 — FLAG only the entity that differs (DUYỆT 2026-10-26)

## FACT
- 26-062647/062648: PDF `2-M8` vs 4 tapped holes in DATA, and the upper two slots at 17.74 / 127.73 from the edge against the PDF chain 17/110. Both were reported through part-level `flags:`, which painted the WHOLE outline Magenta, added an "Ước lượng - kiểm tra bản vẽ" note and a `[FLAG]` suffix to the code label; the reader could not see which holes or slots were in question.
- No tool compared a slot or hole POSITION with a PDF dimension (only OD, width, Ø, R, C were gated), so the 0.7 mm slot offset was found by the user, not by the build.

## ROOT_CAUSE
`AI_RULE_GAP` in tools: the only flag target was the part; Magenta was applied to `outer`; the exporter wrote note TEXT and grey/magenta labels. `AI_WORKFLOW_ERROR`: an ambiguous M8 count / slot chain was flagged at part level instead of isolating the members (`OUTPUT.md` §5, `DATUM.md` §6 "isolate the unknown").

## LESSON
A FLAG belongs to an entity: `flag:` on a hole / slot / cut-out (4 M8 rings → the 4 holes), a corner `FLAG` with R/C (only that arc or chamfer piece, `flag_segments`), and the DATA/PDF gates `pdf_d`, `pdf_size`, `pdf_R/C` and the new `pdf_pos` (position against the PDF chain, same parameter and datum) flag their own member. The outline stays ByLayer; no note TEXT; every `AI_META` text is white: the code only, `FLAG:` lines at the right, `dx` / `HL` at the left. A flag with nothing to point at (overall size, closure snap) keeps the whole outline Magenta. Executable: `tools/export_dxf.py`, `tools/build_canonical.py`, `tools/data_part.py`, `tests/test_local_flags.py`.
