param(
    [string]$Output = ".chatgpt-codex\permissions.json",
    [switch]$Force
)

$ErrorActionPreference = "Stop"

Set-Location (Join-Path $PSScriptRoot "..")

if ((Test-Path $Output) -and -not $Force) {
    throw "$Output already exists. Use -Force to overwrite. / $Output 已存在，请使用 -Force 覆盖。"
}

$Parent = Split-Path -Parent $Output
if ($Parent) {
    New-Item -ItemType Directory -Force -Path $Parent | Out-Null
}

Copy-Item -Path "permissions.example.json" -Destination $Output -Force:$Force

Write-Host "Permissions template written:"
Write-Host "授权模板已写入:"
Write-Host "  $Output"
Write-Host ""
Write-Host "Edit this file, or replace it by running:"
Write-Host "编辑此文件，或运行下面命令替换为自动生成版本:"
Write-Host "  chatgpt-codex authorize --workspace C:\absolute\path\to\project --operating-system windows --access-plan built-in-quick-tunnel --public-base-url https://actions.example.com --allow-browser-automation --allow-start-services --allow-install-helpers --allow-workspace-write --allow-command-execution --force"
