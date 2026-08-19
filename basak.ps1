# Başak - PowerShell alias
# Bu dosyayı PowerShell profilinize ekleyin veya doğrudan çalıştırın.
# Kullanım: .\basak.ps1
# Veya profile ekleyin: Add-Content $PROFILE "Import-Module C:\Projects\Başak\basak.ps1"

function Start-Basak {
    param(
        [switch]$Terminal
    )
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    Push-Location $scriptDir
    if ($Terminal) {
        python basak.py
    } else {
        python basak_app.py
    }
    Pop-Location
}

Set-Alias -Name basak -Value Start-Basak
