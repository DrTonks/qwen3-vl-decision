param([switch]$Watch,[int]$IntervalSeconds=20)
$ErrorActionPreference='Stop'
if ($IntervalSeconds -lt 2) { throw 'IntervalSeconds must be at least 2.' }
$boundaryRoot=Split-Path -Parent $PSScriptRoot

function Read-SharedText([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    # Best-effort sharing only; this does not prove atomic replacement is safe.
    # Callers deliberately avoid the live files that the worker replaces.
    $share=[IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete
    $stream=[IO.File]::Open($Path,[IO.FileMode]::Open,[IO.FileAccess]::Read,$share)
    $reader=$null
    try {
        $reader=[IO.StreamReader]::new($stream,[Text.Encoding]::UTF8,$true)
        return $reader.ReadToEnd()
    } finally {
        if ($null -ne $reader) { $reader.Dispose() } else { $stream.Dispose() }
    }
}

do {
    # Never open status.json or training-summary.json while their writer is live.
    # Observe immutable protocol/launch metadata and append-only training logs.
    $launchText=Read-SharedText (Join-Path $boundaryRoot '.local/qwen35-boundary-launch.json')
    if (-not $launchText) { Write-Output 'Study has not started.'; break }
    $launch=$launchText | ConvertFrom-Json
    $launchStarted=if ($launch.started_at -is [datetime]) {
        [DateTimeOffset]$launch.started_at
    } else { [DateTimeOffset]::Parse([string]$launch.started_at) }
    $alive=$false
    try {
        $worker=Get-Process -Id $launch.pid -ErrorAction Stop
        $created=([DateTimeOffset]$worker.StartTime.ToUniversalTime()).ToUnixTimeMilliseconds()/1000.0
        $launched=$launchStarted.ToUnixTimeMilliseconds()/1000.0
        $alive=[Math]::Abs($created-$launched) -lt 5
    } catch { $alive=$false }
    $protocolText=Read-SharedText (Join-Path $boundaryRoot 'results/financial-qwen35-boundary-v1/protocol.json')
    if (-not $protocolText) {
        [ordered]@{phase='initializing';launcher_identity_alive=$alive;total_steps=$null;remaining_train_minutes_estimate=$null} | ConvertTo-Json
        if (-not $Watch -or -not $alive) { break }
        Start-Sleep -Seconds $IntervalSeconds
        continue
    }
    $protocol=$protocolText | ConvertFrom-Json
    $arms=[ordered]@{}
    $stepsDone=0
    $recent=@()
    foreach ($arm in @('replay','overlay')) {
        $logPath=Join-Path $boundaryRoot "results/financial-qwen35-boundary-v1-$arm/train.jsonl"
        $logText=Read-SharedText $logPath
        $entries=@()
        if ($logText) {
            # Ignore only the not-yet-completed last append, never an earlier row.
            $lines=$logText -split "`n"
            for ($i=0; $i -lt ($lines.Length-1); $i++) {
                if ($lines[$i].Trim()) { $entries+=($lines[$i] | ConvertFrom-Json) }
            }
        }
        $step=0
        if ($entries.Count) {
            $step=$entries[-1].step
            $recent+=@($entries | Select-Object -Last 30 | ForEach-Object { $_.elapsed_s })
        }
        $stepsDone+=$step
        $precedesLaunch=$false
        if ($logText) { $precedesLaunch=(Get-Item -LiteralPath $logPath).LastWriteTimeUtc -lt $launchStarted.UtcDateTime }
        $arms[$arm]=[ordered]@{step=$step;total_steps=$protocol.config.max_steps;log_precedes_current_launch=$precedesLaunch}
    }
    $estimate=$null
    if ($recent.Count) {
        $sorted=@($recent | Sort-Object)
        $median=$sorted[[int][Math]::Floor(($sorted.Count-1)/2)]
        $estimate=[Math]::Round((2*$protocol.config.max_steps-$stepsDone)*$median/60,1)
    }
    [ordered]@{observed_at=(Get-Date).ToString('o');launcher_pid=$launch.pid;
        launcher_identity_alive=$alive;arms=$arms;remaining_train_minutes_estimate=$estimate;
        estimate_scope='training only; excludes loading/evaluation/saving';
        reader='append-only training logs; never opens live status/summary files';
        note='Launcher alive does not prove forward progress; compare steps across observations. On exit inspect status/error log.'} | ConvertTo-Json -Depth 5
    if (-not $Watch -or -not $alive) { break }
    Start-Sleep -Seconds $IntervalSeconds
} while ($true)
