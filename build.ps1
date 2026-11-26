# Build RaksToolKit for Windows and prepare a portable ZIP release.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$version = '1.1.0'
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
$icon = Join-Path $PSScriptRoot 'assets\icons\rakstoolkit.ico'
if (-not (Test-Path $python)) { throw 'Missing .venv\Scripts\python.exe. Create the virtual environment and install requirements first.' }
if (-not (Test-Path $icon)) { throw 'Missing assets\icons\rakstoolkit.ico.' }

& $python -m PyInstaller --version
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller is not installed in .venv. Run: .\.venv\Scripts\python.exe -m pip install pyinstaller' }

& $python -m PyInstaller --noconfirm --clean RaksToolKit.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

$buildFolder = Join-Path $PSScriptRoot 'dist\RaksToolKit'
$exe = Join-Path $buildFolder 'RaksToolKit.exe'
if (-not (Test-Path $exe)) { throw 'Expected executable not found.' }
$zip = Join-Path $PSScriptRoot "dist\RaksToolKit-v$version-Windows-x64.zip"
$checksum = "$zip.sha256.txt"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $buildFolder -DestinationPath $zip -CompressionLevel Optimal
$hash = (Get-FileHash -Path $zip -Algorithm SHA256).Hash.ToLowerInvariant()
"$hash  $(Split-Path $zip -Leaf)" | Set-Content -Path $checksum -Encoding ascii
Write-Host "Built: $exe"
Write-Host "Release ZIP: $zip"
Write-Host "SHA-256: $hash"
Write-Host 'Test the extracted ZIP on Windows before publishing.'
