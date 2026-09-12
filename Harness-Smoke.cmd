@echo off
setlocal
cd /d "%~dp0"

echo.
echo =============================================
echo  BASAK HARNESS V1 - GERCEK CANLI SMOKE
echo =============================================
echo.
echo Bu islem:
echo - yalniz guvenli feature dalinda calisir,
echo - gercek ucretsiz provider zincirini kullanir,
echo - gercek gecmis/profil/gorev verisini yazmaz,
echo - yazma ve sistem araclarini engeller,
echo - 4 kisa gorev sonunda kaniti ekrana basar.
echo.

python scripts\harness_smoke_live.py
set RC=%ERRORLEVEL%

echo.
if "%RC%"=="0" (
  echo SMOKE SONUCU: GECTI
) else (
  echo SMOKE SONUCU: INCELEME GEREKIYOR ^(kod %RC%^)
)
echo.
echo Otomatik PR veya merge YAPILMADI.
echo.
pause
exit /b %RC%
