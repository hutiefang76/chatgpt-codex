$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")
$Root = (Get-Location).Path

$PythonCommand = $null
$PythonArgs = @()

if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = "py"
    $PythonArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = "python"
} else {
    throw "Python 3 was not found. Install Python 3.9 or newer first. / 未找到 Python 3，请先安装 Python 3.9 或更新版本。"
}

& $PythonCommand @PythonArgs -m venv .venv
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$LauncherPath = Join-Path $Root ".venv\Scripts\chatgpt-codex.cmd"
$PythonPath = Join-Path $Root ".venv\Scripts\python.exe"

$Launcher = @"
@echo off
set "PYTHONPATH=$Root;%PYTHONPATH%"
"$PythonPath" -m chatgpt_codex %*
"@

Set-Content -Path $LauncherPath -Value $Launcher -Encoding ASCII

Write-Host "chatgpt-codex installed for Windows PowerShell."
Write-Host "chatgpt-codex 已完成 Windows PowerShell 安装。"
Write-Host ""
Write-Host "Next:"
Write-Host "下一步:"
Write-Host "  . .\.venv\Scripts\Activate.ps1"
Write-Host "  chatgpt-codex init --workspace C:\absolute\path\to\project --public-base-url https://actions.example.com"
Write-Host "  chatgpt-codex serve"
