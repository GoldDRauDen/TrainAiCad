# HANDOFF — giảm token / tăng tốc LuanAppTools (17/10/2026)

Nhánh: `codex/local-tool-token-speed-20261017` (tách từ `main` tại `13c5669`). **Chưa merge, chưa có PR.** Đọc `AGENTS.md`, `AI_BOOTSTRAP.md` trước. Quy tắc cứng: không sửa rule sản xuất và không push/merge nếu người dùng chưa nói `DUYỆT`/`PUSH`; không đưa file mẫu (`*_mau.dxf`) cho AI giải; không đoán kích thước/PASS.

## Mục tiêu người dùng
Chạy tool ở local, giảm token, tăng tốc, tăng độ chính xác khi xuất DXF. Người dùng chạy job thật qua `LuanAppTools` (Claude CLI, gói Pro nên **hạn mức rất nhạy**).

## Đã làm (5 commit trên nhánh)
| Commit | Nội dung |
| --- | --- |
| `602bf59` | `.gitattributes` ép LF (ngân sách byte của rule bị vượt khi checkout CRLF; `*.dxf -text`). Ghi rulepack/RAG index bằng đúng byte UTF-8. `cut_dxf` trong manifest dùng `/` (`as_posix`). Test đọc file bằng UTF-8. Thêm DATA nén: `compact_entity` (bỏ thuộc tính DXF vô nghĩa, làm tròn 1e-6, giữ `color`/`linetype`/giải mã đường cong) và nhóm DATA do host tính (`data_groups`, bbox chồng nhau → cùng nhóm). `data_groups` trong intake được host bung thành danh sách entity. |
| `b1e3f5e` | Intake chỉ gửi **tóm tắt nhóm** (`Evidence.intake_view`: bbox, đếm theo loại, lớp, đường cong không hỗ trợ, lỗ/cung chính, ghi chú). Chi tiết entity lấy bằng tool `data_group` (≤300 entity/lần) hoặc ở bước giải từng mã. DATA 521016-23: 1,62 MB raw → 19 KB ở intake. |
| `c689906` | Host tự sở hữu các thông tin AI chỉ lặp lại: `complete_code_links` (view/note/data/page ids của mã suy ra từ `codes` của từng mục), `pin_source_mode` (mọi mã lấy chế độ nguồn của job), gói trong `normalize_inventory`. Lý do: lần chạy thật đầu fail intake vì AI ghi thiếu trang p2 và ghi `PDF_ONLY` cho mã không có DATA. |
| `72f6282` | Mỗi mã (và intake) một phiên hội thoại riêng thay vì một phiên cho cả job; prompt giải bảo AI gọi tool `validate` trước khi trả lời; dừng job sau 2 mã liên tiếp hết cả hai lượt (`MAX_CONSECUTIVE_FAILED_CODES`, lỗi `no_progress`, chạy tiếp không đếm lại mã đã fail); chờ hạn mức giãn dần 60s→30 phút (`usage_retry_delay`). |
| (commit này) | File ghi chú này. |

Kiểm thử: `473 passed, 1 deselected` (`python -m pytest tests LuanAppTools/tests -q --deselect LuanAppTools/tests/test_runners.py::test_cancel_terminates_provider_process`). Test bị loại **fail y hệt trên `main`** (kiểm tra kết thúc tiến trình trên Windows), không do nhánh này. `LuanAppTools/tests/test_e2e.py` đã từng timeout một lần khi máy tải nặng, chạy riêng thì qua. Chưa chạy frontend (`npm test`) và 14 script `regression/tools/check_*` (không đụng rule sản xuất).

