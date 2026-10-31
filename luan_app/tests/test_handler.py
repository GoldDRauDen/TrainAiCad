import base64
import json
import re
import shutil
import subprocess
import sys
import urllib.parse
from pathlib import Path

import pytest

from luan_app import handler

STATIC = Path(__file__).resolve().parents[1] / "static"
UNC = "\\\\VietNam2025\\d\\LASER"
JP = "D:\\図面\\Gốc"
REG_COMMAND = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File \"{}\\AICAD\\open.ps1\" \"%1\""

needs_windows = pytest.mark.skipif(sys.platform != "win32" or not shutil.which("powershell"),
                                   reason="needs Windows PowerShell")


def _payload(text):
    m = re.search(r"FromBase64String\('([A-Za-z0-9+/=]+)'\)", text)
    assert m, "no base64 payload"
    return base64.b64decode(m.group(1))


def test_installer_shape():
    text = handler.build_installer([UNC, JP])
    assert handler.SCHEME == "aicad-open"
    assert "\r\n" in text and "\n" not in text.replace("\r\n", "")
    assert text.startswith("@echo off\r\n")
    assert "%%1" in text and '\\"%%1\\""' in text
    assert 'reg add "HKCU\\Software\\Classes\\aicad-open" /ve /d "URL:AI CAD open folder" /f' in text
    assert 'reg add "HKCU\\Software\\Classes\\aicad-open" /v "URL Protocol" /d "" /f' in text
    assert 'reg add "HKCU\\Software\\Classes\\aicad-open\\shell\\open\\command" /ve /d "powershell.exe' in text
    assert '-File \\"%LOCALAPPDATA%\\AICAD\\open.ps1\\"' in text
    assert "Đã cài bộ mở thư mục AI CAD. Quay lại trình duyệt, bấm nút thư mục ở job." in text
    assert text.rstrip().splitlines()[-1] == "exit /b 1" and "pause" in text
    assert all(len(line) < 8000 for line in text.splitlines())


def test_payload_is_open_ps1_with_roots():
    raw = _payload(handler.build_installer([UNC, JP]))
    assert raw.startswith(b"\xef\xbb\xbf")
    script = raw[3:].decode("utf-8")
    assert script == handler.OPEN_PS1.replace("__AICAD_ROOTS__", f"'{UNC}','{JP}'")
    assert script == handler.render_open_ps1([UNC, JP])
    assert "param([string]$Url" in script and "[switch]$DryRun" in script
    assert "Start-Process explorer.exe" in script and "UnescapeDataString" in script


def test_root_quotes_are_escaped():
    script = handler.render_open_ps1(["D:\\O'Brien\\x", "E:\\a\u2019b"])
    assert "@('D:\\O''Brien\\x','E:\\a\u2019\u2019b')" in script
    with pytest.raises(ValueError):
        handler.render_open_ps1([])
    with pytest.raises(ValueError):
        handler.render_open_ps1(["D:\\a\r\nb"])


def test_uninstall_variant():
    text = handler.build_installer([], uninstall=True)
    assert "\r\n" in text
    assert 'reg delete "HKCU\\Software\\Classes\\aicad-open" /f' in text
    assert 'rmdir /s /q "%LOCALAPPDATA%\\AICAD"' in text
    assert "reg add" not in text and "FromBase64String" not in text
    assert "pause" in text


def test_guide_page():
    html = (STATIC / "guide.html").read_text(encoding="utf-8")
    assert "AI CAD" in html and 'href="/api/open-handler.cmd"' in html
    assert "/api/open-handler.cmd?uninstall=1" in html
    assert not re.search(r'(src|href)="https?://', html)
    for ref in re.findall(r'(?:src|href)="([^"#/][^"#]*)"', html):
        assert (STATIC / ref).is_file(), ref


# --- Windows only: run the real script / installer -------------------------------------------

def _url(path):
    return "aicad-open:" + urllib.parse.quote(str(path).replace("\\", "/"), safe="/:")


@pytest.fixture
def dry(tmp_path):
    root = tmp_path / "Gốc 図面"
    (root / "JOB1" / "AI_L").mkdir(parents=True)
    (root / "JOB2").mkdir()
    (tmp_path / "outside").mkdir()
    ps1 = tmp_path / "open.ps1"
    ps1.write_bytes(_payload(handler.build_installer([str(root)])))

    def run(url):
        p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1),
                            "-Url", url, "-DryRun"], capture_output=True, timeout=60, cwd=tmp_path)
        assert p.returncode == 0, p.stderr
        assert not p.stderr.strip(), p.stderr.decode("utf-8", "replace")
        return p.stdout.decode("utf-8-sig", "replace").strip()

    run.root, run.tmp = root, tmp_path
    return run


