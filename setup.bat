@echo off
REM Quick setup script for Windows users
REM This script sets up the G25 Telegram Bot for local development

setlocal enabledelayedexpansion

echo.
echo ========================================
echo G25 Telegram Bot - Windows Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

echo [OK] Python found
python --version

REM Create virtual environment
if not exist venv (
    echo.
    echo Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

REM Activate virtual environment
call venv\Scripts\activate.bat
echo [OK] Virtual environment activated

REM Install dependencies
echo.
echo Installing dependencies...
pip install -r requirements.txt --quiet
if !errorlevel! neq 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM Create .env file if it doesn't exist
if not exist .env (
    echo.
    echo Creating .env file...
    copy .env.example .env
    echo [OK] .env file created
    echo.
    echo !!! IMPORTANT !!!
    echo Please edit .env and add your BOT_TOKEN
    echo Get your token from @BotFather on Telegram
    echo.
) else (
    echo [OK] .env file already exists
)

REM Create necessary directories
if not exist logs (
    mkdir logs
    echo [OK] Created logs directory
)

if not exist temp (
    mkdir temp
    echo [OK] Created temp directory
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env and add your BOT_TOKEN
echo 2. Run: python bot.py
echo.
echo For Docker:
echo   docker-compose up -d
echo.
pause
