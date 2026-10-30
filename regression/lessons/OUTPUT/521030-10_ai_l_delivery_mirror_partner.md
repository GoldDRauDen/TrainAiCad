# 521030-10 — AI_L delivery, urgent per-code flow, mirror partner, customer per code

**FACT.** The slip lists several customers in one job (639 / 824 / 795), so the job-level `customer_code` could not be set; the 対称 partner 26-064688 (本図の反対勝手) was a hand-made script mirror of 26-064687; PREVIEW parts had to be delivered too; the user wants every delivery in a folder `AI_L` of the job's input folder, per code for Express / とても急ぎます jobs (easy codes first, composite at the end), one composite otherwise, version +1 on change.

**ROOT_CAUSE.** `job.py deliver` copied the composite next to the sources only; `build_canonical` took one customer per job; a mirror was not a spec feature; delivery had no per-code path.

**LESSON.** `customer_code` per part (job level only when all files agree); `mirror_of: {code, axis}` builds the partner and runs `pair_consistency`; `estimate: true` paints a whole estimated blank Magenta (needs a flag); `job.py deliver` / `deliver-code CODE` write into `AI_L/` (`_v2` on changed entities, identical drawings are not repeated); `.work/<JOB>/make/` (ours) and `QA/` (DWG side). Urgency comes from the slip tag (`tools/slip.py`).
