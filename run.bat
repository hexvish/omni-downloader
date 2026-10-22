@echo off
setlocal

title Omni Downloader - Launcher

:: Set current directory to the directory of this batch file
cd /d "%~dp0"

echo ========================================================
echo               Omni Downloader Launcher
echo ========================================================
echo.

:: 1. Verify app.py exists (ensures user extracted the ZIP)
if not exist "%~dp0app.py" (
    echo [ERROR] Cannot find app.py!
    echo Please make sure you have EXTRACTED the ZIP folder before running run.bat.
    echo.
    pause
    exit /b 1
)

:: 2. Verify Python Installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in your system PATH.
    echo Please install Python 3.8+ from https://www.python.org/downloads/
    echo Make sure to check the box: "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: 3. Setup / Activate Virtual Environment
if exist "%~dp0.venv\Scripts\activate.bat" goto VENV_READY

echo [*] Setting up virtual environment .venv ...
python -m venv "%~dp0.venv"
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    echo Continuing with system Python...
    goto VENV_DONE
)
echo [*] Virtual environment created successfully.

:VENV_READY
echo [*] Activating virtual environment...
call "%~dp0.venv\Scripts\activate.bat"

:VENV_DONE

:: 4. Check & Install Base Requirements
echo [*] [1/3] Verifying dependencies from requirements.txt...
python -m pip install -r "%~dp0requirements.txt"
if errorlevel 1 (
    echo.
    echo [WARNING] Encountered an issue while installing requirements.
    echo Continuing to start application...
)

:: 5. Check for yt-dlp and FFmpeg Updates
echo [*] [2/3] Checking for latest yt-dlp and FFmpeg updates...
python -m pip install --upgrade yt-dlp imageio-ffmpeg

:: 6. Verify FFmpeg engine
echo [*] [3/3] Verifying FFmpeg installation...
python -c "import imageio_ffmpeg; print('    FFmpeg ready: ' + imageio_ffmpeg.get_ffmpeg_exe())"
if errorlevel 1 (
    echo [WARNING] FFmpeg check encountered an issue, but continuing...
)

echo.
echo ========================================================
echo   Starting Omni Downloader Server...
echo   Web UI: http://localhost:5000
echo   Press CTRL+C in this terminal window to stop the server
echo ========================================================
echo.

:: 7. Launch browser after a 2-second delay to give Flask time to bind
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://localhost:5000"

:: 8. Run the Flask application
python "%~dp0app.py"

echo.
echo The application server has stopped.
pause
