#!/usr/bin/env python3
"""
Скрипт для создания .exe файла из приложения
Требует установки: pip install pyinstaller
"""
import subprocess
import sys
import os
import platform
import logging

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def build_exe():
    """Создает .exe файл с помощью PyInstaller"""
    logger.info("Начинаем сборку .exe файла...")
    logger.info("Убедитесь, что установлен PyInstaller: pip install pyinstaller\n")
    
    # Определяем разделитель для --add-data в зависимости от ОС
    sep = ";" if platform.system() == "Windows" else ":"
    
    # Команда для PyInstaller
    cmd = [
        "pyinstaller",
        "--name=PremiumPark",
        "--onefile",
        # "--windowed",  # Раскомментируйте для скрытия консоли (но лучше оставить для отладки)
        f"--add-data=messages.json{sep}.",
        f"--add-data=settings.json{sep}.",
        f"--add-data=blacklist.json{sep}.",
        "--hidden-import=streamlit",
        "--hidden-import=streamlit.web.cli",
        "--hidden-import=streamlit.runtime.scriptrunner",
        "--hidden-import=streamlit.runtime.server",
        "--hidden-import=streamlit.runtime.state",
        "--hidden-import=streamlit.web.server",
        "--collect-all=streamlit",
        "launcher.py"
    ]
    
    logger.info("Выполняется команда:")
    logger.info(" ".join(cmd))
    logger.info("")
    
    try:
        subprocess.run(cmd, check=True)
        logger.info("\nСборка завершена!")
        logger.info(".exe файл находится в папке dist/PremiumPark.exe")
        logger.info("\nВАЖНО:")
        logger.info("   - Файлы messages.json и settings.json должны быть рядом с .exe")
        logger.info("   - Файл .env должен быть рядом с .exe")
        logger.info("   - При первом запуске может потребоваться время на инициализацию")
        logger.info("   - Размер .exe файла может быть большим (100+ МБ) из-за включения всех зависимостей")
    except subprocess.CalledProcessError as e:
        logger.error(f"\nОшибка при сборке: {e}")
        logger.error("\nПопробуйте установить PyInstaller:")
        logger.error("  pip install pyinstaller")
    except FileNotFoundError:
        logger.error("\nPyInstaller не найден!")
        logger.error("Установите его командой:")
        logger.error("  pip install pyinstaller")

if __name__ == "__main__":
    build_exe()

