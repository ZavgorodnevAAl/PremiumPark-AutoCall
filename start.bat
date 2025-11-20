@echo off
echo Запуск Premium Park - Автоматические напоминания...
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ОШИБКА] Python не найден!
    echo Установите Python с https://www.python.org/
    pause
    exit /b 1
)

REM Проверяем наличие виртуального окружения
if exist "venv\Scripts\activate.bat" (
    echo [OK] Виртуальное окружение найдено
    call venv\Scripts\activate.bat
) else (
    echo [INFO] Виртуальное окружение не найдено, создаем...
    python -m venv venv
    if errorlevel 1 (
        echo [ОШИБКА] Ошибка при создании виртуального окружения
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    echo [OK] Виртуальное окружение создано
)

REM Проверяем наличие requirements.txt
if not exist "app\requirements.txt" (
    echo [ОШИБКА] Файл app\requirements.txt не найден!
    pause
    exit /b 1
)

REM Проверяем установлен ли streamlit (как индикатор установленных зависимостей)
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Устанавливаем зависимости...
    echo Это может занять несколько минут при первом запуске...
    python -m pip install --upgrade pip
    python -m pip install -r app\requirements.txt
    if errorlevel 1 (
        echo [ОШИБКА] Ошибка при установке зависимостей
        pause
        exit /b 1
    )
    echo [OK] Зависимости установлены
) else (
    echo [OK] Зависимости уже установлены
)

REM Проверяем наличие и заполненность .env файла
if not exist "app\.env" (
    echo.
    echo [WARNING] Файл app\.env не найден!
    echo [INFO] Запускаем настройку переменных окружения...
    echo.
    python app\setup_env.py
    if errorlevel 1 (
        echo [ОШИБКА] Ошибка при настройке .env
        pause
        exit /b 1
    )
) else (
    REM Проверяем, заполнен ли .env
    python app\setup_env.py --check
    if errorlevel 1 (
        echo.
        echo [WARNING] Файл app\.env не полностью заполнен!
        echo [INFO] Запускаем настройку переменных окружения...
        echo.
        python app\setup_env.py
        if errorlevel 1 (
            echo [ОШИБКА] Ошибка при настройке .env
            pause
            exit /b 1
        )
    )
)

echo.
echo [INFO] Откроется браузер с веб-интерфейсом
echo [INFO] Для остановки нажмите Ctrl+C
echo.

REM Запускаем приложение
cd app
python -m streamlit run app.py
cd ..

pause

