# LuanAppTools — Đặc tả thiết kế để duyệt

Ngày: 15/10/2026, Asia/Bangkok. Trạng thái: người dùng đã duyệt triển khai trong phiên thiết kế ngày 15/10/2026; đây là yêu cầu thiết kế, không phải báo cáo phần mềm đã kiểm thử.

## 1. Mục tiêu và quyết định đã thống nhất

LuanAppTools là phần phát triển thêm trong `GoldDRauDen/TrainAiCad`. Ứng dụng giúp một người trên một máy Windows chọn công việc từ thư mục LAN, điều phối AI đọc PDF/DXF và nhận DXF để kiểm tra. Repo tiếp tục là nguồn tài liệu, quy tắc và công cụ CAD chính thức cho các AI khác có đủ năng lực thực thi, kể cả khi không cài ứng dụng.

Mọi đầu ra của AI chỉ phục vụ người dùng kiểm tra, không được coi là lệnh hoặc phê duyệt sản xuất. `PASS` kỹ thuật và việc người dùng đã kiểm tra là hai thông tin riêng. Mục đích này không miễn các kiểm tra nguồn, kỹ thuật và DXF của repo.

| Nội dung | Quyết định của người dùng |
| --- | --- |
| Đơn vị job | Một thư mục chứa trọn bộ PDF và DATA DXF của một công việc |
| Ví dụ | `...\2025\18-03-2025\520318-15\520318-15.pdf` và `data.dxf` nếu có |
| Nguồn DXF | DATA khách hàng; thư mục không chứa mẫu tham chiếu/kết quả đã duyệt của bên khác |
| DXF tổng | Có kết quả tổng khi hoàn tất được luồng CAD, dù toàn PASS hay còn REVIEW/VIEWS_ONLY; đặt tại thư mục nguồn job |
| DXF riêng | Tùy chọn; chỉ xuất mã PASS; có nút mở thư mục riêng |
| Chạy lại | Kết quả hiện tại dùng tên chuẩn; lịch sử bản trước được lưu trong app |
| Số lượt giải | Tối đa hai lượt tổng cộng cho mỗi mã trong một lần chạy: ban đầu và một lượt xử lý lại |
| Model | Claude chính; app tự chọn và nâng model/effort; Opus chỉ tự dùng cho ngoại lệ khó |
| 9Router | Dự phòng chữa cháy; chờ người dùng chọn tiếp tục bằng 9Router |
| GPT | Giữ khả năng mở rộng, không dùng song song mặc định với Claude |
| Triển khai | Một máy Windows, một tài khoản AI; dữ liệu đầu vào/đầu ra trên LAN |
| Nguồn thay đổi | Job đã đưa vào theo dõi tự được xếp chạy lại khi nguồn cập nhật ổn định |

Tối đa ba job đang xử lý. Bản đầu ưu tiên độ đúng, thời gian hoàn tất và usage; không mở rộng sang nesting, NC/toolpath hoặc mô phỏng 3D.

## 2. Quan hệ giữa repo và ứng dụng

Ứng dụng dự kiến nằm trong `LuanAppTools/`. Backend Python/FastAPI dùng công cụ CAD hiện có; SQLite lưu trạng thái tại máy; React cung cấp giao diện local. Đây là lựa chọn kỹ thuật đề xuất để triển khai, không phải thay đổi quy tắc cơ khí.

Các module có trách nhiệm như sau:

| Module | Trách nhiệm và interface |
| --- | --- |
| Job sources | Quét thư mục được cấu hình, nhận diện nguồn, chụp phiên bản đầu vào và thông báo thay đổi |
| Job scheduler | Xếp hàng, giới hạn đồng thời, pause/resume/cancel, checkpoint và phục hồi |
| AI runner | Chạy phiên chính thức, gửi nguồn/rules đúng phạm vi, nhận sự kiện, kiểm soát lượt giải và ghi usage |
| CAD execution | Gọi Router, kiểm tra canonical, exporter và saved-DXF QA của repo |
| Output publisher | Công bố đúng kết quả lên LAN, lưu lịch sử, chống kết quả cũ và chống quét output thành input |
| Local UI | Chọn job, theo dõi tiến trình, xem bằng chứng/kết quả, mở thư mục và ghi nhận kiểm tra thủ công |

