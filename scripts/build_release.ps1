# Build release artifacts (wheel + sdist)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)
python -m pip install -q build
python -m build
Get-ChildItem dist | Format-Table Name, Length
Write-Host "Upload with: twine upload dist/*"
