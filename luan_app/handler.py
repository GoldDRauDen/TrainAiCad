"""`aicad-open:` links: open a job folder in File Explorer from the browser.

A web page cannot open `\\\\server\\share\\...\\AI_L` in Explorer, so each user installs, for their own
Windows account only (HKCU, no admin rights), a tiny URL handler: `build_installer()` returns a
self-contained `.cmd` that writes `%LOCALAPPDATA%\\AICAD\\open.ps1` and registers the scheme.

The link is data, never code: it reaches `open.ps1` only as its `-Url` argument, and the script opens
a folder only when it lies under one of the allowed roots baked in at install time.
"""
from __future__ import annotations

import base64

SCHEME = "aicad-open"
REG_KEY = r"HKCU\Software\Classes" + "\\" + SCHEME
_ROOTS_MARK = "__AICAD_ROOTS__"
# PowerShell treats these as single quotes too; inside a '...' string each is escaped by doubling it.
_PS_QUOTES = "'\u2018\u2019\u201a\u201b"
_CMD_LINE_MAX = 8000  # cmd.exe refuses lines longer than 8191 characters

OPEN_PS1 = r"""param([string]$Url = '', [switch]$DryRun)
# AI CAD: opens a company folder in File Explorer from an aicad-open: link.
# The link only ever arrives here as data (-Url); it is never run as code.
$Roots = @(__AICAD_ROOTS__)
$ErrorActionPreference = 'Stop'

function Test-Allowed([string]$p) {
    foreach ($r in $Roots) {
        $r = ([string]$r).Replace('/', '\').TrimEnd('\')
        if (-not $r) { continue }
        if ($p.Equals($r, [StringComparison]::OrdinalIgnoreCase)) { return $true }
        if ($p.StartsWith($r + '\', [StringComparison]::OrdinalIgnoreCase)) { return $true }
    }
    return $false
}

function Get-AicadPath([string]$u) {
    $head = 'aicad-open:'
    if (-not $u.StartsWith($head, [StringComparison]::OrdinalIgnoreCase)) { return $null }
    $s = $u.Substring($head.Length).TrimStart('/', '\')
    $s = [uri]::UnescapeDataString($s).Replace('/', '\').TrimStart('\')
    if (-not $s) { return $null }
    foreach ($ch in $s.ToCharArray()) { if ([int]$ch -lt 32) { return $null } }
    if ($s.IndexOfAny([char[]]'"|<>*?;''`') -ge 0) { return $null }
    if ($s -match '^[A-Za-z]:\\') {
        if ($s.IndexOf(':', 2) -ge 0) { return $null }
    } else {
        if ($s.IndexOf(':') -ge 0) { return $null }
        $s = '\\' + $s
    }
    $s = $s.TrimEnd('\')
    if ($s.Length -eq 2) { $s += '\' }
    foreach ($seg in $s.Split('\')) { if ($seg -match '^[. ]+$') { return $null } }
    if (-not (Test-Allowed $s)) { return $null }
    return $s
}

try {
    $p = Get-AicadPath $Url
    if (-not $p) { exit 0 }
    $target = $null
    if (Test-Path -LiteralPath $p -PathType Container) {
        $target = $p
    } else {
        $i = $p.TrimEnd('\').LastIndexOf('\')
        if ($i -gt 1) {
            $parent = $p.Substring(0, $i)
            if ($parent.Length -eq 2) { $parent += '\' }
            if ((Test-Allowed $parent) -and (Test-Path -LiteralPath $parent -PathType Container)) { $target = $parent }
        }
    }
    if (-not $target) { exit 0 }
    if ($DryRun) {
        try { [Console]::OutputEncoding = New-Object Text.UTF8Encoding $false } catch { }
        Write-Output $target
    } else {
        Start-Process explorer.exe -ArgumentList ('"' + $target + '"')
    }
} catch {
    exit 0
}
exit 0
"""


