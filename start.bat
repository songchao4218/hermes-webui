@echo off
chcp 65001 >nul 2>&1
title Hermes WebUI

echo.
echo   马鞍 Saddle — The Saddle for Hermes
echo   =====================================
echo.

set "PROJECT_DIR=%~dp0"

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ first.
    pause
    exit /b 1
)

REM Create venv if needed
if not exist "%PROJECT_DIR%.venv" (
    echo Creating virtual environment...
    python -m venv "%PROJECT_DIR%.venv"
)

REM Activate venv
call "%PROJECT_DIR%.venv\Scripts\activate.bat"

REM Install deps if needed
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r "%PROJECT_DIR%backend\requirements.txt" -q
)

echo Starting server on http://localhost:8080
echo Press Ctrl+C to stop
echo.

REM Open browser after 2 seconds
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8080"

cd /d "%PROJECT_DIR%backend"

REM Try port 8080
python app.py --host 0.0.0.0 --port 8080

REM If port 8080 is busy, try 8081
if %errorlevel% neq 0 (
    echo Port 8080 is busy, trying port 8081...
    start "" cmd /c "timeout /t 1 /nobreak >nul && start http://localhost:8081"
    python app.py --host 0.0.0.0 --port 8081
)

REM If port 8081 is busy, try 8082
if %errorlevel% neq 0 (
    echo Port 8081 is busy, trying port 8082...
    start "" cmd /c "timeout /t 1 /nobreak >nul && start http://localhost:8082"
    python app.py --host 0.0.0.0 --port 8082
)

REM If port 8082 is busy, try 8083
if %errorlevel% neq 0 (
    echo Port 8082 is busy, trying port 8083...
    start "" cmd /c "timeout /t 1 /nobreak >nul && start http://localhost:8083"
    python app.py --host 0.0.0.0 --port 8083
)

pause

