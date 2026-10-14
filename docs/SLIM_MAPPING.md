# Sơ đồ ánh xạ: SKILL.md và AI_ENTRYPOINT.md (bản nháp, chưa áp dụng)

Trạng thái: **đã áp dụng (2026-10-14)**. Mọi mục dưới đây đã được đối chiếu từng câu với file đích trước khi thay bằng con trỏ. Xem mục "Kết quả áp dụng" ở cuối. Bảng bên dưới giữ nguyên làm hồ sơ kế hoạch ban đầu; ước lượng tiết kiệm trong đó lạc quan hơn kết quả thật.

## Cách đọc các cột

- **Byte**: kích thước của mục trong file nguồn.
- **Khớp định danh**: tỷ lệ định danh viết hoa (ví dụ `BEND_ATTACHMENT_EDGE_LOCKED`) trong mục mà cũng xuất hiện trong file đích. Đây chỉ là bộ lọc sơ bộ. Nó không chứng minh nội dung tương đương, và mục có ít định danh thì tỷ lệ 100% không có nhiều ý nghĩa.
- **Hành động đề xuất**:
  - **KEEP**: giữ nguyên, vì là nguồn duy nhất hoặc bị test khóa.
  - **CON TRỎ (cần kiểm tra từng câu)**: thay bằng con trỏ tới file đích sau khi xác nhận mọi quy tắc đã có ở đó.
  - **GỘP (cần kiểm tra)**: có phần chưa thấy ở đích, phải chuyển phần đó trước.

## AI_ENTRYPOINT.md

| Mục | Byte | Khớp định danh | Đích đề xuất | Hành động |
|---|---:|---|---|---|
| Đầu file, bản hiện hành V4.34 và phần bổ sung | ~2.4 KB | n/a | — | KEEP (test khóa "Current production release is **V4.34**", `TrainAiCad-CANONICAL-V4.34`) |
| Invocation contract | 497 | n/a | — | KEEP (test khóa) |
| 1. Normal production flow | 1656 | n/a | — | KEEP: đây là nguồn duy nhất của luồng |
| 2. V4.33 holistic / reference firewall | 1826 | 50% (4/8) | `HOLISTIC_ENGINEERING_CHALLENGE.md`, `REFERENCE_EXPOSURE_FIREWALL.md`, `PART_IDENTITY_GRAPH.md` | GỘP (kiểm tra: `SOURCE_ONLY_SNAPSHOT`, `REFERENCE_ASSISTED_UNDERSTANDING` chưa thấy ở đích) |
| 2A. V4.32 attachment edge / OD | 2208 | 79% (11/14) | `BEND_ATTACHMENT_EDGE_OWNERSHIP.md`, `FORMED_PROFILE_OD_MEASUREMENT.md` | GỘP (kiểm tra: `BEND_UNFOLD`, `FACE_GRAPH_UNFOLD_PROTOCOL`) |
| 2B. V4.31 canonical completeness | 1737 | 71% (5/7) | `CANONICAL_MEMBER_COMPLETENESS.md` | GỘP (kiểm tra: `CANONICAL_INPUT_SCHEMA_V431`, `SOURCE_VIEW`) |
| 3. V4.30 runtime authority | 676 | 100% (5/5) | `RUNTIME_AUTHORITY_GUARD.md` | CON TRỎ (kiểm tra từng câu) |
| 4. Census before specialized rules | 532 | — | `FEATURE_CENSUS.md` | KEEP hoặc chuyển nguyên văn |
| 4a. V4.30 feature group | 1224 | 100% (7/7) | `SOURCE_FEATURE_GROUP_CLOSURE.md` | CON TRỎ (kiểm tra từng câu) |
| 4b. V4.29 manufacturing note | 880 | 100% (1/1) | `SOURCE_MANUFACTURING_NOTE_CENSUS.md` | CON TRỎ (chỉ 1 định danh, kiểm tra kỹ) |
| 4c. V4.28 face creation | 443 | 100% (4/4) | `FACE_CREATION_BEND_EVIDENCE.md` | CON TRỎ (kiểm tra từng câu) |
| 4d. V4.27 weld-cue | 300 | 100% (2/2) | `WELD_SITE_KEGAKI_CLOSURE.md` | CON TRỎ (kiểm tra từng câu) |
| 4e. V4.26 physical curve | 337 | 100% (1/1) | `DXF_PHYSICAL_CURVE_DECODING.md` | CON TRỎ (chỉ 1 định danh, kiểm tra kỹ) |
| 5. Bent / multi-face gate | 1635 | 80% (8/10) | `BEND_EDGE_RELIEF_90.md`, `BEND_UNFOLD.md` | CON TRỎ (kiểm tra `BEND_UNFOLD`, `FACE_CREATION_BEND_EVIDENCE`) |
| 6. Source and mode routing | 1464 | 57% (8/14) | `ROUTER.yaml` (đã là nguồn máy đọc) | GỘP (chuyển các định danh chưa thấy: `RAW_DATA_SNAPSHOT`, `PHYSICAL_DATA_BASELINE`, `SAME_PARAMETER_GATE`, `MANUFACTURING_CHANGE_LEDGER`) |
| 7. Release wiring index | 189 | — | `docs/RELEASE_WIRING_INDEX.md` | Đã là con trỏ, KEEP |
| 8. Production completeness | 990 | 75% (3/4) | `ROUTER.yaml` post_route_checks | GỘP (chuyển `BEND_ATTACHMENT_EDGE_LOCKED` nếu chưa có) |
| 9. Portable and history policy | 922 | 67% (2/3) | `ROUTER.yaml` history_policy | GỘP (chuyển `SKILL_LISPCAD_CURRENT` và cảnh báo cũ) |
| 10. Regression and output | 578 | 100% (1/1) | `VALIDATION.md`, `CAD_OUTPUT.md` | CON TRỎ (chỉ 1 định danh, kiểm tra kỹ) |
| 11. MCP boundary | 317 | — | — | KEEP |

