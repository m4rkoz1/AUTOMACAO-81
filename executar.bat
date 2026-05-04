@echo off
chcp 65001 >nul
echo ============================================
echo   EXECUTANDO AUTOMAÇÃO SSW
echo ============================================
echo.
cd /d "%~dp0"
python automacao_ssw.py
echo.
pause
