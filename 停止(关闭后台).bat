@echo off
title 停止 OmniExtract 后端服务
color 0C
cd /d "%~dp0"
echo ==================================================
echo       正在停止 OmniExtract 后端服务...
echo ==================================================
echo.
netstat -aon | findstr /c:":8000" | findstr /c:"LISTENING" > port_listening.txt 2>nul
set found=0
for /f "tokens=5" %%a in (port_listening.txt) do (
    taskkill /F /PID %%a >nul 2>&1
    echo [√] 已成功释放端口 8000 (结束进程 PID: %%a)
    set found=1
)
if exist port_listening.txt del port_listening.txt

if %found%==0 (
    echo [!] 未检测到运行在端口 8000 的后端服务。
) else (
    echo [√] 后端服务已安全关闭。
)
echo.
pause
