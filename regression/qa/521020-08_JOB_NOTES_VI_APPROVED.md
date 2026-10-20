# 521020-08 — notes inside the combined DXF are Vietnamese

**Status:** USER APPROVED / PUSH 2026-10-20 (Project TrainAiCad). Corrects the first reading of this lesson (PR #54 made *chat/job notes* Vietnamese; the user meant the notes inside the DXF).

## FACT -> ROOT_CAUSE -> LESSON

| Topic | FACT | ROOT_CAUSE | LESSON |
|---|---|---|---|
| DXF note language | The 521020-08 combined DXF carried English notes (`26-061846 FLAG: ...`, the Magenta estimate note, `REVIEW ONLY - NO CUT ...`), while `templates/CAD_OUTPUT_TEMPLATE.dxf` shows its FLAG sample as "Ghi bằng tiếng việt". | The rule only existed as the template sample; no written rule or test pinned it, and the exporter banner was English. | Every note written into the DXF is Vietnamese. Owner: `AGENTS.md` §6; exporter constant `REVIEW_BANNER`; FLAG line wording in `CAD_OUTPUT.md` §7. Identifiers stay verbatim. |