Ước lượng tiết kiệm (chỉ tính sau khi kiểm tra từng câu):
- Mục CON TRỎ: khoảng 6.0 KB.
- Mục GỘP: khoảng 7.1 KB, nhưng còn phần phải chuyển trước khi xóa.

## SKILL.md

| Mục | Byte | Đề xuất | Lý do |
|---|---:|---|---|
| 0. Compatibility and tool gate | 928 | KEEP | Nội dung cross-agent, không có ở nơi khác |
| 1. Production authority | 910 | KEEP, rút gọn | Test khóa các thuật ngữ `AI_BOOTSTRAP.md`, `AI_ENTRYPOINT.md`, `ROUTER.yaml`, `Geometry JSON`, `saved-DXF`, `REVIEW`, `SOURCE` |
| 2. Trigger and per-code workflow | 3455 | GỘP lớn | Trùng luồng ở `AI_ENTRYPOINT.md` §1. Giữ phần đặc thù: quy trình theo từng mã, xử lý độc lập từng mã, bàn giao PASS/REVIEW |
| 3. Canonical status and artifacts | 1684 | GỘP (kiểm tra) | Trùng `AI_ENTRYPOINT.md` và README. Test khóa "Implemented canonical production artifact contract" và "every code, including REVIEW/FLAG" |
| 4. Execution and QA rules | 601 | KEEP | Nội dung đặc thù |
| 5. Portable one-file use | 471 | KEEP | Nội dung đặc thù |

Ước lượng tiết kiệm SKILL: khoảng 2.5 đến 3.5 KB, tùy kết quả kiểm tra mục 2 và 3.

## Quyết định cần bạn xác nhận

1. **Nguyên tắc:** chỉ thay bằng con trỏ khi đã kiểm tra từng câu. Nếu chưa chắc thì giữ nguyên.
2. **SKILL §2 (3455 byte)** có nên rút gọn thành danh sách 8 bước ngắn, trỏ về `AI_ENTRYPOINT.md` §1 không? Đây là phần tiết kiệm lớn nhất.
3. **Mục 6 và 9 của ENTRYPOINT** có nên chuyển hẳn về `ROUTER.yaml` không? Router là nguồn máy đọc, còn ENTRYPOINT chỉ là bản mô tả lại.
4. **Test khóa cụm chữ:** mọi thay đổi chữ ở các mục bị test khóa đều phải sửa test trong cùng commit. Mình sẽ liệt kê từng test trước khi sửa.

## Ghi chú

- Chỉ mục gate (`docs/GATE_INDEX.yaml`) bắt được tên theo hậu tố. Tên như `SOURCE_ONLY_SNAPSHOT` chưa được bắt, nên bảng này chưa dùng nó để xác nhận mục nào bị thiếu.

## Kết quả áp dụng

- `AI_ENTRYPOINT.md`: 20864 → 13290 byte. `SKILL.md`: 8523 → 5991 byte. Tổng giảm khoảng 10.1 KB (34%).
- §6 và §9 của ENTRYPOINT: nội dung chuyển sang `references/SOURCE_DATA_CLASSIFICATION.md` và `ROUTER.yaml` `history_policy` (tổng byte gần như không đổi; lợi ích là rule nằm ở file máy đọc).
- §2, §2A, §2B, §3, §4a–4e, §5, §8, §10 của ENTRYPOINT và §2, §3 của SKILL: mọi câu được đối chiếu với file đích. Câu đã có thì bỏ, chỉ giữ điều kiện nạp và định danh gate.
- Phán đoán "phủ về ngữ nghĩa" (không trùng nguyên văn): câu cảnh báo cuối SKILL §3 (so với `CAD_OUTPUT.md` §7); câu "valid DXF/bbox không override" của §2B (đã có dạng mạnh hơn ở ENTRYPOINT §8); các ghi chú "Vx.y không đổi schema" (đã có ở phần bổ sung V4.34 đầu file); danh sách "load" của §2A (đã có ở `ROUTER.yaml` `mode_routes`).
- Không sửa test khóa cụm chữ nào (chỉ `tests/test_gate_index.py` và một assertion regression `check_521001_03_v423.py`, ở các commit trước).

