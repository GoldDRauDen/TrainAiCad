# 521030-10 26-064687/064688 — small chamfers at a notch mouth with no callout

**FACT.** Every drawn corner of the flanges and ear tabs carries `C2`; the two convex corners at the mouth of the 60 × 25 notch are drawn with the same small chamfer but have no callout.

**ROOT_CAUSE.** `CORNER_RC.md` §2 had two rules that both apply: a sibling drawn identically is CALLED, and a drawn chamfer with no callout is a FLAG row.

**LESSON.** Draw them as sibling C2 (group of their own, quantity 2) and put one FLAG line to confirm with the customer; do not auto-round them (the user confirmed the reasoning and sent the question to the customer).
