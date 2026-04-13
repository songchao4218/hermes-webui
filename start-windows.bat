@echo off
chcp 65001 >nul 2>&1
title Hermes WebUI - 马鞍 安装向导
echo.
echo ============================================
echo    马鞍 Saddle - Hermes WebUI 安装向导
echo ============================================
echo.

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

:: ============================================
:: 步骤 1: 检测 WSL2
:: ============================================
echo [1/4] 检测 WSL2 环境...

wsl.exe --version >nul 2>&1
if %errorlevel% equ 0 (
    echo     ✓ WSL2 已安装
    goto :check_distro
)

echo     ✗ WSL2 未安装
echo.
echo ============================================
echo    需要安装 WSL2
echo ============================================
echo.
echo WSL2 是 Windows 的子系统，用于运行 Hermes Agent。
echo.
echo 安装步骤：
echo   1. 以管理员身份打开 PowerShell
echo   2. 运行: wsl --install
echo   3. 重启电脑
echo   4. 设置 Ubuntu 用户名和密码
echo.
echo 详细教程: https://docs.microsoft.com/zh-cn/windows/wsl/install
echo.
pause
exit /b 1

:check_distro
:: 获取默认 WSL 发行版
for /f "tokens=1,* delims= " %%a in ('wsl.exe --list --verbose 2^>nul ^| findstr /B "*"') do (
    set "WSL_DISTRO=%%b"
    goto :found_distro
)

:: 如果没有默认发行版，查找 Ubuntu
wsl.exe --list --quiet 2>nul | findstr /I "ubuntu" >nul
if %errorlevel% equ 0 (
    set "WSL_DISTRO=Ubuntu"
    goto :found_distro
)

:: 使用第一个可用的发行版
for /f "tokens=1" %%a in ('wsl.exe --list --quiet 2^>nul') do (
    set "WSL_DISTRO=%%a"
    goto :found_distro
)

echo [错误] 未找到可用的 WSL 发行版
echo 请先安装一个 Linux 发行版: wsl --install -d Ubuntu
pause
exit /b 1

:found_distro
:: 清理发行版名称中的空格
set "WSL_DISTRO=%WSL_DISTRO: =%"
echo     ✓ 使用发行版: %WSL_DISTRO%
echo.

:: ============================================
:: 步骤 2: 检测并安装 Hermes
:: ============================================
echo [2/4] 检测 Hermes CLI...

wsl.exe -d %WSL_DISTRO% which hermes >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%a in ('wsl.exe -d %WSL_DISTRO% which hermes') do set "HERMES_PATH=%%a"
    echo     ✓ Hermes 已安装: %HERMES_PATH%
    goto :check_ollama
)

echo     ✗ Hermes 未安装
echo.
echo     正在自动安装 Hermes...
echo.

:: 尝试安装 Hermes
wsl.exe -d %WSL_DISTRO% -- bash -c "pip3 install hermes-agent --user 2>/dev/null || pip3 install hermes-agent"

if %errorlevel% equ 0 (
    echo     ✓ Hermes 安装成功
) else (
    echo     ! Hermes 自动安装失败
    echo       请手动在 WSL 内运行: pip3 install hermes-agent
    echo.
    choice /C YN /M "是否继续启动 WebUI (无 Agent 功能)"
    if %errorlevel% equ 2 exit /b 1
)
echo.

:: ============================================
:: 步骤 3: 检测并安装 Ollama
:: ============================================
:check_ollama
echo [3/4] 检测 Ollama...

:: 检查本地 Ollama
wsl.exe -d %WSL_DISTRO% which ollama >nul 2>&1
if %errorlevel% equ 0 (
    echo     ✓ Ollama 已安装
    goto :check_model
)

:: 检查远程 Ollama 配置
wsl.exe -d %WSL_DISTRO% test -f ~/.hermes/config.yaml >nul 2>&1
if %errorlevel% equ 0 (
    for /f "tokens=*" %%a in ('wsl.exe -d %WSL_DISTRO% grep ollama_base_url ~/.hermes/config.yaml 2^>nul') do (
        echo     ✓ 发现远程 Ollama 配置
        goto :check_model
    )
)

echo     ✗ Ollama 未安装
echo.
echo     正在自动安装 Ollama...
echo.

:: 安装 Ollama
wsl.exe -d %WSL_DISTRO% -- curl -fsSL https://ollama.com/install.sh | sh

