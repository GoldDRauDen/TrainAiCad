# Luan App — app LAN chạy job CAD (giai đoạn 1)

Ngày: 2026-10-30 · Trạng thái: chờ Admin duyệt · Mockup: [2026-10-30-luan-app-mockup.html](2026-10-30-luan-app-mockup.html)

## 1. Mục tiêu

Hiện nay chỉ Admin (Luân) làm job: copy đường dẫn job, dán vào Claude Code kèm lời nhắn "làm job này …", rồi tự theo dõi. Luan App chia sẻ đúng phần việc tay chân đó cho 7–8 người trong mạng LAN:

- Máy Admin đăng nhập Claude và chạy app ngầm. Mọi người mở `http://<IP-máy-admin>:8765`.
- Người dùng dán đường dẫn job, chọn mã (mặc định chọn tất cả), rồi bấm **Chạy job**. Admin có thêm nút **QA**.
- Mọi người cùng nhìn một bảng theo dõi job đang chạy, đang chờ và đã xong.
- Admin có thêm mục **Chờ duyệt**: chỉ chứa bài học mới hoặc kỹ thuật cần mẫu DXF, không chứa thiếu dữ liệu bản vẽ.

**Tiêu chí thành công**
1. Một người không phải Admin chạy được một job thật từ máy khác trong LAN, và nhận DXF trong `AI_L\` giống hệt khi Admin tự chạy trong Claude Code.
2. Ba job chạy song song không giẫm lên nhau.
3. Không đường nào cho người dùng gửi chữ tự do tới Claude, hoặc làm Claude sửa repo.

**Ngoài phạm vi giai đoạn 1**
- Pet trên desktop: giai đoạn 2, spec riêng. Giai đoạn 1 chỉ làm sẵn API thông báo và mục chọn pet.
- Chat với AI và hỏi đáp sau khi job xong.
- Sửa rule hoặc tool từ app, tự tạo PR.
- `https`.

## 2. Người dùng và quyền

| Việc | Người dùng | Admin |
|---|---|---|
| Xem Bảng, chạy job (RUN) | ✓ | ✓ |
| Hủy / chạy lại | job của mình | mọi job |
| Lịch sử | job của mình | tất cả, kèm transcript, xuất gói lỗi, CSV |
| QA | ✗ | ✓ |
| Chờ duyệt | ✗ | ✓ |
| Cài đặt hệ thống | ✗ | ✓ |
| Cài đặt cá nhân (giao diện; pet ở giai đoạn 2) | ✓ | ✓ |

- **Người dùng:** lần đầu mở app thì nhập tên. Server cấp cookie `luan_uid` (ngẫu nhiên, HttpOnly, 1 năm) gắn với tên. Không được dùng tên trùng "admin" hay tên đang thuộc cookie khác (không phân biệt hoa/thường).
- **Admin:**
  - Mật khẩu đặt ở lần chạy đầu, chỉ đặt được từ `127.0.0.1`. Lưu dạng băm `hashlib.scrypt` kèm salt.
  - Đăng nhập được từ mọi máy trong LAN. Phiên dùng cookie `luan_admin`, HttpOnly, SameSite=Strict, hết hạn sau 12 giờ.
  - Sai 5 lần thì khóa 5 phút theo IP.
  - Đổi mật khẩu trong Cài đặt.
- Mọi quyền được **kiểm tra ở server**, giao diện chỉ ẩn nút cho gọn.

## 3. Kiến trúc

```text
Máy Admin (Windows, tài khoản đã `claude auth login`, truy cập được \\VietNam2025)
├─ luan_app (pythonw, ngầm) ── FastAPI/uvicorn 0.0.0.0:8765 ── static/ (HTML/CSS/JS, không build)
│     ├─ store      SQLite WAL       %LOCALAPPDATA%\LuanApp\state.sqlite
│     ├─ scheduler  hàng đợi, N suất (mặc định 3)
│     ├─ slots      git worktree     C:\TrainAiCad-slots\slot1..N
│     ├─ runner     `claude -p` stream-json, 1 tiến trình / suất
│     ├─ progress   đọc job_state.json + AI_L\ + result.json
│     ├─ archive    %LOCALAPPDATA%\LuanApp\runs\<run-id>\
│     └─ tray       biểu tượng khay hệ thống (Mở app / Copy link LAN / Thoát)
└─ C:\TrainAiCad   repo chính của Admin: app không ghi gì vào đây khi chạy job
```

Code nằm ở `luan_app/` trong repo TrainAiCad. Phụ thuộc thêm: `fastapi`, `uvicorn`, `pystray`, `pillow`. Các thư viện này nằm trong `luan_app/requirements.txt`, tách khỏi `requirements.txt` của repo.

| Module | Trách nhiệm | Phụ thuộc |
|---|---|---|
| `luan_app/store.py` | Schema SQLite, các truy vấn | sqlite3 |
| `luan_app/sources.py` | Chuẩn hóa và kiểm tra đường dẫn; đọc phiếu bằng `tools/slip.py` → danh sách mã | `tools/slip.py` |
| `luan_app/slots.py` | Tạo, làm mới, kiểm tra worktree | git |
| `luan_app/prompts.py` | Câu lệnh cố định cho RUN/QA | không |
| `luan_app/runner.py` | Dựng lệnh `claude`, đọc luồng sự kiện, ghi transcript, hủy cả cây tiến trình | claude CLI |
| `luan_app/scheduler.py` | Cấp suất, vòng đời run, tạm dừng khi hết hạn mức, phục hồi khi khởi động | store, slots, runner |
| `luan_app/progress.py` | Tiến độ từng mã, trạng thái cuối, đọc `review_items.json` | không |
| `luan_app/archive.py` | Cất gói run, xuất zip/CSV | không |
| `luan_app/auth.py` | Tên người dùng, mật khẩu Admin, khóa khi sai nhiều lần | store |
| `luan_app/api.py` | Các route REST, cache bảng theo dõi | tất cả |
| `luan_app/tray.py`, `__main__.py` | Chạy ngầm, chỉ một bản, giữ máy thức | pystray |
| `luan_app/static/` | `index.html`, `app.css`, `app.js` | api |

## 4. Luồng chạy job

### 4.1 Gửi job
1. Người dùng dán đường dẫn. Trình duyệt gọi `POST /api/sources/inspect`. Server:
   - chuẩn hóa đường dẫn: bỏ `\` cuối, đổi `/` thành `\`, so sánh không phân biệt hoa/thường;
   - kiểm tra đường dẫn nằm trong **thư mục gốc cho phép** (Admin cấu hình, ví dụ `\\VietNam2025\`), tồn tại và đọc được;
   - kiểm tra có ít nhất một file PDF, DXF, DWG hoặc ảnh;
   - đọc phiếu `*_依頼.xlsx` bằng `slip.read_slip`.

   Trả về: tên job, danh sách mã (mã, vật liệu, t, kích thước), thẻ gấp, các cảnh báo.
2. Giao diện hiện danh sách mã, **tất cả đã tick**. Thư mục không có phiếu thì không có danh sách, nghĩa là làm cả job.
3. Bấm **Chạy job** (Admin có thêm **QA**) → `POST /api/runs {path, kind, codes}`. Server kiểm tra lại toàn bộ, gồm:
   - mọi mã gửi lên phải có trong phiếu;
   - **chặn trùng:** không có run nào khác đang `QUEUED/PREPARING/RUNNING/FINISHING` với cùng đường dẫn đã chuẩn hóa. Nếu có thì trả 409 *"Job này đang được {tên} chạy, bắt đầu {giờ}"*;
   - nếu đường dẫn đã có run kết thúc, giao diện hỏi xác nhận *"Job này đã chạy lúc …, chạy lại?"* trước khi gửi (`confirm_rerun=true`).

Người dùng **không có ô nhập chữ tự do**. Claude chỉ nhận đường dẫn và danh sách mã đã kiểm tra.

### 4.2 Vòng đời
`QUEUED → PREPARING → RUNNING → FINISHING → DONE | REVIEW | ERROR | CANCELLED`

- **PREPARING** (suất k):
  1. `git -C C:\TrainAiCad-slots\slotk checkout --detach -f main`.
  2. `git clean -fdx -e .work`.
  3. Xóa `.work/` cũ của suất (đã được cất ở lần trước).
  4. Ghi commit vào run.
  
  Worktree được tạo lần đầu bằng `git worktree add --detach`.
- **RUNNING:** chạy `claude` trong worktree (xem 4.3). Tiến độ được cập nhật mỗi 2 giây từ `.work/<JOB>/job_state.json` (giai đoạn L0–L3 và trạng thái từng mã) và từ sự kiện tool cuối cùng trong luồng stream-json (dòng "đang làm gì").
- **FINISHING:**
  1. Cất gói run (mục 6).
  2. Đọc `result.json` và `review_items.json`.
  3. Chạy `git status --porcelain` trong worktree, bỏ qua `.work/`. Nếu có thay đổi thì gắn cờ `repo_touched` (Lịch sử hiện *"Job đã sửa file repo, đã khôi phục"*) và chạy lại `checkout -f` + `clean`.
  4. Trả suất.
- **Trạng thái cuối**
  - RUN:
    - `DONE`: mọi mã PASS và `AI_L\` có file giao mới sau giờ bắt đầu.
    - `REVIEW`: có mã PREVIEW, FLAG hoặc FAIL.
    - `ERROR`: không có `job_state.json`, CLI thoát mã khác 0, hoặc không giao được file nào.
  - QA:
    - `DONE` khi `result.json.verdict == "OK"`.
    - `REVIEW` khi `"ISSUES"`.
    - `ERROR` khi thiếu `result.json` hoặc CLI lỗi.
  - Nếu `job_state.json` và `result.json` mâu thuẫn thì lấy trạng thái **xấu hơn**.

### 4.3 Gọi Claude
```text
claude -p <prompt> --output-format stream-json --verbose
       --allowedTools Read Glob Grep Write Edit "Bash(python:*)" "Bash(ls:*)" ...
       --disallowedTools "Bash(git:*)" "Edit(rules/**)" "Edit(tools/**)" "Edit(data/**)" "Edit(templates/**)" "Edit(tests/**)" "Write(rules/**)" ... 
       --add-dir <run_dir> --add-dir <đường dẫn job>
       [--model <cài đặt Admin, mặc định để trống = model mặc định của tài khoản>]