Rules không được sao chép thành một bộ độc lập trong prompt app hoặc cơ sở dữ liệu. Các file cấu hình app chỉ quy định vận hành, model và đường dẫn. Không tự cập nhật rules khi AI đang xử lý job.

Mỗi lần chạy khóa một commit repo và phiên bản nguồn. Phiên bản kỹ thuật được đọc từ entrypoint/Router của commit đó, không ghi cứng V4.34 trong logic app. Các file đã khảo sát cho thiết kế hiện tại gồm `SKILL.md`, `AI_BOOTSTRAP.md`, `AI_ENTRYPOINT.md`, `AGENTS.md`, Router, Feature Census, Validation và Rule Brain; entrypoint được đọc ở đợt khảo sát là V4.34.

## 3. Nhận diện job và nguồn trên LAN

Người dùng cấu hình một hoặc nhiều thư mục gốc. App quét đệ quy, liệt kê thư mục job có PDF phù hợp, cho chọn một hoặc nhiều job rồi bắt đầu. Phát hiện một thư mục mới không tự đồng nghĩa người dùng đã đưa job đó vào theo dõi.

Job đã chọn được theo dõi thay đổi về sau. Bộ nguồn có thể gồm nhiều PDF và DATA DXF liên quan. ID hiển thị lấy từ thư mục; khóa nội bộ bao gồm đường dẫn chuẩn hóa để hai thư mục khác nhau cùng tên không đè nhau.

App duy trì danh mục file nguồn và file do nó tạo. DXF tổng, thư mục DXF riêng, lịch sử, file tạm và hình render do app tạo không trở thành đầu vào của lần chạy sau. Không suy ra danh sách nguồn bằng cách lấy mọi DXF trong thư mục ở mỗi lần quét.

Ứng dụng hỗ trợ UNC và đường dẫn ổ đĩa mà tài khoản Windows hiện tại truy cập được. Trước khi nhận job, kiểm tra khả năng đọc nguồn và quyền ghi đích; lỗi quyền truy cập là lỗi vận hành, không phải thiếu kích thước của bản vẽ.

Nguồn được sao chép vào bộ nhớ đệm local theo phiên bản. Chỉ nhận snapshot khi file đã ổn định qua các lần kiểm tra, đọc được đầy đủ và không thay đổi trong lúc sao chép; dùng hash nội dung cùng danh mục file để xác định phiên bản. PDF phải mở/render được; DXF phải qua bước đọc/giải mã cần thiết. Một khoảng thời gian ổn định đơn thuần không được coi là bằng chứng file hợp lệ.

Mặc định vận hành đề xuất: quét thay đổi mỗi 5 giây; yêu cầu ít nhất 10 giây không đổi trước khi thử snapshot. Các khoảng này chỉnh được. Độ đúng cuối cùng dựa vào snapshot và kiểm tra file, không chỉ đồng hồ.

## 4. Luồng xử lý và ngữ cảnh AI

Luồng bắt buộc: snapshot nguồn → bootstrap repo → kiểm kê toàn bộ mã/ghi chú/quan hệ nguồn → Feature Census và Router → giải hình học → kiểm tra độc lập → canonical → exporter → mở lại DXF thực tế → công bố output.

Giữ toàn bộ các cổng của repo, gồm nguồn/mã/nhóm/member, datum/witness, source-to-canonical completeness, các kiểm tra uốn khi áp dụng, holistic challenge, trạng thái REVIEW và saved-DXF read-back. File xuất mở được không đủ để kết luận đúng nguồn.

Mỗi mã có hồ sơ kết quả riêng, gồm bằng chứng, trạng thái, canonical và checkpoint. Workspace riêng không buộc tạo phiên AI riêng hoặc đọc toàn repo.

Thông tin chung được kiểm kê ở cấp job: ghi chú, mã khách hàng có bằng chứng, vật liệu, độ dày, trang và quan hệ giữa các mã. Mỗi mã vẫn nhận đủ các hình chiếu, chi tiết và ghi chú thuộc phạm vi của nó. Không tách máy móc theo trang PDF.

Chỉ nạp rules qua Router và các giai đoạn cần thiết. `UNKNOWN` không được đổi thành `NO` để giảm context. Manifest đường dẫn không thay thế việc đọc nội dung rules. Không dùng lịch sử/portable/regression để lấy kích thước cho nguồn mới.

