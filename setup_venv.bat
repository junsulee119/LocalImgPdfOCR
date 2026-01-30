@echo off
REM OCR Application - Virtual Environment Setup
REM Can be run standalone or called from ocr.bat
REM Arguments: --gpu, --cpu, or --auto (default)

echo ================================================
echo OCR Application - Virtual Environment Setup
echo ================================================
echo.
echo Creating Python 3.11 virtual environment
echo with PyTorch 2.10 + CUDA 12.8 (RTX 5070 ready)
echo.

REM Check if Python 3.11 is available
py -3.11 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11 is not installed
    echo.
    echo Available Python versions:
    py -0
    echo.
    echo Please install Python 3.11 from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python 3.11 detected: 
py -3.11 --version
echo.

echo [1/4] Creating virtual environment with Python 3.11...
py -3.11 -m venv .venv
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)

echo [2/4] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo [3/4] Upgrading pip...
python -m pip install --upgrade pip

echo [4/4] Installing PyTorch and dependencies...
echo.

REM Determine installation mode
set INSTALL_MODE=%~1
if "%INSTALL_MODE%"=="" set INSTALL_MODE=--auto

if "%INSTALL_MODE%"=="--gpu" goto gpu_install
if "%INSTALL_MODE%"=="--cpu" goto cpu_install
if "%INSTALL_MODE%"=="--auto" goto auto_install

REM Default: ask user
:ask_user
choice /C YN /M "Do you have an NVIDIA GPU and want CUDA support"
if errorlevel 2 goto cpu_install
if errorlevel 1 goto gpu_install

:auto_install
REM Auto-detect: Check if nvidia-smi exists (indicates NVIDIA GPU)
echo Auto-detecting GPU...
nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo No NVIDIA GPU detected, installing CPU version
    goto cpu_install
) else (
    echo NVIDIA GPU detected, installing CUDA version
    goto gpu_install
)

:gpu_install
echo Installing PyTorch 2.10 with CUDA 12.8 support (RTX 5070 compatible)...
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128
if errorlevel 1 (
    echo WARNING: CUDA installation failed, falling back to CPU version
    goto cpu_install
)
goto install_rest

:cpu_install
echo Installing PyTorch (CPU version)...
pip install torch torchvision
if errorlevel 1 (
    echo ERROR: Failed to install PyTorch
    pause
    exit /b 1
)

:install_rest
echo Installing all dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo ================================================
echo Setup Complete!
echo ================================================
echo Virtual environment is ready at: .venv
echo You can now use ocr.bat to run the application
echo.

REM Only pause if run standalone (not from ocr.bat)
if "%~1"=="" pause
exit /b 0