cwd = C:\TrainAiCad-slots\slotk ; env: LUAN_RUN_DIR=<run_dir>, PYTHONUTF8=1
```
- Chạy ở chế độ không hỏi quyền: tool ngoài allowlist **bị từ chối tự động**, không bao giờ chờ người bấm. Cờ chính xác (`--permission-mode …`) và cú pháp mẫu đường dẫn sẽ được xác minh trên Claude Code 2.1.301 ở bước đầu của kế hoạch triển khai.
- `run_dir = %LOCALAPPDATA%\LuanApp\runs\<run-id>\out\`: chỗ duy nhất app đọc báo cáo.
- Khung câu lệnh RUN (`prompts.py`, chỉ Admin sửa trong code):
  ```text
  E2E {path}
  Mã cần làm: {danh sách mã | "tất cả mã trong phiếu"}  → job.py init ... --codes ...
  Chạy qua Luan App, không có người trả lời:
  - Không hỏi lại. Mọi câu hỏi và điểm chưa rõ ghi vào báo cáo (JOB_CARD §5: luôn vẽ, không dừng).
  - Không sửa file nào của repo, không chạy git. File làm việc ở .work/ như bình thường.
  - Giao DXF bằng job.py deliver / deliver-code theo chế độ của phiếu như bình thường.
  Khi xong ghi vào {run_dir}:
  - report.md   : báo cáo theo rules/OUTPUT.md §8
  - result.json : {"verdict": "OK|ISSUES", "summary": "<1 dòng tiếng Việt>", "codes": {"<mã>": "PASS|PREVIEW|FAIL"}}
  - review_items.json : xem mục 5 (mảng rỗng nếu không có gì)
  ```
  QA dùng cùng khung, thay dòng đầu bằng `QA {path}` (thư mục job: DXF mới nhất trong `AI_L\`; hoặc một file `.dxf` cụ thể).

### 4.4 Hủy
Người chạy job hoặc Admin bấm Hủy. Giao diện hiện hộp xác nhận *"Hủy job {job} của {tên}? Phần đã làm vẫn được lưu."* với nút **Hủy job** / **Không**. Server:
1. `taskkill /PID <pid> /T /F`.
2. Cất gói run.
3. Đặt trạng thái `CANCELLED`, ghi ai hủy và lúc nào.
4. Trả suất.

Run đang `QUEUED` chỉ cần đổi trạng thái. Trong Lịch sử, run đã hủy có nhãn **Đã hủy** và nút **Chạy lại** (tạo run mới cùng đường dẫn và danh sách mã).

### 4.5 Lỗi và giới hạn
| Tình huống | Xử lý |
|---|---|
| Hết hạn mức Claude (nhận ra từ sự kiện `result` / lỗi trong stream-json) | Run → `ERROR` *"Hết hạn mức Claude"*. Hàng đợi **tạm dừng** tới giờ mở lại hạn mức (lấy từ thông báo lỗi nếu có, không thì 30 phút). Bảng hiện *"Tạm dừng tới HH:MM"*. Admin bấm **Chạy tiếp** được. |
| Quá thời gian (mặc định 120 phút, Admin chỉnh) | Hủy như 4.4, trạng thái `ERROR` *"Quá thời gian"* |
| Tiến trình chết hoặc thoát mã khác 0 | `ERROR`, chi tiết hiện 20 dòng log cuối |
| App hoặc máy khởi động lại | Lúc khởi động, run `PREPARING/RUNNING/FINISHING` mà tiến trình không còn → `ERROR` *"Bị ngắt do app khởi động lại"* (có Chạy lại). Run `QUEUED` giữ nguyên thứ tự. |
| Không có `claude` hoặc chưa đăng nhập | Kiểm tra lúc khởi động bằng `claude --version` và `claude auth status`. Bảng hiện băng cảnh báo cho Admin; hàng đợi không chạy. |

## 5. Chờ duyệt (chỉ Admin)

**Nguồn dữ liệu:** `review_items.json` do phiên Claude ghi. Câu lệnh cố định nói rõ cái gì được ghi và cái gì không:

```json
[{"type": "NEW_LESSON | NEED_SAMPLE_DXF",
  "code": "26-061247", "card": "rules/BEND.md",
  "title": "<1 dòng>", "detail": "<FACT → ROOT_CAUSE → LESSON đề xuất, hoặc điều không biết cách vẽ>",
  "evidence": "<trang/khung nhìn/crop>"}]
