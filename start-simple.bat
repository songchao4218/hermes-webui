@echo off
echo Starting Hermes WebUI...
echo.

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

cd /d "%PROJECT_DIR%"

:: 激活虚拟环境并启动
call .venv\Scripts\activate.bat

:: 启动后端
cd backend
start http://localhost:8080
python app.py --host 0.0.0.0 --port 8080

pause