Mặc định đề xuất: gom tối đa ba mã dễ đã chứng minh độc lập, có cùng loại rules, trong một phiên giải; mã trung bình/khó dùng phiên theo mã. Có thể gom phiên QA cho nhóm mã dễ nhưng vẫn phải kiểm tra bằng chứng từng mã. Nếu phân loại hoặc quan hệ nguồn thay đổi thì tách/reroute mã liên quan.

Giới hạn nhóm là cấu hình ban đầu cần benchmark, không phải khẳng định tối ưu token. Chuẩn bị nguồn chung giảm đọc/render lặp; các phiên model độc lập vẫn có thể tốn lại token cho ngữ cảnh chung. Chỉ ghi nhận lợi ích cache khi công cụ thực sự báo số liệu.

## 5. Model, nâng cấp và hai lượt giải

Claude được chạy qua Claude Code chính thức, bằng tài khoản người dùng đăng nhập tại máy. Thông tin đăng nhập do công cụ chính thức quản lý. Kiểm tra phiên bản CLI, model và effort có thể dùng trước khi chạy; ghi lại model/effort thực tế và phát hiện việc thay model ngoài cấu hình.

| Độ khó | Lượt đầu | Xử lý lại nếu cần |
| --- | --- | --- |
| Dễ | Haiku 5.5, medium | Sonnet 5.5, high; tăng mức nếu bằng chứng mới xác định cần thiết |
| Trung bình | Sonnet 5.5, high | Sonnet 5.5, xhigh hoặc max theo vấn đề còn mắc |
| Khó | Sonnet 5.5, xhigh | Sonnet max, hoặc Opus 5.5 nếu cần cứu trường hợp quá khó |

Phân loại dựa trên nguồn, cấu trúc, witness/datum, đặc điểm uốn và vấn đề chưa giải quyết; không chỉ dựa vào số trang, độ đơn giản bề ngoài hoặc lời tự tin của model. Người dùng chỉnh được cấu hình mặc định theo độ khó; chọn mức dễ không miễn QA.

Hai lượt là một lượt giải ban đầu và tối đa một lượt dựng/giải lại. Không chạy Haiku → Sonnet → Opus thành ba lượt. Router chọn đích xử lý lại từ báo cáo lỗi và bằng chứng cụ thể. Opus không làm quét job, đọc lại toàn bộ bộ hồ sơ không liên quan hoặc trở thành bước bắt buộc của mọi mã khó.

Một lượt giải có thể gồm nhiều tương tác và công cụ, nên số lượt không đồng nghĩa số request hay giới hạn token. Mặc định đề xuất: trần 20 phút cho một lượt giải, chỉnh được sau benchmark; theo dõi riêng thời gian đang hoạt động, tạm dừng và chờ provider. Khi hết ngân sách mà vẫn chưa chứng minh được thì giữ REVIEW cùng phần đúng đã có.

QA đối chiếu nguồn phải độc lập với quá trình dựng hình; không chỉ tin checklist tự khai của solver. Mặc định đề xuất dùng Sonnet high cho QA ngữ nghĩa, có gom nhóm mã dễ, cùng kiểm tra xác định được bằng code. QA phát hiện cần sửa hình học thì tiêu thụ lượt giải còn lại; không lách lượt ba bằng cách gọi nó là QA. Sau sửa phải kiểm tra lại kết quả sửa.

Nếu kiểm tra chứng minh nguồn thực sự thiếu dữ kiện, không gọi model mạnh hơn để tự tạo dữ kiện. Phải phân biệt điều này với AI chưa hiểu nguồn. Thực thi nguồn-exhaustion và fallback đầy đủ theo repo trước khi kết thúc ở REVIEW/VIEWS_ONLY.

Lỗi kết nối trước khi provider nhận request có thể thử kết nối lại, không tính thành một lần giải hình học mới. Request có thể đã thực thi nhưng chưa biết kết quả phải được đối soát bằng phiên/sự kiện, không tự gửi lại mù quáng. Budget sử dụng và thời gian không được đặt lại khi pause, reconnect hoặc khởi động lại app.

## 6. 9Router và GPT

9Router dùng địa chỉ cấu hình được, mặc định `http://localhost:20128/v1`. Đây là endpoint trên máy chạy app. Chưa có bằng chứng trong phiên thiết kế này rằng endpoint trên máy người dùng đã được kiểm thử.

