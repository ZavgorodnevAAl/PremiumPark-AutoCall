@echo off
chcp 65001 >nul
echo 🔄 Обновление Premium Park - Автоматические напоминания...
echo.

REM Переходим в папку с проектом (где находится этот bat-файл)
cd /d "%~dp0"

REM Проверяем наличие git
git --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Ошибка: Git не найден!
    echo Установите Git с https://git-scm.com/
    pause
    exit /b 1
)

REM Проверяем, является ли текущая папка git-репозиторием
if not exist ".git" (
    echo ❌ Ошибка: текущая папка не является git-репозиторием!
    pause
    exit /b 1
)

echo 📥 Выполняем git pull...
echo.

git pull

if errorlevel 1 (
    echo.
    echo ❌ Ошибка при выполнении git pull
    pause
    exit /b 1
) else (
    echo.
    echo ✅ Проект успешно обновлен!
)

pause

