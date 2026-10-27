# 521027-26 — struck locating-pin callout, milled recess, same-name material

FACT: 26-063858 / 26-063859 drew four Ø8 holes although their callout `2-φ8 (ピッチ公差±0.02)` was struck out by hand; the user
ruled they are locating pins (chốt định vị) done after the laser, and a struck callout of that type cancels every hole of it.
The thin rectangles around the 2x4-M8 groups (R5 代, `赤丸部位は弊社にて加工`, `2mm削る加工は不要`) are milled recesses, not cuts.
SK85 was not recognised although the table has SK (group SS): the resolver only matched aliases of 3+ characters.

ROOT_CAUSE: strike-through was treated as ambiguous for the hole family; `material_resolver` had no rule for a 2-letter alias
followed by digits.

LESSON: cancel the whole struck locating-pin type, not only the leader's pair; same-name material grades are never asked.
`resolve_material("SK85")` -> SS, A33 (`tests/test_data_fidelity.py`).