def _ps_single_quoted(s: str) -> str:
    for q in _PS_QUOTES:
        s = s.replace(q, q + q)
    return "'" + s + "'"


def _clean_roots(roots: list[str]) -> list[str]:
    out = []
    for r in roots or []:
        r = str(r).strip()
        if not r:
            continue
        if any(ord(c) < 32 for c in r):
            raise ValueError(f"Thư mục gốc có ký tự điều khiển: {r!r}")
        out.append(r)
    if not out:
        raise ValueError("Chưa có thư mục gốc nào trong Cài đặt — không tạo được bộ cài mở thư mục.")
    return out


def render_open_ps1(roots: list[str]) -> str:
    """OPEN_PS1 with the allowed roots baked in as a PowerShell single-quoted string array."""
    return OPEN_PS1.replace(_ROOTS_MARK, ",".join(_ps_single_quoted(r) for r in _clean_roots(roots)))


def ps1_payload(roots: list[str]) -> str:
    """Base64 of open.ps1 as UTF-8 with BOM (so Windows PowerShell 5.1 reads non-ASCII roots right)."""
    return base64.b64encode(b"\xef\xbb\xbf" + render_open_ps1(roots).encode("utf-8")).decode("ascii")


def _cmd(lines: list[str]) -> str:
    return "\r\n".join(lines) + "\r\n"


def build_installer(roots: list[str], uninstall: bool = False) -> str:
    """Text of the per-user `.cmd` (CRLF; serve it as UTF-8 without BOM — it switches cmd to code page 65001)."""
    head = ["@echo off", "setlocal", "chcp 65001 >nul"]
    if uninstall:
        return _cmd(head + [
            f'reg delete "{REG_KEY}" /f >nul 2>nul',
            r'if exist "%LOCALAPPDATA%\AICAD\" rmdir /s /q "%LOCALAPPDATA%\AICAD"',
            "echo.",
            "echo Đã gỡ bộ mở thư mục AI CAD.",
            "echo.",
            "pause",
        ])
    write_ps1 = ("powershell -NoProfile -ExecutionPolicy Bypass -Command "
                 "\"[IO.File]::WriteAllBytes($env:LOCALAPPDATA + '\\AICAD\\open.ps1', "
                 f"[Convert]::FromBase64String('{ps1_payload(roots)}'))\" || goto :fail")
    if len(write_ps1) > _CMD_LINE_MAX:
        raise ValueError("Danh sách thư mục gốc quá dài cho bộ cài mở thư mục.")
    # reg.exe reads \" as a literal quote; %%1 is %1 once cmd has read the batch file. Stored value:
    # powershell.exe ... -File "C:\Users\X\AppData\Local\AICAD\open.ps1" "%1"
    command = (r'reg add "' + REG_KEY + r'\shell\open\command" /ve /d "powershell.exe -NoProfile '
               r'-ExecutionPolicy Bypass -WindowStyle Hidden -File \"%LOCALAPPDATA%\AICAD\open.ps1\" '
               r'\"%%1\"" /f >nul || goto :fail')
    return _cmd(head + [
        r'if not exist "%LOCALAPPDATA%\AICAD\" mkdir "%LOCALAPPDATA%\AICAD"',
        r'if not exist "%LOCALAPPDATA%\AICAD\" goto :fail',
        write_ps1,
        f'reg add "{REG_KEY}" /ve /d "URL:AI CAD open folder" /f >nul || goto :fail',
        f'reg add "{REG_KEY}" /v "URL Protocol" /d "" /f >nul || goto :fail',
        command,
        "echo.",
        "echo Đã cài bộ mở thư mục AI CAD. Quay lại trình duyệt, bấm nút thư mục ở job.",
        "echo.",
        "pause",
        "exit /b 0",
        ":fail",
        "echo.",
        "echo Cài không thành công. Chụp màn hình này gửi Admin.",
        "pause",
        "exit /b 1",
    ])
