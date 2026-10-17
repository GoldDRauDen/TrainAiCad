# LuanAppTools — giảm chi phí, tăng độ chính xác (đặc tả)

Ngày: 17/10/2026. Trạng thái: người dùng đã duyệt hướng làm trong phiên 17/10 ("duyệt làm đi toàn bộ e2e"), bỏ QA độc lập. Nhánh local `codex/luanapp-cost-accuracy-20261017`, **chưa push**. Không sửa rule sản xuất của repo (AGENTS.md §5).

## 1. Mục tiêu và thước đo

Chạy job local nhanh hơn và rẻ hơn luồng web (web: dưới 10 phút, dưới 10% usage Pro; lần chạy local đầu tốn ~20% và không ra DXF).

Thước đo thành công: DXF tổng của job `520925-07` khớp mẫu `F:\AI\Train_AI_CAD\practice\data-train\_AInoTouch\520925-07.dxf`.

- Mẫu **chỉ dùng để chấm**, không đưa vào job, không nằm trong thư mục job.
- Ghép chi tiết **từ trên xuống**, cho phép tịnh tiến và xoay 0/90/180/270.
- Dung sai theo rule repo (`references/REFERENCE_CALIBRATION_AUDIT.md` §2.4): chênh lệch tuyệt đối **< 0,01 mm** cho giá trị suy ra; đúng 0,01 là không đạt. ARC+LINE tương đương LWPOLYLINE đóng có bulge; số entity thô không phải tiêu chí; entity trùng hệt được gộp.
- Job chạy **tại chỗ** trên `F:\AI\Train_AI_CAD\practice\data-train\520925-07`; DXF ra đúng thư mục job.
- Mỗi mã tự kiểm (agent + validator tất định của host). Không bật QA độc lập.

## 2. Bằng chứng gốc (run `be89439f`, 12,5 phút, 17 lần gọi, 0 DXF)

| Phát hiện | Bằng chứng |
| --- | --- |
| 7 vòng `validate` liên tiếp cùng một lỗi | `tools/export_dxf.py:237` yêu cầu `flags` khác rỗng và `preview_reason == "separate_source_views"`; 0 lần xuất hiện trong 289k ký tự rule; chỉ `tools/DXF_INPUT_SCHEMA.md` mô tả |
| Schema đầu ra host thiếu trường | `pipeline.py` (solve, single_agent) không có `preview_reason`; `entities` không có `view_id`, `center`, `radius`... |
| AI chọn `VIEWS_ONLY` ở vòng 1 | Trái `AI_ENTRYPOINT` §2, `REVIEW_PREVIEW_POLICY` mục 3, `HOLISTIC` §3/§6, `CROSS_FEATURE_VALIDATION`, `FACE_GRAPH` G7A; bản vẽ có phép tính phẳng viết tay |
| Rule nạp như một khối text trong tin nhắn người dùng | Thí nghiệm CLI 2.1.301: tiền tố trong tin nhắn người dùng không dùng lại cache giữa phiên; qua `--append-system-prompt-file` thì phiên thứ hai đọc lại 11.374 và chỉ tạo mới 625 token |
| `customer_code` không tới resolver | Census của app không có `customer_code`; job KH851 không chịu cổng weld-site/KEGAKI của repo |
| Cache đọc lại 2,12M token cho 12 lần gọi của một mã | Mỗi vòng tool là một tiến trình `claude --resume` đọc lại 130–190k token |

## 3. Phạm vi

Trong phạm vi (chỉ phía app `LuanAppTools/`, không đổi nội dung rule/tool sản xuất):

