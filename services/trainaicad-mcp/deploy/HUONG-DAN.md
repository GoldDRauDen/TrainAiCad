# TrainAiCad MCP V0.5 — phần bạn thực hiện sau

Code đã chuẩn bị để thử kết nối. Chưa có endpoint cloud và chưa xác nhận hoạt động trong ChatGPT. Toàn bộ thay đổi chỉ nằm trong `services/trainaicad-mcp/`; quy tắc và dữ liệu sản xuất của repo không đổi. Bản DXF canary vẫn **REVIEW ONLY / NO CUT**, mới kiểm tra một mã ở trang 5.

## 1. Đưa code vào nhánh riêng

Bản vá được tạo từ snapshot upstream `8467f2292cef3cb2212a83d1f10b93c1cd4190d5`. Không push lịch sử git trong gói nghiên cứu; hãy dùng checkout GitHub thật.

Trong PowerShell, tại checkout TrainAiCad:

```powershell
git status --short
git switch -c research/mcp-v05
git apply --check C:\DUONG-DAN\TrainAiCad-MCP-v05.patch
git apply C:\DUONG-DAN\TrainAiCad-MCP-v05.patch
git diff --name-only
```

Tất cả file trong diff phải bắt đầu bằng `services/trainaicad-mcp/`. Nếu `apply --check` thất bại do repo mới hơn, giữ nguyên repo và đối chiếu phần MCP; không ép ghi đè. Nếu checkout có thay đổi riêng của bạn, giữ chúng và dùng checkout/worktree sạch để áp dụng.

Nếu bạn đồng ý đưa lên GitHub, dùng nhánh này và mở PR. Chưa merge nhánh chính. Render có thể deploy từ nhánh thử nghiệm, nên chưa cần merge.

```powershell
git add services/trainaicad-mcp
git commit -m "Prepare MCP native files and Supabase OAuth research workflow"
git push -u origin research/mcp-v05
```

Những lệnh push trên là hướng dẫn để bạn chủ động thực hiện; assistant chưa push.

## 2. Tạo một dự án Supabase Free dành riêng cho CAD

1. Tạo project mới tại https://supabase.com/dashboard — chọn **Free**, không nâng cấp gói.
2. SQL Editor: chạy `deploy/supabase.sql` để tạo bucket **private** `trainaicad-private`.
3. Project Settings / API Keys: lấy **Project URL**, **publishable key** và **legacy service_role key**. Publishable key có thể nằm ở trang đăng nhập; service_role chỉ nhập vào backend Render, không gửi vào chat hay commit.
4. Authentication / Users: tạo một tài khoản email + mật khẩu dành cho bạn, đánh dấu email đã xác nhận; copy **User UUID**. Đây là tài khoản CAD, không phải mật khẩu tài khoản quản trị Supabase.
5. Authentication / Providers: tắt đăng ký tài khoản mới; dùng tài khoản đã tạo. Server cũng chỉ chấp nhận UUI`572cbd8a-75b5-41b2-8f44-1a68fc9fc4f8`'này.
6. Authentication / Signing Keys: chọn signing key **ES256 hoặc RS256**. Server từ chối HS256.
7. Authentication / OAuth Server: bật OAuth 2.1. Tạm để Dynamic Client Registration **tắt**; dùng client được đăng ký trước ở bước 4.

Supabase OAuth Server đang beta, không có phụ phí riêng và có trên các gói. Free project có thể bị pause; trước phiên làm việc hãy kiểm tra project vẫn hoạt động.

## 3. Tạo Render Free và lấy URL

1. https://dashboard.render.com — tạo Web Service từ nhánh `research/mcp-v05` của repo thật.
2. Runtime **Docker**, Instance **Free**; Dockerfile: `services/trainaicad-mcp/Dockerfile`; build context ở **gốc repo**. Không đặt Root Directory thành thư mục MCP vì Docker cần đọc quy tắc ở gốc repo.
3. Health Check Path: `/health`; Auto Deploy: **Off**. Blueprint tương đương nằm ở `deploy/render.yaml`.
4. Sau khi service được tạo, copy URL HTTPS dạng `https://TEN.onrender.com`. Để lấy callback ChatGPT trước khi có OAuth client, deploy lần đầu với `TRAINAICAD_AUTH_MODE=setup`, URL Render, Project URL/service_role, artifact secret, storage và commit SHA. Chế độ setup chỉ mở health/discovery; mọi CAD tool bị chặn. Khi hoàn tất bước 4, đổi thành `supabase` và điền đủ bảng dưới. Không chọn gói trả phí để khắc phục cold start.

