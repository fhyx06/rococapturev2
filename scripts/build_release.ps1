param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$Python = Join-Path $Root ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $Python = "python"
}

$Version = (& $Python -c "from src.__about__ import APP_VERSION; print(APP_VERSION)").Trim()
$AppDirName = "RocoCaptureV2-v$Version-win-x64"
$DistAppDir = Join-Path $Root "dist\$AppDirName"
$ReleaseDir = Join-Path $Root "release"
$ZipPath = Join-Path $ReleaseDir "$AppDirName-portable.zip"
$LatestJsonPath = Join-Path $ReleaseDir "latest.json"

if ($Clean) {
    foreach ($Path in @("build", "dist", "release")) {
        $FullPath = Join-Path $Root $Path
        if (Test-Path $FullPath) {
            Remove-Item -LiteralPath $FullPath -Recurse -Force
        }
    }
}

$PyInstaller = Join-Path $Root ".venv\Scripts\pyinstaller.exe"
if (-not (Test-Path $PyInstaller)) {
    $PyInstaller = "pyinstaller"
}

& $PyInstaller --noconfirm "RocoCaptureV2.spec"

if (-not (Test-Path $DistAppDir)) {
    throw "Build output directory was not found: $DistAppDir"
}

New-Item -ItemType Directory -Force -Path $ReleaseDir | Out-Null
Copy-Item -LiteralPath (Join-Path $Root "README.md") -Destination (Join-Path $DistAppDir "README.md") -Force

$VersionText = @(
    "RocoCaptureV2 v$Version",
    "Build: Windows x64 portable",
    "Entry: RocoCaptureV2-v$Version.exe"
)
Set-Content -LiteralPath (Join-Path $DistAppDir "VERSION.txt") -Value $VersionText -Encoding UTF8

if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}
Compress-Archive -Path $DistAppDir -DestinationPath $ZipPath -Force

$LatestManifest = [ordered]@{
    version = $Version
    tag_name = "v$Version"
    release_url = "https://github.com/fhyx06/RocoCaptureV2/releases/tag/v$Version"
    download_url = "https://github.com/fhyx06/RocoCaptureV2/releases/download/v$Version/$AppDirName-portable.zip"
    notes = "v$Version"
}
$LatestJson = $LatestManifest | ConvertTo-Json -Depth 4
$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($LatestJsonPath, ($LatestJson + [Environment]::NewLine), $Utf8NoBom)

Write-Host "Release package created:"
Write-Host $ZipPath
Write-Host "Update manifest created:"
Write-Host $LatestJsonPath
