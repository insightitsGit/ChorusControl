# Build release artifacts (wheel + sdist)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m pip install -q build twine
if (Test-Path dist) { Remove-Item dist -Recurse -Force }
python -m build
twine check dist/*
python scripts/inspect_wheel.py
Get-ChildItem dist | Format-Table Name, Length
Write-Host "Tag publish: git tag v0.1.0 && git push origin v0.1.0"
Write-Host "Manual upload: twine upload dist/*"