| Biến môi trường Render | Giá trị |
|---|---|
| `TRAINAICAD_AUTH_MODE` | `supabase` |
| `TRAINAICAD_PUBLIC_URL` | URL HTTPS Render, chỉ origin, không `/mcp` |
| `TRAINAICAD_OWNER_ID` | User UUID từ Supabase |
| `TRAINAICAD_OAUTH_CLIENT_ID` | Client ID được tạo ở bước 4 |
| `TRAINAICAD_OAUTH_REDIRECT_URIS` | Callback HTTPS chính xác do ChatGPT cung cấp |
| `SUPABASE_URL` | Project URL |
| `SUPABASE_PUBLISHABLE_KEY` | Publishable key; không dùng secret/service_role |
| `SUPABASE_SERVICE_ROLE_KEY` | Legacy service_role key; chỉ lưu trong Render secrets |
| `TRAINAICAD_ARTIFACT_SECRET` | Chuỗi ngẫu nhiên ít nhất 32 ký tự; giữ ổn định sau restart |
| `TRAINAICAD_REQUIRE_DURABLE` | `1` |
| `TRAINAICAD_STORAGE_BUCKET` | `trainaicad-private` |
| `TRAINAICAD_STORAGE_NAMESPACE` | `research-owner` |
| `TRAINAICAD_SOURCE_COMMIT` | SHA của commit thực sự deploy |

Dockerfile đã đặt `TRAINAICAD_MCP_HOST=0.0.0.0`, Python và thư mục data. Render tự cấp `PORT`. Không bật `TRAINAICAD_ALLOW_PRIVATE_URL`; giá trị đó chỉ dùng cho thử nghiệm loopback cục bộ.

## 4. Đăng ký OAuth client và bật token hook

1. Trong giao diện kết nối MCP/plugin riêng của ChatGPT, chuẩn bị endpoint `https://TEN.onrender.com/mcp`, chọn OAuth. Copy **chính xác Redirect URI** ở phần quản lý kết nối. Tên menu có thể khác tùy tài khoản; nếu tài khoản không có chức năng tạo kết nối riêng, chưa thể kiểm tra bước này trên tài khoản đó.
2. Supabase / Authentication / OAuth Apps: tạo client **Confidential**, tên `TrainAiCad ChatGPT`; dán callback vừa copy, không wildcard. Lưu Client ID và Client Secret; nhập chúng vào phần OAuth của kết nối ChatGPT. Client Secret không nhập vào code, cũng không cần lưu ở backend MCP. Nếu giao diện ChatGPT yêu cầu scan/kết nối hoàn chỉnh ngay, giữ mục kết nối đang tạo và hoàn tất cấu hình client trước khi thử lại scan.
3. Nhập Client ID vào `TRAINAICAD_OAUTH_CLIENT_ID`; callback vào `TRAINAICAD_OAUTH_REDIRECT_URIS` trong Render.
4. Mở `deploy/supabase-oauth.sql`, thay **đủ 3 giá trị**:
   - `REPLACE_OAUTH_CLIENT_ID`: Client ID.
   - `REPLACE_OWNER_UUID`: UUID tài khoản CAD.
   - `REPLACE_HTTPS_RENDER_ORIGIN`: URL Render, không dấu `/` cuối; SQL tự nối `/mcp`.
5. Chạy SQL; Authentication / Hooks / Custom Access Token: chọn `public.trainaicad_access_token_hook`.
6. Authentication / URL Configuration: Site URL = origin Render. OAuth Server / Authorization Path = `/oauth/consent`.
7. Đổi `TRAINAICAD_AUTH_MODE` từ `setup` sang `supabase`, deploy lại Render với đủ cấu hình. Hook chỉ đổi audience và quyền CAD cho đúng owner + OAuth client; phiên đăng nhập thông thường giữ audience `authenticated`.

Dùng **project riêng** như trên để không thay hook của một ứng dụng khác. Nếu project đã có Custom Access Token Hook, tích hợp logic vào hook hiện có và kiểm tra trước, vì một project chỉ chọn một hook cho giai đoạn này.

Nếu callback được quản lý bởi ChatGPT thay đổi, cập nhật cả Supabase client và Render allowlist. Không tự đoán callback từ ví dụ. Server công bố issuer Supabase; discovery/token/PKCE do Supabase xử lý.

## 5. Kiểm tra rồi kết nối

