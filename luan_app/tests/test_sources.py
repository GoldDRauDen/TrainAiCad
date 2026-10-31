import os

import pytest

from luan_app import sources
from luan_app.sources import SourceError, clean, inspect, is_allowed, path_key, validate_codes


def test_clean_and_key_equivalence():
    a = path_key(' "\\\\VietNam2025\\banve\\521030-10\\" ')
    b = path_key("//VietNam2025/BanVe/521030-10")
    c = path_key("\\\\vietnam2025\\banve\\\\521030-10")
    assert a == b == c == "\\\\vietnam2025\\banve\\521030-10"
    assert clean("C:\\") == "C:\\"
    assert clean("C:/jobs/x/") == "C:\\jobs\\x"


def test_is_allowed():
    roots = ["\\\\VietNam2025\\banve"]
    assert is_allowed("\\\\vietnam2025\\BANVE\\2026\\x", roots)
    assert not is_allowed("\\\\VietNam2025\\banve2\\x", roots)
    assert not is_allowed("C:\\x", roots)
    assert not is_allowed("\\\\VietNam2025\\banve\\x", [])


def test_inspect_with_slip(jobs_root, job_dir):
    info = inspect(str(job_dir), [str(jobs_root)])
    assert info["job"] == "521030-10" and info["has_slip"] and not info["urgent"]
    assert [c["code"] for c in info["codes"]] == ["26-064689", "26-064687", "26-064643"]
    assert info["codes"][1]["material"] == "SPHCP(酸洗)" and info["codes"][1]["size"] == "316.64×275"
    assert info["codes"][0]["size"] == ""
    assert info["warnings"] == []


def test_inspect_without_slip_warns(jobs_root):
    d = jobs_root / "521031-02 hom nay"
    d.mkdir()
    (d / "a.pdf").write_bytes(b"%PDF")
    info = inspect(str(d), [str(jobs_root)])
    assert info["has_slip"] is False and info["codes"] == []
    assert info["job"] == "521031-02"
    assert "sẽ làm tất cả mã" in info["warnings"][0]


def test_inspect_errors(jobs_root, tmp_path):
    other = tmp_path / "elsewhere"
    other.mkdir()
    with pytest.raises(SourceError, match="không nằm trong thư mục được phép"):
        inspect(str(other), [str(jobs_root)])
    with pytest.raises(SourceError, match="Không tìm thấy"):
        inspect(str(jobs_root / "nope"), [str(jobs_root)])
    empty = jobs_root / "empty"
    empty.mkdir()
    with pytest.raises(SourceError, match="không có bản vẽ"):
        inspect(str(empty), [str(jobs_root)])


def test_inspect_qa_dxf_file(jobs_root, job_dir):
    ai_l = job_dir / "AI_L"
    ai_l.mkdir()
    f = ai_l / "521030-10_ALL.dxf"
    f.write_text("0\nEOF\n")
    info = inspect(str(f), [str(jobs_root)], kind="QA")
    assert os.path.normcase(info["job_dir"]) == os.path.normcase(str(job_dir))
    assert info["has_slip"]
    with pytest.raises(SourceError):
        inspect(str(f), [str(jobs_root)], kind="RUN")


def test_inspect_qa_dxf_deep_in_job_finds_job_folder(jobs_root, job_dir):
    deep = job_dir / "gui" / "521030-10" / "521030-10"
    deep.mkdir(parents=True)
    f = deep / "26-064689.dxf"
    f.write_text("0\nEOF\n")
    info = inspect(str(f), [str(jobs_root)], kind="QA")
    assert os.path.normcase(info["job_dir"]) == os.path.normcase(str(job_dir))
    assert info["has_slip"] and info["job"] == "521030-10"


def test_inspect_qa_dxf_never_climbs_above_allowed_root(tmp_path):
    root = tmp_path / "jobs"
    loose = root / "x"
    loose.mkdir(parents=True)
    (tmp_path / "above.pdf").write_bytes(b"%PDF-1.4\n")  # outside the allowed root: must not be chosen
    f = loose / "a.dxf"
    f.write_text("0\nEOF\n")
    info = inspect(str(f), [str(root)], kind="QA")
    assert os.path.normcase(info["job_dir"]) == os.path.normcase(str(loose))


def test_validate_codes(jobs_root, job_dir):
    info = inspect(str(job_dir), [str(jobs_root)])
    assert validate_codes(None, info) is None
    assert validate_codes([c["code"] for c in info["codes"]], info) is None
    assert validate_codes(["26-064687"], info) == ["26-064687"]
    with pytest.raises(SourceError, match="26-999999"):
        validate_codes(["26-999999"], info)


def test_validate_codes_without_slip_rejects_selection(jobs_root):
    d = jobs_root / "x1"
    d.mkdir()
    (d / "a.pdf").write_bytes(b"%PDF")
    info = sources.inspect(str(d), [str(jobs_root)])
    assert validate_codes([], info) is None
    with pytest.raises(SourceError):
        validate_codes(["26-000001"], info)
