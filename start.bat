@echo off
setlocal
cd /d "%~dp0"
set "LOG=%~dp0avvio_log.txt"
echo VCriptoV - log di avvio > "%LOG%"

echo ==============================================
echo    VCriptoV - avvio del sito
echo ==============================================
echo.

REM --- 0. Aggiornamento automatico (se e' un git clone) ---
where git >nul 2>nul
if errorlevel 1 goto skip_update
if not exist ".git" goto skip_update
echo Controllo aggiornamenti...
git pull >> "%LOG%" 2>&1
:skip_update

REM --- 1. Trova Python: prima "py" (piu' affidabile su Windows), poi "python" ---
set "PYCMD="
where py >nul 2>nul && set "PYCMD=py"
if defined PYCMD goto have_python
where python >nul 2>nul && set "PYCMD=python"
if defined PYCMD goto have_python
goto no_python

:have_python
echo Uso Python: %PYCMD% >> "%LOG%"
%PYCMD% --version >> "%LOG%" 2>&1

REM --- 2. Ambiente virtuale ---
if exist ".venv\Scripts\python.exe" goto have_venv
echo Preparo l'ambiente la prima volta, attendi un minuto...
%PYCMD% -m venv .venv >> "%LOG%" 2>&1
if errorlevel 1 goto venv_error

:have_venv
set "VENV_PY=.venv\Scripts\python.exe"
echo Installo o aggiorno le dipendenze. Puo' metterci 1-2 minuti, attendi...
"%VENV_PY%" -m pip install --upgrade pip >> "%LOG%" 2>&1
"%VENV_PY%" -m pip install -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 goto pip_error

REM --- 3. Scelta modalita': DEMO o REALE ---
if not exist "instance" mkdir instance
set "CURR="
if not exist "instance\stripe.key" goto askmode
findstr /b "sk_" "instance\stripe.key" >nul 2>nul && set "CURR=REALE"
findstr /i /b "demo" "instance\stripe.key" >nul 2>nul && set "CURR=DEMO"
if not defined CURR goto askmode
echo.
echo Modalita' attuale: %CURR%
set /p CH="Premi INVIO per continuare cosi', oppure scrivi  cambia  per cambiare: "
if /i "%CH%"=="cambia" goto askmode
goto run

:askmode
echo.
echo ==============================================
echo   Come vuoi avviare il sito?
echo.
echo     demo    = per PROVARLO tu, senza pagamenti. Per testare o aggiornare.
echo     reale   = i clienti PAGANO davvero. Serve la tua chiave Stripe.
echo ==============================================
set /p MODE="Scrivi demo oppure reale: "
if /i "%MODE%"=="demo" goto savedemo
if /i "%MODE%"=="reale" goto askrealkey
if /i "%MODE%"=="real" goto askrealkey
echo.
echo Non ho capito. Scrivi la parola  demo  oppure la parola  reale.
goto askmode

:savedemo
>"instance\stripe.key" echo demo
echo Modalita' DEMO attivata: nessun pagamento, per le tue prove.
goto run

:askrealkey
echo.
echo ----------------------------------------------
echo Modalita' REALE: incolla la tua STRIPE SECRET KEY e premi Invio.
echo Inizia con sk_live_ per incassare soldi veri, o sk_test_ per prove con carte finte.
echo NON quella che inizia con pk_ : quella e' sbagliata.
echo ----------------------------------------------
set /p STRIPE_KEY="Incolla la chiave: "
if "%STRIPE_KEY%"=="" goto askmode
>"instance\stripe.key" echo %STRIPE_KEY%
echo Chiave salvata. Modalita' REALE attivata.

:run
echo.
echo ==============================================
echo   Sito avviato. Apri Chrome o Edge e scrivi:
echo      localhost:5001
echo   Per fermarlo: chiudi questa finestra.
echo ==============================================
echo.
"%VENV_PY%" app.py >> "%LOG%" 2>&1
echo.
echo Il sito si e' fermato. Se non si e' aperto, guarda il file avvio_log.txt.
pause
goto end

:no_python
echo.
echo ERRORE: Python non e' stato trovato sul computer.
echo 1. Vai su https://www.python.org/downloads/
echo 2. Scarica e installa Python.
echo 3. IMPORTANTISSIMO: nella PRIMA schermata metti la spunta su
echo    "Add Python to PATH", poi premi "Install Now".
echo 4. Riavvia il computer e riprova questo file.
echo.
echo Dettagli salvati nel file avvio_log.txt
echo.
pause
goto end

:venv_error
echo.
echo ERRORE nella preparazione dell'ambiente Python.
echo Ecco cosa e' successo:
echo ----------------------------------------------
type "%LOG%"
echo ----------------------------------------------
echo Spesso si risolve reinstallando Python da python.org
echo con la spunta "Add Python to PATH".
echo Se non capisci l'errore, mandami il file avvio_log.txt
echo che si trova nella stessa cartella di questo programma.
echo.
pause
goto end

:pip_error
echo.
echo ERRORE nell'installazione delle dipendenze.
echo Ecco cosa e' successo:
echo ----------------------------------------------
type "%LOG%"
echo ----------------------------------------------
echo Controlla di essere connesso a internet e riprova.
echo Se non capisci l'errore, mandami il file avvio_log.txt
echo che si trova nella stessa cartella di questo programma.
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