Khi Claude hết usage hoặc không khả dụng, lưu checkpoint và chờ. Người dùng có thể chọn tiếp tục bằng 9Router; app chỉ cung cấp model dự phòng đã kiểm thử về ảnh, cấu trúc đầu ra và tool calling phù hợp. OpenAI-compatible không tự đồng nghĩa tương thích giao thức của Claude Code; adapter phải xác minh đường chạy thực tế.

Model không có vision không được nhận phần đọc bản vẽ như thể đã xem ảnh. Gateway không được âm thầm bỏ ảnh, cắt rules hoặc thay model ngoài chính sách; ghi provider/model thực tế nếu có. Đăng nhập Claude chính và cấu hình gateway được cô lập theo tiến trình.

Chuyển provider tiếp tục lượt đang gián đoạn hoặc dùng lượt giải còn lại, không mở lượt thứ ba. Nếu đã dùng hết hai lượt, muốn chạy thêm phải là một lần chạy mới do người dùng yêu cầu rõ. Không tự chuyển sang nguồn API trả phí.

GPT/Codex là khả năng mở rộng sau, tắt mặc định. Bản đầu không hiển thị một kết nối chưa thực thi như đã sẵn sàng sử dụng. Hợp đồng runner phải đủ cho Claude và 9Router trước; không xây nhiều lớp trừu tượng chỉ để dự phòng GPT.

## 7. Hàng đợi, điều khiển và phục hồi

Trạng thái vận hành gồm: phát hiện, xếp hàng, đang xử lý, yêu cầu tạm dừng, đã tạm dừng, chờ usage, chờ lựa chọn dự phòng, chờ ghi LAN, hoàn tất, hủy và lỗi. Trạng thái kỹ thuật từng mã giữ vocabulary của repo. Trạng thái người dùng đã kiểm tra là trường riêng, gắn đúng phiên bản nguồn/kết quả.

Tối đa ba job đang xử lý và tối đa ba lượt AI đang hoạt động trên toàn app, gồm giải và QA. Mặc định ban đầu hai lượt AI đồng thời, chỉnh từ một đến ba. Opus tối đa một lượt đồng thời. Có thể tự giảm đồng thời khi provider giới hạn; không tự tăng vượt trần.

App điều phối phiên; không cho phiên AI tự sinh một số agent con không được tính vào giới hạn. Tính toán/render CPU có giới hạn riêng và không chiếm slot suy luận khi không gọi model.

Tạm dừng ngăn bước mới; bước đang chạy chuyển về checkpoint hợp lệ hoặc được ngắt có kiểm soát khi cần. UI phải thể hiện rõ đang yêu cầu dừng hay đã dừng. Tiếp tục dùng phần đã kiểm chứng; phần dang dở có thể phải thực thi lại trong cùng ngân sách lượt đang có. Không hứa khôi phục nguyên vẹn suy nghĩ nội bộ của model.

Hủy ngắt đúng tiến trình của lần chạy và tiến trình con thuộc nó, thu hồi quyền công bố, giữ lịch sử và không xóa nguồn. Kết quả dở dang không được công bố là hoàn tất. Khởi động lại app phục hồi hàng đợi/checkpoint, đối soát phiên còn sống, không khởi tạo hai worker cho cùng một lần chạy.

## 8. Nguồn thay đổi và công bố kết quả

Khi nguồn của job theo dõi thay đổi, tạo phiên bản nguồn mới sau khi snapshot ổn định. Lần chạy cũ bị đánh dấu đã có nguồn thay thế, ngừng thực hiện thêm bước tốn AI và không được ghi kết quả hiện tại của job. Bảo tồn phần cũ trong lịch sử. Chỉ một lần chạy được quyền công bố cho mỗi job; thay đổi liên tiếp được gộp về phiên bản mới nhất, không sinh hàng đợi trùng.

Đầu ra mặc định giữ hợp đồng của repo:

| Kết quả kỹ thuật | DXF tổng tại thư mục job |
| --- | --- |
| Toàn bộ mã PASS | `<JOB>_ALL.dxf` |
| Có REVIEW/PREVIEW/VIEWS_ONLY/FLAG phù hợp hợp đồng repo | `<JOB>_ALL_REVIEW_ONLY.dxf` |