@needs_windows
def test_open_ps1_dry_run(dry):
    root, tmp = dry.root, dry.tmp
    ail = root / "JOB1" / "AI_L"
    assert dry(_url(ail)) == str(ail)                               # allowed, exists
    upper = dry(_url(ail).upper().replace("AICAD-OPEN:", "aicad-open:"))  # root match ignores case
    assert upper.casefold() == str(ail).casefold()
    assert dry("aicad-open:" + urllib.parse.quote(str(ail), safe="")) == str(ail)  # %5C-encoded backslashes
    assert dry(_url(root)) == str(root)                             # the root itself
    assert dry(_url(root / "JOB2" / "AI_L")) == str(root / "JOB2")  # AI_L missing -> its job folder
    assert dry(_url(tmp / "outside")) == ""                          # outside the roots
    assert dry(_url(str(root) + "x")) == ""                          # not a whole path segment
    assert dry(_url(str(root) + "/JOB1/../../outside")) == ""        # .. segment
    assert dry(_url(str(root) + "/JOB1/%2E%2E/%2E%2E/outside")) == ""  # encoded ..
    assert dry(_url(root / "nope" / "deeper")) == ""                 # parent missing too
    assert dry("http://example.com/") == ""                          # wrong scheme
    assert dry("aicad-open:") == ""


@needs_windows
def test_open_ps1_never_runs_the_url(dry):
    root, tmp = dry.root, dry.tmp
    assert dry("aicad-open:" + str(root).replace("\\", "/") + "/JOB1'; calc; '") == ""
    pwned = tmp / "pwned.txt"
    for code in (f"$(New-Item -ItemType File '{pwned}')", "$(New-Item -ItemType File pwned.txt)",
                 "x`; New-Item pwned.txt", "%22; New-Item pwned.txt; %22"):
        assert dry("aicad-open:" + str(root).replace("\\", "/") + "/" + code) in ("", str(root))
    assert not pwned.exists() and not (root / "pwned.txt").exists() and not (tmp / "pwned.txt").exists()


@needs_windows
def test_open_ps1_unc(tmp_path):
    share = "\\\\localhost\\C$\\Windows"
    probe = subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"Test-Path -LiteralPath '{share}' -PathType Container"], capture_output=True, text=True)
    if probe.stdout.strip() != "True":
        pytest.skip("admin share \\\\localhost\\C$ not reachable")
    ps1 = tmp_path / "open.ps1"
    ps1.write_bytes(_payload(handler.build_installer([share])))
    p = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-Url",
                        "aicad-open://localhost/C$/Windows/System32", "-DryRun"], capture_output=True, text=True)
    assert p.stdout.strip() == share + "\\System32"


@needs_windows
def test_installer_runs_with_reg_stubbed(tmp_path):
    """Run the real .cmd with LOCALAPPDATA in tmp and `reg` replaced by an argv recorder (the registry is untouched)."""
    lad = tmp_path / "Local App Data"
    lad.mkdir()
    log = tmp_path / "argv.jsonl"
    rec = tmp_path / "rec.py"
    rec.write_text("import json, sys\nwith open(sys.argv[1], 'a', encoding='utf-8') as f:\n"
                   "    f.write(json.dumps(sys.argv[2:]) + '\\n')\n", encoding="utf-8")
    roots = [str(tmp_path / "Gốc"), "D:\\O'Brien"]
    text = handler.build_installer(roots)
    stub = f'"{sys.executable}" "{rec}" "{log}" '
    lines = [stub + ln[4:] if ln.startswith("reg ") else ln for ln in text.split("\r\n") if ln != "pause"]
    cmd = tmp_path / "install.cmd"
    cmd.write_bytes("\r\n".join(lines).encode("utf-8"))
    env = {**__import__("os").environ, "LOCALAPPDATA": str(lad)}
    p = subprocess.run(["cmd", "/c", str(cmd)], capture_output=True, env=env, cwd=tmp_path, timeout=120)
    out = p.stdout.decode("utf-8", "replace")
    assert p.returncode == 0, out + p.stderr.decode("utf-8", "replace")
    assert "Đã cài bộ mở thư mục AI CAD" in out
    written = (lad / "AICAD" / "open.ps1").read_bytes()
    assert written == b"\xef\xbb\xbf" + handler.render_open_ps1(roots).encode("utf-8")
    calls = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines()]
    assert calls == [
        ["add", "HKCU\\Software\\Classes\\aicad-open", "/ve", "/d", "URL:AI CAD open folder", "/f"],
        ["add", "HKCU\\Software\\Classes\\aicad-open", "/v", "URL Protocol", "/d", "", "/f"],
        ["add", "HKCU\\Software\\Classes\\aicad-open\\shell\\open\\command", "/ve", "/d",
         REG_COMMAND.format(lad), "/f"],
    ]
