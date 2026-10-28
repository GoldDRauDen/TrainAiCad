# 521028-22 — KEGAKI only where the plates' own edges leave X or Y free; one union outline

Rule: `rules/KEGAKI.md` §3–4. Approved by the user (DUYỆT) after a sample audit. KH851, welded frame (6 plates) and bracket (3 plates).

## FACT
- Frame: bars A/B (368 x 32) cross bars C/D (325 x 32). D is flush with the bar end, B-bottom is flush with the C/D end; A, B-top and C sit mid-length.
- Approved marks: on A/B only C's position along the bar (x=66, 98); on C/D only A and B-top along the bar (y=121, 153, 242, 274). None for the flush contacts (D on the bars, B-bottom on C/D): the physical edge already locates them in X and Y.
- Bracket: rib C (t6) stands on B and against A. B carries A's inner face (x=43) and C's strip (y=22..28, centred); A carries C's strip from the foot up. Where the rib meets the A line the line is cut (0..22, 28..50): one union outline.
- 062113/062114 keep their inner line because the child is set back from the edge, so the edge does not locate it.

## ROOT_CAUSE
`AI_RULE_OVER_APPLICATION`: "KH851 every contact needs a KEGAKI" was applied per contact, not per axis, so flush contacts got a line (y=32) and the mid-length crossings were put on one plate only; the A line was drawn through the rib's end (a segment inside the union).

## LESSON
1. A mark is drawn only on an axis the two plates' physical edges leave free; edges that fix both X and Y need none.
2. Plates crossing mid-length each carry the other's position along itself.
3. A union outline has no segment inside the union.
