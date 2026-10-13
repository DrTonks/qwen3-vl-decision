param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$full2bArguments = @{ Resume = $true }
if ($Probe) { $full2bArguments.Probe = $true }
& (Join-Path $PSScriptRoot 'start-financial-2b-full-coverage.ps1') @full2bArguments