Mở `https://TEN.onrender.com/health`: phải trả `ok`.
Mở `https://TEN.onrender.com/.well-known/oauth-protected-resource/mcp`: phải có resource đúng `https://TEN.onrender.com/mcp`.

Nếu có Node 22+:

```powershell
cd services/trainaicad-mcp
npm ci
npm run check:remote -- https://TEN.onrender.com
```

Nếu Render vừa ngủ, chờ service khởi động rồi chạy lại check. Script chỉ đọc metadata/health, không in token, không tạo CAD job.

Hoàn tất OAuth ở ChatGPT: đăng nhập bằng email/mật khẩu CAD đã tạo; xem quyền rồi chọn **Cho phép**. Scan tools phải thấy **14 tools**, trong đó có `open_chatgpt_cad_job`.

Nếu báo 401 sau đăng nhập: kiểm tra signing key, owner UUID, client ID, hook đã được chọn, audience = origin + `/mcp`, `trainaicad_access=true`. Ngắt kết nối và đăng nhập lại sau khi sửa hook để nhận token mới. Không gửi access token vào chat. Quyền bị thu hồi ở Supabase làm refresh bị chặn; JWT đã cấp có thể còn hiệu lực đến thời hạn token. Muốn chặn ngay, đổi owner/client allowlist trên backend.

## 6. Dùng PDF của job này

Chọn plugin/MCP TrainAiCad và đính kèm `520625-01(2).pdf`. Gửi:

> Job này PDF_ONLY, không có DATA DXF. Dùng open_chatgpt_cad_job với file đính kèm, đọc ảnh nguồn và quy tắc của job. Làm một mã end-to-end trước, kiểm tra kích thước/datum rồi xuất và đọc lại DXF. Trả link tải bằng get_cad_artifact; báo rõ phần chưa đủ căn cứ.

GPT phải dùng file params do ChatGPT cung cấp; không tự viết `download_url` từ đường dẫn sandbox, không gửi PDF base64. Nếu host không cấp file params hoặc không nhận schema, giữ job ở trạng thái chưa nhận nguồn và kiểm tra chức năng file của kết nối/plugin đó; code phía server không tự mở được mọi attachment.

Luồng: `open_chatgpt_cad_job` → `get_cad_rules` → `prepare_cad_source` → `get_cad_source_image` → evidence/routes → canonical geometry → `verify_cad_geometry` → `export_dxf` → `audit_dxf` → `get_cad_artifact`.

DXF trả dưới dạng link HTTPS ký số, hiệu lực 10 phút. Nếu hết hạn, gọi lại `get_cad_artifact` cho cùng job; không dựng lại bản vẽ. Kiểm tra tải file thật và mở lại trong CAD trước khi coi đường truyền hoàn tất.

## 7. Giới hạn và kết quả hiện tại

- Hosting/lưu trữ cấu hình Free; không thêm API model hay OCR trả phí. Tài khoản ChatGPT của bạn vẫn có hạn mức riêng.
- Render Free có cold start, filesystem tạm; checkpoint Supabase giữ dữ liệu. Chỉ **một process/writer cho một namespace**; chưa có cơ chế nhiều người dùng.
- Free storage có hạn; cache/checkpoint không có tác vụ dọn blobs cũ tự động. Theo dõi quota và dọn theo quy trình riêng, không xóa bucket giữa job.
- Dù file truyền được, chưa có xác nhận trong host ChatGPT, OAuth/Supabase cloud, Docker build và cold restart cloud cho đến khi thực hiện các bước trên.
- Bộ đọc/QA hiện chỉ cho phép xuất nghiên cứu đối với contour thẳng và lỗ tròn đã kiểm tra; các dạng uốn/slot/R-C phức tạp chưa đủ QA sẽ bị chặn. Có đường truyền DXF không có nghĩa là đã đủ năng lực xuất sản xuất cho mọi mã.
- Không thay đổi/huấn luyện thêm quy tắc sản xuất; không tự đánh dấu `PRODUCTION_PASS`.

## Tài liệu chính thức

- File params ChatGPT: https://developers.openai.com/plugins/reference#file-apis
- OAuth ChatGPT: https://developers.openai.com/plugins/build/auth
- Supabase OAuth setup và chi phí: https://supabase.com/docs/guides/auth/oauth-server/getting-started
- MCP với Supabase: https://supabase.com/docs/guides/auth/oauth-server/mcp-authentication
- Token hook/audience: https://supabase.com/docs/guides/auth/oauth-server/token-security
- Render Free: https://render.com/docs/free
- Supabase Free: https://supabase.com/pricing
