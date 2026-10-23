# CLAUDE.md — TrainAiCad (Claude Code)

Repo này là bộ rule sản xuất CAD kim loại tấm đã được người dùng duyệt: PDF / ảnh / DXF DATA của khách → canonical Geometry JSON → DXF đã kiểm tra lại. File này **chỉ là con trỏ điều phối** cho Claude, giống `AGENTS.md`: không chứa công thức, không ghim số release. Nếu có mâu thuẫn, rule trong repo hiện tại thắng (trừ chỉ dẫn trực tiếp của user).

## 1. Xác định vai trò trước khi làm

| User nói | Vai trò | Đọc đầu tiên |
|---|---|---|
| `E2E`, `Đọc repo TrainAiCad làm E2E`, gửi PDF/ảnh/DXF DATA | Kỹ sư làm job CAD | `SKILL.md` → `JOB_CARD.md` → `AI_BOOTSTRAP.md` → `AI_ENTRYPOINT.md` |
| `QA`, `QA file này`, `QA ngược DXF này` | Kiểm tra ngược DXF đã có | `QA_ENTRYPOINT.md` (chỉ khi user gọi rõ) |
| Sửa rule / tool / test, bài học mới | Bảo trì repo | `docs/RULE_LESSON_INTAKE.md`, mục 4 bên dưới |
| Việc trong `LuanAppTools/` | Phát triển app Windows | `LuanAppTools/README.md`, `LuanAppTools/HANDOFF.md` |

Ý định không rõ giữa tạo DXF và QA thì nói ra trước, không tự đổi vai.

## 2. Job CAD (E2E)

Thứ tự thẩm quyền: `USER TASK → AI_BOOTSTRAP.md → AI_ENTRYPOINT.md → skills/lispcad/router/FEATURE_CENSUS.md → skills/lispcad/router/ROUTER.yaml → module được route → tool canonical/export`.

- Ghim một commit (`git rev-parse HEAD`) cho cả job; không đổi rule giữa chừng.
- **Đọc lại `JOB_CARD.md` ở đầu mỗi bước L0/L1/L2/L3** — không làm theo trí nhớ. 12 điều cấm quên nằm ở đó.
- Tự nhìn bản vẽ bằng `tools/pdf_views.py` (render có lưới, `text --dims`, crop 600 dpi). OCR, tên file, bbox, số entity không phải bằng chứng.
- Mọi con số vào sổ kích thước (2 đầu đường gióng, datum, loại kích thước) trước khi tính.
- Census mỗi họ tính năng: `YES` / `NO` / `UNKNOWN`. **UNKNOWN ≠ NO**; `python tools/resolve_rules.py census.json` cho danh sách file rule cần đọc — phải đọc thật nội dung, không chỉ liệt kê đường dẫn.
- Bảng tra (Nobi, Laser R, lỗ POINT/CIRCLE, lỗ mồi ren, ID→OD, trải phôi) chỉ lấy từ `python tools/lookup.py`, không tra bằng mắt. Thiếu Nobi → `SPLIT_FLANGE_10MM` + FLAG.
- Chi tiết uốn: khóa cạnh gắn uốn, `OD_actual`, chiều dài cạnh uốn từ cạnh chung thật trước khi trải (`skills/lispcad/modes/BEND_UNFOLD.md` và các file `mode_routes`).
- Làm từng mã, lưu kết quả từng mã ra file (census.json, ledger, job.json); mã lỗi không bắt làm lại mã đã đúng. Cặp mã đối xứng (対称): `python tools/pair_consistency.py`.
- Hình học đi theo `canonical JSON → python tools/export_canonical_dxf.py job.json OUT/ → mở lại DXF đã lưu`. **Không bao giờ ghi DXF trực tiếp bằng ezdxf.**
- Luôn vẽ đủ mọi mã: chỗ chưa chắc vẽ Magenta + `FLAG:` tiếng Việt, trạng thái REVIEW (`references/REVIEW_PREVIEW_POLICY.md`); không dừng job để hỏi, không bịa kích thước, không lấy tọa độ từ file mẫu.
- PASS chỉ cho kiểm tra đã thực sự chạy. Đầu ra mặc định: một file `<JOB>_ALL.dxf` hoặc `<JOB>_ALL_REVIEW_ONLY.dxf` (`skills/lispcad/core/CAD_OUTPUT.md` §1). DXF riêng chỉ khi có `--individual-dxf`.
- Ghi chú trong DXF bằng tiếng Việt có dấu; mã job, entity ID, tên file, chữ Nhật trong bản vẽ giữ nguyên (`AGENTS.md` §6).
- Báo cáo theo `CAD_OUTPUT.md` §11: bảng từng mã, mọi FLAG, câu hỏi cho khách ở cuối; kèm tổng thời gian làm (ngắn gọn).