## Bằng chứng từ job thật 521016-23 (PDF 9 trang + DATA DXF 2553 entity, 37 nhóm)
Nguồn: `D:\luan\data-train\521016-23\` (thư mục phải tên đúng `521016-23`; tên có dấu cách như `521016-23 hom nay` bị pipeline từ chối — xem "Việc chưa làm"). File mẫu đối chiếu nằm ngoài thư mục job: `D:\luan\data-train\521016-23_mau.dxf` — **chưa được mở, không dùng để tạo**; chỉ so sau khi có kết quả.
- Intake (sau khi sửa) **thành công**: 8 mã (`26-060792`, `26-060793`, `26-060794`, `26-060806`, `26-060787`, `26-060788`, `26-060767`, `26-060772`), gán đủ 37 nhóm DATA bằng `data_groups`. Prompt intake 121 KB + 9 ảnh (khoảng 85k token).
- Giải từng mã: **cả 8 mã fail cả hai lượt** (`UNRESOLVED`, không ra DXF):
  - 3 mã có DATA: `UNTOUCHED_DATA_INVARIANCE_FAIL`, `RAW_DATA_SNAPSHOT_INCOMPLETE` (AI gõ lại tọa độ không khớp DATA gốc).
  - 5 mã còn lại: validator của repo từ chối (`BEND_OD_NOBI_CLOSURE_FAIL:B1..B4`, `CONTAINMENT_OUTER_GEOMETRY_UNVERIFIABLE`, thiếu bằng chứng 8 kiểm tra ngữ nghĩa, `REVIEW requires HL_DIRECTION_UNPROVED`).
- Chi phí lần đó (chế độ cũ, một phiên cho cả job): 17 lần gọi; đầu ra ≈183k token, đọc cache ≈2,77M, tạo cache ≈4,15M; chạm giới hạn Pro sau ≈19 phút (mã thứ 7) rồi thử lại mỗi phút nhiều giờ. Nguyên nhân chính: lịch sử một hội thoại phình tới 430–690k token và bị đọc lại mỗi lần gọi, cache hết hạn thì tạo lại; mỗi lượt giải ra 20–35k token đầu ra (AI viết tay toàn bộ `entities`, `source_groups`, `canonical_members`).
- **Chưa chạy lại sau commit `72f6282`**, nên chưa biết mức tiết kiệm thực tế và chưa biết 8 mã có qua cổng kiểm tra không. Người dùng yêu cầu dừng chạy job để tiết kiệm hạn mức.

## Việc cần làm tiếp (theo thứ tự đề nghị; mục 3–4 cần `DUYỆT` riêng + spec)
1. **Chạy lại 521016-23 một lần để đo** (xin phép người dùng trước vì tốn hạn mức): ghi số token/thời gian mỗi lần gọi từ bảng `events` (`kind='usage'`, `request_prepared`) trong `state.sqlite`. Mong đợi dừng sớm nếu 2 mã đầu lại fail.
2. **Đọc lỗi validator thật của 5 mã không DATA** (`checkpoint.parts[code].issues`), xem AI thiếu bằng chứng gì (nobi, containment, 8 kiểm tra ngữ nghĩa). Có thể cần cải thiện prompt hoặc để host chạy trước các cổng đó và trả lỗi cụ thể cho AI sửa trong cùng phiên (không dùng lượt mới).
3. **Host sao DATA nguyên vẹn** (cần `DUYỆT` + spec): với entity `UNCHANGED`, host tạo canonical entity và `data_provenance` trực tiếp từ DATA gốc; AI chỉ nói nhóm nào giữ/đổi. Loại bỏ `UNTOUCHED_DATA_INVARIANCE_FAIL`. Điểm vào: `check_data_provenance` trong `LuanAppTools/cad/evidence.py`, phần context `scoped_data` trong `pipeline.py`.
4. **Bộ biên dịch tham số** (cần `DUYỆT` + spec, đổi giao diện canonical): AI khai báo lỗ/rãnh/đường gấp, host dựng entity, ID và sổ cái; tham khảo `tools/slot_anchor.py`, `tools/slit_geometry.py`, `tools/CANONICAL_INPUT_SCHEMA_V434.md`.
5. **Nhóm DATA khung viền**: nhóm lớn nhất của 521016-23 (600 entity, bbox 0..1682 × 0..1188, gồm DIMENSION/ELLIPSE/SPLINE) rất có thể là khung bản vẽ; ghép theo bbox chồng nhau không tách được. Cân nhắc loại hoặc tách khung/ghi chú ra nhóm riêng. Nhóm lớn tốn ≈169 KB ở bước giải.
6. **Tên thư mục job**: cho phép thư mục như `521016-23 hom nay` và lấy phần `521016-23` đầu làm tên job (hiện tên thư mục được dùng nguyên văn và regex `[\w.-]+` trong `pipeline.run` từ chối dấu cách). Người dùng đã yêu cầu làm sau; cần xử lý trùng mã.
7. **Nạp rule theo giai đoạn**: prompt giải đầu tiên ≈211 KB (rule L3 validate/xuất/QA nạp trước khi cần). Chỉ đổi cách nạp ở phía app; không sửa nội dung rule (rule còn bị ràng buộc bởi `tests/test_rule_load_budget.py`).
8. Xem lại: `test_cancel_terminates_provider_process` (fail sẵn trên `main`), độ ổn định `test_e2e`, và `README`/`STATUS.md` của LuanAppTools chưa cập nhật các thay đổi trên.

## Cạm bẫy khi chạy local trên Windows
- **Đường dẫn dài**: thư mục trạng thái + hai mã băm 64 ký tự vượt 260 ký tự → job lỗi ngay (`manifest.json` not found). Dùng thư mục ngắn, ví dụ `--data-dir C:\lat\state`, nguồn ở `C:\lat\jobs\<mã>`.
- Ứng dụng ghim **commit HEAD** của checkout (`git archive`), nên thay đổi chưa commit ở `tools/` không vào ứng dụng; phần code `LuanAppTools/` chạy trực tiếp từ checkout.
- Cần `claude auth login` (Claude Code ≥ 2.1.300, đăng nhập bằng gói claude.ai). Mọi lượt gọi dùng hạn mức gói của người dùng; sửa test không cần gọi AI (dùng `ScriptedRunner`).
- Chạy backend: `python -m LuanAppTools --data-dir C:\lat\state --repo-root <checkout> --port 8765`; mutation cần header `X-Luan-Token` lấy từ `/api/health`. Môi trường thử dùng venv riêng (`pip install -r requirements.txt -r LuanAppTools/requirements-dev.txt`).
- Đừng dùng lệnh dừng tiến trình theo `CommandLine` chứa chuỗi `LuanAppTools`: nó trúng cả shell của chính phiên đang chạy. Dừng theo cổng 8765.
- Python 3.14 đang được dùng; `fitz` báo deprecated (không ảnh hưởng).
