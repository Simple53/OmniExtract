@echo off
title OmniExtract - 多模态提取
color 0B

cd /d "%~dp0"

:: 清除系统全局的 Conda 干扰，确保使用 .venv 环境
set CONDA_PREFIX=
set CONDA_DEFAULT_ENV=
set CONDA_PYTHON_EXE=
set CONDA_SHLVL=
set SSL_CERT_FILE=
set SSL_CERT_DIR=

echo.
echo  ================================================
echo        OmniExtract 多模态提取
echo  ================================================
echo.

:: 1. 清理端口 8000
echo [1/3] 正在检查端口 8000 占用...
netstat -aon | findstr /c:":8000" | findstr /c:"LISTENING" > port_listening.txt 2>nul
for /f "tokens=5" %%a in (port_listening.txt) do (
    echo 端口 8000 已被 PID %%a 占用。正在清理...
    taskkill /F /PID %%a >nul 2>&1
)
if exist port_listening.txt del port_listening.txt
echo [√] 端口就绪

:: 2. 环境检查与准备
echo [2/3] 正在检查 Python 虚拟环境...
if exist .venv\Scripts\python.exe (
    echo [√] 虚拟环境已就绪
    goto start_server
)

echo 未检测到虚拟环境，开始自动创建与安装...

where uv >nul 2>&1
if errorlevel 1 (
    echo [×] 系统未安装 uv，请先安装 uv。
    pause
    exit /b 1
)

echo 正在创建虚拟环境 (.venv)...
uv venv .venv
if errorlevel 1 (
    echo [×] 创建失败。
    pause
    exit /b 1
)

echo 正在安装项目依赖...
uv pip install --python .venv -r requirements.txt
if errorlevel 1 (
    echo [×] 依赖安装失败。
    pause
    exit /b 1
)
echo [√] 依赖安装完成。

:start_server
if not exist output mkdir output

:: 3. 启动后台系统托盘
echo [3/3] 正在启动后台服务，并最小化至系统托盘...
echo.
echo  -------------------------------------------------
echo   本地网页界面: http://127.0.0.1:8000
echo   此控制台窗口将自动关闭，以防止误操作关闭服务。
echo   需要关闭服务或打开界面时，请使用系统右下角的托盘图标。
echo  -------------------------------------------------
echo.

start "" .venv\Scripts\pythonw.exe tray_icon.py

echo 正在退出当前控制台...
ping 127.0.0.1 -n 4 >nul
exit
