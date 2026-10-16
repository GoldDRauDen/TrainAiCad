# Tiến độ LuanAppTools — 16/10/2026

Đã tiếp nối bản triển khai đang dang dở trên nhánh `codex/luan-app-tools-20261015`. Đây là bản để chạy thử và review; chưa nghiệm thu trên tài khoản AI và mạng LAN thực của người dùng.

| Phần | Tiến độ |
| --- | --- |
| Lưu job, snapshot nguồn, khóa commit, lịch sử | Đã triển khai |
| Claude CLI, 9Router opt-in, giới hạn hai lượt giải, canonical/export/read-back | Đã triển khai; chưa kiểm tra bằng tài khoản thật |
| Scheduler/API, ba job, AI/Opus caps, pause/resume/cancel, phục hồi | Đã triển khai và kiểm thử tự động |
| Dashboard React tiếng Việt, PDF/DXF, output tổng/riêng, usage, lịch sử, xác nhận kiểm tra | Đã triển khai; build và kiểm thử UI |
| Launcher Windows, hướng dẫn cài, CI Windows/Linux | Đã thêm; cần kết quả Windows CI và chạy trên máy đích |
| Benchmark model trên bản vẽ đã xác nhận, độ chính xác với tài khoản thật/Windows SMB | Chưa thực hiện |

## Bằng chứng trong phiên tiếp nối

- `python -m pytest tests LuanAppTools/tests -q`: **390 passed** sau bổ sung kiểm thử Windows (xem CI của PR để biết kết quả từng nền tảng).
- `npm test`: **2 passed**; `npm run build`: typecheck và build thành công.
- HTTP E2E dùng SQLite, snapshot, canonical/export/read-back và Publisher thật; AI được thay bằng fixture nguồn tổng hợp. Đã kiểm tra mixed PASS/REVIEW, tổng REVIEW_ONLY, chỉ xuất riêng PASS, xác nhận kiểm tra, chạy lại, tải bản lưu lịch sử và chống quét output thành nguồn.
- 14 script regression trong workflow CAD hiện có: exit 0.
- Audit coverage, build rule index/bundle, benchmark routes, duplicate audit: exit 0; 51 active modules, không có đoạn trùng chéo theo audit.
- Review độc lập: không phát hiện Critical; ba Important đã có kiểm thử RED→GREEN: tạo thư mục probe gateway lần đầu, unpause/queue nguyên tử, tải DXF lưu lịch sử có hash và phạm vi đường dẫn đúng.
- Browser smoke với backend HTTP thật và provider fixture: quét/chọn/chạy, nhận mixed DXF, ghi nhận kiểm tra, giải mã preview SVG, lưu cài đặt; desktop 1440px và mobile 390px không có lỗi JavaScript hay tràn ngang.
- Lượt CI Windows đầu tìm lỗi phân cách đường dẫn và flush descriptor chỉ đọc. Đã sửa đường dẫn native bằng biểu diễn POSIX trước kiểm tra, dùng descriptor có quyền ghi khi fsync; kiểm thử timeout/cancel dùng tác vụ chậm chủ động và phân biệt worker với taskkill.
- CI bổ sung tìm hai khác biệt Windows: native PDF parser giữ file hỏng mở và fixture DXF có CRLF. Đọc PDF bằng buffer đã đóng file và dùng đúng newline trong fixture. Giao dịch release worker ghi kèm lỗi, không thể ghi đè lệnh hủy đến sau; kiểm thử interleaving RED→GREEN.
- Hai lỗi phát hiện khi khôi phục bản sửa dang dở cũng được kiểm thử lại: ý định pause trước khi dừng publisher, đọc lại lease sau đối soát tiến trình đang kết thúc.

Các con số trên không phải bằng chứng độ chính xác hình học từ AI thật trên bản vẽ khách hàng.

## Những điểm còn cần hoàn thiện/đánh giá

- Timeline đã ghép cursor qua mốc 1.000 sự kiện và khóa cùng run với chi tiết; hiện vẫn tải lại lịch sử mỗi lần refresh, cần benchmark với phiên rất dài.
- API đọc job/file/hash đã chuyển sang worker thread; có test health vẫn phản hồi trong khi đọc file bị chặn. Chuẩn bị PDF/DXF trong pipeline còn đồng bộ; chưa cam kết độ trễ điều khiển trên mạng LAN thật.
- Đã sửa thời gian pause lịch sử, hỗ trợ event cũ và chặn tăng sau hủy/kết thúc; có regression theo mốc thời gian cố định.
- Có cảnh báo tương thích fitz/Starlette ở một số lệnh kiểm tra, không làm bộ kiểm thử thất bại.
- Cần chạy Windows launcher, UNC/SMB bị ngắt/khóa, tài khoản Claude chính và 9Router thật, giới hạn quyền CLI và benchmark trên nguồn đã xác nhận trước nghiệm thu.

## Quyết định vận hành giữ từ thiết kế

- Pause của người dùng được giữ khi nguồn job thay đổi.
- Khi người dùng chọn 9Router, QA độc lập cũng dùng gateway đã xác minh; Claude chính vẫn dùng QA riêng theo cấu hình bắt buộc. Chất lượng model gateway cần nghiệm thu riêng.
- Ghi LAN dùng tiến trình do app sở hữu để có thể dừng/reap client; không hứa rollback SMB phía server hay transaction nhiều file.
- Không sửa quy tắc kỹ thuật, không merge main tự động.

## Tiếp nối kiểm tra 16/10/2026

- Đã xác minh commit nền `9513891` có workflow CAD và LuanAppTools thành công trên GitHub. PR hiện có: #45.
- Sửa timeline nhiều trang, khóa run ngay từ trang đầu và bỏ kết quả refresh đã cũ.
- Sửa phục hồi khi owner nhả lease giữa lần đọc trạng thái và giao dịch release; giao dịch kiểm tra quyền và chỉ ghi recovered khi thực sự thu hồi được. Test interleaving RED→GREEN.
- Rà soát độc lập phát hiện bộ đếm pause tiếp tục tăng sau hủy; đã sửa và có test RED→GREEN.
- Kiểm tra mới: bộ tổng Python **394 passed** (50.72s); bổ sung sau đó một biến thể event legacy đã chạy nhóm metrics **3 passed**. Frontend **5 passed**, typecheck/build thành công.
- Không có xác nhận mới trên tài khoản AI thật, máy Windows người dùng hoặc UNC/SMB thật. Chưa merge main.
