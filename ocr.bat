@echo off
REM OCR Application Main Entry Point
REM Usage: ocr.bat [CLI arguments]
REM   Double-click: Launches Web GUI
REM   With args: Runs CLI mode

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found. Running setup...
    echo.
    call setup_venv.bat
    if errorlevel 1 (
        echo.
        echo Setup failed. Please check the error messages above.
        pause
        exit /b 1
    )
    echo.
    echo Setup completed successfully
    echo.
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Check and download models
echo Checking models...
python -m pipeline.download_models
if errorlevel 1 (
    echo.
    echo Model download failed. Exiting.
    pause
    exit /b 1
)
echo.

REM Launch application
REM If no arguments provided, launch Web GUI. Otherwise, run CLI.
if "%~1"=="" (
    echo ================================================
    echo Starting OCR Web Application
    echo ================================================
    echo.
    echo Server will start on: http://localhost:8000
    echo Opening browser in 2 seconds...
    echo.
    echo Press Ctrl+C to stop the server
    echo.
    
    REM Wait 2 seconds then open browser
    start /b timeout /t 2 /nobreak >nul && start http://localhost:8000
    
    REM Start server (blocks until Ctrl+C)
    python -m uvicorn pipeline.api.server:app --host 127.0.0.1 --port 8000
    
    REM Deactivate on exit
    call deactivate
) else (
    REM CLI mode
    python -m pipeline.cli_module %*
)
