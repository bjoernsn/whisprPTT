@echo off
echo ============================================
echo  WhisprPTT - Setup
echo ============================================
echo.

:: --- Locate Python ---
set PYTHON=

:: Try the Windows Python Launcher first (works even without PATH changes)
py --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=py & goto :found_python )

:: Try bare `python`
python --version >nul 2>&1
if not errorlevel 1 ( set PYTHON=python & goto :found_python )

:: Try common install locations (user-level install from python.org)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" ( set PYTHON="%%D\python.exe" & goto :found_python )
)

:: Try system-level install
for /d %%D in ("%PROGRAMFILES%\Python3*" "%PROGRAMFILES(X86)%\Python3*") do (
    if exist "%%D\python.exe" ( set PYTHON="%%D\python.exe" & goto :found_python )
)

echo ERROR: Python 3.10+ not found.
echo.
echo Install it from https://www.python.org/downloads/
echo Make sure to check "Add python.exe to PATH" during install.
pause
exit /b 1

:found_python
echo Found Python: %PYTHON%
%PYTHON% --version

:: Require 3.10+
%PYTHON% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10 or newer is required.
    echo Please upgrade from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Creating virtual environment...
%PYTHON% -m venv .venv
if errorlevel 1 ( echo ERROR: Failed to create venv. && pause && exit /b 1 )

echo Installing dependencies...
call .venv\Scripts\activate
pip install -r requirements.txt
if errorlevel 1 ( echo ERROR: pip install failed. && pause && exit /b 1 )

echo.
echo ============================================
echo  Setup complete!
echo  Run whispr_ptt.py to start, or
echo  run build.bat to create a standalone .exe
echo ============================================
pause
