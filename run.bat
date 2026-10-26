@echo off
setlocal

cd /d "%~dp0"

call :venv_ok

if errorlevel 1 (
    echo Preparing the environment for first use...
    call "%~dp0setup.bat"
)

call :venv_ok

if errorlevel 1 (
    echo.
    echo ERROR: The environment is not ready.
    echo Run setup.bat and review any errors shown.
    pause
    exit /b 1
)

echo.
echo Starting Campus Copilot 1.0...
echo Press Ctrl+C or close this window to stop.
echo.

".venv\Scripts\python.exe" -m streamlit run app.py

pause
exit /b 0

:venv_ok
if not exist ".venv\Scripts\python.exe" exit /b 1

".venv\Scripts\python.exe" -c "import sys" >nul 2>nul

exit /b %errorlevel%
