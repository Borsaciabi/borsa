@echo off
chcp 65001 >nul
title BIST Analiz - Otomatik Baslatma

:: Bu dosyayi Windows Baslangic klasorune kopyalayarak
:: bilgisayar acildiginda otomatik baslatabilirsiniz.

cd /d "%~dp0"

:: Python kontrol
python --version >nul 2>&1
if errorlevel 1 (
    exit /b 1
)

:: Kutuphane kontrol
python -c "import fastapi, streamlit" >nul 2>&1
if errorlevel 1 (
    python -m pip install -r requirements.txt --quiet >nul 2>&1
)

:: Eski surecleri temizle
taskkill /F /IM "python.exe" /T >nul 2>&1
timeout /t 2 /nobreak >nul

:: API baslat
start /min python run_api.py
timeout /t 6 /nobreak >nul

:: Streamlit baslat
start /min python -m streamlit run web/streamlit_app.py --server.port 8501 --server.headless true --server.fileWatcherType none
