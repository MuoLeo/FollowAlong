$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$faEncoderEnv = Join-Path $env:USERPROFILE 'fa50_env'
$faEncoderPython = Join-Path $faEncoderEnv 'Scripts\python.exe'
if (-not (Test-Path $faEncoderPython)) {
    py -3.11 -m venv $faEncoderEnv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 environment creation failed.' }
}
& $faEncoderPython -m pip install -r .\requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Installation failed. Send console output.' }
& $faEncoderPython .\experiment.py
if ($LASTEXITCODE -ne 0) { throw 'Experiment failed. Send console output.' }
