#!/usr/bin/env python3
"""
Лаунчер для запуска Streamlit приложения
"""
import subprocess
import sys
import os

def main():
    """Запускает Streamlit приложение"""
    # Получаем директорию, где находится скрипт
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, 'app.py')
    
    # Проверяем наличие app.py
    if not os.path.exists(app_path):
        print(f"❌ Ошибка: файл app.py не найден в {script_dir}")
        input("\nНажмите Enter для выхода...")
        return
    
    print("🚗 Запуск Premium Park - Автоматические напоминания...")
    print("📱 Откроется браузер с веб-интерфейсом")
    print("⏹️  Для остановки нажмите Ctrl+C\n")
    
    try:
        # Запускаем Streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path], check=True)
    except KeyboardInterrupt:
        print("\n\n👋 Приложение остановлено")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка при запуске: {e}")
        print("\nВозможные причины:")
        print("  - Streamlit не установлен: pip install streamlit")
        print("  - Проблемы с зависимостями: pip install -r requirements.txt")
        input("\nНажмите Enter для выхода...")
    except FileNotFoundError:
        print("\n❌ Ошибка: Python не найден!")
        print("Убедитесь, что Python установлен и добавлен в PATH")
        input("\nНажмите Enter для выхода...")
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()

