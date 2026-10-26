# 521026-03 — slanted web edge at a bend end (SỬA TOOLS directive 2026-10-26)

## FACT
- `26-063194` / `26-063197` (SPHCP t3.2, U 30/120/30, Nobi 5.5): the web's bottom edge rises 48.4 over 103.7 starting exactly on the flange-side bend line of B1 (S = 0). Corner between the flange side edge and the slanted edge: 115.02°.
- `build_canonical` refused it (`no straight web edge from the corner`), so the part was built with a straight edge and the outline patched by hand; the slit lead stayed the straight-edge one (P offset 3 | 3.99 from the two edges).
- User: the T+0.2 slit is right; the lead end lies on the bisector (57.51°) of the 115.02° corner, each edge offset by LeadVal = 3 (square edge 3 correct, slanted edge 3.99 wrong).

## ROOT_CAUSE
`AI_RULE_GAP` in tools: `bend_corner.end_step` and `bend_end_guard._measured_step` only knew a web edge parallel to the bend; `slit_entities` fixed the web normal to the bend axis. `AI_RULE_MISAPPLICATION` in the job: the rule (SLIT_RELIEF §3, `lead_end_by_offset`: both edges offset by LeadVal) was not re-applied after the hand patch.

## LESSON
A straight web edge leaving B toward the web is the same bend-end corner: S is measured at B (side edge ∩ web edge), the slit is T+0.2−S, the lead end is the intersection of the two edges each offset LeadVal perpendicular to itself (SS t3.2: P = (479.3, 22.5895) from B = (476.3, 24.5), 3 | 3). Executable: `tools/bend_corner.py`, `tools/bend_end_guard.py`, `tests/test_bend_corner_slanted_web.py`.
