@echo off
chcp 65001 >nul
title BIST Analiz - Kurulum
color 0B

echo ============================================
echo     BIST Hisse Analiz Platformu - Kurulum
echo ============================================
echo.

echo [1/4] Python kontrol ediliyor...
python --version >nul 2>&1
if errorlevel 1 (
    echo HATA: Python bulunamadi!
    echo https://www.python.org/downloads/ adresinden Python yukleyin
    echo "Add Python to PATH" isaretlediginizden emin olun
    pause
    exit /b 1
)
python --version
echo.

echo [2/4] pip guncelleniyor...
python -m pip install --upgrade pip --quiet
echo.

echo [3/4] Kutuphaneler yukleniyor...
echo Bu islem ilk seferde 2-5 dakika surebilir...
echo.
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo.
    echo Uyari: Bazı kutuphaneler yuklenemedi, devam ediliyor...
)
echo.

echo [4/4] Kurulum tamamlandi!
echo.
echo ============================================
echo     Artik "start.bat" ile baslatabilirsiniz
echo ============================================
echo.
pause
