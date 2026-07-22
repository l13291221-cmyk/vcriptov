@echo off
REM ==========================================================
REM  Avviatore "tutto-in-uno" di VCriptoV per Windows.
REM  Fai doppio click su questo file. Fa tutto da solo:
REM   1. prepara Python e installa le dipendenze;
REM   2. la PRIMA volta ti chiede la Stripe Secret Key e la salva
REM      in instance\stripe.key (file locale, mai caricato su GitHub);
REM   3. avvia il sito su http://127.0.0.1:5000
REM ==========================================================
cd /d "%~dp0"

echo ==============================================
echo    VCriptoV - avvio del sito
echo ==============================================

REM --- 1. Controllo Python ---------------------------------
where python >nul 2>nul
if errorlevel 1 (
  echo ERRORE: Python non e' installato.
  echo Scaricalo da https://www.python.org/downloads/
  echo IMPORTANTE: durante l'installazione spunta "Add Python to PATH".
  pause
  exit /b 1
)

REM --- 2. Ambiente virtuale + dipendenze -------------------
if not exist ".venv" (
  echo -^> Preparo l'ambiente (solo la prima volta)...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo -^> Installo/aggiorno le dipendenze...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

REM --- 3. Stripe Secret Key (chiesta una sola volta) -------
if not exist "instance" mkdir instance
if not exist "instance\stripe.key" goto askkey
goto run

:askkey
echo.
echo ----------------------------------------------
echo Incolla la tua STRIPE SECRET KEY e premi Invio.
echo (sk_live_... per soldi veri, sk_test_... per le prove)
echo ----------------------------------------------
set /p STRIPE_KEY="Chiave: "
if "%STRIPE_KEY%"=="" (
  echo Nessuna chiave inserita. Riesegui il file quando ce l'hai.
  pause
  exit /b 1
)
>instance\stripe.key echo|set /p="%STRIPE_KEY%"
echo -^> Chiave salvata. Non te la chiedero' piu'.

:run
echo.
echo ==============================================
echo   Sito avviato! Apri il browser su:
echo      http://127.0.0.1:5000
echo   (per fermarlo: chiudi questa finestra)
echo ==============================================
python app.py
pause