Luôn cố gắng xuất bản tổng đến giới hạn có thể thực thi, bảo tồn hình học/nguồn đã chứng minh theo fallback của repo. Nếu không đọc được nguồn hoặc không có biểu diễn hợp lệ để xuất, báo lỗi cụ thể; không tạo DXF trống hoặc hình học bịa để đủ tên file.

Khi bật DXF riêng, chỉ lấy mã PASS từ cùng canonical đã kiểm tra, theo quy ước tên/số công việc của repo. Thư mục mặc định `parts_dxf` trong job; cho chọn đích riêng. Nút Output tổng mở thư mục job, nút Output riêng mở đích DXF riêng của lần chạy hiện tại. Cơ chế mở thư mục thực hiện tại máy Windows chạy app.

Tạo, mở lại và kiểm tra output local trước khi chuyển. Trên LAN, ghi file tạm rồi đổi tên tại cùng đích khi hệ thống file hỗ trợ; đọc lại file cuối để xác nhận hash và tính toàn vẹn. Không tuyên bố nhiều file trên SMB được cập nhật bằng một transaction nguyên khối. App chỉ báo công bố hoàn tất khi mọi file yêu cầu đã đúng phiên bản.

DXF tổng được công bố sau bộ DXF riêng nếu có. Các file PASS riêng không còn hợp lệ ở phiên bản mới được đưa khỏi bộ hiện tại vào lịch sử; chỉ thao tác file app sở hữu. Trường hợp chuyển từ `_ALL.dxf` sang `_ALL_REVIEW_ONLY.dxf` hoặc ngược lại cũng không để bản cũ hiện như kết quả mới nhất. Không ghi đè một file không xác định được quyền sở hữu như thể đó là output của app.

Mất LAN hoặc file đích đang bị khóa: giữ kết quả đã kiểm tra local, báo chờ ghi, thử chuyển lại với thời gian giãn cách. Không gọi lại AI chỉ để ghi file. Trước công bố lại phải xác minh lần chạy còn được quyền ghi và nguồn chưa bị thay thế.

## 9. Giao diện và usage

Giao diện tiếng Việt, gọn, gồm danh sách job và vùng chi tiết. Mặc định đề xuất: nền sáng xám nhạt, chữ rõ, xanh cho hành động chính, màu riêng cho trạng thái, kèm nhãn chữ để không phụ thuộc màu. Hàng trên hiển thị tổng job, đang chạy, chờ, lỗi, PASS/REVIEW/VIEWS_ONLY theo mã và số chưa kiểm tra thủ công. Mỗi job có số mã, trạng thái, model đang dùng, công đoạn, thời gian và nút thao tác.

Chi tiết có PDF/bằng chứng và preview DXF để pan/zoom, danh sách vấn đề cùng vị trí nguồn, hoạt động mới nhất, lượt giải, thời gian, output và lịch sử. Tiến độ dùng số mã/công đoạn đã hoàn tất; không suy phần trăm công việc từ token. Theo dõi hoạt động công cụ và tóm tắt tiến trình; không hứa có toàn bộ suy nghĩ nội bộ.

Ghi token input/output/cache nếu công cụ cung cấp; cộng cả triage, giải, xử lý lại và QA vào usage job. Phần dùng chung được ghi riêng ở cấp job, không nhân lên thành chi phí thật cho mọi mã. Bộ đếm cộng dồn của phiên được lấy delta và chống đếm trùng khi resume hoặc nhận lại sự kiện.

Quota/reset là thông tin cấp tài khoản. Không lấy mức hao hụt quota khi nhiều việc cùng chạy để tuyên bố phần trăm chính xác của từng job. Thiếu số liệu hiển thị chưa có dữ liệu, không ghi số 0 giả. Tiền quy đổi theo giá API, nếu có, phải ghi là ước tính tham khảo và không phải hóa đơn của gói đăng nhập.

## 10. Quyền chạy và bài học mới

UI chỉ nghe loopback mặc định; thư mục LAN là nguồn dữ liệu, không phải yêu cầu mở web app cho các máy LAN. Backend giới hạn đường dẫn vào các root người dùng cấu hình; bảo vệ thao tác ghi khỏi yêu cầu ngoài phiên local hợp lệ.

