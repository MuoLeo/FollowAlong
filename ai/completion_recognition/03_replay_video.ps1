$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Run 01_setup.ps1 first.' }
& '.\.venv\Scripts\python.exe' -m followalong_v50.replay --simulate-external-approval
if ($LASTEXITCODE -ne 0) { throw 'Replay failed. Send the result ZIP and console output.' }
