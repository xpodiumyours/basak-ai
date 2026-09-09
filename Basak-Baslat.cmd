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
    echo  Sirasiyla kontrol et:
    echo   1. Internet baglantin var mi?
    echo   2. Ollama calisiyor mu? Kontrol et: ollama list
    echo   3. Bulut biletleri gecerli mi? (ayarlar.json'daki anahtarlar)
    echo.
)
pause
