$ErrorActionPreference = 'Stop'
$qwenControlRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
& (Join-Path $qwenControlRoot '.venv/Scripts/python.exe') -u -m qwenlab.support_control resume-check
if ($LASTEXITCODE -ne 0) { throw '恢复校验失败，未启动训练。' }
& (Join-Path $PSScriptRoot 'start-support-v8.ps1') -Resume
