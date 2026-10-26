@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo    Campus Copilot 1.0  -  One-time Setup
echo ============================================
echo.

REM --- If a working venv already exists here, keep it ---
call :venv_ok
if not errorlevel 1 (
    echo [1/3] Virtual environment already present and working.
    goto deps
)

REM --- Remove an unusable/foreign venv (e.g. one that was unzipped from another PC) ---
if exist ".venv" (
    echo [1/3] Existing .venv is not usable on this PC - removing it...
    rmdir /s /q ".venv" 2>nul
    if exist ".venv" (
        echo.
        echo ERROR: Could not remove the old .venv because it is in use.
        echo Close the app window ^(run.bat / Streamlit^) if it is open, then run setup.bat again.
        pause
        exit /b 1
    )
)

REM --- Find THIS PC's Python and use its real path (no path is ever hard-coded) ---
set "BASEPY="
for /f "delims=" %%E in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do set "BASEPY=%%E"
if not defined BASEPY for /f "delims=" %%E in ('python -c "import sys; print(sys.executable)" 2^>nul') do set "BASEPY=%%E"
if not defined BASEPY for /f "delims=" %%E in ('python3 -c "import sys; print(sys.executable)" 2^>nul') do set "BASEPY=%%E"
if not defined BASEPY (
    echo.
    echo ERROR: No Python 3.10+ was found on this computer.
    echo Install it from https://www.python.org/downloads/ ^(tick "Add Python to PATH"^), then run setup.bat again.
    pause
    exit /b 1
)
echo [1/3] Building the virtual environment using your Python:
echo       "%BASEPY%"
"%BASEPY%" -m venv ".venv"
call :venv_ok
if errorlevel 1 (
    echo.
    echo ERROR: the virtual environment could not be built. Ensure your Python is 3.10 or newer.
    pause
    exit /b 1
)

:deps
REM --- Make sure pip is available inside the venv ---
".venv\Scripts\python.exe" -m pip --version >nul 2>nul
if errorlevel 1 (
    echo     bootstrapping pip...
    ".venv\Scripts\python.exe" -m ensurepip --upgrade >nul 2>nul
)
echo [2/3] Installing dependencies ^(first time can take several minutes^)...
set "PIP_ARGS=--index-url https://pypi.org/simple --trusted-host pypi.org --trusted-host files.pythonhosted.org --prefer-binary"
".venv\Scripts\python.exe" -m pip install --upgrade pip %PIP_ARGS%
".venv\Scripts\python.exe" -m pip install -r requirements.txt %PIP_ARGS%
if errorlevel 1 (
    echo.
    echo ERROR: core dependency installation failed. Check your internet connection and retry.
    pause
    exit /b 1
)
echo     adding the optional semantic-search engine ^(best effort^)...
".venv\Scripts\python.exe" -m pip install -r requirements-optional.txt --index-url https://pypi.org/simple --trusted-host pypi.org --trusted-host files.pythonhosted.org --only-binary=:all: || echo    ^(Semantic search unavailable on this Python; the app will use keyword search instead.^)

echo [3/3] Pre-training the placement models ^(one-time^)...
".venv\Scripts\python.exe" -c "from services.predictor_engine import load_bundle; load_bundle(force=True); print('Models ready.')" || echo    ^(Models will be trained automatically on first launch instead.^)

echo.
echo ============================================
echo   Setup complete.  Now double-click run.bat
echo ============================================
pause
exit /b 0

:venv_ok
REM Succeeds (errorlevel 0) only if the local venv's Python actually runs.
if not exist ".venv\Scripts\python.exe" exit /b 1
".venv\Scripts\python.exe" -c "import sys" >nul 2>nul
exit /b %errorlevel%
