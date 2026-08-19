@echo off
title BASAK - Yapay Zeka Asistani
echo.
echo  ==========================================
echo   BASAK Baslatiliyor...
echo   Acilmazsa tarayicida su adrese git:
echo   http://localhost:8080
echo  ==========================================
echo.
start "" http://localhost:8080
"C:\Users\Casper\AppData\Local\Programs\Python\Python312\Scripts\open-webui.exe" serve
pause