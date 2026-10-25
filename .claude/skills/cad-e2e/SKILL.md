---
name: cad-e2e
description: TrainAiCad sheet-metal CAD job — PDF / scan / customer DXF DATA → verified DXF. Use when the user says E2E, "làm E2E", "Đọc repo TrainAiCad làm E2E", or sends a drawing (図面, 作業No, slip, CAD依頼書) to be drawn as DXF.
---

1. Read `JOB_CARD.md` in full and follow it; re-read it at the start of every stage (L0–L3).
2. L0: `python tools/job.py init <JOB> --codes <slip work numbers> --source <files> [--customer <JOB STATISTICS code>]`.
3. Per code: read `rules/READ_SOURCE.md` + `rules/CENSUS.md`, fill `census_<code>.json`, run `python tools/job.py census <code>`, then read only the cards it lists for the current stage.
4. Write the ledger/spec of each code to its file as you go and record progress with `python tools/job.py set`. After a compaction, `python tools/job.py status` tells you where you are.
5. Tables and arithmetic come from `tools/`; never write DXF with ezdxf yourself; a job never edits the repo.
