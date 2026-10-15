# Optional Windows PowerShell 5.1 smoke test. No downloads, no database writes.
# Not run by the three launchers. Example from repository root:
# powershell -NoProfile -File tests/native_ui/test_bootstrap_020.ps1 -Python C:\...\python.exe
param([string]$Python = '', [string]$Output = '')
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$bootstrap = Join-Path $Root 'tools/local/tactic_bootstrap.ps1'
$tokens = $null; $errors = $null
[void][Management.Automation.Language.Parser]::ParseFile($bootstrap, [ref]$tokens, [ref]$errors)
if (@($errors).Count) { throw ('PowerShell parse errors: ' + ($errors | Out-String)) }
. $bootstrap
$Results = New-Object Collections.Generic.List[object]
function Check([string]$Name, [bool]$Passed) {
    [void]$Results.Add(@{ name = $Name; passed = $Passed })
    if (!$Passed) { throw ('FAILED: ' + $Name) }
    Write-Host ('PASS ' + $Name)
}
Check 'PowerShell AST parses bootstrap' $true

$ea = Get-TacticEntryArguments 'start' @()
Check 'START without args launches, not menu' ($ea.Count -eq 1 -and $ea[0] -ceq 'start')
$ea = Get-TacticEntryArguments 'start' @('--data-dir','C:\Data & ! %')
Check 'START preserves arguments as data' ($ea.Count -eq 3 -and $ea[2] -ceq 'C:\Data & ! %')
$ea = Get-TacticEntryArguments 'setup' @('--offline','--repair')
Check 'SETUP uses its dedicated action' ($ea.Count -eq 3 -and $ea[0] -ceq 'setup')
$ea = Get-TacticEntryArguments 'manage' @()
Check 'MANAGE without args selects menu' ($ea.Count -eq 0)
$ea = Get-TacticEntryArguments 'manage' @('check','db','--data-dir','C:\Data')
Check 'MANAGE preserves direct commands' ($ea.Count -eq 4 -and $ea[0] -ceq 'check')
$denied = $false
try { Get-TacticEntryArguments 'unknown' @() | Out-Null } catch { $denied = $true }
Check 'Unknown entry does not become start' $denied

Check 'Empty native argument' ((ConvertTo-TacticNativeArgument '') -ceq '""')
Check 'Plain native argument' ((ConvertTo-TacticNativeArgument 'plain') -ceq 'plain')
Check 'Native spaces' ((ConvertTo-TacticNativeArgument 'a b') -ceq '"a b"')
Check 'Trailing backslash' ((ConvertTo-TacticNativeArgument 'C:\Space dir\') -ceq '"C:\Space dir\\"')
Check 'Embedded quote' ((ConvertTo-TacticNativeArgument 'say "hi"') -ceq '"say \"hi\""')
Check 'Metacharacters are not shell syntax' ((ConvertTo-TacticNativeArgument 'a&b!%') -ceq 'a&b!%')
$opts = Get-TacticSetupOptions @('--offline','--repair','--dry-run')
Check 'Setup flags' ($opts.Flags -contains '-Repair' -and $opts.Flags -contains '-Offline' -and $opts.DryRun)
$denied = $false
try { Get-TacticSetupOptions @('--yes') | Out-Null } catch { $denied = $true }
Check 'Unknown setup flag rejected' $denied
$temp = Join-Path ([IO.Path]::GetTempPath()) ('tactic-bootstrap-check-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $temp | Out-Null
$previousPython = $env:TACTIC_PYTHON
$previousJSON = $env:TACTIC_BOOTSTRAP_ARGV_JSON
try {
    $one = Join-Path $temp 'one.exe'; $two = Join-Path $temp 'two.exe'
    [IO.File]::WriteAllText($one, 'TEST sentinel - not an executable')
    [IO.File]::WriteAllText($two, 'TEST sentinel - not an executable')
    $env:TACTIC_PYTHON = $one
    Check 'Environment Python selected' ((Get-TacticPython $temp @()) -ceq $one)
    Check 'Explicit Python wins' ((Get-TacticPython $temp @('--python',$two)) -ceq $two)
    $denied = $false
    try { Get-TacticPython $temp @('--python',(Join-Path $temp 'missing.exe')) | Out-Null } catch { $denied = $true }
    Check 'Missing explicit path rejected without fallback' $denied
    if ($Python) {
        $exe = Resolve-TacticPath $Python $Root
        if (!(Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'Test Python not found.' }
        $env:TACTIC_BOOTSTRAP_ARGV_JSON = ConvertTo-Json -InputObject @('start','--dry-run','--data-dir',(Join-Path $temp 'Данные & ! %')) -Compress
        $rc = Invoke-TacticNative $exe @('-X','utf8','-s',(Join-Path $Root 'tools/local/control.py'),'--bootstrap-argv') $Root
        Check 'Real Python receives JSON arguments and dry-runs' ($rc -eq 0)
        $rc = Invoke-TacticNative $exe @('-c','raise SystemExit(7)') $Root
        Check 'Actual native child exit code' ($rc -eq 7)
    } else { Write-Host 'SKIP actual native Python execution: pass -Python to enable.' }
} finally {
    $env:TACTIC_PYTHON = $previousPython
    $env:TACTIC_BOOTSTRAP_ARGV_JSON = $previousJSON
    Remove-Item -LiteralPath $temp -Recurse -Force
}
$result = @{ passed = $true; checks = @($Results); powershell_version = $PSVersionTable.PSVersion.ToString(); python_native_test = [bool]$Python }
if ($Output) { $result | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $Output -Encoding UTF8 }
$result | ConvertTo-Json -Depth 8
