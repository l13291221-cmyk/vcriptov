@echo off
REM ==========================================================
REM  Aggiorna VCriptoV all'ultima versione (senza riscaricare).
REM  Funziona SOLO se hai scaricato il progetto con "git clone"
REM  (vedi README). Doppio click su questo file per aggiornare.
REM ==========================================================
cd /d "%~dp0"

where git >nul 2>nul
if errorlevel 1 goto no_git
if not exist ".git" goto not_repo

echo Scarico gli aggiornamenti...
git pull
echo.
echo ==============================================
echo   Aggiornamento completato.
echo   Ora puoi riavviare il sito con start.bat
echo ==============================================
pause
goto end

:no_git
echo.
echo Git non e' installato. Scaricalo da https://git-scm.com/download/win
echo Poi potrai aggiornare con un click. (Vedi README, sezione Aggiornamenti.)
echo.
pause
goto end

:not_repo
echo.
echo Questa cartella non e' collegata a GitHub (non e' un "git clone").
echo Per usare gli aggiornamenti automatici scarica il progetto con:
echo    git clone https://github.com/l13291221-cmyk/vcriptov.git
echo (Vedi README, sezione Aggiornamenti.)
echo.
pause

:end
