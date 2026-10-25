# 521015-04 — `dx` label = INNER-face drawing; 対称 parts are drawn mirrored directly

**Status:** USER APPROVED / PUSH 2026-10-15.

## FACT

Job 521015-04 (Aikoku 646, codes 26-059934 … 26-059939):

- `059934` (C1-01) and `059935` (C1-02) are the same L-angle family. The C1-02 PDF section view (vertical leg on the right) and its lower view (20 / 37.6 dimensions from the bottom edge) are mirrored/flipped relative to C1-01 (vertical leg on the left, dimensions from the top edge). C1-02 is therefore drawn from the INNER face.
- AI delivered `059935` without `dx` (assumed outer face) and `059937` (対称 of `059936`) with `dx_label: true`.
- User correction: `dx` is written when the part is drawn from the inner face; a 対称 part is drawn as the directly mirrored geometry of its sibling, without writing `dx`. Mirror axis for the 795 mm plate: the axis along its length (x' = W - x).

## ROOT_CAUSE

`AI_SOURCE_SEMANTICS_ERROR`: outer face was assumed instead of compared between sibling views, and `dx` was conflated with "symmetric part" (the old wording of `CAD_OUTPUT.md` rule 7 said `dx` marks a file symmetric to the PDF view).

## APPROVED LESSON (scoped, not one-drawing-only)

1. `dx_label: true` iff the part is drawn from its INNER face (`CAD_OUTPUT.md` rule 5d/7). Geometry stays as drawn.
2. Decide the face by comparing section/lower views of sibling codes; do not default to the outer face.
3. 対称 / symmetric parts: reuse the sibling geometry, draw the mirror image directly (`CAD_OUTPUT.md` rule 5e), `dx_label: false`.

## REGRESSION_CASE

`tests/test_dx_inner_face_label.py` (executable): exactly one `dx` label for a part with `dx_label: true`, none for the mirrored-pair part, and the rule text in `CAD_OUTPUT.md` / `DXF_INPUT_SCHEMA.md`.
