$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3.11 .\verify_bundle.py
if ($LASTEXITCODE -ne 0) { throw 'Model verification failed. Send this console output.' }
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    py -3.11 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 is required. Send this console output.' }
}
& '.\.venv\Scripts\python.exe' -m pip install -r '.\requirements.txt'
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Send this console output.' }
Write-Host 'SETUP OK. Run 02_start_server.ps1 in this terminal.'
