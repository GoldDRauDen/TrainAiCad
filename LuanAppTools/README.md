# LuanAppTools — điều phối TrainAiCad trên Windows

Ứng dụng local cho một người dùng: chọn thư mục job trên LAN, chạy Claude, kiểm tra PDF/DXF và mở kết quả. **Mọi DXF đều cần người dùng kiểm tra lại**, kể cả PASS. Ứng dụng không phê duyệt sản xuất.

## Chạy trên Windows

Cài Git for Windows, Python 3.11+, Node.js 20.19+ và Claude Code chính thức. Đăng nhập Claude dưới đúng tài khoản Windows chạy ứng dụng bằng `claude auth login`.

```powershell
git clone --branch codex/luan-app-tools-20261015 https://github.com/GoldDRauDen/TrainAiCad.git
cd TrainAiCad
.\LuanAppTools\start.cmd
```

Launcher tạo venv riêng, cài dependency app, build giao diện rồi mở `http://127.0.0.1:8765`. Giữ cửa sổ launcher trong lúc chạy; Ctrl+C để dừng. Lần đầu cài cần mạng. Dashboard mở được khi chưa có Claude/nguồn, nhưng không giả kết quả AI.

Tùy chỉnh cổng và thư mục trạng thái local:

```powershell
.\LuanAppTools\start.cmd -Port 8877 -DataDir "C:\Luan App State"
```

Trong **Cài đặt**, mỗi dòng nhập một root như `\\server\banve\2026`. Bấm **Lưu cài đặt**, **Công việc → Quét thư mục**, chọn job rồi **Chạy đã chọn**. Mỗi job là thư mục có trọn bộ PDF và DATA DXF; không chọn thư mục chứa file tham chiếu trộn với nguồn.

**Thư mục workspace chung** mặc định là thư mục dữ liệu app (`%LOCALAPPDATA%\LuanAppTools`). Bản nguồn cố định ở `cache\<job-id>\<source-hash>` và dữ liệu xử lý từng lượt ở `work\<run-id>`. Có thể nhập đường dẫn gốc khác trong Cài đặt; thay đổi chỉ áp dụng cho lượt chạy mới. Đường dẫn cụ thể của mỗi lượt được hiển thị trong chi tiết job.

DXF tổng nằm tại thư mục job: `<JOB>_ALL.dxf` nếu toàn PASS, hoặc `<JOB>_ALL_REVIEW_ONLY.dxf` khi còn REVIEW theo hợp đồng repo. Bật DXF riêng để xuất **mã PASS** vào `parts_dxf` hoặc đích đã cấu hình. Nút mở thư mục thực hiện trên máy Windows chạy app. Chi tiết có nguồn PDF, preview DXF kéo/zoom, tải file, hồ sơ từng mã, hoạt động, usage và lịch sử. Xác nhận “đã kiểm tra” gắn đúng phiên bản kết quả, tách biệt PASS kỹ thuật.

Trong **Cài đặt → Kết nối AI**, chọn provider dùng cho job mới:

- **Claude**: bấm **Đăng nhập Claude**, hoàn tất cửa sổ Claude Code rồi bấm **Kiểm tra kết nối**.
- **GPT**: nhập model và OpenAI API key. API key dùng thanh toán API riêng, không dùng gói ChatGPT.
- **Custom endpoint**: nhập base URL OpenAI-compatible, model ID, rồi chọn không xác thực, Bearer API key hoặc header tùy chỉnh.

Bấm **Lưu & kiểm tra kết nối**. Khóa API được mã hóa bằng Windows DPAPI theo tài khoản Windows hiện tại; app không trả khóa về giao diện và không lưu khóa vào settings, run hay repo. Provider đã chọn được dùng cho job mới; có thể đổi lựa chọn bất cứ lúc nào. Model Claude theo độ khó vẫn giữ cấu hình riêng; GPT/custom dùng model đã nhập. Mỗi mã tối đa hai lượt giải trong một lần chạy.

## Khôi phục và xử lý lỗi

