# Rà soát danh sách `review_candidates` của docs/GATE_INDEX.yaml

Trạng thái: **đã duyệt (2026-10-14)**. Quyết định nằm ở cuối file. Chỉ mục không định nghĩa rule, nên phân loại sai chỉ làm sai bảng tra cứu, không đổi hành vi CAD.

Tổng: 81 định danh. Chia 3 nhóm.

## Nhóm A: có vẻ là gate (kiểm tra bắt buộc). Đề xuất thêm vào `gates`

Các tên này mô tả một kiểm tra hoặc một khóa phải thỏa trước khi xuất file.

- Khóa: `BEND_ATTACHMENT_EDGE_LOCKED`, `BEND_DOMAIN_LOCKED`, `BEND_SIGN_LOCKED`, `FACE_ORDER_LOCKED`, `FEATURE_OWNERSHIP_LOCKED`, `TOPOLOGY_LOCKED`, `DIMENSION_WITNESS_LOCKED`
- Đối chiếu nguồn–canonical: `SOURCE_PHYSICAL_TO_CANONICAL`, `CANONICAL_TO_SOURCE_PHYSICAL`, `SOURCE_EXHAUSTED_BEFORE_VIEWS_ONLY`, `CONSTRAINTS_CLOSED`, `FINAL_ENGINEERING_SANITY_REVIEW`, `ENGINEERING_ANOMALY_DETECTED`
- Ranh giới tham chiếu: `SOURCE_ONLY_SNAPSHOT`, `SAME_PHYSICAL_PARAMETER_BEFORE_REFERENCE_CONFLICT`, `POST_REFERENCE_SOURCE_REWRITE`, `SAME_FACE_FIRST`
- Snapshot đóng băng: `RAW_DATA_SNAPSHOT`, `PHYSICAL_DATA_BASELINE`, `THICKNESS_SINGLE_USE`
- Kiểm tra bổ sung: `PART_IDENTITY_COLLISION`, `DATA_PDF_DIM_DIFF`, `SAVED_DXF_LAYER0_ENTITY_IDS`, `FOLD_BACK` (là phần đầu của `FOLD_BACK_SOURCE_REPROJECTION`, nên nên ghi đầy đủ tên này)

## Nhóm B: nhãn trạng thái hoặc phân loại (không phải gate)

Đây là giá trị đầu ra hoặc nhãn chặn, không phải kiểm tra.

- Đầu ra: `REVIEW_ONLY`, `VIEWS_ONLY`, `PASS_CODE`, `FLAGGED_NO_GEOMETRY`, `WELD_REQUIRED_CUE`
- Xung đột và trạng thái: `CONFIRM_CONFLICT`, `SOURCE_CONFLICT`, `SOURCE_UNIT_CONFLICT`, `REFERENCE_ANOMALY`, `REFERENCE_ASSISTED_UNDERSTANDING`, `CUSTOMER_CONFIRMATION_PENDING`, `HANDWRITTEN_NOBI_DIFFERS_FROM_TABLE`, `IRRELEVANT_TO_MANUFACTURING`
- Nhãn chặn: `TRUE_SOURCE_AMBIGUITY`, `ROUTING_COVERAGE_GAP`, `GEOMETRY_DECODE_GAP`, `PART_IDENTITY_GAP`, `SOURCE_MEMBER_CENSUS_GAP`, `DATA_REQUIRED_MISSING`
- Phân loại hình học: `DIMENSION_HELPER_OR_CONSTRUCTION`, `DUPLICATE_COINCIDENT`, `HIDDEN_OR_PROJECTION_ONLY`, `PDF_PRIORITY`, `DATA_NO_DIM_COMPARE` (giá trị chính sách khách hàng)

## Nhóm C: tên hình học, cơ chế, file, chế độ (không phải gate)

- Cạnh và điểm: `BEND_EDGE`, `FREE_EDGE`, `OUTER_EDGE`, `LEFT_EDGE`, `RIGHT_EDGE`, `CONTOUR_EDGE`, `HOLE_CENTER`, `SLOT_MIDPOINT`, `INSIDE_VIEW`, `NEAREST_VIEW_EDGE`, `PHYSICAL_CUT_OR_FACE_EDGE`, `PHYSICAL_HOLE_SLOT_OR_FEATURE`
- Đồ thị và định danh: `FACE_GRAPH`, `ASSEMBLY_DATUM_GRAPH`, `ENTITY_ID`, `CANONICAL_ENTITY_IDS`, `MANUFACTURING_CANONICAL`, `SOURCE_FEATURE_GROUP`, `FEATURE_FAMILY`
- Cơ chế: `BEND_END_OFFSET_90`, `DETAILED_SOURCE_BUNDLE`, `THREAD_NOMINAL_REFERENCE`, `THREAD_PREHOLE_SOURCE`, `THICKNESS_REPRESENTATION`
- View và dữ liệu: `SOURCE_VIEW`, `MEASUREMENT_CONSTRUCTION_VIEW`, `NEW_PDF_TO_DXF`
- File và tiêu đề: `SKILL_LISPCAD_CURRENT`, `LEGACY_COMPATIBILITY_TEXT`

## Cần bạn xác nhận

1. Nhóm A có đúng là gate không? Đặc biệt `THICKNESS_SINGLE_USE`, `RAW_DATA_SNAPSHOT`, `PHYSICAL_DATA_BASELINE`, `DATA_PDF_DIM_DIFF`.
2. `NEAREST_VIEW_EDGE` là một cấm (không được coi là bằng chứng). Có nên đưa vào nhóm gate dưới dạng quy tắc phủ định không?
3. `DATA_NO_DIM_COMPARE` là giá trị chính sách khách hàng. Nó nên nằm trong catalog, không nằm trong chỉ mục gate.

## Ghi chú

- Chỉ mục vẫn sinh tự động và không định nghĩa rule. Khi bạn chốt nhóm, mình sẽ đưa nhóm A vào `gates` và chuyển phần còn lại sang danh sách đã biết.

## Quyết định đã duyệt

1. `THICKNESS_SINGLE_USE`, `RAW_DATA_SNAPSHOT`, `PHYSICAL_DATA_BASELINE`, `DATA_PDF_DIM_DIFF` là gate.
2. `NEAREST_VIEW_EDGE` là gate.
3. `DATA_NO_DIM_COMPARE` giữ ngoài chỉ mục gate, thuộc catalog khách hàng.

Các gate đã duyệt được liệt kê trong `APPROVED_GATES` của `tools/build_gate_index.py`. Gate đã duyệt gồm nhóm A, cộng thêm `NEAREST_VIEW_EDGE`. `FOLD_BACK` được thay bằng tên đầy đủ `FOLD_BACK_SOURCE_REPROJECTION`.
