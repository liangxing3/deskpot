$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

$python = if ($env:DESKTOP_PET_PYTHON) { $env:DESKTOP_PET_PYTHON } else { "python" }
$iconArgs = @()
$iconPath = Join-Path $projectRoot "assets\icons\app.ico"
if (Test-Path $iconPath) {
    $iconArgs = @("--icon", $iconPath)
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --windowed `
    --name DesktopPetAssistant `
    --add-data "assets;assets" `
    --add-data "config.json;." `
    --add-data "线条小狗 动态表情包 200张等2个文件;线条小狗 动态表情包 200张等2个文件" `
    @iconArgs `
    main.py
