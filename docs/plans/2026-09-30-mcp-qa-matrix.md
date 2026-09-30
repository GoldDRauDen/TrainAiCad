# TrainAiCad MCP — ma trận test/QA/E2E

Trạng thái: **test specification, chưa triển khai các test mới**. Baseline hiện có 33 MCP + 77 Python tests đạt nhưng còn 5 nhóm false PASS đã tái hiện. Tham chiếu [implementation plan](2026-09-30-mcp-production-e2e.md).

U = unit; I = integration thật Node/Python/file; H = HTTP MCP E2E; V = phiên Codex đọc nguồn thật. Mỗi test ghi expected status/error, actual result, input/output hash và artifact path. H không được gọi nội bộ JobStore để bỏ qua tool schema. V không được thay bằng evidence fixture phát lại.

## Gate matrix

| ID | Đầu vào / hành động | Kết quả bắt buộc | Lớp / mốc |
|---|---|---|---|
| SRC01 | Chỉ khai tên/SHA, không có bytes được xác minh | Không SOURCE_VERIFIED / không production | U/I/H M2 |
| SRC02 | Descriptor SHA A, bind DRAWING hoặc DATA SHA B | Reject trước mutation; job và binding giữ nguyên | U/I/H M1–2 |
| SRC03 | Bind nguồn khác sau evidence hoặc sau PASS | Source locked; không giữ PASS cho revision mới | I/H M2 |
| SRC04 | Reference/AI DXF bị dùng như raw DATA | Source mode/authority conflict, không build production | U/H M2 |
| SRC05 | Family 646 thiếu DATA | DATA_REQUIRED_MISSING; không PDF_ONLY fallback | U/H/V M2 |
| SRC06 | PDF hỏng, page sai, crop ngoài trang, ảnh không đọc được | Lỗi cụ thể; không ghi coverage giả | I/H M2 |
| SRC07 | File local traversal/symlink ra ngoài allowlist | Từ chối đọc; không lộ nội dung tệp khác | U/I/H M2 |
| SRC08 | Cùng source/view/crop params gọi lại | Cache hit bytes/hash như cũ; không render lại vô cớ | I M2 |
| RULE01 | Entrypoint/CURRENT lệch hoặc thiếu mandatory module | SKILL_CONFLICT/FRESHNESS_UNVERIFIED phù hợp | U/I/H M2 |
| RULE02 | CURRENT/module thay giữa job hoặc sau restart | Dùng immutable pin hoặc yêu cầu revalidation; không mixed release | I/H M2 |
| EV01 | Witness/datum reference không tồn tại, graph trống | Evidence invalid/review; không geometry PASS | U/H M3 |
| EV02 | Printed Ø6; canonical Ø8 | DIMENSION_MISMATCH; không export production | U/I/H M1/M3 |
| EV03 | Source top-left nhưng mapping mặc định bottom-left | Datum/source-equation check fail | U/I/V M3 |
| EV04 | Center-distance slot được dùng như overall | SLOT_SEMANTICS mismatch | U/I/V M3 |
| EV05 | Cancelled family còn entity; active family thiếu/extra | Feature completeness/count fail theo family | U/I/H/V M3 |
| EV06 | Dimension mm được dùng như degree hoặc sai derivation | Unit/derivation fail; không eval tùy ý | U/H M3 |
| GEO01 | Plate thật có notch + hole + slot trong supported scope | Contour/typed features đúng, đủ QA, saved DXF khớp | U/I/H/V M3–4 |
| GEO02 | Linear input có notch nhưng output rectangle | Reject unsupported hoặc bảo toàn notch; không bbox PASS | U/I/H M1/M6 |
| GEO03 | Evidence có hole, geometrySources features rỗng | FEATURE_GEOMETRY_MISSING; không empty-features shortcut | U/H M1 |
| GEO04 | Extra/duplicate feature ID dù counts trong một map trông đúng | Reject duplicate/extra; không overwrite Map âm thầm | U/H M1/M3 |
| GEO05 | Hole/slot ngoài material; self-intersecting arc/bulge | Containment/topology fail trên true curve | U/I M3 |
| GEO06 | Material/pilot/POINT/CIRCLE/R/C sai rule áp dụng | Material/feature semantic fail; không generic CIRCLE fallback | U/I/V M3 |
| DATA01 | Raw DATA có multi-arc slot và source IDs | Giữ curve chain/provenance; inverse reprojection đạt | I/H/V M4 |
| DATA02 | Bỏ entity relevant hoặc idealize multi-arc thành stadium | Source completeness/reprojection fail | I/H M4 |
| DATA03 | Sai scale/mirror; chỉ đổi $INSUNITS để hợp thức | Reject khi chưa có physical-unit/source transform proof | U/I/V M4 |
| DATA04 | Primitive unsupported nằm trong manufacturing family | Báo rõ unsupported và giữ evidence; không drop/PASS | I/H M4 |
| BEND01 | L đúng có feature trên cả hai face | Exact face-local placement, Nobi, bend domain, fold-back đạt | U/I/H/V M6 |
| BEND02 | U sai face order/sign nhưng flat bbox vẫn giống | Fold-back/source constraints fail | U/I/H M6 |
| BEND03 | Caller khai foldBack PASS trong khi canonical structural-only | Production export bị chặn | U/H M1/M6 |
| BEND04 | Bend line xuyên void/notch/ngoài material | Clip theo source-proved domain hoặc fail | U/I/V M6 |
| BEND05 | Nobi sai, nhầm ID/OD hoặc dùng table không applicable | Evidence/rule/arithmetic mismatch; không fit theo reference | U/I/V M6 |
| QA01 | Client gửi toàn PASS nhưng không có machine QA record | Reject; không tự tạo certification từ claims | U/H M1 |
| QA02 | Geometry/source revision đổi sau QA | Invalidate QA/export authorization cũ | I/H M1/M4 |
| QA03 | Check bắt buộc khai N/A không có lý do applicability | Reject critical N/A | U/H M3 |
| OUT01 | Xóa hole khỏi DXF sau export rồi audit | Read-back geometry mismatch; không production PASS | I/H M4 |
| OUT02 | Giữ count nhưng đổi radius/center/bulge/color/layer | Bắt đúng difference; entity count bằng nhau không đủ | I/H M4 |
| OUT03 | Sửa file sau lần audit thành công rồi lấy output | Detect SHA/revision mismatch; không trả file như đã certified | I/H M4 |
| OUT04 | Tráo labels/code order; sai units/gap/AI_META plot | Packaging QA fail | I/H M5 |
| OUT05 | Nhiều code, một code pending | Một ALL_REVIEW_ONLY, đủ code theo nguồn, NO CUT và local FLAG | I/H/V M5 |
| OUT06 | Caller yêu cầu VIEWS_ONLY khi source census chưa đầy đủ | Không chấp nhận source-exhausted claim; yêu cầu xử lý evidence còn thiếu | U/H/V M5 |
| OUT07 | ARC+LINE và polyline tương đương khi audit reference | Physical comparison chấp nhận trong đúng mode/transform | I M4 hoặc capability direct audit |
| NUM01 | Derived-only residual dưới / đúng / trên 0.01 mm | Đúng biên theo CURRENT; không áp tolerance này cho printed value | U/I M3–4 |
| NUM02 | DATA/PDF delta 0.099 và 0.1; KH433 đúng scope | Boundary đúng; không tái dùng cho serialization/reprojection | U M3–4 |
| OPS01 | Restart giữa evidence/geometry/export | Khôi phục đúng revision/hash/state; không tự tiến PASS | I/H M5 |
| OPS02 | Retry cùng request hoặc hai request cùng job | Idempotent hoặc version conflict; không mất/corrupt record | I/H M5 |
| OPS03 | Python missing/timeout/nonzero, output invalid JSON, disk write fail | Error thực, checkpoint còn dùng được, không artifact PASS dở dang | I/H M5 |
| OPS04 | Port busy/cwd khác/env chưa load | Doctor báo chính xác; startup không giả ready | I M5/M7 |
| OPS05 | Host/Origin không hợp lệ; private download URL theo config | Từ chối đúng policy, không tự mở public/private access | I/H M7 |
| E2E01 | Fresh install → source bytes → evidence fixture → engine → DXF → actual read-back | Runtime E2E PASS; file thật tồn tại và exact expected scope | H M7 |
| E2E02 | Phiên Codex mới nhận PDF thật, không biết expected coordinates | Thực sự thấy ảnh, nạp rules, gọi MCP, trả artifact và QA đúng | V M7 |
| E2E03 | Phiên Codex nhận PDF+DATA thật | Parse DATA thật, semantic mapping, source reprojection, artifact QA đạt | V M7 |
| E2E04 | Nguồn có uncertainty không thể resolve sau source exhaustion | Câu hỏi cụ thể + geometry đã chứng minh + review output nếu đủ điều kiện; không bịa | V M5/M7 |
| E2E05 | Mandatory fixture/oracle thiếu | Acceptance ghi BLOCKED/UNAVAILABLE, không silently skip và báo complete | I/H/V M0/M7 |

