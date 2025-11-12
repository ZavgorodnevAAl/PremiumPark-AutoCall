@echo off
chcp 65001 >nul
echo 🚗 Запуск Premium Park - Автоматические напоминания...
echo.

REM Проверяем наличие Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Ошибка: Python не найден!
    echo Установите Python с https://www.python.org/
    pause
    exit /b 1
)

REM Проверяем наличие виртуального окружения
if exist "venv\Scripts\activate.bat" (
    echo ✅ Виртуальное окружение найдено
    call venv\Scripts\activate.bat
) else (
    echo ⚠️  Виртуальное окружение не найдено, создаем...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Ошибка при создании виртуального окружения
        pause
        exit /b 1
    )
    call venv\Scripts\activate.bat
    echo ✅ Виртуальное окружение создано
)

REM Проверяем наличие requirements.txt
if not exist "requirements.txt" (
    echo ❌ Ошибка: файл requirements.txt не найден!
    pause
    exit /b 1
)

REM Проверяем установлен ли streamlit (как индикатор установленных зависимостей)
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo 📦 Устанавливаем зависимости...
    echo Это может занять несколько минут при первом запуске...
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Ошибка при установке зависимостей
        pause
        exit /b 1
    )
    echo ✅ Зависимости установлены
) else (
    echo ✅ Зависимости уже установлены
)

echo.
echo 📱 Откроется браузер с веб-интерфейсом
echo ⏹️  Для остановки нажмите Ctrl+C
echo.

REM Запускаем приложение
python -m streamlit run app.py

pause