- Nguồn thay đổi: job đã chọn tự xếp phiên bản ổn định mới; job đang tạm dừng vẫn giữ ý định tạm dừng.
- Mất LAN/khóa output: kết quả local giữ lại, trạng thái chờ ghi; thử chuyển lại không gọi AI để dựng lại.
- Phiên AI bị ngắt không biết kết quả: app chặn gửi lại mù quáng và báo cần đối soát; chọn fallback được xác minh hoặc chủ động hủy/chạy một lần mới khi phù hợp.
- Không ghi đè file output không thuộc app. Chuyển file trùng tên do người khác tạo ra nơi khác sau khi tự kiểm tra.
- Chỉ một app được dùng một thư mục trạng thái. Không đặt SQLite/trạng thái trên LAN. Mặc định `%LOCALAPPDATA%\LuanAppTools`.
- Dùng UNC nếu ổ mạng không hiện trong tài khoản chạy app. Kiểm tra quyền đọc nguồn/ghi đích bằng chính tài khoản đó.
- Không sửa rules trong lúc job đang chạy; mỗi lần chạy khóa commit và hash nguồn. Không lưu credential vào repo/cài đặt.
- Launcher không thay đổi Execution Policy vĩnh viễn; tổ chức có policy chặn script cần quản trị viên xử lý theo chính sách nội bộ.

## Xuất phần đã chốt, bằng chứng JSON, công cụ dựng sẵn (21/10/2026)

Các thay đổi này chỉ nằm trong `LuanAppTools/`, không sửa rule hay công cụ của repo. **Chưa được chạy bằng job thật**; bật/tắt ở Cài đặt.

| Việc | Mặc định | Ghi chú |
| --- | --- | --- |
| Xuất từ phần đã chốt, không gọi AI (`POST /api/jobs/{id}/export-saved`, nút "Xuất từ phần đã chốt") | luôn có | Gom các mã đã qua validate, xuất DXF tổng REVIEW ONLY có ghi mã thiếu trên lớp `AI_META`. Mã không có JSON hợp lệ nhưng có bản nháp thì vào như VIEWS_ONLY có cờ `DRAFT_UNVALIDATED` (serializer `export_dxf.py`) |
| Tự xuất khi hết lượt giải mà còn mã chưa xong (`salvage_export`) | bật | Trước đây chỉ báo lỗi `no_valid_representation` và không ra file nào |
| JSON từng mã ghi vào `evidence/<mã>.json` cạnh DXF tổng, kèm `_run.json` và `_job_canonical.json` (`write_evidence`) | bật | Thư mục con không bị quét như nguồn; lỗi ghi evidence không làm hỏng run đã publish |
| Công cụ host `unfold_calc`, `build_part`, `render_preview` | luôn có | `build_part` dựng hồ sơ từ bản phác và chạy `validate` cùng lệnh; không bao giờ tự đặt PASS, Nobi hay `endpoint_verified` |
| Trả `part_ref` thay vì chép lại cả JSON (`answer_by_ref`) | tắt | Đổi schema đáp án (`anyOf`), cần thử trước |
| Mã khó chạy hội thoại riêng với effort cao hơn (`effort_by_difficulty`) | tắt | Chưa đo |
| Gọi `boxmet_flat` / `boxmet_job` của repo (`repo_generators`, tool `run_generator`) | tắt | Chỉ chạy nếu snapshot repo đã có `tools/boxmet_*.py` |
| Cắt sẵn ảnh từng hình chiếu (`precrop_views`) | tắt | Số đo: `crop` là yêu cầu công cụ nhiều nhất |
| Kiểu chạy `agent` (`run_mode`) | `host` | Cho Claude CLI chạy `cad/agent_cli.py` bằng công cụ shell; **chưa xác minh** CLI `--restricted` chấp nhận mẫu `Bash(python ...:*)` |

Đếm số lượt gọi AI theo mã và công cụ (chỉ đọc DB): `python -m LuanAppTools.bench.round_trips [--run RUN_ID]`.

## Phát triển và kiểm thử

```bash
python -m pip install -r LuanAppTools/requirements-dev.txt
python -m pytest tests LuanAppTools/tests -q
cd LuanAppTools/frontend
npm ci
npm test
npm run build
```

Chạy backend bằng `python -m LuanAppTools --data-dir <local-dir>`. Chỉ bind loopback, frontend build cùng origin. API `/docs`; mọi mutation yêu cầu JSON và `X-Luan-Token` lấy từ `/api/health`. Không expose lên LAN.

Kiểm thử tự động dùng nguồn tổng hợp, provider fixture và công cụ CAD thật. Các test này không chứng minh độ chính xác trên bản vẽ khách hàng, tài khoản Claude/9Router thật hay Windows/SMB của người dùng. Những kiểm tra đó vẫn cần thực hiện trên máy đích trước khi nghiệm thu vận hành.
