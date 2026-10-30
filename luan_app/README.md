# Luan App — chạy job CAD trên mạng LAN

App web nhỏ chạy trên máy Admin. Mọi người trong LAN mở link, dán đường dẫn thư mục job, chọn mã rồi bấm **Chạy job**. App chạy `claude -p` (Claude Code, tài khoản của máy Admin) đúng như khi Admin gõ `E2E <đường dẫn>`. Admin có thêm **QA**, **Chờ duyệt** và **Cài đặt**. App không sửa repo; rule vẫn chỉ đổi khi Admin `DUYỆT` / `PUSH` trong Claude Code.

Thiết kế: `docs/superpowers/specs/2026-10-30-luan-app-design.md`.

## Cài trên máy Admin (một lần)

Cần: Python 3.11+, Git, Claude Code đã `claude auth login` bằng chính tài khoản Windows này, và quyền đọc/ghi `\\VietNam2025\...`.

```bat
luan_app\install.cmd
```

Bộ cài làm:
1. Tạo `luan_app\.venv` và cài thư viện.
2. Tạo tác vụ **Luan App** tự chạy khi đăng nhập Windows. App chạy ngầm, có biểu tượng ở khay hệ thống: *Mở app · Copy link LAN · Thoát*.
3. Mở cổng 8765 cho mạng **Private**. Windows sẽ hỏi quyền Administrator một lần.
4. Hỏi đặt mật khẩu Admin.
5. Mở `http://127.0.0.1:8765` và in link LAN cho mọi người, ví dụ `http://192.168.1.25:8765`.

Sau khi cài, vào **Cài đặt → Thư mục gốc được phép** và thêm `\\VietNam2025\...`. Job nằm ngoài các thư mục này bị từ chối.

Gỡ cài: `luan_app\install.cmd -Uninstall`. Dữ liệu vẫn nằm ở `%LOCALAPPDATA%\LuanApp`.

## Dùng

- **Mọi người:** nhập tên lần đầu. Dán đường dẫn job, app đọc phiếu `依頼` và tick sẵn mọi mã, bỏ tick mã không làm, rồi bấm **Chạy**. Theo dõi trên **Bảng**; xem lại ở **Lịch sử**. Chỉ hủy và chạy lại được job của mình.
- **Admin:** bấm tên ở góc phải → **Đăng nhập Admin**.
  - **QA:** dán thư mục job hoặc một file `.dxf`.
  - **Chờ duyệt:** dùng *Chép để duyệt*, rồi dán vào Claude Code.
  - **Cài đặt:**
    - số job chạy cùng lúc (1–6, mặc định 3);
    - thời gian tối đa;
    - model;
    - bản repo (mặc định `origin/main`);
    - chạy tiếp hàng đợi khi bị tạm dừng vì hết hạn mức.
  - **Lịch sử:**
    - xem transcript;
    - *Xuất gói lỗi* (zip để đưa Claude Code phân tích);
    - xuất CSV.

## Cách chạy job

- Mỗi suất là một git worktree riêng ở `C:\TrainAiCad-slots\slotN`. Trước mỗi job, worktree được đưa về `origin/main` mới nhất. Repo của Admin (`C:\TrainAiCad`) không bị đụng.
- Claude chạy với `--permission-mode dontAsk`. Nó được đọc, chạy `python …` và ghi vào `.work/`, thư mục job và thư mục kết quả. Nó bị chặn sửa `rules/ tools/ data/ …` và chạy `git`. Sau mỗi job app kiểm tra `git status`; nếu có file repo bị sửa thì gắn cờ trong Lịch sử và khôi phục.
- Mỗi lượt chạy được lưu ở `%LOCALAPPDATA%\LuanApp\runs\<id>\`: `transcript.jsonl`, `stderr.log`, `out/` (report.md, result.json, review_items.json), `work/`, `meta.json`.
- Khi hết hạn mức Claude, hàng đợi tạm dừng tới giờ hạn mức mở lại.
- Nếu app hoặc máy khởi động lại, job đang chạy chuyển thành *Lỗi* và có nút *Chạy lại*; job đang chờ giữ nguyên thứ tự.

## Phát triển

```sh
pip install -r luan_app/requirements.txt
python -m pytest luan_app/tests -q          # Claude giả (tests/fake_claude.py), không tốn hạn mức
python -m luan_app --no-tray --port 8766    # chạy thử; LUAN_CLAUDE_CMD="python luan_app/tests/fake_claude.py" để không gọi Claude thật
```
Biến môi trường: `LUAN_DATA_DIR`, `LUAN_SLOTS_ROOT`, `LUAN_CLAUDE_CMD`. Log: `%LOCALAPPDATA%\LuanApp\app.log`.
