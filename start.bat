@echo off
title OmniExtract - 万象多模态提取引擎
color 0B

cd /d "%~dp0"

:: 彻底清理所有来自系统全局的 Conda 环境变量，防止其干扰独立的 .venv 虚拟环境
set CONDA_PREFIX=
set CONDA_DEFAULT_ENV=
set CONDA_PYTHON_EXE=
set CONDA_SHLVL=
set SSL_CERT_FILE=
set SSL_CERT_DIR=

echo.
echo  ================================================
echo        OmniExtract 万象多模态提取引擎
echo  ================================================
echo.

:: 1. 检查并清理端口 8000
echo [1/3] 正在检查端口 8000 占用情况...
netstat -aon | findstr /c:":8000" | findstr /c:"LISTENING" > port_listening.txt 2>nul
for /f "tokens=5" %%a in (port_listening.txt) do (
    echo 端口 8000 已被进程 PID %%a 占用。正在自动释放...
    taskkill /F /PID %%a >nul 2>&1
)
if exist port_listening.txt del port_listening.txt
echo [√] 端口已就绪。

:: 2. 检查并准备虚拟环境
echo [2/3] 正在检查 Python 虚拟运行环境...
if exist .venv\Scripts\python.exe (
    echo [√] 虚拟环境就绪。即将启动服务...
    goto start_server
)

echo 未检测到虚拟环境。正在初始化全新环境...

where uv >nul 2>&1
if errorlevel 1 (
    echo [错误] 系统中未安装 uv 依赖包管理器！请先安装 uv。
    pause
    exit /b 1
)

echo 正在创建本地虚拟环境 (.venv)...
uv venv .venv
if errorlevel 1 (
    echo [错误] 创建虚拟环境失败！
    pause
    exit /b 1
)

echo 正在安装项目依赖包（可能需要几分钟）...
uv pip install --python .venv -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖包安装失败！
    pause
    exit /b 1
)
echo [√] 依赖包安装完成。

:start_server
if not exist output mkdir output

:: 3. 启动服务
echo [3/3] 正在拉起后端服务...
echo.
echo  -------------------------------------------------
echo   服务地址: http://127.0.0.1:8000
echo   正在自动打开浏览器页面...
echo   按 Ctrl+C 可以随时停止运行
echo  -------------------------------------------------
echo.

start http://127.0.0.1:8000

.venv\Scripts\python.exe -m uvicorn server:app --host 127.0.0.1 --port 8000 --reload

echo.
echo 服务已停止退出。
pause
