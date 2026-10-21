# LuanAppTools — VIEWS_ONLY phải có bằng chứng thử dựng (đặc tả)

Ngày: 18/10/2026. Trạng thái: thiết kế đã được người dùng duyệt bằng lời trong phiên 18/10; **đặc tả viết này chờ người dùng duyệt** trước khi lập kế hoạch. Nhánh local `codex/luanapp-cost-accuracy-20261017`, **chưa push**. Không sửa rule hay `tools/` sản xuất của repo (AGENTS.md §5); mọi thay đổi nằm trong `LuanAppTools/`.

## 1. Vấn đề và bằng chứng

Mục tiêu của người dùng: mở app, AI nhận job, đọc rule của repo, đọc bản vẽ, xuất DXF tổng đúng quy tắc repo vào thư mục job.

Run thật `48cf0b85…` (job `520925-07`, repo `b471194`, chế độ `conversation=job`, sonnet-5.5 high, hủy ở phút 14,7) cho hai mã `26-056152` và `26-056153` trạng thái **VIEWS_ONLY**, không có biên phẳng. Bằng chứng lấy từ checkpoint của run:

| Quan sát | Chi tiết |
| --- | --- |
| AI tự khớp số học viết tay với bản vẽ | `161=155+6`, `41=38+3`, `73=70+3`, `71=65+6`, tức `161+41−9,78=192,22` và `73+71−9,78=134,22` khép với các chân thấy trên view |
| Vẫn từ chối dùng | Lý do ghi: "chưa chứng minh chi tiết nào sở hữu phép tính" |
| Ghi chú số học không có chủ | `N7_HW_CALC2` được gán `codes: []` dù trang 2 chỉ có hai mã 056152/056153 |
| Kích thước slip bị dùng làm lý do bác | Ứng viên `C1`: "FAIL: slip size 155x70 is reference only…". Repo ghi slip chỉ để tham khảo (`CAD_OUTPUT.md`) |
| Cổng hiện tại chỉ kiểm hình thức | AI điền `source_exhausted`, `holistic_challenge_run`, liệt kê ứng viên với kết quả "UNPROVED". Cổng thỏa, nhưng không có lần dựng phẳng nào |
| Mã còn lại | 056153 đi nhanh (1,2 phút, 5k token) vì dùng lại hội thoại của 056152, nên sao chép luôn quyết định sai |

Rule của repo mà hành vi này vi phạm:

- `HOLISTIC_ENGINEERING_CHALLENGE` §3: số học phẳng viết tay đóng một kích thước chính trong khi chi tiết bị hạ thẳng xuống VIEWS_ONLY mà chưa thử dựng hình gập, là `ENGINEERING_ANOMALY_DETECTED` buộc mở lại nguồn.
- Cùng file §7: sự không chắc chắn cục bộ vẫn là cục bộ; một FLAG cục bộ không được ép cả chi tiết thành VIEWS_ONLY khi có phẳng chứng minh được.
- `DRAWING_READING.md`: chỉnh sửa viết tay áp cho chi tiết mà bối cảnh nguồn chỉ ra; phạm vi không rõ thì FLAG cục bộ, không bỏ.
- `KEGAKI.md` và `RIB.md`: huỷ RIB không tự huỷ KEGAKI định vị trên chi tiết chính. Người dùng xác nhận mã 056158 và 057722 là RIB, mã đã bỏ (theo người dùng: có sẵn), nhưng vẫn phải hàn, nên tấm chính vẫn cần KEGAKI định vị (khách 851 bắt buộc).

Phân loại theo từ vựng repo: `AI_INTERPRETATION_GAP` (HOLISTIC §5), không phải thiếu dữ liệu nguồn.

## 2. Mục tiêu và thước đo

Chi tiết có phẳng chứng minh được không bị hạ xuống VIEWS_ONLY chỉ vì một chỗ chưa chắc. VIEWS_ONLY chỉ được chấp nhận khi AI đã **thử dựng phẳng thật** và thất bại ở một cổng có tên của repo.

Thước đo:

