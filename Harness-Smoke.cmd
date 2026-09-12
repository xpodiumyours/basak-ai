@echo off
setlocal
cd /d "%~dp0"

echo.
echo =============================================
echo  BASAK HARNESS V1 - KISA GERCEK SMOKE

echo =============================================
echo.
echo 1. Bu dali bilgisayarinda ac:
echo    feature/task-model-harness-v1-20260912
echo.
echo 2. Basak-Baslat.cmd ile Basak'i normal sekilde ac.
echo.
echo 3. Basak'a sirayla su 4 mesaji yaz:
echo.
echo    [A] Merhaba, nasilsin?
echo    [B] ANA-PLAN.md dosyasini oku ve ilk basligi soyle.
echo    [C] Bu reponun son commitini goster.
echo    [D] Vixrex icin ne yapabiliriz?
echo.
echo Beklenen routing:
echo    A = chat-lite
    B = read-lite
    C = read-lite
    D = legacy

echo.
echo Mesajlari tamamladiktan sonra bu pencereye don ve bir tusa bas.
pause >nul

echo.
echo --- Son harness kararlari ---
if not exist "hata.log" (
  echo hata.log bulunamadi. Basak bu dizinden acilmamis olabilir.
  goto :end
)

powershell -NoProfile -Command "Select-String -Path 'hata.log' -Pattern 'Harness task=' | Select-Object -Last 20 | ForEach-Object { $_.Line }"

echo.
echo KURAL: Bu cikti yalniz gozlem kanitidir. Otomatik merge/PR yapmaz.

:end
echo.
pause
endlocal
