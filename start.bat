@echo off
echo Starting Premium Park - Automatic Reminders...
echo.

REM Check for Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo Install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Check for virtual environment
if exist "venv\Scripts\activate.bat" (
    echo [OK] Virtual environment found
    call venv\Scripts\activate.bat
) else (
    echo [INFO] Virtual environment not found, creating...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Error creating virtual environment
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    echo [OK] Virtual environment created
)

REM Check for requirements.txt
if not exist "app\requirements.txt" (
    echo [ERROR] File app\requirements.txt not found!
    pause
    exit /b 1
)

REM Check if streamlit is installed (as indicator of installed dependencies)
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing dependencies...
    echo This may take a few minutes on first run...
    python -m pip install --upgrade pip
    python -m pip install -r app\requirements.txt
    if errorlevel 1 (
        echo [ERROR] Error installing dependencies
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
) else (
    echo [OK] Dependencies already installed
)

REM Check for .env file existence and completeness
if not exist "app\.env" (
    echo.
    echo [WARNING] File app\.env not found!
    echo [INFO] Starting environment variables setup...
    echo.
    python app\setup_env.py
    if errorlevel 1 (
        echo [ERROR] Error setting up .env
        pause
        exit /b 1
    )
) else (
    REM Check if .env is complete
    python app\setup_env.py --check
    if errorlevel 1 (
        echo.
        echo [WARNING] File app\.env is not fully configured!
        echo [INFO] Starting environment variables setup...
        echo.
        python app\setup_env.py
        if errorlevel 1 (
            echo [ERROR] Error setting up .env
            pause
            exit /b 1
        )
    )
)

echo.
echo [INFO] Browser will open with web interface
echo [INFO] Press Ctrl+C to stop
echo.

REM Start application
cd app
python -m streamlit run app.py
cd ..

pause

