# No param block: every token after -File remains a literal item in $args.
# In particular --data-dir/--config must not become PowerShell parameters.
# Requires only Windows PowerShell 5.1, available before Python is installed.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-TacticEntryArguments([string]$Entry, [string[]]$Arguments) {
    $items = @($Arguments)
    switch ($Entry) {
        'start' { return ,(@('start') + $items) }
        'setup' { return ,(@('setup') + $items) }
        'manage' { return ,$items }
        '' { return ,$items }  # direct internal helper invocation
        default { throw 'Unknown launcher entry; use START_TACTIC, SETUP_ENV or MANAGE_TACTIC.' }
    }
}

function Get-TacticRoot {
    return [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
}

function Resolve-TacticPath([string]$Value, [string]$Root) {
    $value = $Value.Trim()
    if ($value.Length -ge 2 -and $value.StartsWith('"') -and $value.EndsWith('"')) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    if (!$value -or $value -match '[\x00-\x1f"]') { throw 'Некорректный путь к Python.' }
    if (![IO.Path]::IsPathRooted($value)) { $value = Join-Path $Root $value }
    return [IO.Path]::GetFullPath($value)
}

function Get-TacticPython([string]$Root, [string[]]$Arguments) {
    # Explicit --python > environment > saved profile > adjacent runtime.
    # Never silently substitute an unrelated Python found on PATH.
    $candidate = $null
    $explicit = $false
    for ($i = 0; $i -lt $Arguments.Count; $i++) {
        if ($Arguments[$i] -eq '--python') {
            if ($i + 1 -ge $Arguments.Count) { throw '--python требует путь.' }
            $candidate = $Arguments[$i + 1]
            $explicit = $true
        } elseif ($Arguments[$i].StartsWith('--python=')) {
            $candidate = $Arguments[$i].Substring(9)
            $explicit = $true
        }
    }
    if (!$candidate -and $env:TACTIC_PYTHON) { $candidate = $env:TACTIC_PYTHON }
    if (!$candidate) {
        $profilePath = Join-Path $Root 'launcher.local.json'
        if (Test-Path -LiteralPath $profilePath) {
            if ((Get-Item -LiteralPath $profilePath).Length -gt 16384) { throw 'Слишком большой launcher.local.json.' }
            $profile = Get-Content -LiteralPath $profilePath -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($profile.format -ne 1) { throw 'Неверный format в launcher.local.json. Базы не изменены.' }
            if ($profile.PSObject.Properties['python']) { $candidate = [string]$profile.python }
        }
    }
    if (!$candidate) { $candidate = Join-Path $Root '.runtime/python/python.exe' }
    $result = Resolve-TacticPath $candidate $Root
    if (!(Test-Path -LiteralPath $result -PathType Leaf)) {
        if ($explicit) { throw 'Указанный --python не найден. Исправьте параметр; другой Python автоматически не выбирается.' }
        return $null
    }
    if ($env:OS -eq 'Windows_NT' -and [IO.Path]::GetExtension($result) -ine '.exe') {
        throw 'Нужен путь к python.exe, не команда CMD/BAT.'
    }
    return $result
}


function ConvertTo-TacticNativeArgument([AllowEmptyString()][string]$Value) {
    # Windows argv escaping, not shell quoting. No cmd.exe is involved.
    if ($Value.Length -gt 0 -and $Value -notmatch '[\s"]') { return $Value }
    $b = New-Object Text.StringBuilder
    [void]$b.Append('"')
    $slashes = 0
    foreach ($ch in $Value.ToCharArray()) {
        if ($ch -eq '\') { $slashes++; continue }
        if ($ch -eq '"') {
            [void]$b.Append(('\' * (2 * $slashes + 1)))
            [void]$b.Append('"')
        } else {
            [void]$b.Append(('\' * $slashes))
            [void]$b.Append($ch)
        }
        $slashes = 0
    }
    [void]$b.Append(('\' * (2 * $slashes)))
    [void]$b.Append('"')
    return $b.ToString()
}

function Invoke-TacticNative([string]$Executable, [string[]]$Arguments, [string]$Root) {
    # Inherit all three console handles. Piping Python through Out-Host would
    # buffer newline-free input/getpass prompts and can make a menu look stuck.
    $info = New-Object Diagnostics.ProcessStartInfo
    $info.FileName = $Executable
    $quoted = @($Arguments | ForEach-Object { ConvertTo-TacticNativeArgument $_ })
    $info.Arguments = $quoted -join ' '
    $info.WorkingDirectory = $Root
    $info.UseShellExecute = $false
    $info.RedirectStandardInput = $false
    $info.RedirectStandardOutput = $false
    $info.RedirectStandardError = $false
    $info.CreateNoWindow = $false
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $info
    try {
        if (!$process.Start()) { throw 'Не удалось запустить дочерний процесс.' }
        # Parent console Ctrl+C also reaches the original launcher. Never
        # force-kill its workers or replay a request while cleanup is running.
        $process.WaitForExit()
        return [int]$process.ExitCode
    } finally {
        $process.Dispose()
    }
}

function Get-TacticSetupOptions([string[]]$Arguments) {
    $flags = @()
    $dry = $false
    $help = $false
    foreach ($item in $Arguments) {
        switch ($item.ToLowerInvariant()) {
            '--repair' { $flags += '-Repair' }
            '-repair' { $flags += '-Repair' }
            '--offline' { $flags += '-Offline' }
            '-offline' { $flags += '-Offline' }
            '--dry-run' { $dry = $true }
            '--help' { $help = $true }
            '-h' { $help = $true }
            default { throw "Неизвестный параметр setup: $item. Допустимы --repair и --offline." }
        }
    }
    return @{ Flags = @($flags | Select-Object -Unique); DryRun = $dry; Help = $help }
}

function Invoke-TacticSetup([string]$Root, [string[]]$Arguments) {
    $options = Get-TacticSetupOptions $Arguments
    if ($options.Help) {
        Write-Host 'SETUP_ENV.bat [--repair] [--offline] [--dry-run]'
        Write-Host 'Устанавливается только .runtime. INIT/UPGRADE и изменение разрешений не запускаются.'
        return 0
    }
    $exe = Join-Path $PSHOME 'powershell.exe'
    if (!(Test-Path -LiteralPath $exe)) { $exe = Join-Path $PSHOME 'pwsh' }
    $tail = @('-NoLogo', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $Root 'tools/local/setup_env.ps1')) + $options.Flags
    if ($options.DryRun) {
        @{ dry_run = $true; argv = @($exe) + $tail; cwd = $Root } | ConvertTo-Json -Depth 5 | Write-Host
        return 0
    }
    # The setup script runs in a NEW PowerShell process. Its exit cannot skip
    # our cleanup. No Python process is left using the runtime during Repair.
    return (Invoke-TacticNative $exe $tail $Root)
}

function Show-TacticHelp {
    Write-Host @'
START_TACTIC.bat                   3 процесса (или сохранённый режим)
START_TACTIC.bat --single          один процесс
START_TACTIC.bat --legacy          один процесс, старый UI
SETUP_ENV.bat                      загрузить локальный Python и зависимости
SETUP_ENV.bat --repair --offline   ремонт из локального кэша
MANAGE_TACTIC.bat                  меню настроек и обслуживания
MANAGE_TACTIC.bat check env|db|startup   диагностика
MANAGE_TACTIC.bat db init|upgrade|restore   обслуживание managed SQLite
MANAGE_TACTIC.bat configure --writes on    разрешение записи, с подтверждением
MANAGE_TACTIC.bat settings --save ...   сохранить пути/порт/режим запуска
MANAGE_TACTIC.bat build             пересобрать Vue (нужен Node)

Общие параметры запуска/обслуживания:
  --data-dir "D:\TACTIC\local_data" --config "...xml" --python "...python.exe"
Запуск: --port 9123 --workers 3. --dry-run показывает команду без запуска.
Окружение: TACTIC_PYTHON="полный путь к python.exe" или сохранённые Параметры.
Никакая инициализация/миграция не выполняется при обычном запуске.
SETUP работает до установки Python. Ни один BAT не меняет права записи молча.
MANAGE_TACTIC без Python предложит указать существующий Python либо установить его.
Для подробностей конкретной команды добавьте --help (после установки Python).
'@
}

function Invoke-TacticBootstrap([string[]]$Arguments) {
    $root = Get-TacticRoot
    Set-Location -LiteralPath $root
    $entry = if ($env:TACTIC_LAUNCH_ENTRY) { $env:TACTIC_LAUNCH_ENTRY } else { '' }
    $arguments = Get-TacticEntryArguments $entry @($Arguments)
    if ($arguments.Count -gt 0 -and $arguments[0].ToLowerInvariant() -in @('help', '--help', '-h', '/?')) {
        Show-TacticHelp
        return 0
    }
    if ($arguments.Count -eq 2 -and $arguments[0] -ieq 'start' -and $arguments[1].ToLowerInvariant() -in @('help', '--help', '-h', '/?')) {
        Show-TacticHelp
        return 0
    }
    if ($arguments.Count -gt 0 -and $arguments[0] -ieq 'setup') {
        $rest = @()
        if ($arguments.Count -gt 1) { $rest = @($arguments[1..($arguments.Count - 1)]) }
        return (Invoke-TacticSetup $root $rest)
    }
    $menu = $arguments.Count -eq 0 -or $arguments[0] -ieq 'menu' -or $arguments[0].StartsWith('--')
    while ($true) {
        $python = Get-TacticPython $root $arguments
        if (!$python) {
            if (!$menu -or [Console]::IsInputRedirected) {
                Write-Host 'Python не найден. SETUP_ENV.bat установит окружение. Либо задайте TACTIC_PYTHON/--python.'
                return 2
            }
            Write-Host 'Python не выбран. Базы и конфигурация не изменены.'
            Write-Host "1  Скачать локальное окружение`n2  Указать существующий python.exe`n0  Выход"
            $choice = Read-Host 'Действие'
            if ($choice -eq '0') { return 0 }
            if ($choice -eq '1') {
                $code = Invoke-TacticSetup $root @()
                if ($code -ne 0) { Write-Host "Установка не завершена, код $code. Автоматического повтора нет."; return $code }
                # A stale explicitly selected interpreter must not override a
                # successful user-selected local install within this session.
                $env:TACTIC_PYTHON = Join-Path $root '.runtime/python/python.exe'
            } elseif ($choice -eq '2') {
                $env:TACTIC_PYTHON = Read-Host 'Полный путь к существующему python.exe (не папка)'
            }
            continue
        }
        # JSON travels through the environment instead of command-string
        # interpolation. This preserves spaces, Unicode, !, &, %, trailing
        # slashes and empty argv tokens across Windows PowerShell 5.1.
        $previous = $env:TACTIC_BOOTSTRAP_ARGV_JSON
        $previousUnbuffered = $env:PYTHONUNBUFFERED
        try {
            $env:PYTHONUNBUFFERED = '1'
            $env:TACTIC_BOOTSTRAP_ARGV_JSON = ConvertTo-Json -InputObject @($arguments) -Compress
            $pythonArgs = @('-X', 'utf8', '-s', (Join-Path $root 'tools/local/control.py'), '--bootstrap-argv')
            $code = Invoke-TacticNative $python $pythonArgs $root
        } finally {
            if ($null -eq $previousUnbuffered) { Remove-Item Env:PYTHONUNBUFFERED -ErrorAction SilentlyContinue }
            else { $env:PYTHONUNBUFFERED = $previousUnbuffered }
            if ($null -eq $previous) { Remove-Item Env:TACTIC_BOOTSTRAP_ARGV_JSON -ErrorAction SilentlyContinue }
            else { $env:TACTIC_BOOTSTRAP_ARGV_JSON = $previous }
        }
        return $code
    }
}

# Dot-sourcing exposes functions for tests; normal -File executes exactly once.
if ($MyInvocation.InvocationName -ne '.') {
    try {
        [Console]::OutputEncoding = New-Object Text.UTF8Encoding($false)
        $rc = Invoke-TacticBootstrap -Arguments @($args)
        if (@($args).Count -eq 0 -and ![Console]::IsInputRedirected -and $env:TACTIC_NO_PAUSE -ne '1' -and ($rc -ne 0 -or $env:TACTIC_LAUNCH_ENTRY -eq 'setup')) {
            Write-Host "Код завершения: $rc"
            Read-Host 'ENTER — закрыть' | Out-Null
        }
        exit $rc
    } catch {
        Write-Host ('ERROR: ' + $_.Exception.Message) -ForegroundColor Red
        if (@($args).Count -eq 0 -and ![Console]::IsInputRedirected -and $env:TACTIC_NO_PAUSE -ne '1') {
            Read-Host 'ENTER — закрыть' | Out-Null
        }
        exit 2
    }
}
