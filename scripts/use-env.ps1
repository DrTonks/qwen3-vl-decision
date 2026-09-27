$qwenRoot = Split-Path -Parent $PSScriptRoot
$env:TEMP = Join-Path $qwenRoot '.cache\tmp'
$env:TMP = $env:TEMP
$env:HF_HOME = Join-Path $qwenRoot '.cache\huggingface'
$env:TORCH_HOME = Join-Path $qwenRoot '.cache\torch'
$env:PIP_CACHE_DIR = Join-Path $qwenRoot '.cache\pip'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
New-Item -ItemType Directory -Force -Path $env:TEMP,$env:HF_HOME,$env:TORCH_HOME,$env:PIP_CACHE_DIR | Out-Null