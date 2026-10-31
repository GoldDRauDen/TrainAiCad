"""The only text the AI CAD app sends to Claude. Users supply nothing but a checked path and slip codes."""
from __future__ import annotations

import os
from pathlib import Path

from .config import REPO_ROOT

REVIEW_RULES = """\
review_items.json — mảng JSON (mảng rỗng [] nếu không có gì). Mỗi mục:
  {"type": "NEW_LESSON" | "NEED_SAMPLE_DXF", "code": "<mã>", "card": "<rules/....md liên quan>",
   "title": "<1 dòng tiếng Việt>", "detail": "<FACT → ROOT_CAUSE → LESSON đề xuất, hoặc điều không biết cách vẽ>",
   "evidence": "<trang / khung nhìn / crop>"}
  CHỈ ghi khi: kỹ thuật/chi tiết chưa thẻ rule nào bao; rule hiện có cho kết quả sai; không biết cách vẽ và cần mẫu DXF.
  KHÔNG ghi: thiếu hoặc không rõ kích thước, chờ xác nhận Nobi, thiếu dữ liệu bản vẽ, câu hỏi cho khách
  (những thứ đó để ở FLAG và report.md như bình thường)."""


MARKUP = REPO_ROOT / "tools" / "qa_markup.py"   # the app's own checkout: works before the slot's origin/main has it
SHORT = ("Báo cáo NGẮN, không kể quá trình làm, không phân tích dài: mã nào FAIL/PREVIEW thì 1 dòng lý do "
         "(fail gì / chưa rõ gì / cần xác nhận gì); mã PASS chỉ ghi PASS.")


