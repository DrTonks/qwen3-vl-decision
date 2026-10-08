$ErrorActionPreference='Stop'
$qwen35Root=Split-Path -Parent $PSScriptRoot
. (Join-Path $PSScriptRoot 'use-env.ps1')
$qwen35BasePython=Join-Path $qwen35Root '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $qwen35BasePython)) { throw 'Create the existing project .venv first; see README.' }
$qwen35Env=Join-Path $qwen35Root '.venv-qwen35'
if (-not (Test-Path -LiteralPath (Join-Path $qwen35Env 'Scripts/python.exe'))) {
    & $qwen35BasePython -m venv --without-pip $qwen35Env
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create Qwen3.5 environment.' }
}
# The old runtime is an import fallback only. pip writes upgraded packages into the new venv.
$qwen35Fallback=(Join-Path $qwen35Root '.venv/Lib/site-packages')+"`n"+(Join-Path $qwen35Root 'src')+"`n"
[IO.File]::WriteAllText((Join-Path $qwen35Env 'Lib/site-packages/shared-runtime.pth'),$qwen35Fallback,(New-Object Text.UTF8Encoding($false)))
& (Join-Path $qwen35Env 'Scripts/python.exe') -m pip install -r (Join-Path $qwen35Root 'requirements-qwen35.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& (Join-Path $qwen35Env 'Scripts/python.exe') -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency compatibility check failed.' }
