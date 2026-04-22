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

$projectRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $projectRoot "DesktopPetAssistantV1.iss"
$finalOutputDir = Join-Path $projectRoot "installer"
$metadataScript = Join-Path $projectRoot "tools\export_build_metadata.py"

$pythonExe = Get-PythonExecutable
$metadataJson = & $pythonExe $metadataScript
if (-not $metadataJson) {
    throw "Failed to load build metadata from $metadataScript"
}
$metadata = $metadataJson | ConvertFrom-Json
$internalName = [string]$metadata.internal_name
$distDir = Join-Path $projectRoot ("dist\" + $internalName)
$tempOutputDir = Join-Path $env:LOCALAPPDATA ("Temp\" + $internalName + "-installer")

if (-not (Test-Path -LiteralPath $distDir)) {
    throw "Packaged app not found: $distDir"
}

if (-not (Test-Path -LiteralPath $scriptPath)) {
    throw "Installer script not found: $scriptPath"
}

$iscc = $null
$command = Get-Command iscc.exe -ErrorAction SilentlyContinue
if ($command) {
    $iscc = $command.Source
}

if (-not $iscc) {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate) {
            $iscc = $candidate
            break
        }
    }
}

if (-not $iscc) {
    throw "ISCC.exe not found. Install Inno Setup first."
}

if (Test-Path -LiteralPath $tempOutputDir) {
    Remove-Item -LiteralPath $tempOutputDir -Recurse -Force
}
New-Item -ItemType Directory -Path $tempOutputDir -Force | Out-Null
New-Item -ItemType Directory -Path $finalOutputDir -Force | Out-Null
Get-ChildItem -LiteralPath $finalOutputDir -Filter "*.tmp" -ErrorAction SilentlyContinue | ForEach-Object {
    try {
        Remove-Item -LiteralPath $_.FullName -Force -ErrorAction Stop
    } catch {
    }
}

& $iscc `
    ("/O" + $tempOutputDir) `
    ("/DMyAppName=" + [string]$metadata.display_name) `
    ("/DMyAppVersion=" + [string]$metadata.version) `
    ("/DMyAppPublisher=" + [string]$metadata.publisher) `
    ("/DMyAppURL=" + [string]$metadata.repository_url) `
    ("/DMyAppInternalName=" + [string]$metadata.internal_name) `
    ("/DMyAppExeName=" + [string]$metadata.exe_name) `
    ("/DMySetupBasename=" + [string]$metadata.setup_basename) `
    $scriptPath

$installerFile = Get-ChildItem -LiteralPath $tempOutputDir -Filter "*.exe" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not $installerFile) {
    throw "Installer output not found in temp directory: $tempOutputDir"
}

$finalInstallerPath = Join-Path $finalOutputDir $installerFile.Name
Copy-Item -LiteralPath $installerFile.FullName -Destination $finalInstallerPath -Force
Write-Host "Installer ready: $finalInstallerPath"
