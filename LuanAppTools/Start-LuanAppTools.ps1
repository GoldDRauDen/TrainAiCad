[CmdletBinding()]
param(
    [ValidateRange(1,65535)][int]$Port = 8765,
    [string]$DataDir = (Join-Path $env:LOCALAPPDATA 'LuanAppTools'),
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path $PSScriptRoot -Parent
$VenvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
function Invoke-Checked {
    param([string]$Program, [string[]]$Arguments)
    & $Program @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Command failed ($LASTEXITCODE): $Program" }
}
try {
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Install Git for Windows, then reopen this launcher.' }
    if (-not (Test-Path $VenvPython)) {
        $PythonCommand = Get-Command py -ErrorAction SilentlyContinue
        if ($PythonCommand) {
            Invoke-Checked -Program $PythonCommand.Source -Arguments @('-3','-c','import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"')
            Invoke-Checked -Program $PythonCommand.Source -Arguments @('-3','-m','venv',(Join-Path $PSScriptRoot '.venv'))
        } else {
            $PythonCommand = Get-Command python -ErrorAction SilentlyContinue
            if (-not $PythonCommand) { throw 'Install Python 3.11+ with PATH enabled, then run again.' }
            Invoke-Checked -Program $PythonCommand.Source -Arguments @('-c','import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"')
            Invoke-Checked -Program $PythonCommand.Source -Arguments @('-m','venv',(Join-Path $PSScriptRoot '.venv'))
        }
    }
    Invoke-Checked -Program $VenvPython -Arguments @('-c','import sys; assert sys.version_info >= (3,11), "Python 3.11+ required"')
    Invoke-Checked -Program $VenvPython -Arguments @('-m','pip','install','-r',(Join-Path $PSScriptRoot 'requirements.txt'))
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'Install Node.js 20.19+ (LTS recommended), then run again.' }
    $NpmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
    if (-not $NpmCommand) { throw 'npm.cmd is missing. Reinstall Node.js with npm.' }
    Push-Location (Join-Path $PSScriptRoot 'frontend')
    try {
        Invoke-Checked -Program $NpmCommand.Source -Arguments @('ci','--no-audit','--no-fund')
        Invoke-Checked -Program $NpmCommand.Source -Arguments @('run','build')
    } finally { Pop-Location }
    if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
        Write-Host 'Claude CLI is missing. The dashboard still opens. Install the official Claude Code CLI and run claude auth login as this Windows user before starting jobs.' -ForegroundColor Yellow
    }
    $Url = "http://127.0.0.1:$Port"
    # Own the server process; a delayed browser launch never steals an occupied port.
    Push-Location $RepoRoot
    try {
        if (-not $NoBrowser) {
            $BrowserJob = Start-Job -ArgumentList $Url -ScriptBlock {
                param($Address)
                for ($Attempt=0; $Attempt -lt 120; $Attempt++) {
                    try {
                        $Health = Invoke-RestMethod -Uri "$Address/api/health" -TimeoutSec 1
                        if ($Health.status -eq 'ok') { Start-Process $Address; return }
                    } catch { }
                    Start-Sleep -Milliseconds 500
                }
            }
        }
        Invoke-Checked -Program $VenvPython -Arguments @('-m','LuanAppTools','--data-dir',$DataDir,'--repo-root',$RepoRoot,'--port',"$Port")
    } finally {
        if ($BrowserJob) { Stop-Job $BrowserJob -ErrorAction SilentlyContinue; Remove-Job $BrowserJob -Force -ErrorAction SilentlyContinue }
        Pop-Location
    }
} catch {
    Write-Host "LuanAppTools could not start: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
