---
name: cad-e2e
description: TrainAiCad sheet-metal CAD job — PDF / scan / customer DXF DATA → verified DXF. Use when the user says E2E, "làm E2E", "Đọc repo TrainAiCad làm E2E", or sends a drawing (図面, 作業No, slip, CAD依頼書) to be drawn as DXF.
---

1. Read `JOB_CARD.md` in full and follow it; re-read it at the start of every stage (L0–L3).
2. L0: `python tools/job.py init <JOB> --source <files>` (codes, customer per code, material, urgency come from the slip `<JOB>_依頼.xlsx`; `--codes` only to pick some). Work files go to `.work/<JOB>/make/`; a job with DWGs also `python tools/job.py qa` (`QA/`).
3. Per code: read `rules/READ_SOURCE.md` + `rules/CENSUS.md`, set the census with `python tools/job.py census <code> --set HOLE=YES:<evidence> --rest NO ...`, then read only the cards it lists for the current stage.
4. Write the ledger/spec of each code to its file as you go and record progress with `python tools/job.py set`. After a compaction, `python tools/job.py status` tells you where you are.
5. Tables and arithmetic come from `tools/`; never write DXF with ezdxf yourself; a job never edits the repo.
6. Delivery goes to `<input folder>/AI_L/` (never overwrites: `_v2`, `_v3`…). Urgent slip tag (Express / とても急ぎます): as soon as a code is drawn and reopened, `python tools/job.py deliver-code <code>` (easy codes first, PREVIEW too), the composite at the end. Default tag: `python tools/job.py deliver` once. Easy codes first: `python tools/job.py order`. Before a slow tool chain say what you are doing. After the job is delivered, follow-ups (a sample, a check) are confirm / rebut / propose repo fixes only: no new DXF unless asked.
