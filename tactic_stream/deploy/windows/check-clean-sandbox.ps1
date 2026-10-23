$ErrorActionPreference = 'Stop'
$results = 'C:\L12\Results'
$work = 'C:\L12\Work'
$report = @{ status = 'failed'; clean_windows_verified = $false; kind = 'Windows Sandbox' }
try {
    if ($env:USERNAME -ne 'WDAGUtilityAccount') { throw 'Run this check inside a new Windows Sandbox session.' }
    New-Item -ItemType Directory -Path $work -ErrorAction Stop | Out-Null
    $kit = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'kit.json') -Raw | ConvertFrom-Json
    foreach ($entry in $kit.files) {
        $path = Join-Path $PSScriptRoot $entry.path
        if ((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.sha256) { throw "Acceptance input checksum mismatch: $($entry.path)" }
    }
    Expand-Archive -LiteralPath (Join-Path $PSScriptRoot $kit.archive) -DestinationPath $work
    $bundle = Join-Path $work $kit.bundle
    $python = Join-Path $bundle 'runtime\python.exe'
    $exe = Join-Path $bundle 'TACTIC Stream.exe'
    $profile = Join-Path $work 'Test data'
    $report.os = (Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, BuildNumber)
    $report.system_commands = @(Get-Command python.exe, node.exe -ErrorAction SilentlyContinue | Select-Object Name, Source)
    $probe = Join-Path $PSScriptRoot 'tests\scripts\windows_package_probe.py'
    $report.runtime = (& $python -I -B -X utf8 $probe $bundle | ConvertFrom-Json)
    if ($LASTEXITCODE -ne 0) { throw 'Embedded Python/Qt isolation probe failed' }
    $env:WINDOWS_CHECK_PASSWORD = [Guid]::NewGuid().ToString('N')
    $env:ELECTRON_RUN_AS_NODE = '1'
    $script = Join-Path $PSScriptRoot 'frontend\tests\windows_delivery.mjs'
    $arguments = @(('"' + $script + '"'), ('"' + $bundle + '"'), ('"' + $profile + '"'))
    $test = Start-Process -FilePath $exe -ArgumentList $arguments -WorkingDirectory (Join-Path $PSScriptRoot 'frontend') -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput (Join-Path $work 'desktop.log') -RedirectStandardError (Join-Path $work 'desktop.err')
    if ($test.ExitCode -ne 0) { throw "Desktop acceptance failed: exit $($test.ExitCode); inspect $work\desktop.err" }
    Remove-Item Env:ELECTRON_RUN_AS_NODE
    $report.desktop = (Get-Content -LiteralPath (Join-Path $work 'desktop.log') | Where-Object { $_.StartsWith('{') } | Select-Object -Last 1 | ConvertFrom-Json)
    $env:TACTIC_HANDLER_SETTINGS_DIR = Join-Path $profile 'native-handler'
    $env:TACTIC_QML_SMOKE_OFFLINE = '1'
    $env:TACTIC_QML_SMOKE_EXIT_MS = '1800'
    $env:QT_QUICK_BACKEND = 'software'
    & $python -I -B -X utf8 (Join-Path $bundle 'TACTIC-Handler\launch.pyw') 2>&1 | Out-File -LiteralPath (Join-Path $work 'handler.log')
    if ($LASTEXITCODE -ne 0 -or (Select-String -LiteralPath (Join-Path $work 'handler.log') -Pattern 'Traceback|TypeError|ReferenceError|Binding loop|QML startup failed')) { throw 'Native Handler launch failed; inspect guest handler.log' }
    & $python -I -B -X utf8 $probe $bundle
    if ($LASTEXITCODE -ne 0) { throw 'Program files changed during acceptance' }
    Copy-Item -LiteralPath (Join-Path $profile 'desktop.png') -Destination (Join-Path $results 'desktop.png')
    $report.status = 'passed'
    $report.clean_windows_verified = $true
    $report.native_handler = 'passed'
    $report.program_inventory_unchanged = $true
} catch {
    $report.error = $_.Exception.Message
} finally {
    $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $results 'result.json') -Encoding UTF8
}
if ($report.status -ne 'passed') { exit 1 }
