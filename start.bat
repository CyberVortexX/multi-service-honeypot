@echo off
setlocal enabledelayedexpansion
title HoneyTrap Launcher
color 0A

echo.
echo  ============================================================
echo   HoneyTrap  ^|  Multi-Service Honeypot
echo  ============================================================
echo.

REM Step 1 - Kill any old server on port 5000
echo  [1/4] Stopping any previous instances...
for /f "tokens=5" %%p in ('netstat -ano 2^>nul ^| findstr ":5000 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%p >nul 2>&1
)
ping -n 2 127.0.0.1 >nul

REM Step 2 - Check and install dependencies
echo  [2/4] Checking Python dependencies...
python -c "import flask,flask_socketio,paramiko,requests" >nul 2>&1
if errorlevel 1 (
    echo  Installing missing packages, please wait...
    pip install flask flask-socketio paramiko requests --quiet
    echo  Done.
)

REM Step 3 - Start server in a minimized background window
echo  [3/4] Starting HoneyTrap server...
start "HoneyTrap Server" /MIN cmd /c "cd /d %~dp0 && python honeypot_server.py"

REM Step 4 - Wait until server responds (goto loop, max 20 seconds)
echo  [4/4] Waiting for server to be ready...
set TRIES=0
:WAIT_LOOP
set /a TRIES+=1
if %TRIES% GTR 20 goto TIMEOUT_ERR
python -c "import urllib.request,sys; urllib.request.urlopen('http://localhost:5000/api/stats',timeout=1)" >nul 2>&1
if errorlevel 1 (
    ping -n 2 127.0.0.1 >nul
    goto WAIT_LOOP
)

REM Server is ready - open browser and show status
echo.
echo  ============================================================
echo   HoneyTrap is LIVE!
echo  ============================================================
echo   Dashboard:       http://localhost:5000
echo   SSH  Honeypot:   port 2222
echo   FTP  Honeypot:   port 2121
echo   Telnet Honeypot: port 2323
echo   HTTP Honeypot:   port 8080
echo  ============================================================
echo.
start "" "http://localhost:5000"
echo  Dashboard opened in your browser.
echo.
echo  Press S + Enter  to run the attack simulator now.
echo  Press Enter only  to skip simulation.
echo.
set /p CHOICE="  Your choice: "
if /i "!CHOICE!"=="S" (
    echo.
    echo  Running 5-campaign MITRE ATT^&CK simulation...
    python "%~dp0simulate_attacks.py"
    echo.
    echo  Simulation complete! Refresh the dashboard.
) else (
    echo  Skipped. Honeypot is listening for real attacks.
)
echo.
echo  HoneyTrap is running in the background.
echo  Close the "HoneyTrap Server" window to stop it.
echo.
pause
goto :EOF

:TIMEOUT_ERR
echo.
echo  ERROR: Server did not start in 20 seconds.
echo  Make sure Python is installed and try again.
echo.
pause