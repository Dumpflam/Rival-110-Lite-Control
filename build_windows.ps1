$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $root
$stage = Join-Path $root '_build'
$venv = Join-Path $stage 'venv'
$python = Join-Path $venv 'Scripts\python.exe'

function RequireSuccess([string] $message) {
    if ($LASTEXITCODE -ne 0) { throw "$message (exit code $LASTEXITCODE)" }
}
try {
    Write-Host 'Rival 110 Lite Control - full Windows EXE build' -ForegroundColor Cyan
    Write-Host 'Self-contained rebuild: no upstream source download, no patcher.'
    New-Item -ItemType Directory -Force -Path $stage | Out-Null
    if (-not (Test-Path -LiteralPath $python)) {
        if (Get-Command py -ErrorAction SilentlyContinue) {
            & py -3 -m venv $venv
        } elseif (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m venv $venv
        } else {
            throw 'Python 3.10+ is required only to BUILD. Get it from python.org, then rerun BUILD_EXE.bat.'
        }
        RequireSuccess 'Could not create isolated Python environment'
    }
    Write-Host '[1/4] Installing build dependencies into private virtual environment...'
    & $python -m pip install --disable-pip-version-check --upgrade pip
    RequireSuccess 'pip upgrade failed'
    & $python -m pip install --disable-pip-version-check -r (Join-Path $root 'requirements-build.txt')
    RequireSuccess 'Dependency installation failed'

    Write-Host '[2/4] Running all mouse/effect/profile tests...'
    & $python -m unittest discover -s (Join-Path $root 'tests') -p 'test_*.py' -v
    RequireSuccess 'Core tests failed'

    Write-Host '[3/4] Running Qt interface and tray-menu integration tests...'
    $env:QT_QPA_PLATFORM = 'offscreen'
    # Qt's offscreen plugin may not find the system font folder automatically.
    # This only affects test-rendering; the app itself uses native Windows fonts.
    $fontFolder = Join-Path $env:WINDIR 'Fonts'
    if (Test-Path -LiteralPath $fontFolder) { $env:QT_QPA_FONTDIR = $fontFolder }
    & $python (Join-Path $root 'tests\qt_smoke.py')
    RequireSuccess 'UI/tray smoke test failed'
    Remove-Item Env:\QT_QPA_PLATFORM -ErrorAction SilentlyContinue
    Remove-Item Env:\QT_QPA_FONTDIR -ErrorAction SilentlyContinue

    Write-Host '[4/4] Freezing GUI and Rivalcfg HID support into one Windows EXE...'
    & $python -m PyInstaller --clean --noconfirm --onefile --windowed `
        --name Rival110LiteControl `
        --icon (Join-Path $root 'assets\Rival110.ico') `
        --add-data "$root\assets;assets" `
        --paths (Join-Path $root 'src') `
        --collect-all rivalcfg `
        --collect-all psutil `
        --distpath (Join-Path $stage 'dist') `
        --workpath (Join-Path $stage 'work') `
        --specpath (Join-Path $stage 'spec') `
        (Join-Path $root 'src\main.py')
    RequireSuccess 'PyInstaller failed'

    $built = Join-Path $stage 'dist\Rival110LiteControl.exe'
    if (-not (Test-Path -LiteralPath $built)) {
        throw 'PyInstaller returned successfully but there was no .exe output'
    }
    Copy-Item -LiteralPath $built -Destination (Join-Path $root 'Rival110LiteControl.exe') -Force
    $sha = (Get-FileHash -Algorithm SHA256 -Path (Join-Path $root 'Rival110LiteControl.exe')).Hash
    Write-Host ''
    Write-Host 'BUILD SUCCEEDED' -ForegroundColor Green
    Write-Host "Executable: $(Join-Path $root 'Rival110LiteControl.exe')"
    Write-Host "SHA256: $sha"
    Write-Host 'The executable does not require Python, G HUB or SteelSeries GG to run.'
    Write-Host 'USB functionality can only be verified with a physical Rival 110.'
    exit 0
} catch {
    Write-Host ''
    Write-Host "BUILD FAILED: $_" -ForegroundColor Red
    exit 1
}