## Bộ E2E bắt buộc thực hiện

### A. Runtime tự động, có thể chạy trong CI

1. Tạo temp data root, start server thật trên port động, chờ readiness có timeout.
2. MCP initialize → tools/list; assert schema/server version/capabilities theo contract.
3. Ingest **bytes hợp lệ**, open job, nhận source/rule snapshot.
4. Submit fixture evidence có provenance hợp lệ. Đây là replay có kiểm soát, không phải test Vision.
5. Route → build → server-side semantic QA → export → audit saved file.
6. Dùng reader độc lập kiểm tra file/expected geometry/labels/units; assert trạng thái và hashes.
7. Chạy variants âm theo matrix trên job riêng; mỗi variant phải fail đúng gate, không chỉ HTTP error bất kỳ.
8. Restart server, kiểm tra persistent job, idempotency và artifact tamper detection.
9. Đóng server trong finally, lưu report; timeout/process leak làm test fail.

### B. Source E2E có Codex/Vision thật

1. Chọn canary được catalog xác minh role/approval/hash; mở phiên mới để tránh dựa vào tọa độ trong hội thoại review/regression.
2. Người vận hành chỉ chọn nguồn và yêu cầu; agent tự ingest/open job qua MCP.
3. Agent nhận overview/crops cần thiết, đọc CURRENT/core và applicable modules. Lưu câu hỏi → ảnh → kết luận/evidence; không đặt quota crop làm mất thông tin.
4. Agent nộp structured model; service phản hồi constraints/flags cụ thể. Agent sửa bằng source evidence, không đoán theo output mong muốn.
5. Geometry + source QA + DXF read-back hoàn thành cho một code trước; sau đó mới composite.
6. Đánh giá độc lập bằng source checklist và approved reference đúng mode. Không cho reference geometry làm construction input của NEW job.
7. Mở actual saved DXF trong viewer/CAD để xem code labels, completeness, annotations; visual inspection bổ sung cho numeric QA, không thay numeric QA. Nếu viewer chưa có, ghi phần này chưa thực hiện.
8. Lưu trace/crops/evidence/canonical/checks/file SHA và conclusion theo code. Thiếu source hoặc unresolved engineering không được ghi PRODUCTION_PASS.

## Quy tắc kết luận

- Test hiện hữu xanh không bù được một P1 tái hiện được.
- All-negative-rejected không đủ; cần positive canary có geometry đúng, tránh implementation luôn reject mà test vẫn xanh.
- Source E2E thủ công/agent phải ghi đúng tên; không gọi đó là CI autonomous Vision E2E.
- Cùng model/algorithm tạo và chấm cùng sai lệch có thể cùng PASS; oracle và source constraints phải có phần độc lập.
- `0 false PASS` trên bộ test là tiêu chí nghiệm thu bộ test, không phải cam kết xác suất lỗi bằng 0 ngoài thực tế.
- Không dùng test fixtures/ref coordinates như constants trong production code; test-only expectations được cách ly.
