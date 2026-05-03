@echo off
echo ============================================
echo  WhisperPTT - Setup
echo ============================================
echo.

:: Check Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv .venv
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
