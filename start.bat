@echo off
setlocal
cd /d "%~dp0"
set "LOG=%~dp0avvio_log.txt"
echo VCriptoV - log di avvio > "%LOG%"

echo ==============================================
echo    VCriptoV - avvio del sito
echo ==============================================
echo.

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

REM --- 3. Chiave Stripe, chiesta una sola volta (e ricontrollata) ---
if not exist "instance" mkdir instance
if not exist "instance\stripe.key" goto askkey
REM Va bene una vera chiave "sk_" oppure la parola "demo". Altrimenti richiedo.
findstr /b "sk_" "instance\stripe.key" >nul 2>nul && goto run
findstr /i /b "demo" "instance\stripe.key" >nul 2>nul && goto run
goto askkey

:askkey
echo.
echo ----------------------------------------------
echo Per PROVARE il sito senza pagamenti, scrivi:   demo
echo Oppure incolla la tua STRIPE SECRET KEY vera.
echo La chiave vera inizia con sk_test_ per le prove o sk_live_ per soldi veri.
echo NON quella che inizia con pk_ : quella e' sbagliata.
echo ----------------------------------------------
set /p STRIPE_KEY="Scrivi demo oppure incolla la chiave: "
if "%STRIPE_KEY%"=="" goto no_key
>"instance\stripe.key" echo %STRIPE_KEY%
echo Salvato. Non te lo chiedero' piu'.

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
