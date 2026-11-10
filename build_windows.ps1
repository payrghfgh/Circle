# Builds the Windows installer for Circle.
#
#   powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
#
# Needs: Python 3.10+ (64-bit) and Inno Setup 6 (https://jrsoftware.org/isdl.php).
# Output: installer\output\Circle-1.1.1-setup.exe

param(
    [string]$Python = "python",
    [string]$IsccPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

Write-Host "== Circle build ==" -ForegroundColor Cyan
& $Python --version

Write-Host "`n[1/4] Installing build dependencies" -ForegroundColor Cyan
& $Python -m pip install --upgrade pip
& $Python -m pip install -r requirements.txt pyinstaller

Write-Host "`n[2/4] Running the build checks" -ForegroundColor Cyan
& $Python -m compileall -q . | Out-Null
if ($LASTEXITCODE -ne 0) { throw "compileall failed" }

Write-Host "`n[3/4] Freezing with PyInstaller" -ForegroundColor Cyan
& $Python -m PyInstaller Circle.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }
if (-not (Test-Path "dist\Circle\Circle.exe")) { throw "dist\Circle\Circle.exe was not produced" }

Write-Host "`n[4/4] Building the installer" -ForegroundColor Cyan
if (-not (Test-Path $IsccPath)) {
    $IsccPath = (Get-ChildItem "C:\Program Files (x86)\Inno Setup*\ISCC.exe" -ErrorAction SilentlyContinue |
                 Select-Object -First 1).FullName
}
if (-not $IsccPath -or -not (Test-Path $IsccPath)) {
    throw "ISCC.exe not found. Install Inno Setup 6 from https://jrsoftware.org/isdl.php"
}
& $IsccPath "installer\Circle.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }

Write-Host "`nDone." -ForegroundColor Green
Get-ChildItem "installer\output\*.exe" | ForEach-Object {
    Write-Host ("  {0}  ({1:N1} MB)" -f $_.FullName, ($_.Length / 1MB))
}