- WP0 Bộ chấm DXF và bộ đo chi phí.
- WP1 Hợp đồng đầu ra: schema host đầy đủ trường; mô tả `VIEWS_ONLY` lấy từ `tools/DXF_INPUT_SCHEMA.md` của snapshot; test chống lệch với exporter.
- WP2 Lỗi có điều kiện cổng: truy ngược thông báo lỗi của exporter về câu lệnh `if` sinh ra nó (AST), trả điều kiện đó cho AI.
- WP3 Dừng khi lỗi lặp: cùng một lỗi `validate` lần 3 thì kết thúc lượt của mã đó (không dừng cả job).
- WP4 Cổng chống `VIEWS_ONLY` sớm: bắt buộc bản ghi `unresolved_record` theo `HOLISTIC_ENGINEERING_CHALLENGE` §4 và phải dùng các ghi chú có phép tính phẳng.
- WP5 Rule dùng chung qua system prompt (`--append-system-prompt-file`) để các mã cùng route dùng chung cache.
- WP6 `customer_code` vào census/resolver/job, kèm census mối hàn cho KH851, kiểm tra sớm trong intake.

Ngoài phạm vi: sửa nội dung rule repo; QA độc lập; nạp rule theo giai đoạn (repo ghi rõ chỉ giảm ngữ cảnh ban đầu, không giảm tổng token cả job); push/merge.

## 4. Thiết kế

### WP0 — `LuanAppTools/bench/`
- `score_dxf.py`: đọc DXF kết quả và DXF mẫu; bỏ TEXT/layer `AI_META`; phân loại entity theo CUT / BEND (DASHED) / KEGAKI (màu 1) / GREEN (3) / PREVIEW (6) / POINT; tách cụm bằng gộp bbox (LINE/ARC trước, CIRCLE vào cụm chứa tâm); sắp từ trên xuống; ghép cụm bằng quy hoạch động bảo toàn thứ tự (cho phép bỏ qua cụm thừa/thiếu); mỗi cặp thử 4 góc xoay, tịnh tiến theo bỏ phiếu điểm khóa; gộp LINE cộng tuyến và ARC cùng đường tròn trước khi so; báo `MATCH/PARTIAL/DIFF` theo chiều dài khớp và số CIRCLE khớp, độ lệch lớn nhất, danh sách thừa/thiếu, và recall ở các mức dung sai 0,01 / 0,1 / 1.
- `run_metrics.py`: từ `state.sqlite` tổng hợp thời gian, số lần gọi, token tạo/đọc cache và output theo giai đoạn/mã, cỡ prompt, số lần lỗi lặp.

### WP1 — `cad/contract.py`
- `solve_part_schema(check_names, code, page_ids)` thay schema nội tuyến; thêm: `preview_reason`, `review_reason`, `grain`, `dx_label`, `unresolved_record`, các trường KH851 (`source_assembly_view_ids`, `source_weld_site_ids`, `weld_site_census`), trường witness; entity thêm `view_id`, `center`, `radius`, `start`, `end`, `start_angle`, `end_angle`, `point`, `color`, `linetype`, `text`, `insert`, `height`.
- `contract_notes(repo)`: trích mục "Input JSON" của `tools/DXF_INPUT_SCHEMA.md` trong snapshot để đưa vào prompt (đọc từ repo, không sao chép).
- Test chống lệch: mọi khóa `part.get(...)`/`ent.get(...)` trong `export_dxf.py` và `canonical_contract.py` phải có trong schema hoặc danh sách nội bộ đã khai báo.

### WP2 — chỉ mục cổng
- `GateIndex` phân tích AST `tools/export_dxf.py` và `tools/canonical_contract.py` của snapshot: mỗi lời gọi `fail(...)`/`CanonicalContractError(...)` → mẫu thông báo (regex từ f-string) và điều kiện `if` bao quanh.
- `advise(error)`: tách `canonical:`/`export:`/`geometry:`, tìm mẫu khớp, trả `{gate, file:line, fires_when}`. Dùng trong kết quả tool `validate` và trong `issues` của lượt sau.

