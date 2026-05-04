@echo off
echo ============================================
echo  WhisperPTT - Build
echo ============================================
echo.

:: Check venv exists
if not exist .venv\Scripts\activate (
    echo ERROR: .venv not found. Run setup.bat first.
    pause
    exit /b 1
)

call .venv\Scripts\activate

:: Install PyInstaller if needed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install pyinstaller
)

:: Convert PNG to ICO for the exe icon
echo Generating icon...
python -c "from PIL import Image; img = Image.open('whisprPTT.png'); img.save('whisprPTT.ico')"
if errorlevel 1 ( echo ERROR: Failed to generate icon. && pause && exit /b 1 )

:: Build
echo Building executable...
pyinstaller whispr_ptt.spec --noconfirm
if errorlevel 1 ( echo ERROR: PyInstaller build failed. && pause && exit /b 1 )

:: Clean up temp ICO
del whisprPTT.ico >nul 2>&1

echo.
echo ============================================
echo  Build complete!
echo  Executable: dist\whispr-ptt\whispr-ptt.exe
echo  Zip the dist\whispr-ptt\ folder to share it.
echo ============================================
pause
