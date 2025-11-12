#!/bin/bash
echo "🚗 Запуск Premium Park - Автоматические напоминания..."
echo ""

# Проверяем наличие Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Ошибка: Python3 не найден!"
    echo "Установите Python3: sudo apt-get install python3 python3-pip (Ubuntu/Debian)"
    exit 1
fi

# Проверяем наличие виртуального окружения
if [ -f "venv/bin/activate" ]; then
    echo "✅ Виртуальное окружение найдено"
    source venv/bin/activate
else
    echo "⚠️  Виртуальное окружение не найдено, создаем..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при создании виртуального окружения"
        exit 1
    fi
    source venv/bin/activate
    echo "✅ Виртуальное окружение создано"
fi

# Проверяем наличие requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo "❌ Ошибка: файл requirements.txt не найден!"
    exit 1
fi

# Проверяем установлен ли streamlit (как индикатор установленных зависимостей)
python3 -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📦 Устанавливаем зависимости..."
    echo "Это может занять несколько минут при первом запуске..."
    python3 -m pip install --upgrade pip
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "❌ Ошибка при установке зависимостей"
        exit 1
    fi
    echo "✅ Зависимости установлены"
else
    echo "✅ Зависимости уже установлены"
fi

echo ""
echo "📱 Откроется браузер с веб-интерфейсом"
echo "⏹️  Для остановки нажмите Ctrl+C"
echo ""

# Запускаем приложение
python3 -m streamlit run app.py

