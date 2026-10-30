# 521030-10 — which DWG is the checked sample, and what the colours mean

**FACT.** Job folder 30-10-2026 holds one DWG per job named `<JOB>-<creator>` (tronghieu, Phat, LUAN, Quyen, Toan) or without a name (07, 13); 05 and 10 also hold a checked copy (`…-Toan -T.dwg`, `…-LUAN - hcheck.dwg`). The slip columns 作成担当 / チェック担当 are empty. In the checked sample (and its DXF export) red dimension text = FLAG for the customer, red outline circles = KEGAKI (Ø48 tube mark, 2 × Ø10 bar ends), yellow outline = guide lines, blue/green text = bend dimensions highlighted for reading only.

**ROOT_CAUSE.** Roles and colours lived in the user's head; a DWG could not be read at all (ezdxf reads DXF only).

**LESSON.** `tools/dwg_roles.py`: tokens after the job number are creator then checker (t = Thanh, h = Hiếu, `hcheck`), no token = Thanh, `.bak/.dwl` ignored; checker present = SAMPLE, else QA target. `tools/dwg_to_dxf.py` converts a COPY with AutoCAD `accoreconsole` (`_.DXFOUT V 2018`, no /readonly; with Git Bash set `MSYS_NO_PATHCONV=1`). Unknown text colour in a sample: ask FLAG or highlight. The checked sample is a reference for outline only; its pending FLAGs stay `CUSTOMER_CONFIRMATION_PENDING`.