```
- **Ghi** khi: kỹ thuật hoặc chi tiết chưa thẻ rule nào bao, rule hiện có cho kết quả sai, hoặc không biết cách vẽ và cần mẫu DXF.
- **Không ghi** khi: thiếu hoặc không rõ kích thước, chờ xác nhận Nobi, thiếu dữ liệu bản vẽ, câu hỏi cho khách. Những thứ này vẫn nằm trong FLAG và `report.md`.
- App kiểm tra schema. Mục sai schema bị bỏ và ghi cảnh báo vào run.

**Giao diện:** danh sách gồm loại, job·mã, tiêu đề, chi tiết 2 dòng (bấm để xem hết), thẻ rule, đường dẫn job. Mỗi mục có 3 nút:
- **Chép để duyệt:** copy `DUYỆT bài học: {title} — job {job}, mã {code}, thẻ {card}\n{detail}\nNguồn: {path}` để Admin dán vào Claude Code.
- **Đính kèm mẫu DXF:** tải file lên, lưu ở `%LOCALAPPDATA%\LuanApp\attachments\<item-id>\`; đường dẫn file được thêm vào nội dung chép.
- **Bỏ qua.**

Trạng thái mỗi mục: `PENDING → COPIED → DONE | DISMISSED`. Admin đánh dấu **Đã xử lý** khi đã sửa repo xong. App **không bao giờ** tự sửa repo.

## 6. Lịch sử và lưu trữ

Gói mỗi run nằm ở `%LOCALAPPDATA%\LuanApp\runs\<run-id>\`:
- `transcript.jsonl`: toàn bộ luồng stream-json.
- `stderr.log`
- `out/`: report.md, result.json, review_items.json.
- `work/`: bản sao `.work/<JOB>/`.
- `meta.json`: người chạy, đường dẫn, mã, loại, commit, thời gian, mã thoát, token nếu stream có, cờ `repo_touched`.

Tab **Lịch sử:**
- **Lọc** theo trạng thái (Xong / Cần xem / Lỗi / Đã hủy), loại (RUN/QA), người chạy, khoảng ngày.
- **Ô tìm kiếm** trên tên job, mã và nội dung FLAG, dùng chỉ mục FTS5 trên cột `search_text` (job + mã + FLAG + summary).
- Người dùng chỉ thấy run của mình. Admin thấy tất cả.
- **Chạy lại:** tạo run mới.
- **Xuất gói lỗi** (Admin): zip gói run, trả file và copy đường dẫn.
- **Xuất CSV** (Admin) danh sách đang lọc.

Gói run không tự xóa. Admin dọn bằng tay; một tính năng dọn tự động có thể thêm sau nếu ổ đĩa cần.

## 7. Giao diện

- **Phong cách:** Swiss minimal, theo mockup đã duyệt.
  - Màu trung tính slate; màu chỉ dùng cho trạng thái: xanh lá = PASS/Xong, cam = FLAG/Cần xem, đỏ = Lỗi, xanh dương = Đang chạy/RUN, tím = QA, xám = Đã hủy/Đang chờ.
  - Font Be Vietnam Pro cho chữ, JetBrains Mono cho số job, mã và đường dẫn. Font được tải về `static/fonts/` để không phụ thuộc Internet.
  - Icon SVG nội tuyến, không dùng emoji.
- **Giao diện Sáng / Tối / Theo hệ thống:** dùng `data-theme` trên `<html>`, lưu trong `localStorage` theo từng trình duyệt.
- **Màn hình**
  1. **Bảng:**
     - ô đường dẫn, danh sách mã (khi có phiếu), nút Chạy job / QA;
     - dải 4 số: Đang chạy, Đang chờ, Xong hôm nay, Cần xem;
     - thẻ job đang chạy: bảng mã có 4 vạch L0–L3 và trạng thái, dòng lệnh đang chạy;
     - cột phải: Hàng đợi, Hôm nay;
     - băng "Tạm dừng tới HH:MM" khi hàng đợi dừng.
  2. **Chi tiết job:** ngăn trượt từ phải, gồm bảng mã, mọi FLAG, câu hỏi cho khách, nút Mở thư mục AI_L (chỉ trên máy Admin) và Copy đường dẫn DXF. Admin có thêm Transcript và Xuất gói lỗi.
  3. **Lịch sử** (mục 6).
  4. **Chờ duyệt** (mục 5).
  5. **Cài đặt hệ thống** (Admin): số suất (1–6), thời gian tối đa, thư mục gốc cho phép, model, tạm dừng/chạy tiếp hàng đợi, đổi mật khẩu.
  6. **Cài đặt cá nhân:** đổi tên hiển thị, giao diện, (giai đoạn 2: bật/tắt và chọn pet).
- **Thông báo trong trang:** khi một run của người đang xem kết thúc, một thông báo nhỏ hiện ở góc dưới phải trong 6 giây.
- **Mượt khi dùng chung:**
  - Trình duyệt gọi `GET /api/board` mỗi 2 giây, kèm `If-None-Match`.
  - Server giữ bản dựng sẵn trong bộ nhớ, làm mới tối đa 1 lần mỗi giây; không đổi thì trả 304.
  - JS chỉ vẽ lại phần thay đổi (khóa theo run id).
  - Tab bị ẩn thì giãn nhịp gọi ra 10 giây.
- **Truy cập:** điều hướng được bằng bàn phím, có viền focus rõ, tôn trọng `prefers-reduced-motion`, chữ đạt tương phản ≥ 4.5:1 ở cả hai chế độ. Từ 900px trở xuống thì gộp thành một cột.

## 8. Vận hành trên máy Admin

- **Cài đặt:** chạy `luan_app\install.cmd` một lần. Nó sẽ:
  1. tạo venv và cài `luan_app/requirements.txt`;
  2. tạo tác vụ Task Scheduler "Luan App" chạy `pythonw -m luan_app` **khi Admin đăng nhập Windows**, dưới chính tài khoản Admin;
  3. thêm luật Windows Firewall mở cổng 8765 cho profile **Private** (cần xác nhận UAC một lần);
  4. hỏi đặt mật khẩu Admin.
- **Chạy ngầm:** không có cửa sổ console. Biểu tượng khay hệ thống có các mục *Mở app*, *Copy link LAN*, *Thoát*. Thoát khi còn job đang chạy thì hỏi xác nhận và liệt kê các job sẽ bị hủy.
- **Chỉ một bản:** dùng file khóa `%LOCALAPPDATA%\LuanApp\app.lock` kèm cổng. Mở lần hai thì chỉ mở trình duyệt vào bản đang chạy.
- **Giữ máy thức:** khi có run đang chạy, app gọi `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)`; khi hết run thì trả lại.
- **Log app:** `%LOCALAPPDATA%\LuanApp\app.log` (xoay vòng 5 × 5 MB).

## 9. An toàn

- **Nội dung tới Claude:** chỉ đường dẫn (đã qua kiểm tra thư mục gốc cho phép) và danh sách mã (đã đối chiếu với phiếu), đưa vào khung câu lệnh cố định. Lệnh được gọi bằng danh sách đối số, không qua shell.
- **Quyền tool:** dùng allowlist/denylist (4.3). Job chạy trong worktree riêng, nên repo chính `C:\TrainAiCad` không bị đụng tới. Sau mỗi job có kiểm tra `git status` (4.2).
- **Cập nhật repo:** Admin merge vào `main` theo quy trình hiện có. Mỗi run lấy `main` mới nhất lúc PREPARING. Run đang chạy giữ nguyên commit của nó.
- **Mạng:** chỉ LAN, luật firewall chỉ cho profile Private. Mọi request thay đổi dữ liệu đều phải có header `X-Luan-CSRF` khớp với cookie. Cho phép CORS từ origin của chính app.
- **Giới hạn đã biết:** dùng `http`, nên mật khẩu Admin đi trên LAN không được mã hóa. Chấp nhận được cho mạng nội bộ. Có thể bật `https` sau.

## 10. Dữ liệu (SQLite)

```text
users(id, name UNIQUE COLLATE NOCASE, created_at, last_seen, prefs_json)
runs(id, kind RUN|QA, path, path_norm, job, codes_json, user_id, status, slot, pid,
     commit, queued_at, started_at, ended_at, exit_code, error, verdict, summary,
     codes_status_json, repo_touched, cancelled_by, rerun_of)
