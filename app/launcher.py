#!/usr/bin/env python3
"""
Лаунчер для запуска Streamlit приложения
"""
import subprocess
import sys
import os
import logging

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def main():
    """Запускает Streamlit приложение"""
    # Получаем директорию, где находится скрипт
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(script_dir, 'app.py')
    
    # Проверяем наличие app.py
    if not os.path.exists(app_path):
        logger.error(f"Ошибка: файл app.py не найден в {script_dir}")
        input("\nНажмите Enter для выхода...")
        return
    
    logger.info("Запуск Premium Park - Автоматические напоминания...")
    logger.info("Откроется браузер с веб-интерфейсом")
    logger.info("Для остановки нажмите Ctrl+C\n")
    
    try:
        # Запускаем Streamlit
        subprocess.run([sys.executable, "-m", "streamlit", "run", app_path], check=True)
    except KeyboardInterrupt:
        logger.info("\n\nПриложение остановлено")
    except subprocess.CalledProcessError as e:
        logger.error(f"\nОшибка при запуске: {e}")
        logger.error("\nВозможные причины:")
        logger.error("  - Streamlit не установлен: pip install streamlit")
        logger.error("  - Проблемы с зависимостями: pip install -r requirements.txt")
        input("\nНажмите Enter для выхода...")
    except FileNotFoundError:
        logger.error("\nОшибка: Python не найден!")
        logger.error("Убедитесь, что Python установлен и добавлен в PATH")
        input("\nНажмите Enter для выхода...")
    except Exception as e:
        logger.error(f"\nНеожиданная ошибка: {e}")
        input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()