1. Phát lại câu trả lời đã lưu của run `48cf0b85` qua cổng mới (không gọi AI): 056152 và 056153 bị chặn.
2. Test ngược: VIEWS_ONLY có bản thử thất bại ở cổng có tên thì được qua; chi tiết không phẳng hóa được thật sự không bị ép sai.
3. Nghiệm thu thật (chỉ khi người dùng cho phép chạy): 056152 ra biên phẳng kèm FLAG cục bộ cho KEGAKI, chấm bằng `bench/score_dxf.py`; so chi phí với run này (14,7 phút, khoảng 57k token đầu ra).

## 3. Phạm vi

Trong phạm vi: cổng thử dựng cho VIEWS_ONLY; kho kích thước in trên view; chủ sở hữu bắt buộc cho ghi chú số học phẳng; bản ghi chặn có cấu trúc.

Ngoài phạm vi (spec sau): bộ dựng sổ kê từ khai báo của AI, chồng hình lên PDF, vòng học và hàng đợi quyết định, sửa đọc nhầm chữ viết tay (ví dụ 対称 bị đọc thành "別部/逆部?"), kiểm tra văn bản lý do có nhắc kích thước slip.

Cổng này chỉ có thể **từ chối** một VIEWS_ONLY; nó không bao giờ biến VIEWS_ONLY thành PASS. Mọi cổng PASS của repo vẫn quyết định sau đó.

## 4. Thiết kế

### 4.1 Kho kích thước trong intake

- Schema intake (single_agent, `interaction_schema` trong `cad/pipeline.py`): mỗi `view` có mã thêm trường `dimensions`: mảng số, các kích thước in trên view đó (mảng rỗng khi view không có, ví dụ bảng slip).
- `INTAKE_CACHE_VERSION` tự đổi theo schema, nên inventory đã lưu của các job cũ không tái dùng; chấp nhận, chỉ tốn một lần intake lại.
- Chi phí đầu ra: vài chục số mỗi view.

### 4.2 Chủ sở hữu ghi chú số học phẳng

- `validate_inventory` thêm quy tắc: mọi ghi chú khớp `FLAT_ARITHMETIC` (đã có trong `cad/contract.py`) phải có `codes` khác rỗng và là tập con các mã của job.
- Lỗi đi vào đường sửa intake có sẵn (`inventory_repaired`, một lượt sửa), không thêm lượt mới.

### 4.3 Mô-đun đóng số học `cad/closure.py` (hàm thuần, kiểm thử riêng)

- `parse_flat_arithmetic(text)`: tách các số hạng có dấu và kết quả. Phép tính đúng khi `|Σ − r| < 0,005` (làm tròn hai chữ số thập phân).
- `terms_close(positive_terms, dimensions, t)`: mỗi số hạng dương phải bằng một kích thước trong kho của view, hoặc tổng hai kích thước khác nhau trong kho, hoặc kích thước ± độ dày `t`. Số hạng âm (Nobi) không cần có trong kho.
- `closed_notes(code, notes, views, t)`: ghi chú được coi là của mã khi `codes` chứa mã đó (hoặc `codes` rỗng và trang của ghi chú thuộc `page_ids` của mã). Trả về danh sách ghi chú **đã đóng** cùng phương trình khớp.
- Đây là kiểm tra heuristic có chủ ý: chỉ dùng để quyết định **có cần thử dựng trước khi bỏ cuộc hay không**. Khớp nhầm chỉ khiến AI phải thử dựng một lần; không làm sai kết quả DXF.

### 4.4 Cổng nhận VIEWS_ONLY (`ViewsOnlyAdmission`)

Chạy ở hai chỗ, cùng một hàm:

1. Trong tool `validate` (`HostTools.validate` ở `ai/tools.py`): lỗi trả về trong cùng hội thoại, không tốn lượt mới.
2. Sau câu trả lời cuối (`CadPipeline.run`, cạnh `check_flat_attempt`): nếu AI bỏ qua `validate`, phần này chặn và dùng lượt thử thứ hai.

Quy tắc:

