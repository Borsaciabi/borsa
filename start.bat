@echo off
chcp 65001 >nul
title BIST Analiz Platformu
color 0A

echo ============================================
echo     BIST Hisse Analiz Platformu
echo ============================================
echo.

cd /d "%~dp0"

if exist "%USERPROFILE%\Desktop\Yapay Zeka\Python Borsa\.env" (
    set "BORSA_ENV_FILE=%USERPROFILE%\Desktop\Yapay Zeka\Python Borsa\.env"
) else if exist "%USERPROFILE%\BorsaAnalizData\.env" (
    set "BORSA_ENV_FILE=%USERPROFILE%\BorsaAnalizData\.env"
)

echo [1/4] Kutuphaneler kontrol ediliyor...
python -c "import fastapi, uvicorn, streamlit, yfinance, requests, bs4, pandas, plotly" >nul 2>&1
if errorlevel 1 (
    echo Kutuphaneler eksik, kuruluyor...
    call setup.bat
)
echo OK
echo.

echo [2/4] Eski surecler temizleniyor...
taskkill /F /IM "python.exe" /T >nul 2>&1
timeout /t 2 /nobreak >nul
echo OK
echo.

echo [3/4] API baslatiliyor (port 8000)...
start "BIST-API" /min python run_api.py
echo Bekleniyor...
timeout /t 6 /nobreak >nul

echo [4/5] Dashboard baslatiliyor (port 8501)...
start "BIST-Dashboard" /min python -m streamlit run web/streamlit_app.py --server.port 8501 --server.headless true --server.fileWatcherType none
timeout /t 5 /nobreak >nul

echo [5/5] Telegram bot kontrol ediliyor...
python -c "from config.settings import TELEGRAM_BOT_TOKEN; raise SystemExit(0 if TELEGRAM_BOT_TOKEN else 1)" >nul 2>&1
if errorlevel 1 (
    echo Telegram bot atlandi: TELEGRAM_BOT_TOKEN bulunamadi
) else (
    start "BIST-Telegram" /min cmd /c "python run_bot.py"
    echo Telegram bot baslatildi
)

echo.
echo ============================================
echo     Her sey hazir!
echo ============================================
echo.
echo   Dashboard: http://localhost:8501
echo   API:       http://localhost:8000
echo.
echo   Kapatmak icin bu pencereyi kapatmaniz yeterli
echo.

:: Tarayiciyi ac
start http://localhost:8501

:: Pencereyi acik tut
pause
