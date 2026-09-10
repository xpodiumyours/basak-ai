@echo off
title BASAK - Telegram Koprusu
cd /d "%~dp0"
echo.
echo  ==========================================
echo   BASAK Telegram koprusu baslatiliyor...
echo   Kapatmak icin bu pencereyi kapat.
echo  ==========================================
echo.
python telegram_bot.py
pause
