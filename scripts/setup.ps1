param([switch]$Direct)
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
. ./scripts/use-env.ps1
if ($Direct) { $env:NO_PROXY = '*' }
if (!(Test-Path .venv/Scripts/python.exe)) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Failed to create venv' }
}
& ./.venv/Scripts/python.exe -m pip install torch==2.8.0 --index-url https://download.pytorch.org/whl/cu128
if ($LASTEXITCODE -ne 0) { throw 'PyTorch install failed' }
& ./.venv/Scripts/python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependencies install failed' }
& ./.venv/Scripts/python.exe -m pip install -r requirements-train.txt
if ($LASTEXITCODE -ne 0) { throw 'Training dependencies install failed' }
& ./.venv/Scripts/python.exe -m pip install -e . --no-build-isolation
if ($LASTEXITCODE -ne 0) { throw 'Project installation failed' }
& ./.venv/Scripts/python.exe -c "import torch; print(torch.__version__); print('CUDA:',torch.cuda.is_available()); print(torch.cuda.get_device_name() if torch.cuda.is_available() else 'No CUDA GPU')"
