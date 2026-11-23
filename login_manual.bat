@echo off
title Autenticacao Diaria SSW - Renovador de Sessao
cd /d "%~dp0"
echo ========================================================
echo  INICIANDO AUTENTICACAO MANUAL NO SSW
echo ========================================================
python login_manual.py
echo.
pause
