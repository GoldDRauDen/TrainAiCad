[CmdletBinding()]
param(
    [ValidateRange(1,65535)][int]$Port = 8765,
    [switch]$Uninstall
)
# Luan App installer: venv + deps, auto-start at logon (current user), firewall rule (Private), admin password.
$ErrorActionPreference = 'Stop'
$AppDir   = $PSScriptRoot
$RepoRoot = Split-Path $AppDir -Parent
$Venv     = Join-Path $AppDir '.venv'
$Py       = Join-Path $Venv 'Scripts\python.exe'
$PyW      = Join-Path $Venv 'Scripts\pythonw.exe'
$TaskName = 'Luan App'
$RuleName = "Luan App $Port"

function Invoke-Checked([string]$Program, [string[]]$Arguments) {
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Lệnh lỗi ($LASTEXITCODE): $Program $($Arguments -join ' ')" }
}

function Invoke-Elevated([string]$Command) {
    $p = Start-Process powershell.exe -Verb RunAs -Wait -PassThru -WindowStyle Hidden `
         -ArgumentList @('-NoProfile', '-Command', $Command)
    return $p.ExitCode
}

if ($Uninstall) {
    if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
        Write-Host "Đã gỡ tác vụ tự khởi động '$TaskName'."
    }
    if (Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue) {
        Write-Host 'Gỡ luật firewall (cần xác nhận quyền Administrator)...'
        Invoke-Elevated "Remove-NetFirewallRule -DisplayName '$RuleName'" | Out-Null
    }
    Write-Host 'Xong. Dữ liệu app vẫn ở %LOCALAPPDATA%\LuanApp (xóa tay nếu muốn).'
    exit 0
}

# 1. Python + venv
if (-not (Test-Path $Py)) {
    $Base = Get-Command py -ErrorAction SilentlyContinue
    $BaseArgs = @('-3')
    if (-not $Base) { $Base = Get-Command python -ErrorAction SilentlyContinue; $BaseArgs = @() }
    if (-not $Base) { throw 'Chưa có Python 3.11+. Cài Python (bật Add to PATH) rồi chạy lại.' }
    Invoke-Checked $Base.Source ($BaseArgs + @('-c', 'import sys; assert sys.version_info >= (3, 11), "Cần Python 3.11+"'))
    Invoke-Checked $Base.Source ($BaseArgs + @('-m', 'venv', $Venv))
}
Write-Host 'Cài thư viện cho Luan App...'
Invoke-Checked $Py @('-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '-r', (Join-Path $AppDir 'requirements.txt'))

# 2. Claude CLI
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Warning 'Không thấy Claude CLI. Cài Claude Code và chạy "claude auth login" bằng tài khoản Windows này trước khi chạy job.'
}

# 3. Auto-start at logon, as this user (needs this user's Claude login and network drives)
$Action    = New-ScheduledTaskAction -Execute $PyW -Argument "-m luan_app --port $Port --no-browser" -WorkingDirectory $RepoRoot
$Trigger   = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$Settings  = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Principal $Principal -Force | Out-Null
Write-Host "Đã tạo tác vụ '$TaskName' (tự chạy khi đăng nhập Windows)."

# 4. Firewall: Private profile only
if (-not (Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue)) {
    Write-Host 'Mở cổng cho mạng LAN (Private) — cần xác nhận quyền Administrator...'
    $code = Invoke-Elevated "New-NetFirewallRule -DisplayName '$RuleName' -Direction Inbound -Protocol TCP -LocalPort $Port -Profile Private -Action Allow | Out-Null"
    if ($code -ne 0) { Write-Warning 'Chưa mở được cổng firewall. Máy khác trong LAN sẽ chưa vào được.' }
}
$Net = Get-NetConnectionProfile -ErrorAction SilentlyContinue | Where-Object { $_.NetworkCategory -ne 'Private' }
if ($Net) { Write-Warning "Mạng '$($Net[0].Name)' đang là $($Net[0].NetworkCategory). Đổi sang Private để máy khác vào được." }

# 5. Admin password (first time)
$HasPw = & $Py -c "from luan_app.auth import Auth; from luan_app.store import Store; from luan_app.config import load_paths; print(Auth(Store(load_paths().db_path)).has_admin_password())"
if ($HasPw -ne 'True') {
    Push-Location $RepoRoot
    try { Invoke-Checked $Py @('-m', 'luan_app', '--setup-password') } finally { Pop-Location }
}

# 6. Start now
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3
$Ip = (Get-NetIPAddress -AddressFamily IPv4 -PrefixOrigin Dhcp, Manual -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike '169.254*' } | Select-Object -First 1).IPAddress
Write-Host ''
Write-Host "Luan App đang chạy:  http://127.0.0.1:$Port"
if ($Ip) { Write-Host "Link cho mọi người:  http://${Ip}:$Port" }
Start-Process "http://127.0.0.1:$Port"
