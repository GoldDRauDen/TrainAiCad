# CLAUDE.md — TrainAiCad

Bộ rule sản xuất CAD kim loại tấm đã được người dùng duyệt: PDF / ảnh / DXF DATA của khách → canonical Geometry JSON → DXF đã kiểm tra lại. File này chỉ điều phối; rule nằm trong `rules/`, bảng tra trong `data/` (chỉ tool đọc).

## 1. Vai trò
| User nói | Làm | Đọc đầu tiên |
|---|---|---|
| `E2E`, `Đọc repo TrainAiCad làm E2E`, gửi PDF/ảnh/DXF DATA | Job CAD | `JOB_CARD.md` (đọc lại ở đầu mỗi bước L0–L3) |
| `QA`, `QA file này`, `QA ngược DXF này` | Kiểm tra ngược DXF có sẵn | `rules/QA_REVERSE.md` |
| Sửa rule / tool / test, bài học mới | Bảo trì repo | mục 3 |
| Việc trong `LuanAppTools/` | App Windows | `LuanAppTools/README.md`, `LuanAppTools/HANDOFF.md` |

## 2. Job CAD
Claude Code: skill `cad-e2e` / `cad-qa` (`.claude/skills/`) mở đúng cửa vào; hook trong `.claude/settings.json` tự in trạng thái job (`tools/job.py hook`) sau khi nén hoặc mở lại phiên.
`JOB_CARD.md` là cửa vào duy nhất: 12 điều cấm quên, các bước, lệnh tool. `python tools/resolve_rules.py census.json` cho biết cần đọc thẻ nào ở bước nào — đọc thật nội dung thẻ, không đọc cả repo. Một job E2E không được sửa repo.

## 3. Bảo trì rule (chỉ khi user nói rõ `DUYỆT` hoặc `PUSH`)
1. Bài học `FACT → ROOT_CAUSE → LESSON` ghi vào `regression/lessons/<THẺ>/<job>_<chủ đề>.md` (số job, tọa độ chỉ ở đây).
2. Sửa tại chỗ đúng **một** thẻ sở hữu chủ đề trong `rules/` (1–3 dòng, tiếng Anh; chỉ giữ nguyên từ khóa tiếng Nhật và câu FLAG tiếng Việt). Không thêm mục "Vx.y" hay tiêu đề có ngày; lịch sử nằm ở git. Thêm dòng vào mục `Lessons` của thẻ.
3. Thứ gì tính được bằng code thì viết vào tool (`tools/`) + test, không viết thành văn.
4. Thêm một test chạy được cho hành vi (`tests/`). Không ghim nguyên văn câu chữ của rule.
5. Giới hạn dung lượng ở `tests/test_rule_cards.py`; thiếu chỗ thì rút gọn, nâng giới hạn cần user duyệt.
6. Làm trên nhánh mới, mở PR, merge khi CI xanh. Không viết lại lịch sử git.

Kiểm tra trước khi merge (giống CI `.github/workflows/dxf-export-tests.yml`):
```sh
pip install -r requirements.txt
python -m pytest tests -q
python tools/benchmark_rule_routes.py
```

## 4. Bản đồ repo
```text
JOB_CARD.md      cửa vào job CAD
rules/           ROUTER.yaml, CENSUS.md (bảng từ khóa → thẻ) và các thẻ rule
data/            bảng Nobi, Laser R/lỗ, ren, vòi dẫn, vật liệu, khách hàng (tool đọc)
tools/           lookup, pdf_views, resolve_rules, run_job/build_canonical, export_canonical_dxf, guard…
examples/        spec mẫu cho tools/run_job.py
templates/       CAD_OUTPUT_TEMPLATE.dxf
regression/      bài học đã duyệt + fixture (không phải nguồn kích thước)
tests/           kiểm thử
LuanAppTools/    app Windows tùy chọn (chưa cập nhật theo cấu trúc V5)
```
