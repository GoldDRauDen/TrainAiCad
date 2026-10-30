# 521030-03 26-064602 — a chamfer in the middle of a leg narrowed the bend line

FACT: L bracket t4.5, legs 170 / 290, width 480; the 170 leg has 45° chamfers from (100, 45) to (145, 0) and is full
width again from x 145 to the bend (zone at x ≈ 163–170). The spec build failed (`bend B1 end at 17.5: no straight
flange side edge`); the job merged two canonicals by hand (`merge_602.py`) to keep the bend line 0..480.

ROOT_CAUSE: `bend_corner.face_extent` sampled only the middle half of the face's OD span (x ≈ 41–125), all on the
chamfer; the full-width part next to the bend was never seen. Sampling the whole OD span is wrong too: the span
includes the bend zones, where the next face's edge already starts (slanted web, 521026-03).

LESSON: a single-axis part's face extent samples its flat part (OD span minus its bend zones) from 5 % to 95 %; a
two-axis part keeps the middle half (material next to the zone belongs to the other chain: HD flat step S = −2). Rebuilt
064602 equals the hand merge. Test `tests/test_face_extent_and_datum_ref.py`.
