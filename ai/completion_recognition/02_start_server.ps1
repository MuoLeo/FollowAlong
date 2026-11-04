$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) { throw 'Run 01_setup.ps1 first.' }
& '.\.venv\Scripts\python.exe' -m followalong_v50.server --bundle '.\model_bundle' --device cpu
