# 521019-13 — the KEGAKI face is the OUTER face

**Status:** USER APPROVED / PUSH 2026-10-19.

## FACT

Job 521019-13 (Meinan 851, codes 26-061305 … 26-061313): brackets A/A対称 + B with weld A-B. KEGAKI marks are drawn on host A at the B contact footprint. User rule: the face carrying the KEGAKI is the OUTER face. The delivered `521019-13_ALL.dxf` stays unchanged (no `dx`, geometry as drawn).

## APPROVED LESSON

1. The face that carries the KEGAKI weld marks is the outer face (extends `CAD_OUTPUT.md` rule 5d).
2. A part drawn with its KEGAKI on the drawn face is an outer-face drawing: `dx_label` false, geometry not flipped.
3. Does not change 対称 handling (rule 5e) or the KEGAKI-contact-footprint rule.

## REGRESSION_CASE

`tests/test_dx_inner_face_label.py::test_kegaki_face_is_outer_face_rule_text`.