run_search USING fts5(run_id, search_text)
review_items(id, run_id, type, code, card, title, detail, evidence, status, attachment, created_at, updated_at)
notifications(id, user_id, run_id, kind DONE|REVIEW|ERROR|CANCELLED, text, created_at, seen_at)
settings(key PRIMARY KEY, value_json)       -- slots, timeout_min, allowed_roots, model, queue_paused_until, admin_hash
admin_sessions(token_hash, created_at, expires_at, ip)
```
Có chỉ mục `runs(path_norm, status)` cho kiểm tra trùng. Thao tác cấp suất và chuyển trạng thái nằm trong một transaction `BEGIN IMMEDIATE`.

## 11. API

| Method | Đường dẫn | Quyền |
|---|---|---|
| POST | `/api/me` (đặt tên) · GET `/api/me` | mọi người |
| POST | `/api/admin/login` · `/api/admin/logout` | mọi người |
| POST | `/api/sources/inspect` | mọi người |
| POST | `/api/runs` (`kind=QA` chỉ Admin) | mọi người |
| GET | `/api/board` (ETag) | mọi người |
| GET | `/api/runs?status&kind&user&from&to&q` · `/api/runs/{id}` | của mình / Admin |
| POST | `/api/runs/{id}/cancel` · `/api/runs/{id}/rerun` | của mình / Admin |
| GET | `/api/runs/{id}/transcript` · `/api/runs/{id}/bundle.zip` · `/api/runs.csv` | Admin |
| GET/POST | `/api/review-items` · `/api/review-items/{id}` (trạng thái, đính kèm) | Admin |
| GET/PUT | `/api/settings` · POST `/api/queue/resume` | Admin |
| GET | `/api/me/notifications?since=` · POST `/api/me/notifications/seen` | mọi người (pet giai đoạn 2 dùng) |
| GET | `/api/health` | mọi người |

## 12. Kiểm thử

- **Unit (pytest, `luan_app/tests/`)**
  - chuẩn hóa đường dẫn và thư mục gốc cho phép;
  - đọc phiếu → danh sách mã; đối chiếu mã;
  - chặn trùng;
  - các bước chuyển trạng thái;
  - quyết định trạng thái cuối (bảng ở 4.2);
  - kiểm tra schema `review_items`;
  - phân quyền theo từng route;
  - mật khẩu và khóa khi sai nhiều lần;
  - ETag của `/api/board`.
- **Tích hợp với Claude giả:** `tests/fake_claude.py` phát stream-json mẫu, ghi `job_state.json`/`result.json`/`review_items.json`, mô phỏng hết hạn mức, treo (quá thời gian) và thoát mã khác 0. Chạy qua toàn bộ scheduler → runner → archive trên một repo git tạm, gồm cả 3 suất song song và hủy giữa chừng.
- **Không gọi Claude thật trong test hay CI.**
- CI hiện có (`dxf-export-tests.yml`) thêm bước `python -m pytest luan_app/tests -q`.
- **Nghiệm thu thủ công trên máy Admin:**
  1. chạy 1 job thật từ một máy khác trong LAN;
  2. chạy 3 job song song;
  3. hủy giữa chừng;
  4. khởi động lại Windows khi đang có hàng đợi;
  5. kiểm tra giao diện sáng/tối trên 2 trình duyệt.

## 13. Rủi ro và điều cần xác minh khi triển khai

1. **Cờ quyền của `claude -p` 2.1.301:** cờ cho chế độ không hỏi quyền, và mẫu `Edit(rules/**)` có chặn được đường dẫn tương đối trong worktree không. Xác minh bằng một phiên thử ở bước đầu. Nếu denylist theo đường dẫn không hoạt động thì dựa vào worktree cô lập cộng kiểm tra `git status` sau job.
2. **Nhận ra hết hạn mức:** cần mẫu sự kiện thật. Trong lúc chưa có thì xem mọi lỗi có chữ "limit"/"usage" là hết hạn mức.
3. **Hook SessionStart của repo** (`job.py hook`) chạy trong worktree. Không gây hại, chỉ in trạng thái.
4. Ba phiên chạy song song dùng chung hạn mức của tài khoản Admin. Hết hạn mức thì hàng đợi tạm dừng (4.5).
5. Đường dẫn dài trên Windows: worktree đặt ở `C:\TrainAiCad-slots\slotN`, gói run ở `%LOCALAPPDATA%\LuanApp\runs\<run-id ngắn>`.