AI đọc snapshot repo và nguồn local, ghi hồ sơ làm việc của lần chạy. Backend chịu trách nhiệm công bố ra LAN. Chỉ đặt cwd không đủ để giới hạn quyền: phải dùng giới hạn của CLI/hệ điều hành hoặc công cụ được phép tương ứng; kiểm tra năng lực này trên Windows trước khi cho chạy thực tế. Không đưa thông tin đăng nhập vào log, repo hoặc nguồn đưa cho model.

Phản hồi lỗi lưu bằng chứng cùng phiên bản nguồn/rules. Bài học mới phân loại nguyên nhân: không đọc/không làm đúng rules, thiếu rules, sai công cụ hoặc thiếu nguồn. Người dùng có thể tiếp tục hướng dẫn và cập nhật repo. Quy tắc mới sửa đúng nơi chủ quản, có regression và được duyệt trước khi áp dụng. Chưa xây màn hình huấn luyện hoặc tự sửa rules trong bản đầu; cập nhật repo không có nghĩa huấn luyện lại trọng số model.

## 11. Nghiệm thu và giới hạn bằng chứng

Kiểm tra tích hợp cần chứng minh: job folder nhận đúng nguồn; output không kích hoạt vòng lặp; nguồn thay đổi chỉ có một lần chạy hiện tại; tối đa ba job/ba lượt AI; không vượt hai lượt giải bằng nhãn QA; tự nâng model và giới hạn Opus đúng; 9Router chỉ chạy khi chọn; hủy/khởi động lại không công bố muộn hoặc chạy trùng.

Kiểm tra LAN gồm mất mạng, đích khóa, ghi dở, nguồn đổi lúc sao chép/lúc công bố, file cũ và bản PASS riêng hết hiệu lực. Chạy kiểm thử trên Windows với thư mục chia sẻ thật; kiểm thử trong môi trường khác không được báo là đã xác nhận máy người dùng.

Kiểm tra CAD tái dùng bộ regression hiện có và bản vẽ đã được xác nhận, gồm phẳng, uốn/nhiều mặt, lỗ/slot, KEGAKI và REVIEW/VIEWS_ONLY. Mọi mô hình vẫn phải qua cùng gates; không đạt tốc độ bằng cách bỏ QA. Đối chiếu nguồn độc lập cùng kiểm tra canonical/export/read-back; ảnh đầu ra trông giống hoặc bbox đúng không đủ.

Benchmark so sánh nhóm một/ba/sáu mã dễ và cấu hình model/effort trên cùng tập nguồn. Ghi thời gian toàn job, tỷ lệ hoàn tất đúng, PASS sai, số lần xử lý lại và usage đo được. Chọn cấu hình dựa trên kết quả thực tế, không hứa trước phần trăm tiết kiệm hoặc độ chính xác tuyệt đối. Mục tiêu nghiệm thu trên tập đã xác nhận: không có PASS sai đã biết và không lùi các invariant hiện tại; điều này không chứng minh 100% cho mọi bản vẽ tương lai.

## 12. Tài liệu căn cứ và bước tiếp theo

- [Repo TrainAiCad](https://github.com/GoldDRauDen/TrainAiCad)
- [Authority — AI_ENTRYPOINT](https://github.com/GoldDRauDen/TrainAiCad/blob/main/AI_ENTRYPOINT.md)
- [Routing](https://github.com/GoldDRauDen/TrainAiCad/blob/main/skills/lispcad/router/ROUTER.yaml)
- [Rule brain](https://github.com/GoldDRauDen/TrainAiCad/blob/main/docs/RULE_BRAIN.md)
- [Claude Code headless](https://code.claude.com/docs/en/headless)
- [Model và effort](https://code.claude.com/docs/en/model-config)
- [Đăng nhập](https://code.claude.com/docs/en/authentication) và [điều kiện tích hợp](https://code.claude.com/docs/en/legal-and-compliance)
- [Usage](https://code.claude.com/docs/en/costs)
- [9Router](https://github.com/decolua/9router)

Bản đặc tả tổng hợp các quyết định Q1–Q11 và nêu rõ các mặc định kỹ thuật đề xuất. Bước tiếp theo sau khi duyệt: đọc lại checkout repo thực tế, lập kế hoạch triển khai theo module cùng kiểm tra nghiệm thu, rồi thực hiện. Chưa có thay đổi hay commit nào vào TrainAiCad từ bản thiết kế này.
