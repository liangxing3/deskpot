param(
    [string]$ReleaseDirName = "desktop_pet_clean_release_v1.3.1"
)

$ErrorActionPreference = "Stop"

function Get-PythonExecutable {
    $candidates = @(
        $env:DESKTOP_PET_PYTHON,
        "D:\Python313\python.exe"
    ) | Where-Object { $_ }

    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            return $candidate
        }
    }

    $command = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    throw "Python executable not found. Set DESKTOP_PET_PYTHON or install python.exe."
}

function Get-BuildMetadata {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,
        [Parameter(Mandatory = $true)]
        [string]$PythonExe
    )

    $metadataScript = Join-Path $ProjectRoot "tools\export_build_metadata.py"
    $metadataJson = & $PythonExe $metadataScript
    if (-not $metadataJson) {
        throw "Failed to load build metadata from $metadataScript"
    }
    return $metadataJson | ConvertFrom-Json
}

function Assert-SafeGeneratedPath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$WorkspaceRoot,
        [Parameter(Mandatory = $true)]
        [string]$ProjectRoot,
        [Parameter(Mandatory = $true)]
        [string]$TargetPath
    )

    $workspaceFull = [System.IO.Path]::GetFullPath($WorkspaceRoot).TrimEnd('\')
    $projectFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath).TrimEnd('\')

    if (-not $targetFull.StartsWith($workspaceFull, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside workspace: $targetFull"
    }
    if ($targetFull -eq $projectFull) {
        throw "Refusing to remove the source project directory: $targetFull"
    }
}

$projectRoot = Split-Path -Parent $PSScriptRoot
$workspaceRoot = Split-Path -Parent $projectRoot
$releaseRoot = Join-Path $workspaceRoot $ReleaseDirName
$pythonExe = Get-PythonExecutable
$metadata = Get-BuildMetadata -ProjectRoot $projectRoot -PythonExe $pythonExe

Assert-SafeGeneratedPath -WorkspaceRoot $workspaceRoot -ProjectRoot $projectRoot -TargetPath $releaseRoot

if (Test-Path -LiteralPath $releaseRoot) {
    Remove-Item -LiteralPath $releaseRoot -Recurse -Force
}
New-Item -ItemType Directory -Path $releaseRoot -Force | Out-Null

$robocopyArgs = @(
    $projectRoot,
    $releaseRoot,
    "/E",
    "/XD", ".appdata", "build", "dist", "installer", "__pycache__", ".pycache_verify", ".git", ".reference",
    "/XF", "AI_HANDOFF.md", "AGENTS.md", "*.pyc", "*.tmp"
)

& robocopy @robocopyArgs | Out-Host
if ($LASTEXITCODE -ge 8) {
    throw "robocopy failed with exit code $LASTEXITCODE"
}

$releaseInstallerDir = Join-Path $releaseRoot "installer"
New-Item -ItemType Directory -Path $releaseInstallerDir -Force | Out-Null

$iconSource = Join-Path $projectRoot "installer\图标.png"
if (Test-Path -LiteralPath $iconSource) {
    Copy-Item -LiteralPath $iconSource -Destination (Join-Path $releaseInstallerDir "图标.png") -Force
}

Get-ChildItem -LiteralPath $releaseRoot -Recurse -Directory -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -in @("__pycache__", ".pycache_verify") } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }

Get-ChildItem -LiteralPath $releaseRoot -Recurse -File -Force -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in @(".pyc", ".tmp") -or $_.Name -in @("AI_HANDOFF.md", "AGENTS.md") } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }

$internalName = [string]$metadata.internal_name
$version = [string]$metadata.version
$distDir = Join-Path $releaseRoot ("dist\" + $internalName)
$pyInstallerWorkDir = Join-Path $env:LOCALAPPDATA ("Temp\" + $internalName + "-build-release")

Push-Location $releaseRoot
try {
    & $pythonExe -m PyInstaller --noconfirm --clean --distpath .\dist --workpath $pyInstallerWorkDir .\DesktopPetAssistantV1.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed with exit code $LASTEXITCODE"
    }

    & powershell -ExecutionPolicy Bypass -File .\tools\build_installer.ps1
    if ($LASTEXITCODE -ne 0) {
        throw "Installer build failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

$portableZipPath = Join-Path $releaseInstallerDir ($internalName + "-Portable-v" + $version + ".zip")
if (Test-Path -LiteralPath $portableZipPath) {
    Remove-Item -LiteralPath $portableZipPath -Force
}
Compress-Archive -Path (Join-Path $distDir "*") -DestinationPath $portableZipPath -CompressionLevel Optimal

Write-Host "Release source: $releaseRoot"
Write-Host "Portable dir: $distDir"
Write-Host "Portable zip: $portableZipPath"
