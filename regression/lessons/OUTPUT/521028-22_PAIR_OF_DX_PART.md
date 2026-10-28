# 521028-22 — a 対称 partner of a `dx` part keeps the sibling's coordinates; dx follows the mark face

Rule: `rules/OUTPUT.md` §6. Approved by the user (DUYỆT) after a sample audit.

## FACT
- Bracket plate A (two M8, asymmetric across the width) is drawn from the face opposite the one that carries the rib mark (the rib is hidden-line in that view), so it gets `dx`.
- Its 対称 partner is the same coordinates with no `dx`: the user only translates the sibling. Mirroring an inner-face drawing and viewing it from the other face cancel.
- Frame: C/D lie on top of A/B and their marks sit on the underside, so C/D are viewed from the inner face (`dx`); A/B carry the mark on the viewed face (no `dx`).
- Layer order came from the line types at the crossings (vertical bars' edges run unbroken, the horizontal bars' edges are interrupted); the edge view under third angle agrees. Reading the edge view alone gave the opposite order.
- Symmetric bars (holes on the centre line): any mirror axis gives a valid 対称 partner.

## ROOT_CAUSE
`AI_SOURCE_SEMANTICS_ERROR`: the face question (`OUTPUT.md` §6) was skipped and the viewed face was assumed outer; the partner was then mirrored although its sibling should have carried `dx`. Layer order was read from one view without checking the crossing line types.

## LESSON
1. View face is not the mark face → `dx_label`.
2. At a crossing the continuous outline is the upper part; confirm with the edge view.
3. 対称 partner: mirrored sibling (either axis); if the sibling carries `dx`, the partner keeps its coordinates, translated only, no `dx`.
