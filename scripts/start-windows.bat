@echo off
title Hermes WebUI

set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
for %%i in ("%SCRIPT_DIR%\..") do set "PROJECT_DIR=%%~fi"
set "BACKEND_DIR=%PROJECT_DIR%\backend"
set "VENV_DIR=%PROJECT_DIR%\.venv"
set "PYTHON_EXE="
set "PORT=8080"

echo.
echo ============================================
echo    Hermes WebUI - Saddle
echo ============================================
echo.

:: ============================================
:: Step 1: Check Python
:: ============================================
echo [1/5] Checking Python...

python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo     OK: %%v
    goto :check_wsl
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python3"
    for /f "tokens=*" %%v in ('python3 --version 2^>^&1') do echo     OK: %%v
    goto :check_wsl
)

echo     ERROR: Python not found.
echo     Please install Python 3.10+ from https://www.python.org/downloads/
echo     Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:: ============================================
:: Step 2: Check / Install WSL2
:: ============================================
:check_wsl
echo.
echo [2/5] Checking WSL2...

wsl --status >nul 2>&1
if %errorlevel% equ 0 (
    echo     OK: WSL2 is available
    goto :check_hermes
)

echo     WSL2 not found. Installing...
echo     (This requires administrator privileges and a reboot)
echo.
:: Enable WSL feature
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart >nul 2>&1
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart >nul 2>&1

:: Try wsl --install (Windows 10 2004+ / Windows 11)
wsl --install --no-distribution >nul 2>&1
if %errorlevel% equ 0 (
    echo     OK: WSL2 installed. Installing Ubuntu...
    wsl --install -d Ubuntu
    echo.
    echo     IMPORTANT: Please reboot your computer, then run this script again.
    pause
    exit /b 0
)

echo     Could not auto-install WSL2.
echo     Please run in PowerShell as Administrator:
echo       wsl --install
echo     Then reboot and run this script again.
pause
exit /b 1

:: ============================================
:: Step 3: Check / Install Hermes in WSL
:: ============================================
:check_hermes
echo.
echo [3/5] Checking Hermes CLI in WSL...

wsl -d Ubuntu bash -c "test -f /home/$(whoami)/hermes-agent/venv/bin/hermes || which hermes" >nul 2>&1
if %errorlevel% equ 0 (
    echo     OK: Hermes CLI found
    goto :setup_venv
)

echo     Hermes not found. Installing in WSL Ubuntu...
wsl -d Ubuntu bash -c "pip3 install hermes-agent --user -q 2>/dev/null || pip3 install hermes-agent -q"
if %errorlevel% equ 0 (
    echo     OK: Hermes installed
) else (
    echo     WARNING: Hermes install failed. Agent mode will be unavailable.
    echo     You can install manually in WSL: pip3 install hermes-agent
)

:setup_venv
echo.
echo [4/5] Setting up environment...

if exist "%VENV_DIR%\Scripts\python.exe" (
    echo     OK: Virtual environment exists
    set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
    goto :find_port
)

echo     Creating virtual environment...
%PYTHON_EXE% -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo     WARNING: Failed to create venv, using system Python
    goto :install_global
)
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"

echo     Installing dependencies (first run may take 1 min)...
"%VENV_DIR%\Scripts\pip.exe" install -r "%BACKEND_DIR%\requirements.txt" -q
if %errorlevel% neq 0 (
    echo     ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo     OK: Dependencies installed
goto :find_port

:install_global
echo     Installing dependencies...
%PYTHON_EXE% -m pip install -r "%BACKEND_DIR%\requirements.txt" -q
if %errorlevel% neq 0 (
    echo     ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo     OK: Dependencies installed

:: ============================================
:: Step 5: Find available port
:: ============================================
:find_port
echo.
echo [5/5] Finding available port...

netstat -ano 2>nul | findstr ":8080 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    set "PORT=8080"
    echo     OK: Using port 8080
    goto :start
)

netstat -ano 2>nul | findstr ":8081 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    set "PORT=8081"
    echo     OK: Port 8080 busy, using 8081
    goto :start
)

netstat -ano 2>nul | findstr ":8082 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    set "PORT=8082"
    echo     OK: Port 8081 busy, using 8082
    goto :start
)

netstat -ano 2>nul | findstr ":8083 " | findstr "LISTENING" >nul 2>&1
if %errorlevel% neq 0 (
    set "PORT=8083"
    echo     OK: Port 8082 busy, using 8083
    goto :start
)

echo     ERROR: Ports 8080-8083 all in use. Please close other programs.
pause
exit /b 1

:: ============================================
:: Start server
:: ============================================
:start
echo.
echo ============================================
echo    Starting at http://localhost:%PORT%
echo    Press Ctrl+C to stop
echo ============================================
echo.

start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:%PORT%"

"%PYTHON_EXE%" "%BACKEND_DIR%\app.py" --no-auth --host 0.0.0.0 --port %PORT%

echo.
echo Server stopped.
pause