Không đọc làm nguồn sản xuất: `skills/lispcad/portable/`, `skills/lispcad/versions/`, `docs/history/`, và `regression/` (chỉ là bằng chứng QA, không phải nguồn kích thước). MCP chỉ để nghiên cứu, không nằm trong pipeline.

Nếu không đọc được repo, không chạy được tool hoặc không mở được nguồn: báo đúng bước bị chặn, giữ phần đã chứng minh, không giả vờ đã làm.

## 3. Giới hạn sửa repo

- Một job E2E **không** cho phép sửa repo. Bài học mới chỉ đề xuất trong báo cáo.
- Chỉ sửa / commit / push rule khi user nói rõ `DUYỆT` hoặc `PUSH`; làm trên nhánh mới và mở PR, merge khi mọi check xanh.
- Không xóa hay viết lại lịch sử git: commit `173c098` phải luôn còn trên remote (test đọc snapshot từ đó).

## 4. Bảo trì rule (sau khi đã được duyệt)

Theo `docs/RULE_LESSON_INTAKE.md`:
1. `FACT → ROOT_CAUSE → LESSON` ghi vào `regression/qa/<job>_<topic>_APPROVED.md` (số job, tọa độ chỉ ở đây).
2. Sửa tại chỗ đúng **một** file rule sở hữu chủ đề (1–3 dòng). Không thêm mục "Vx.y supplement" hay tiêu đề có ngày/phiên bản; bản cũ chuyển sang `docs/RULE_HISTORY.md`.
3. Chọn chỗ hẹp nhất: chỉ vài job → route có điều kiện trong `skills/lispcad/router/ROUTER.yaml`; mọi job → file core có sẵn. Không làm phình `AI_ENTRYPOINT.md`.
4. Thêm một test chạy được cho hành vi đó.
5. Giới hạn dung lượng ở `tests/test_rule_load_budget.py`: thiếu chỗ thì rút gọn rule; nâng budget cần user duyệt.
6. File gốc (`AGENTS.md`, `AI_BOOTSTRAP.md`, file này) không ghi số release `V4.xx`; release chỉ nằm trong `AI_ENTRYPOINT.md` và Router.

Kiểm tra trước khi merge (giống CI `.github/workflows/dxf-export-tests.yml`):

```sh
pip install -r requirements.txt
python -m pytest tests -q
python tools/audit_rule_coverage.py
python tools/build_gate_index.py
python tools/build_rule_index.py --output /tmp/TRAINAICAD_RAG_INDEX.yaml
python tools/build_rule_bundle.py --output /tmp/TRAINAICAD_E2E_RULEPACK.md
python tools/benchmark_rule_routes.py
python tools/audit_rule_duplicates.py
for f in regression/tools/check_*.py; do python "$f" || break; done
```

## 5. LuanAppTools

App Windows điều phối job (Python backend + React/Vite frontend). Chỉ sửa trong `LuanAppTools/`; không đụng rule sản xuất.

```sh
pip install -r LuanAppTools/requirements-dev.txt
python -m pytest LuanAppTools/tests -q
cd LuanAppTools/frontend && npm ci && npm test && npm run build
```

Chạy thật trên Windows: `LuanAppTools\start.cmd`. Mọi DXF app sinh ra vẫn cần người kiểm tra.

## 6. Bản đồ repo

```text
SKILL.md, JOB_CARD.md, AI_BOOTSTRAP.md, AI_ENTRYPOINT.md   cửa vào + thẩm quyền
skills/lispcad/router/     FEATURE_CENSUS.md, ROUTER.yaml (RULE_COVERAGE.yaml chỉ cho audit)
skills/lispcad/core/       rule luôn bật: đọc bản vẽ, datum, validation, CAD output
skills/lispcad/modes/      phẳng / uốn-trải
skills/lispcad/features/   lỗ, ren, slot, KEGAKI, slit, rib, vát/bo...
skills/lispcad/topology/   L / U / bậc / nhiều mặt
references/                vật liệu, Nobi, lead, nguồn DATA, face graph...
tools/                     lookup, pdf_views, resolve_rules, export_canonical_dxf, guard
templates/                 CAD_OUTPUT_TEMPLATE.dxf
regression/, tests/        bằng chứng đã duyệt + kiểm thử (không phải nguồn kích thước)
docs/                      chỉ mục gate, lịch sử rule, quy trình bài học
LuanAppTools/              app Windows tùy chọn
```
