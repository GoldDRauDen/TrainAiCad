# 521030-16 — callouts struck out with a circled ② (26-064814)

FACT: the GIKEN SYSTEC drawing D780-2_28_002 (customer 828, t6 L-bracket) has `2-M8 トオシ`, `8-Ø7 トオシ`, `8-Ø2.6 THRU`,
`4-Ø9 トオシ` and `4-C1` struck through by hand, each with a circled ② beside it. `4-Ø16` and `4-C1` sit side by side: only the `4-C1` text is struck.
The job drew the 22 struck holes (2 M8, 8 Ø7, 4 Ø9, 8 Ø2.6), read ② as a quantity, put a FLAG on the part (PREVIEW) and asked
the customer about KEGAKI although the drawing had no KEGAKI cue.

ROOT_CAUSE: strike-through was treated as ambiguous; ② was read as a count. The user's ruling: a struck callout is cancelled
(no machining), the circled ② is the signature that makes it certain; the cancelled holes need not be drawn, only noted.
No cue (ケガキ note, reversed-e above the barcode, customer weld rule) means KEGAKI = NO and no customer question.

LESSON: a struck callout cancels all its members, nothing is drawn, the report notes it, no FLAG and the code can PASS; a struck
`4-C1` leaves `4-Ø16`. Spec key `cancelled:` (`tools/BUILD_CANONICAL_SPEC.md`), test `tests/test_cancelled_callouts.py`.
