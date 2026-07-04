@echo off
title Stop OmniExtract Server
color 0C
cd /d "%~dp0"
echo ==================================================
echo       Stopping OmniExtract Server...
echo ==================================================
echo.
netstat -aon | findstr /c:":8000" | findstr /c:"LISTENING" > port_listening.txt 2>nul
set found=0
for /f "tokens=5" %%a in (port_listening.txt) do (
    taskkill /F /PID %%a >nul 2>&1
    echo [OK] Released port 8000 (PID: %%a)
    set found=1
)
if exist port_listening.txt del port_listening.txt

if %found%==0 (
    echo [!] No server found on port 8000
) else (
    echo [OK] Server stopped successfully.
)
echo.
pause