### WP3 — lỗi lặp
- Chữ ký lỗi = thông báo chuẩn hóa (bỏ mã). Lần 2 liên tiếp: nhắc cụ thể. Lần 3: `PipelineError("validation_stalled")` chỉ kết thúc lượt của mã (không nằm trong nhóm lỗi làm dừng cả job).

### WP4 — VIEWS_ONLY qua chính cổng của repo
- Phát hiện khi đọc `tools/holistic_engineering_guard.py`: đường sản xuất chỉ kiểm bản ghi vét nguồn khi phần tự khai `source_exhausted`/`holistic_challenge_run`; `part_anomalies` (đòi các cờ đó) chỉ dùng trong regression. Vì vậy app **dùng đúng khóa của repo** thay vì tự chế định dạng.
- `validate` của app chạy thêm `job_anomalies` của repo. Với `VIEWS_ONLY`, phần phải khai `source_exhausted`, `holistic_challenge_run`, `face_graph_candidates[{candidate_id, constraint_result, evidence_used}]`, `unresolved_objects`, `proved_source_view_member_ids == views_only_canonical_member_ids`.
- Host đặt `high_source_evidence` khi ghi chú của mã có phép tính phẳng (`a+b-c=d`) và `flat_attempted` cho phần PASS/PREVIEW/REVIEW; `VIEWS_ONLY` phải dẫn id các ghi chú đó trong `evidence_used` (repo: `HOLISTIC` §3, `CROSS_FEATURE_VALIDATION`).

### WP5 — system prompt dùng chung
- `AIRequest.shared_context`; `ClaudeRunner` ghi file đặt tên theo hash trong workspace và thêm `--append-system-prompt-file`; CLI cũ hơn 2.1.301 thì gộp vào prompt. Pipeline đặt vào đó: lời dẫn, `TOOL_DESCRIPTION`, rule của route, và ghi chú hợp đồng đầu ra. Tin nhắn người dùng chỉ còn nhiệm vụ + `CONTEXT_JSON`. Rule mới do đổi route giữa chừng vẫn đi theo tin nhắn người dùng (cơ chế `fresh_rules` có sẵn).
- Gateway (9Router) giữ hành vi cũ.

### WP6 — customer_code
- Intake trả `customer_code` (chuỗi số hoặc null) kèm bằng chứng; host ghim vào census mỗi mã và vào job JSON. Với KH851 (hoặc khi có census mối hàn) intake phải trả census mối hàn theo `references/WELD_SITE_KEGAKI_CLOSURE.md`; host chép sang `part` để AI không phải lặp lại.
- Sau intake, host gọi `resolve` cho từng mã; lỗi `ResolutionError` vào đường sửa intake một lần có sẵn thay vì làm hỏng cả run.

## 5. Kiểm thử và nghiệm thu

- Mỗi thay đổi có test trước (runner giả, exporter thật từ snapshot). Chạy toàn bộ `tests` và `LuanAppTools/tests`; test đã biết fail trên `main` (`test_cancel_terminates_provider_process`) được ghi riêng.
- E2E: một lần chạy thật `520925-07` tại chỗ với **van ngân sách**: dừng nếu cache đọc cộng dồn vượt 1,5M token hoặc quá 25 phút. Chấm bằng `score_dxf.py`, báo từng mã.
- Báo cáo trung thực: kết quả chấm từng mã, chi phí đo được, và những gì chưa đạt. Không push khi chưa có `PUSH`/`DUYỆT`.

## 6. Rủi ro đã biết

- Job thử là KH851 có cụm hàn: cặp `056152/153` khó, `056159/160` đơn giản. Mẫu có 6 cụm trong khi slip có 4 mã (2 cụm nhỏ không có mã); bộ chấm cho phép bỏ qua cụm thừa.
- Cổng WP4 buộc AI nêu bằng chứng nhưng không chứng minh được bằng chứng đúng; độ chính xác vẫn do AI quyết định.
- Rule dùng chung cho cả route khác nhau không chia sẻ cache; chỉ các mã cùng route chia sẻ.
