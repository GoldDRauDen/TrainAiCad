# TrainAiCad

TrainAiCad là môi trường huấn luyện và calibration AI theo quy trình CAD thực tế của người dùng.

Người dùng cung cấp công việc, bản vẽ, kết quả chuẩn và sửa các lỗi của AI. AI phải phân tích nguyên nhân, rút ra lesson và đề xuất các quy tắc có thể tái sử dụng.

Mỗi lesson chỉ được đưa vào skill sau khi người dùng trực tiếp phê duyệt.

GitHub không phải môi trường training. Repository chỉ lưu các **production skills đã được xác nhận**, regression cases và tài liệu cần thiết để một AI mới có thể đọc repo và thực hiện công việc đúng quy trình mà không cần lịch sử hội thoại trước đó.

## Workflow

1. Train/calibrate trong dự án TrainAiCad.
2. AI phân tích lỗi và đề xuất lesson/rule.
3. Người dùng trực tiếp phê duyệt từng lesson.
4. Chỉ lesson đã được phê duyệt mới được chuẩn hóa thành production skill hoặc regression case.
5. Production skill được cập nhật lên repository theo version.
6. AI khác phải có thể đọc repository và thực hiện công việc mà không cần lịch sử hội thoại cũ.

## Repository principle

- Repo này **không** lưu training thô hoặc lesson chưa được duyệt.
- Không tự động biến một case riêng lẻ thành universal rule.
- Không cập nhật production skill nếu chưa có phê duyệt trực tiếp từ người dùng.
- Mỗi thay đổi production cần giữ khả năng regression và truy vết version.

**No approved lesson, no production skill update.**