if %errorlevel% equ 0 (
    echo     ✓ Ollama 安装成功
    echo.
    echo     正在启动 Ollama 服务...
    start /B wsl.exe -d %WSL_DISTRO% -- ollama serve >nul 2>&1
    timeout /t 3 /nobreak >nul
) else (
    echo     ! Ollama 自动安装失败
    echo.
    echo     你可以选择：
    echo       1. 使用远程 Ollama 服务器（局域网其他电脑）
    echo       2. 跳过，稍后手动安装
    echo.
    choice /C 12 /M "请选择"
    if %errorlevel% equ 1 (
        echo.
        set /p REMOTE_IP="请输入远程 Ollama IP（如 192.168.1.100:11434）: "
        if not "!REMOTE_IP!"=="" (
            wsl.exe -d %WSL_DISTRO% -- mkdir -p ~/.hermes
            wsl.exe -d %WSL_DISTRO% -- bash -c "echo 'ollama_base_url: http://!REMOTE_IP!' > ~/.hermes/config.yaml"
            echo     ✓ 已配置远程 Ollama: !REMOTE_IP!
        )
    )
)
echo.

:: ============================================
:: 步骤 4: 检测并下载模型
:: ============================================
:check_model
echo [4/4] 检测 AI 模型...

:: 检查是否有模型
for /f "tokens=*" %%a in ('wsl.exe -d %WSL_DISTRO% ollama list 2^>nul ^| findstr /V "NAME" ^| findstr /V "^$"') do (
    set "MODELS_FOUND=%%a"
    goto :models_exist
)

:models_exist
if defined MODELS_FOUND (
    echo     ✓ 发现已安装的模型
    wsl.exe -d %WSL_DISTRO% ollama list | findstr /V "NAME"
    goto :start_webui
)

echo     ✗ 未安装任何模型
echo.
echo ============================================
echo    下载 AI 模型
echo ============================================
echo.
echo 请选择要安装的模型（推荐）:
echo.
echo   1. gemma3:4b  - 轻量级，适合 8GB 内存 (推荐)
echo   2. gemma3:12b - 标准版，适合 16GB 内存
echo   3. llama3.2:3b - 超轻量，适合低配机器
echo   4. 跳过，稍后手动下载
echo.
choice /C 1234 /M "请选择"

if %errorlevel% equ 1 set "MODEL_NAME=gemma3:4b"
if %errorlevel% equ 2 set "MODEL_NAME=gemma3:12b"
if %errorlevel% equ 3 set "MODEL_NAME=llama3.2:3b"
if %errorlevel% equ 4 goto :start_webui

echo.
echo     正在下载 %MODEL_NAME%...
echo     （这可能需要几分钟，取决于网络速度）
echo.

wsl.exe -d %WSL_DISTRO% -- ollama pull %MODEL_NAME%

if %errorlevel% equ 0 (
    echo     ✓ 模型下载完成: %MODEL_NAME%
) else (
    echo     ! 模型下载失败，请稍后手动运行: ollama pull %MODEL_NAME%
)
echo.

:: ============================================
:: 启动 WebUI
:: ============================================
:start_webui
echo ============================================
echo    启动 WebUI
echo ============================================
echo.

:: 转换 Windows 路径到 WSL 路径
for /f "usebackq tokens=*" %%a in (`wsl.exe -d %WSL_DISTRO% wslpath -u "%PROJECT_DIR%"`) do (
    set "WSL_PROJECT_PATH=%%a"
)

echo 正在启动服务...
echo 浏览器将自动打开 http://localhost:8080
echo.
echo 提示：
echo   - 首次启动可能需要 10-30 秒初始化
echo   - 如果浏览器没有自动打开，请手动访问上述地址
echo   - 按 Ctrl+C 可以停止服务
echo.

:: 延迟打开浏览器
start "" cmd /c "timeout /t 5 /nobreak >nul && start http://localhost:8080"

:: 启动 WebUI（在 WSL2 内）
:try_port_8080
wsl.exe -d %WSL_DISTRO% -- bash -c "cd '%WSL_PROJECT_PATH%' && source .venv/bin/activate && cd backend && python app.py --host 0.0.0.0 --port 8080"
if %errorlevel% equ 0 goto :end

echo.
echo 端口 8080 被占用，尝试 8081...
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8081"
wsl.exe -d %WSL_DISTRO% -- bash -c "cd '%WSL_PROJECT_PATH%' && source .venv/bin/activate && cd backend && python app.py --host 0.0.0.0 --port 8081"
if %errorlevel% equ 0 goto :end

echo.
echo 端口 8081 也被占用，尝试 8082...
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://localhost:8082"
wsl.exe -d %WSL_DISTRO% -- bash -c "cd '%WSL_PROJECT_PATH%' && source .venv/bin/activate && cd backend && python app.py --host 0.0.0.0 --port 8082"
if %errorlevel% equ 0 goto :end

echo.
echo [错误] 所有端口都被占用，请关闭其他程序后重试
pause

:end
