# 521019-05 — quy tắc góc cùng chiều theo độ sâu cánh (061247, 061248) — USER APPROVED 2026-10-20

Nguồn: DXF mẫu của người dùng cho 061247 và 061248 (bóc tách từng mặt + hình hoàn thiện) và DXF `khyetT` giả định. Chỉ ghi số liệu, không sao chép DXF mẫu vào repo.

## 061247 (SPHC-P t3.2, Nobi 5.5 viết tay)
- Chuỗi Y: F1 202x43.2 | F2 265x(43.2+3.2) | F3 265x83.2 | F4 265x30: 43.2 + 46.4 + 83.2 + 30 - 3x5.5 = 186.3. Chuỗi X: 265 + 30 - 5.5 = 289.5 (F5 30x83.2 bên phải F3).
- Số 43.2 của F2 là kích thước IN (ID) đo ở một phía, vì hai nếp trên và dưới F2 ngược chiều nhau (đoạn nhỏ giống nếp Z): OD = 43.2 + t = 46.4.
- Hướng nếp đọc từ ba hình chiếu (mid: nét liền = cánh hướng về phía người nhìn, nét đứt = khuất): F4 và F5 cùng chiều, F2 ngược chiều với F5.
- Góc trên phải F3 (F4 và F5 cùng chiều, cùng sâu 30): lùi cạnh nào cũng được; DXF mẫu lùi F5 (721.08 -> 717.88 trong khung gốc), slit 3.4 từ cạnh lùi, dẫn 3, R0.5.
- Góc dưới phải F3 (F2 và F5 ngược chiều): không lùi; lỗ thoát R = t = 3.2, tâm tại góc F3, nối bằng cung R0.5.
- Ví dụ giả định "khuyết_t" (F4 sâu 70, F5 sâu 30): lùi F4 để lại phần khuyết 3.2 x 30; phải lùi F5 (cánh nông hơn).

## 061248 (SPHC-P t3.2, Nobi 5.2)
- Góc dưới phải: cánh dưới sâu 50, cánh phải sâu 28.2 -> cánh phải lùi. Góc trên phải: cùng sâu 28.2 -> cánh phải lùi cũng đúng.
- Hai lỗ obround thuộc cánh dưới (không phải cánh trên).

## Quy tắc đã đưa vào repo
`references/BEND_EDGE_RELIEF_90.md` mục 9, `tools/corner_retreat.py`, `tools/bend_end_guard.py` (witness `corner_retreat`); đã bỏ cơ chế `CROSSING_BEND` vì trùng với slit theo bậc. Ngưỡng độ sâu 0.1 mm. Không lùi được cả hai cánh (chưa gặp) -> ghép như thường và FLAG cục bộ.

## 055958 xác nhận (2026-10-21) và bảng vòi cột G
- 055958 là góc hộp cùng chiều bình thường: hai cánh OD 55 (phẳng 45.32 = 55 − 9.68, t5) bằng độ sâu → cánh có cạnh uốn dài hơn (cánh trái) lùi t (570 → 565), S = −t, slit 5.2 từ x = 204.208 đến 209.408, vòi 6 (bảng cột G, t4–5 → 6), đầu vòi (198.208, 571) trên phân giác 45°. `connected_slit` tái hiện đúng DXF mẫu của người dùng (tests/test_lead_table.py).
- Vòi lấy từ `references/LEAD_TABLE.yaml` (một lần chốt: người dùng duyệt 2026-10-21). t ≥ 19 (hàng móc) và t nằm giữa các hàng bảng → FLAG `LEAD_VALUE_UNPROVED`, không tự vẽ; người dùng: t lớn nhất thực tế là 16.
