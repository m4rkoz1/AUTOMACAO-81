@echo off
chcp 65001 >nul
title Automação SSW — Instalação
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   INSTALANDO DEPENDÊNCIAS - AUTOMAÇÃO SSW   ║
echo  ╚══════════════════════════════════════════════╝
echo.
cd /d "%~dp0"

pip install -r requirements.txt

echo.
echo  Instalando navegador Chromium...
playwright install chromium

echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║        INSTALAÇÃO CONCLUÍDA!                 ║
echo  ║  Execute: INICIAR_SERVIDOR.bat               ║
echo  ╚══════════════════════════════════════════════╝
echo.
pause
