@echo off
chcp 65001 >nul
title BIST Analiz - Durdur
color 0C

echo ============================================
echo     Tum servisler durduruluyor...
echo ============================================

taskkill /F /IM "python.exe" /T >nul 2>&1

echo.
echo Tum servisler durduruldu.
timeout /t 2 /nobreak >nul
