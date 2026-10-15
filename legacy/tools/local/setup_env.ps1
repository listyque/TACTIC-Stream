param([switch]$Repair, [switch]$Offline)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$Root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$Runtime = Join-Path $Root '.runtime'
$PythonDir = Join-Path $Runtime 'python'
$Download = Join-Path $Runtime 'downloads'
$Spec = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'runtime-manifest.json') -Raw | ConvertFrom-Json
function Invoke-Checked([string]$Exe, [string[]]$Arguments) {
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed (exit $LASTEXITCODE). Setup is NOT complete." }
}
function Fetch([string]$Url, [string]$Path, [string]$Hash = '') {
    if (Test-Path -LiteralPath $Path) {
        if (!$Hash -or (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() -eq $Hash) { return }
        if ($Offline) { throw "Cached archive hash mismatch: $Path" }
        Remove-Item -LiteralPath $Path
    }
    if ($Offline) { throw "Offline cache is missing: $Path" }
    Write-Host "Downloading $Url"
    $Part = "$Path.part"
    try {
        Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $Part -TimeoutSec 180
        if ($Hash -and (Get-FileHash -LiteralPath $Part -Algorithm SHA256).Hash.ToLowerInvariant() -ne $Hash) {
            throw "SHA-256 mismatch. Download will NOT be executed: $Url"
        }
        Move-Item -LiteralPath $Part -Destination $Path -Force
    } finally { if (Test-Path -LiteralPath $Part) { Remove-Item -LiteralPath $Part -Force } }
}
try {
    if (![Environment]::Is64BitOperatingSystem -or $env:PROCESSOR_ARCHITECTURE -eq 'ARM64') {
        throw 'This downloader targets Windows x64, not x86/ARM64.'
    }
    New-Item -ItemType Directory -Path $Download -Force | Out-Null
    $Exe = Join-Path $PythonDir 'python.exe'
    $Marker = Join-Path $Runtime 'python-source.json'
    if ((Test-Path -LiteralPath $PythonDir) -and !(Test-Path -LiteralPath $Marker)) {
        throw "Unknown runtime at $PythonDir. It will NOT be overwritten. Rename this directory first."
    }
    if (Test-Path -LiteralPath $Marker) {
        $Previous = Get-Content -LiteralPath $Marker -Raw | ConvertFrom-Json
        if ($Previous.sha256 -ne $Spec.python.sha256) { throw 'Different managed Python exists. Back it up/rename .runtime before switching versions.' }
    }
    if (!(Test-Path -LiteralPath $Exe) -or $Repair) {
        $Archive = Join-Path $Download ('python-' + $Spec.python.version + '-embed-amd64.zip')
        Fetch $Spec.python.url $Archive $Spec.python.sha256
        $Stage = Join-Path $Runtime ('python-stage-' + [guid]::NewGuid().ToString('N'))
        try {
            Expand-Archive -LiteralPath $Archive -DestinationPath $Stage
            $Signature = Get-AuthenticodeSignature -LiteralPath (Join-Path $Stage 'python.exe')
            if ($Signature.Status -ne 'Valid' -or $Signature.SignerCertificate.Subject -notmatch 'Python Software Foundation') {
                throw 'Python executable signature is not a valid Python Software Foundation signature.'
            }
            $Pth = Join-Path $Stage 'python313._pth'
            # Python's isolated embeddable runtime, with ONLY a project-local site-packages.
            [IO.File]::WriteAllText($Pth, "python313.zip`r`n.`r`nLib/site-packages`r`nimport site`r`n", [Text.Encoding]::ASCII)
            if (Test-Path -LiteralPath $PythonDir) {
                $Backup = Join-Path $Runtime ('python-backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
                Move-Item -LiteralPath $PythonDir -Destination $Backup
                Write-Host "Previous environment retained at $Backup"
            }
            Move-Item -LiteralPath $Stage -Destination $PythonDir
            $Spec.python | ConvertTo-Json | Set-Content -LiteralPath $Marker -Encoding UTF8
        } finally { if (Test-Path -LiteralPath $Stage) { Remove-Item -LiteralPath $Stage -Recurse -Force } }
    }
    $Pip = Join-Path $Download ('pip-' + $Spec.pip.version + '.pyz')
    Fetch $Spec.pip.url $Pip
    try {
        Invoke-Checked $Exe @('-s', (Join-Path $PSScriptRoot 'validate_pip_zipapp.py'), $Pip, '--version', $Spec.pip.version)
    } catch {
        # Fetch used to accept an HTML directory/404 response from the cache.
        # Remove only this failed managed pip download, never the Python runtime.
        if (Test-Path -LiteralPath $Pip) { Remove-Item -LiteralPath $Pip -Force }
        throw "Invalid cached/downloaded pip zipapp was removed. Rerun SETUP_ENV.bat. Details: $($_.Exception.Message)"
    }
    $Site = Join-Path $PythonDir 'Lib/site-packages'
    New-Item -ItemType Directory -Path $Site -Force | Out-Null
    $Req = Join-Path $PSScriptRoot 'requirements.txt'
    $Wheelhouse = Join-Path $Runtime 'wheelhouse'
    New-Item -ItemType Directory -Path $Wheelhouse -Force | Out-Null
    $PipArgs = @('--isolated', 'download', '--only-binary=:all:', '--index-url', 'https://pypi.org/simple', '-r', $Req, '--dest', $Wheelhouse)
    if (!$Offline) { Invoke-Checked $Exe (@($Pip) + $PipArgs) }
    # Install only wheels already downloaded; no arbitrary setup.py compilation.
    Invoke-Checked $Exe @($Pip, '--isolated', 'install', '--no-index', '--find-links', $Wheelhouse, '--only-binary=:all:', '--upgrade', '--target', $Site, '-r', $Req, '--report', (Join-Path $Runtime 'install-report.json'))
    Invoke-Checked $Exe @('-s', (Join-Path $PSScriptRoot 'launch.py'), '--check')
    $Resolved = & $Exe $Pip '--isolated' 'list' '--path' $Site '--format=json'
    if ($LASTEXITCODE -ne 0) { throw 'Cannot record resolved dependencies' }
    $Resolved | Set-Content -LiteralPath (Join-Path $Runtime 'resolved-packages.json') -Encoding UTF8
    @{ python=$Spec.python.version; pip_sha256=(Get-FileHash -LiteralPath $Pip -Algorithm SHA256).Hash; requirements_sha256=(Get-FileHash -LiteralPath $Req -Algorithm SHA256).Hash; completed_utc=[DateTime]::UtcNow.ToString('o') } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $Runtime 'setup-complete.json') -Encoding UTF8
    Write-Host 'Environment import checks passed. Run START_TACTIC.bat --single. No existing TACTIC database was changed.' -ForegroundColor Green
    exit 0
} catch {
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host 'SETUP FAILED. No success marker was written for this run.'
    if (Test-Path -LiteralPath (Join-Path $Runtime 'setup-complete.json')) { Remove-Item -LiteralPath (Join-Path $Runtime 'setup-complete.json') -Force }
    exit 1
}
