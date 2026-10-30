---
name: cad-e2e
description: TrainAiCad sheet-metal CAD job — PDF / scan / customer DXF DATA → verified DXF. Use when the user says E2E, "làm E2E", "Đọc repo TrainAiCad làm E2E", or sends a drawing (図面, 作業No, slip, CAD依頼書) to be drawn as DXF.
---

1. Read `JOB_CARD.md` in full and follow it; re-read it at the start of every stage (L0–L3).
2. L0: `python tools/job.py init <JOB> --source <files>` (codes, customer per code, material, urgency from the slip `<JOB>_依頼.xlsx`; `--codes` only to pick some). Work files go to `.work/<JOB>/make/`; a job with DWGs also `python tools/job.py qa` (`QA/`).
3. Per code read only the cards `job.py census` lists for the current stage. Before a slow tool chain say what you are doing.
4. Delivery goes to `<input folder>/AI_L/` (never overwrites: `_v2`, `_v3`…); `python tools/job.py status` prints the mode from the slip: urgent tag (Express / とても急ぎます) = `job.py order`, then `job.py deliver-code <code>` as soon as each code is reopened (PREVIEW too), composite at the end; default = `job.py deliver` once.
5. After the job is delivered, follow-ups (a sample, a check, a correction) are answered unprompted in four parts: Xác nhận / Phản biện / Câu hỏi (only what is unclear) / Đề xuất cải thiện (repo fixes as proposals); no new DXF unless asked.
