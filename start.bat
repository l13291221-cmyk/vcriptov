@echo off
setlocal
cd /d "%~dp0"

echo ==============================================
echo    VCriptoV - avvio del sito
echo ==============================================
echo.

REM --- 1. Controllo che Python sia installato ---
where python >nul 2>nul
if errorlevel 1 goto no_python

REM --- 2. Ambiente virtuale ---
if exist ".venv\Scripts\python.exe" goto have_venv
echo Preparo l'ambiente la prima volta, attendi un minuto...
python -m venv .venv
if errorlevel 1 goto venv_error

:have_venv
call ".venv\Scripts\activate.bat"
echo Installo o aggiorno le dipendenze, attendi...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 goto pip_error

REM --- 3. Chiave Stripe, chiesta una sola volta ---
if not exist "instance" mkdir instance
if exist "instance\stripe.key" goto run
echo.
echo ----------------------------------------------
echo Incolla la tua STRIPE SECRET KEY e premi Invio.
echo sk_live per soldi veri, sk_test per le prove.
echo ----------------------------------------------
set /p STRIPE_KEY="Chiave: "
if "%STRIPE_KEY%"=="" goto no_key
>"instance\stripe.key" echo|set /p="%STRIPE_KEY%"
echo Chiave salvata. Non te la chiedero' piu'.

:run
echo.
echo ==============================================
echo   Sito avviato. Apri Chrome o Edge e scrivi:
echo      localhost:5001
echo   Per fermarlo: chiudi questa finestra.
echo ==============================================
echo.
python app.py
echo.
echo Il sito si e' fermato.
pause
goto end

:no_python
echo.
echo ERRORE: Python non e' installato sul computer.
echo 1. Vai su https://www.python.org/downloads/
echo 2. Scarica e installa Python.
echo 3. IMPORTANTE: nella prima schermata metti la spunta su "Add Python to PATH".
echo 4. Poi riprova a fare doppio click su questo file.
echo.
pause
goto end

:venv_error
echo.
echo ERRORE nella preparazione dell'ambiente Python.
echo.
pause
goto end

:pip_error
echo.
echo ERRORE nell'installazione. Controlla di essere connesso a internet e riprova.
echo.
pause
goto end

:no_key
echo.
echo Nessuna chiave inserita. Riesegui il file quando ce l'hai.
echo.
pause
goto end

:end
endlocal
