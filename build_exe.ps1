$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

python .\tools\make_icon.py

$buildRoot = Join-Path $env:TEMP "subtitle_tool_pyinstaller_build"
$resolvedTemp = (Resolve-Path -LiteralPath $env:TEMP).Path
if (Test-Path -LiteralPath $buildRoot) {
    $resolvedBuildRoot = (Resolve-Path -LiteralPath $buildRoot).Path
    if (-not $resolvedBuildRoot.StartsWith($resolvedTemp, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove unexpected build path: $resolvedBuildRoot"
    }
    Remove-Item -LiteralPath $buildRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $buildRoot | Out-Null
Copy-Item -LiteralPath .\app.py -Destination $buildRoot
Copy-Item -LiteralPath .\subtitle_tool.spec -Destination $buildRoot
Copy-Item -LiteralPath .\assets -Destination $buildRoot -Recurse

Push-Location -LiteralPath $buildRoot
try {
    python -m PyInstaller --clean --noconfirm .\subtitle_tool.spec
}
finally {
    Pop-Location
}

$projectDist = Join-Path $PSScriptRoot "dist"
New-Item -ItemType Directory -Path $projectDist -Force | Out-Null
$sourceExe = Join-Path $buildRoot "dist\SubtitleTool.exe"
$targetExe = Join-Path $projectDist "SubtitleTool.exe"
Copy-Item -LiteralPath $sourceExe -Destination $targetExe -Force

Write-Host ""
Write-Host "Build complete: $targetExe"
