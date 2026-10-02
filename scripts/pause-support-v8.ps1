param([switch]$CheckOnly, [switch]$Immediate)
$ErrorActionPreference = 'Stop'
$qwenControlRoot = Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$qwenControlArgs = @('-u','-m','qwenlab.support_control')
if ($CheckOnly) { $qwenControlArgs += 'check' } else { $qwenControlArgs += 'pause' }
if ($Immediate) { $qwenControlArgs += '--immediate' }
& (Join-Path $qwenControlRoot '.venv/Scripts/python.exe') @qwenControlArgs
if ($LASTEXITCODE -ne 0) { throw '暂停未确认完成，请检查上方错误，不要依据本命令关机。' }
