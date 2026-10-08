param([switch]$Probe)
$ErrorActionPreference = 'Stop'
$fullcoverArguments = @{ Resume = $true }
if ($Probe) { $fullcoverArguments.Probe = $true }
& (Join-Path $PSScriptRoot 'start-financial-full-coverage.ps1') @fullcoverArguments