def build_prompt(kind: str, path: str, codes: list[str] | None, run_out: Path,
                 share_path: str | None = None, local_job_dir: str | None = None, job: str | None = None,
                 resume_of: int | None = None) -> str:
    out = str(run_out)
    staged = ([f"Bản gốc trên server: {share_path}. App đã chép thư mục job về {local_job_dir} (Claude Code không mở được "
               "đường dẫn \\\\server). Chỉ đọc/ghi bản chép; app chép file mới trong AI_L\\ của bản chép lên server ngay khi có."]
              if share_path and local_job_dir else [])
    if codes:
        codes_line = f"Mã cần làm: {', '.join(codes)} (job.py init ... --codes {' '.join(codes)})"
    elif kind == "QA" and path.lower().endswith(".dxf"):
        codes_line = "Mã cần kiểm tra: chỉ các mã có trong file .dxf đã cho"
    else:
        codes_line = "Mã cần làm: tất cả mã trong phiếu"
    job = job or "<JOB>"
    ai_l = (local_job_dir or (os.path.dirname(path) if path.lower().endswith(".dxf") else path)).rstrip("\\/") + "\\AI_L"
    statuses = "PASS|FAIL" if kind == "QA" else "PASS|PREVIEW|FAIL"
    if kind == "QA":
        head = [f"QA {path}",
                "Vai trò: chuyên bắt lỗi bản người vẽ đã làm. Đối tượng: file DWG của người vẽ trong thư mục job và các DXF "
                "xuất từng mã trong gui\\<job>\\ (dán một file .dxf thì chỉ file đó), so với nguồn của khách (PDF / DATA). "
                "Không lấy AI_L\\ làm đối tượng.",
                "Thư mục gui\\<job>\\*.dxf là bản xuất từng mã của người vẽ, KHÔNG phải DATA của khách.",
                f"Khởi tạo bằng `python tools/job.py init {job} --qa ...` (không tạo make\\). Đọc đúng các thẻ rule áp cho "
                "từng mã (census) để biết thế nào là sai.",
                codes_line,
                "Chỉ xét biên dạng sản xuất (hình, kích thước, lỗ, R, gấp/Nobi, khắc). Ghi chú, kiểu chữ, font, chữ trong "
                "DWG/DXF là của người vẽ, không phải lỗi — không báo. Chữ \"dx\"/\"hl\" chỉ xét nghĩa: dx = đối xứng, "
                "hl = có hướng vân; sai nghĩa so với bản vẽ mới là lỗi.",
                "Không sửa DXF được kiểm tra.",
                f"Chỉ QA, không làm make: không vẽ, không tạo spec/DXF dựng lại. Ảnh render/crop và file tạm để trong "
                f".work\\{job}\\QA\\, không để trong make\\."] + staged
        verdict = '"OK" nếu mọi mã PASS, "ISSUES" nếu có mã FAIL'
        tail = [
            f"Xuất kết quả QA vào {ai_l}\\ (app chép lên AI_L của server):",
            f"- {ai_l}\\{job}_AI_QA.txt : mỗi mã 1 dòng \"<mã> PASS\" hoặc \"<mã> FAIL: <lý do ngắn>\". PASS hết thì chỉ 1 dòng \"ALL_PASS\".",
            f"- Có mã FAIL thì thêm {job}_AI_QA.dxf : biên dạng lỗi chép ra, khoanh tròn + leader chỉ vùng lỗi + note. "
            f"Viết .work\\{job}\\qa_issues.json rồi chạy `python {MARKUP} .work\\{job}\\qa_issues.json {ai_l}\\{job}_AI_QA.dxf`. "
            f'JSON: {{"job": "{job}", "items": [{{"code": "<mã>", "src": "<DXF chứa mã>", "bbox": [x0, y0, x1, y1] '
            '(vùng của mã trong src; bỏ nếu src chỉ có mã đó), "note": "<lỗi gì>", '
            '"marks": [{"x": .., "y": .., "note": "<lỗi tại đây>"}]}]}. Vùng không chỉ được thì bỏ marks (chỉ note).',
        ]
    else:
        head = [f"E2E {path}", codes_line] + staged
        if resume_of:
            head.append(f"LÀM TIẾP lượt #{resume_of} bị ngắt: .work\\{job}\\ đã có job_state.json và các file đã làm. Không chạy "
                        f"lại job.py init; chạy `python tools/job.py status {job}` rồi làm tiếp từ bước đang dừng. Mã đã PASS "
                        "và đã giao thì không làm lại.")
        verdict = '"OK" nếu mọi mã PASS và đã giao, "ISSUES" nếu còn PREVIEW/FLAG/FAIL'
        tail = []
    body = [
        "Chạy qua app AI CAD, không có người trả lời:",
        "- Không hỏi lại. Mọi câu hỏi và điểm chưa rõ ghi vào báo cáo (JOB_CARD §5: luôn vẽ, không dừng).",
        "- Không sửa file nào của repo, không chạy git. File làm việc ở .work/ như bình thường.",
        "- Mỗi lệnh shell chỉ một lệnh `python ...` (không ghép `;`/`&&` với lệnh khác, không gán biến, không New-Item/mkdir:"
        " sẽ bị chặn). Tạo file/thư mục bằng Write; file tạm để trong .work/, không dùng thư mục scratchpad.",
        "- Tiết kiệm: cần tham số của tool thì `python tools/<tool>.py --help`, không đọc mã nguồn tools/. Grep/Glob luôn "
        "giới hạn thư mục (rules/, .work/), không quét cả repo. Ảnh: crop đúng vùng cần với dpi vừa đủ; không render lại "
        "trang hay đọc lại ảnh đã xem.",
        "- Giao DXF bằng job.py deliver / deliver-code theo chế độ của phiếu. Phiếu GẤP (job.py status: DELIVERY: URGENT): "
        "xong mã nào thì `job.py deliver-code <mã>` NGAY rồi mới làm mã tiếp — không để dồn tới cuối." if kind != "QA"
        else "- Đọc so sánh theo rules/QA_REVERSE.md, nhưng xuất kết quả theo mẫu dưới đây.",
        "- " + SHORT,
    ] + tail + [
        f"Khi xong ghi vào thư mục {out}:",
        "- report.md : chỉ câu hỏi cho khách và FLAG (nếu có), mã FAIL/PREVIEW + lý do 1 dòng. Không có gì thì ghi ALL_PASS."
        if kind != "QA" else "- report.md : giống nội dung " + f"{job}_AI_QA.txt",
        f'- result.json : {{"verdict": {verdict}, "summary": "<1 dòng tiếng Việt, ngắn>", '
        f'"codes": {{"<mã>": {{"status": "{statuses}", "note": "<PASS: để trống; khác: lý do 1 dòng>"}}}}, '
        '"questions": ["<câu hỏi cho khách, nếu có>"]}',
        "- " + REVIEW_RULES,
    ]
    return "\n".join(head + body) + "\n"
