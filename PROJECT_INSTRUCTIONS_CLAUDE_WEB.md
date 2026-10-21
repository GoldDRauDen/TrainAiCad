# TrainAiCad — Claude web Project Instructions (dán phần trong khung vào Project Instructions)

```text
Repo GoldDRauDen/TrainAiCad là production authority cho CAD kim loại tấm. Với mọi job PDF / ảnh / customer DXF DATA, hoặc khi user chỉ nói "E2E":

1. Bật code execution. Trong sandbox: git clone --depth 1 https://github.com/GoldDRauDen/TrainAiCad, rồi pip install -r TrainAiCad/requirements.txt. Nếu không clone được, yêu cầu user đính kèm file zip của repo (GitHub > Code > Download ZIP) và giải nén; không làm job khi chưa có repo.
2. Đọc SKILL.md rồi JOB_CARD.md. Đọc lại JOB_CARD.md ở đầu MỖI bước L0/L1/L2/L3 (cat JOB_CARD.md), không dựa vào trí nhớ.
3. Bản vẽ: dùng tools/pdf_views.py (info, render có lưới, text --dims để lấy số chính xác, crop 600 dpi). Mọi số dùng phải nằm trong sổ kích thước có 2 đầu đường gióng.
4. Bảng tra (Nobi, Laser R, lỗ POINT/CIRCLE, lỗ khoan mồi ren, ID→OD, trải phôi): chỉ dùng tools/lookup.py, không tra bằng mắt.
5. Làm từng mã một; lưu kết quả từng mã vào file trong sandbox (census.json, ledger, job.json) thay vì giữ trong chat. Cặp mã đối xứng: chạy tools/pair_consistency.py.
6. Luôn vẽ hết mọi mã: chỗ chưa chắc vẽ Magenta + FLAG tiếng Việt, trạng thái REVIEW; không dừng job để hỏi. Thiếu Nobi: tách bích cách 10 mm + FLAG.
7. Xuất bằng tools/export_canonical_dxf.py, mở lại file DXF đã lưu để kiểm, rồi đưa file cho user tải. Báo cáo theo CAD_OUTPUT.md §11, câu hỏi cho khách để ở cuối.
8. Không sửa repo nếu user chưa nói DUYỆT/PUSH. Nếu repo hoặc tool không chạy được, báo đúng chỗ bị chặn, không giả vờ đã làm.
```

Phần này chỉ là con trỏ. Nếu có gì mâu thuẫn với rule trong repo hiện tại thì repo thắng, trừ chỉ dẫn trực tiếp của user.
