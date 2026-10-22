@echo off
setlocal enabledelayedexpansion

title Omni Downloader - Launcher
cls

echo ========================================================
echo               Omni Downloader Launcher
echo ========================================================
echo.

:: 1. Verify Python Installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in your system PATH.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check the box: "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 2. Setup / Activate Virtual Environment
if not exist ".venv\Scripts\activate.bat" (
    echo [*] Creating virtual environment (.venv)...
    python -m venv .venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [*] Virtual environment created successfully.
)

echo [*] Activating virtual environment...
call .venv\Scripts\activate.bat

:: 3. Check & Install Base Requirements
echo [*] [1/3] Verifying dependencies from requirements.txt...
python -m pip install --upgrade pip --quiet
python -m pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

:: 4. Check for yt-dlp and FFmpeg Updates
echo [*] [2/3] Checking for latest yt-dlp and FFmpeg engine updates...
python -m pip install --upgrade yt-dlp imageio-ffmpeg --quiet

:: 5. Verify FFmpeg engine
echo [*] [3/3] Verifying FFmpeg installation...
python -c "import imageio_ffmpeg; print('    FFmpeg ready: ' + imageio_ffmpeg.get_ffmpeg_exe())"
if %errorlevel% neq 0 (
    echo [WARNING] FFmpeg check encountered an issue, but continuing...
)

echo.
echo ========================================================
echo   Starting Omni Downloader Server...
echo   Web UI: http://localhost:5000
echo   Press CTRL+C in this terminal window to stop the server
echo ========================================================
echo.

:: 6. Launch browser after a 2-second delay to give Flask time to bind
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: 7. Run the Flask application
python app.py

pause
