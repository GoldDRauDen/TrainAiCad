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

- Timeline giao diện đang lấy tối đa 1.000 sự kiện đầu, chưa ghép cursor để theo dõi phiên dài hơn.
- Chuẩn bị PDF/DXF và một số hash/đọc file chi tiết còn đồng bộ trên event loop; file lớn hoặc SMB chậm có thể làm UI điều khiển phản hồi chậm. Chưa cam kết độ trễ điều khiển trên mạng LAN thật.
- Tổng thời gian tạm dừng có thể thiếu khoảng dừng lịch sử sau khi đã tiếp tục/hoàn tất; cần kiểm thử timeline riêng.
- Có cảnh báo tương thích fitz/Starlette ở một số lệnh kiểm tra, không làm bộ kiểm thử thất bại.
- Cần chạy Windows launcher, UNC/SMB bị ngắt/khóa, tài khoản Claude chính và 9Router thật, giới hạn quyền CLI và benchmark trên nguồn đã xác nhận trước nghiệm thu.

## Quyết định vận hành giữ từ thiết kế

- Pause của người dùng được giữ khi nguồn job thay đổi.
- Khi người dùng chọn 9Router, QA độc lập cũng dùng gateway đã xác minh; Claude chính vẫn dùng QA riêng theo cấu hình bắt buộc. Chất lượng model gateway cần nghiệm thu riêng.
- Ghi LAN dùng tiến trình do app sở hữu để có thể dừng/reap client; không hứa rollback SMB phía server hay transaction nhiều file.
- Không sửa quy tắc kỹ thuật, không merge main tự động.
