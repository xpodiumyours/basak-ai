@echo off
title BASAK - Yapay Zeka Asistani
cd /d "%~dp0"
echo.
echo  ==========================================
echo   BASAK Baslatiliyor...
echo  ==========================================
echo.
python basak_app.py
if errorlevel 1 (
    echo.
    echo  HATA: Basak baslatilamadi!
    echo  Ollama calisiyor mu? Kontrol et: ollama list
    echo.
)
pause