- Nếu `status != VIEWS_ONLY`: cổng không làm gì, chỉ ghi lại kết quả mỗi lần `validate` (đạt hoặc thất bại kèm tên cổng) vào lịch sử cuộc hội thoại.
- Nếu `status == VIEWS_ONLY` và `closed_notes` rỗng: nhận như hiện tại.
- Nếu `status == VIEWS_ONLY` và có ghi chú đã đóng: chỉ nhận khi lịch sử cuộc hội thoại có **bản thử** thỏa cả ba điều:
  1. gửi tới `validate` với `status != VIEWS_ONLY`;
  2. thất bại ở một cổng có tên (`GateIndex.advise` trả kết quả, hoặc lỗi chứa mã IN HOA dạng `A_B_C` mà repo dùng);
  3. biên ngoài của bản thử có một cạnh bbox bằng kết quả `r` của ghi chú đã đóng (±0,011, dung sai hiện có của repo cho khép Nobi), để AI không qua cổng bằng một hình chữ nhật bừa.
- Không đạt: trả lỗi `VIEWS_ONLY_ADMISSION` nêu phương trình host đã khớp (ví dụ `161=155+6, 41=38+3 → 192,22`), dẫn `HOLISTIC` §3 và §7, và yêu cầu dựng phẳng, FLAG riêng phần chưa chứng minh được.
- Lặp lại cùng lỗi theo cơ chế có sẵn: lần thứ ba kết thúc lượt của mã (`validation_stalled`), không dừng cả job.

### 4.5 Bản ghi chặn

- Phần có thể khai trường `blocker` (đối tượng): `class` thuộc 7 lớp của `HOLISTIC` §5, `rule` (đường dẫn rule đang chặn), `evidence`. `prepare_part` tách trường này ra khỏi part trước khi vào exporter (đây là khóa của host, không nằm trong hợp đồng repo).
- Host ghi vào checkpoint `parts[code].blocker` và phát sự kiện `blocker_recorded`; hiển thị trong dòng thời gian hoạt động có sẵn của giao diện.
- Ghi bản ghi chặn không thay đổi quyết định nhận hay từ chối VIEWS_ONLY ở §4.4; nó là dữ liệu cho spec vòng học.

## 5. Kiểm thử

- Dữ liệu thử rút gọn từ run `48cf0b85` nhưng **bỏ tên khách và mã vạch**: giữ chuỗi số học, các kích thước view, cấu trúc `status`/`flags`/`face_graph_candidates` của câu trả lời. Đặt ở `LuanAppTools/tests/fixtures/`.
- `test_closure.py`: `161+41−9,78=192,22` và `73+71−9,78=134,22` đóng với kho kích thước của view 056152; `80+60−9,78=130,22` đóng với view của 056159; ghi chú có số hạng không có trong kho thì không đóng; sai số học (±0,01) bị bác.
- `test_views_only_admission.py` (runner giả, exporter thật từ snapshot như các test hiện có): VIEWS_ONLY bị chặn khi chưa có bản thử; qua khi có bản thử thất bại ở cổng có tên và bbox khớp `r`; không qua khi bản thử là hình chữ nhật không khớp `r`; `status != VIEWS_ONLY` không bị đụng.
- `test_inventory_owner.py`: ghi chú số học có `codes` rỗng bị `validate_inventory` bác và đi vào đường sửa intake.
- Chạy toàn bộ `tests` và `LuanAppTools/tests`; test đã biết fail trên `main` (`test_cancel_terminates_provider_process`) ghi riêng. Phạm vi không chạm `tools/` hay rule, nên không cần chạy lại các kiểm tra rule của repo.

## 6. Rủi ro đã biết

- AI ghi kho kích thước sai hoặc thiếu: cổng không nhận ra số học đã đóng, hành vi quay về như hiện tại (không xấu thêm).
- AI cố tình gửi bản thử chỉ để mở khóa VIEWS_ONLY: điều kiện 3 (bbox khớp `r`) chặn dạng rẻ nhất. Một bản thử "đúng kích thước nhưng sai topology" vẫn qua được cổng, và mọi lỗi topology thật sẽ do cổng PASS của repo bắt.
- Độ chính xác đọc chữ viết tay vẫn do AI quyết định; spec này không sửa việc đó.
- Một chi tiết thật sự không phẳng hóa được: chi phí thêm là một bản thử (khoảng 10–20k token đầu ra), không chặn kết quả VIEWS_ONLY hợp lệ.

## 7. Điều kiện để chạy thật

Mọi lần chạy thật tốn hạn mức Pro nên chỉ thực hiện khi người dùng cho phép. Không push khi chưa có `PUSH`/`DUYỆT`.
