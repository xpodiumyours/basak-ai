# Basak - PowerShell baslatici
# Kullanim: .\basak.ps1
# Veya profile ekleyin: Add-Content $PROFILE "Import-Module C:\Projects\Başak\basak.ps1"

function Start-Basak {
    param(
        [switch]$Terminal
    )
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Push-Location $scriptDir
    python basak_app.py
    Pop-Location
}

Set-Alias -Name basak -Value Start-Basak
