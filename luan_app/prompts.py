"""The only text Luan App sends to Claude. Users supply nothing but a checked path and slip codes."""
from __future__ import annotations

from pathlib import Path

REVIEW_RULES = """\
review_items.json — mảng JSON (mảng rỗng [] nếu không có gì). Mỗi mục:
  {"type": "NEW_LESSON" | "NEED_SAMPLE_DXF", "code": "<mã>", "card": "<rules/....md liên quan>",
   "title": "<1 dòng tiếng Việt>", "detail": "<FACT → ROOT_CAUSE → LESSON đề xuất, hoặc điều không biết cách vẽ>",
   "evidence": "<trang / khung nhìn / crop>"}
  CHỈ ghi khi: kỹ thuật/chi tiết chưa thẻ rule nào bao; rule hiện có cho kết quả sai; không biết cách vẽ và cần mẫu DXF.
  KHÔNG ghi: thiếu hoặc không rõ kích thước, chờ xác nhận Nobi, thiếu dữ liệu bản vẽ, câu hỏi cho khách
  (những thứ đó để ở FLAG và report.md như bình thường)."""


def build_prompt(kind: str, path: str, codes: list[str] | None, run_out: Path) -> str:
    out = str(run_out)
    if codes:
        codes_line = f"Mã cần làm: {', '.join(codes)} (job.py init ... --codes {' '.join(codes)})"
    elif kind == "QA" and path.lower().endswith(".dxf"):
        codes_line = "Mã cần kiểm tra: chỉ các mã có trong file .dxf đã cho"
    else:
        codes_line = "Mã cần làm: tất cả mã trong phiếu"
    if kind == "QA":
        head = [f"QA {path}",
                "Đối tượng: DXF mới nhất trong AI_L\\ của thư mục job (hoặc chính file .dxf đã cho), so với nguồn của job.",
                codes_line,
                "Không sửa DXF được kiểm tra."]
        verdict = '"OK" nếu không có điểm sai, "ISSUES" nếu có'
    else:
        head = [f"E2E {path}", codes_line]
        verdict = '"OK" nếu mọi mã PASS và đã giao, "ISSUES" nếu còn PREVIEW/FLAG/FAIL'
    body = [
        "Chạy qua Luan App, không có người trả lời:",
        "- Không hỏi lại. Mọi câu hỏi và điểm chưa rõ ghi vào báo cáo (JOB_CARD §5: luôn vẽ, không dừng).",
        "- Không sửa file nào của repo, không chạy git. File làm việc ở .work/ như bình thường.",
        "- Giao DXF bằng job.py deliver / deliver-code theo chế độ của phiếu như bình thường." if kind != "QA"
        else "- Báo cáo QA theo rules/QA_REVERSE.md.",
        f"Khi xong ghi vào thư mục {out}:",
        "- report.md : báo cáo theo rules/OUTPUT.md §8" if kind != "QA" else "- report.md : báo cáo QA đầy đủ",
        f'- result.json : {{"verdict": {verdict}, "summary": "<1 dòng tiếng Việt>", '
        '"codes": {"<mã>": "PASS|PREVIEW|FAIL"}}',
        "- " + REVIEW_RULES,
    ]
    return "\n".join(head + body) + "\n"
