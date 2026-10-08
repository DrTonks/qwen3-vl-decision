$ErrorActionPreference='Stop'
$boundaryRoot=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
& (Join-Path $boundaryRoot '.venv-qwen35/Scripts/python.exe') -m qwenlab.qwen35_boundary_study pause
if ($LASTEXITCODE -ne 0) { throw 'Pause was not confirmed; do not shut down before inspection.' }
