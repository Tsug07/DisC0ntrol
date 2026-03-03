@echo off
title DisC0ntrol - Bot Dashboard
cd /d "%~dp0.."

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado no PATH.
    echo Instale Python 3.8+ de https://python.org
    pause
    exit /b 1
)

:: Install dependencies if needed
if not exist "venv" (
    echo Criando ambiente virtual...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Instalando dependencias...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

:: Launch DisC0ntrol
echo Iniciando DisC0ntrol...
python main.py

if errorlevel 1 (
    echo.
    echo [ERRO] DisC0ntrol encerrou com erro.
    pause
)
