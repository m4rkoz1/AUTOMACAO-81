@echo off
chcp 65001 >nul
title Automação SSW — Servidor Web
cd /d "%~dp0"

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║       AUTOMAÇÃO SSW — SERVIDOR WEB           ║
echo  ║  Acesse: http://localhost:5000               ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: Abre o navegador automaticamente após 2 segundos
start "" /b cmd /c "timeout /t 2 >nul && start http://localhost:5000"

:: Inicia o servidor Python
python servidor.py

pause
