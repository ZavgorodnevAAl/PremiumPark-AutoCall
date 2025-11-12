#!/usr/bin/env python3
"""
Интерактивная настройка .env файла
"""
import os
import sys

def check_env_exists():
    """Проверяет существование .env файла"""
    return os.path.exists('.env')

def load_env():
    """Загружает существующие значения из .env"""
    env_vars = {}
    if check_env_exists():
        try:
            with open('.env', 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception:
            pass
    return env_vars

def save_env(env_vars):
    """Сохраняет переменные в .env файл"""
    try:
        with open('.env', 'w', encoding='utf-8') as f:
            f.write("# Настройки для API 1C\n")
            f.write(f"LOGIN={env_vars.get('LOGIN', '')}\n")
            f.write(f"PASSWORD={env_vars.get('PASSWORD', '')}\n")
            f.write("\n")
            f.write("# Настройки для WhatsApp API (wappi.pro)\n")
            f.write(f"PROFILE_ID={env_vars.get('PROFILE_ID', '')}\n")
            f.write(f"AUTHORIZATION={env_vars.get('AUTHORIZATION', '')}\n")
            f.write("\n")
            f.write("# Опционально: тестовый номер для тестовой отправки\n")
            f.write(f"TEST_PHONE={env_vars.get('TEST_PHONE', '')}\n")
        return True
    except Exception as e:
        print(f"❌ Ошибка при сохранении .env: {e}")
        return False

def is_env_complete(env_vars):
    """Проверяет, заполнены ли обязательные поля"""
    required = ['LOGIN', 'PASSWORD', 'PROFILE_ID', 'AUTHORIZATION']
    return all(env_vars.get(key) for key in required)

def setup_env_interactive():
    """Интерактивная настройка .env"""
    print("\n" + "="*60)
    print("⚙️  Настройка переменных окружения (.env)")
    print("="*60)
    print("\nЗаполните следующие данные:\n")
    
    env_vars = load_env()
    
    # Данные для API 1C
    print("📋 Данные для API 1C:")
    print("-" * 60)
    
    current_login = env_vars.get('LOGIN', '')
    if current_login:
        login = input(f"Логин для API 1C [{current_login}]: ").strip()
        if not login:
            login = current_login
    else:
        login = input("Логин для API 1C: ").strip()
    env_vars['LOGIN'] = login
    
    current_password = env_vars.get('PASSWORD', '')
    if current_password:
        password = input(f"Пароль для API 1C [***]: ").strip()
        if not password:
            password = current_password
    else:
        password = input("Пароль для API 1C: ").strip()
    env_vars['PASSWORD'] = password
    
    print()
    
    # Данные для WhatsApp API
    print("📱 Данные для WhatsApp API (wappi.pro):")
    print("-" * 60)
    
    current_profile_id = env_vars.get('PROFILE_ID', '')
    if current_profile_id:
        profile_id = input(f"PROFILE_ID [{current_profile_id}]: ").strip()
        if not profile_id:
            profile_id = current_profile_id
    else:
        profile_id = input("PROFILE_ID: ").strip()
    env_vars['PROFILE_ID'] = profile_id
    
    current_authorization = env_vars.get('AUTHORIZATION', '')
    if current_authorization:
        authorization = input(f"AUTHORIZATION [***]: ").strip()
        if not authorization:
            authorization = current_authorization
    else:
        authorization = input("AUTHORIZATION (токен): ").strip()
    env_vars['AUTHORIZATION'] = authorization
    
    print()
    
    # Тестовый номер (опционально)
    print("🧪 Тестовый номер (опционально):")
    print("-" * 60)
    
    current_test_phone = env_vars.get('TEST_PHONE', '')
    if current_test_phone:
        test_phone = input(f"TEST_PHONE [{current_test_phone}]: ").strip()
        if not test_phone:
            test_phone = current_test_phone
    else:
        test_phone = input("TEST_PHONE (можно оставить пустым): ").strip()
    env_vars['TEST_PHONE'] = test_phone
    
    print()
    
    # Проверка обязательных полей
    if not is_env_complete(env_vars):
        print("⚠️  Внимание: не все обязательные поля заполнены!")
        print("Обязательные поля: LOGIN, PASSWORD, PROFILE_ID, AUTHORIZATION")
        response = input("\nПродолжить сохранение? (y/n): ").strip().lower()
        if response != 'y':
            print("❌ Отменено")
            return False
    
    # Сохранение
    if save_env(env_vars):
        print("\n✅ Файл .env успешно сохранен!")
        return True
    else:
        print("\n❌ Ошибка при сохранении .env")
        return False

def main():
    """Главная функция"""
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        # Режим проверки - возвращаем код выхода
        env_vars = load_env()
        if is_env_complete(env_vars):
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        # Интерактивный режим
        setup_env_interactive()

if __name__ == "__main__":
    main()

