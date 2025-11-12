#!/usr/bin/env python3
"""
Скрипт для создания .exe файла из приложения
Требует установки: pip install pyinstaller
"""
import subprocess
import sys
import os
import platform

def build_exe():
    """Создает .exe файл с помощью PyInstaller"""
    print("🔨 Начинаем сборку .exe файла...")
    print("⚠️  Убедитесь, что установлен PyInstaller: pip install pyinstaller\n")
    
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
    
    print("Выполняется команда:")
    print(" ".join(cmd))
    print()
    
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ Сборка завершена!")
        print("📦 .exe файл находится в папке dist/PremiumPark.exe")
        print("\n⚠️  ВАЖНО:")
        print("   - Файлы messages.json и settings.json должны быть рядом с .exe")
        print("   - Файл .env должен быть рядом с .exe")
        print("   - При первом запуске может потребоваться время на инициализацию")
        print("   - Размер .exe файла может быть большим (100+ МБ) из-за включения всех зависимостей")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка при сборке: {e}")
        print("\nПопробуйте установить PyInstaller:")
        print("  pip install pyinstaller")
    except FileNotFoundError:
        print("\n❌ PyInstaller не найден!")
        print("Установите его командой:")
        print("  pip install pyinstaller")

if __name__ == "__main__":
    build_exe()

