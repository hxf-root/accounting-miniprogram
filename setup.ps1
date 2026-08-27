$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $projectRoot 'backend'
$venvDir = Join-Path $backendDir '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
$requirements = Join-Path $backendDir 'requirements.txt'

try {
    & py -3.11 --version | Out-Host
} catch {
    throw 'Python 3.11 x64 was not found. Install it and run setup.ps1 again.'
}

if (-not (Test-Path $venvPython)) {
    & py -3.11 -m venv $venvDir
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r $requirements

Write-Host 'Environment setup complete.'
Write-Host "Run tests: & '$venvPython' -m pytest '$backendDir\tests' -q"
Write-Host "Start backend: Push-Location '$backendDir'; & '$venvPython' main.py; Pop-Location"
