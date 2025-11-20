#!/usr/bin/env python3
"""
Автоматическая отправка напоминаний о задолженности по аренде авто через WhatsApp
"""

import os
import requests
import json
import base64
from dotenv import load_dotenv
import schedule
import time
from datetime import datetime
import sys

# Загружаем переменные окружения
# Ищем .env в текущей директории (app)
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)  # Fallback на поиск в текущей директории

# Настройки для API 1C
LOGIN = os.getenv('LOGIN')
PASSWORD = os.getenv('PASSWORD')

# Настройки для WhatsApp API
PROFILE_ID = os.getenv("PROFILE_ID")
AUTHORIZATION = os.getenv("AUTHORIZATION")

# Тестовый номер для тестовой функции
TEST_PHONE = os.getenv("TEST_PHONE", "")

if not LOGIN or not PASSWORD:
    print('❌ Ошибка: не заданы LOGIN или PASSWORD в .env файле')
    sys.exit(1)

if not PROFILE_ID or not AUTHORIZATION:
    print('❌ Ошибка: не заданы PROFILE_ID или AUTHORIZATION в .env файле')
    sys.exit(1)


def normalize_phone(phone: str) -> str:
    """
    Нормализует номер телефона для отправки в WhatsApp
    Убирает + и пробелы, оставляет только цифры
    """
    if not phone:
        return ""
    # Убираем все нецифровые символы кроме первой цифры
    phone_clean = ''.join(filter(str.isdigit, phone))
    return phone_clean


def get_drivers():
    """
    Получает список водителей из API 1C
    
    Returns:
        list: Список водителей с их данными
    """
    credentials = f"{LOGIN}:{PASSWORD}"
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    headers = {
        'Authorization': f'Basic {encoded_credentials}',
        'Content-Type': 'application/json'
    }
    
    url = 'https://1c.0nalog.com:1710/E-Global/hs/Driver/v1/Get'
    
    try:
        response = requests.post(url, headers=headers, json={}, timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f'❌ Ошибка при получении данных: {response.status_code}')
            print(f'Ответ: {response.text[:200]}')
            return []
    except Exception as e:
        print(f'❌ Ошибка при получении данных: {e}')
        return []


def filter_drivers(drivers, balance_threshold: float):
    """
    Фильтрует водителей по балансу и статусу, исключая черный список
    
    Args:
        drivers: Список водителей
        balance_threshold: Порог баланса (например, 0 или -500)
    
    Returns:
        list: Отфильтрованный список водителей
    """
    filtered = []
    blacklist_phones = get_blacklist_phones()
    
    for driver in drivers:
        try:
            balance = float(driver.get('Balance', 0) or 0)
            is_working = (str(driver.get('Status', '')).lower() == 'работает') and \
                        driver.get('NameConditionWork', '') != ''
            skip = 'не блокировать' in driver.get('FIO', '').lower() or \
                   'не беспокоить' in driver.get('FIO', '').lower()
            phone = driver.get('PhoneNumber', '')
            phone_normalized = normalize_phone(phone)
            
            # Проверяем, не в черном списке ли номер
            in_blacklist = phone_normalized in blacklist_phones
            
            if balance < balance_threshold and is_working and not skip and phone and not in_blacklist:
                filtered.append({
                    'fio': driver.get('FIO', ''),
                    'balance': balance,
                    'phone': phone_normalized
                })
        except Exception:
            continue
    
    return filtered


def send_whatsapp_message(recipient: str, message: str) -> bool:
    """
    Отправляет сообщение в WhatsApp
    
    Args:
        recipient (str): Номер телефона получателя (без +)
        message (str): Текст сообщения
    
    Returns:
        bool: True если сообщение отправлено успешно
    """
    if not recipient:
        print("❌ Номер получателя не указан")
        return False
    
    url = f"https://wappi.pro/api/sync/message/send?profile_id={PROFILE_ID}"
    
    headers = {
        'accept': 'application/json',
        'Authorization': AUTHORIZATION,
        'Content-Type': 'application/json'
    }
    
    data = {
        'body': message,
        'recipient': recipient
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            print(f"✅ Сообщение отправлено на {recipient}")
            return True
        else:
            print(f"❌ Ошибка API для {recipient}: {response.status_code}")
            print(f"Ответ: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при отправке на {recipient}: {e}")
        return False


def load_messages():
    """
    Загружает шаблоны сообщений из файла. Если файл не существует, создает его со стандартными значениями.
    
    Returns:
        dict: Словарь с шаблонами сообщений
    """
    messages_file = os.path.join(os.path.dirname(__file__), 'messages.json')
    
    # Стандартные шаблоны сообщений
    default_messages = {
        "morning": "Добрый день! Напоминаем про оплату аренды авто до 13:00, в случае просрочки платежа будет начислен штраф в размере 5% от суммы задолжености (ШТРАФ НАЧИСЛЯЕТСЯ АВТОМАТИЧЕСКИ), также после 15:00 система заблокирует автомобиль!",
        "weekday_afternoon": "Добрый день! Необходимо срочно закрыть долг по аренде авто. В противном случае с 15:00, авто будет заблокирован!  Приносим свои извинения, если Вы уже произвели оплату.\n\nС уважением, Команда автопроката \"Premium Park\"\n\nтелефон для связи 89242320999",
        "weekend_afternoon": "Добрый день! Необходимо срочно закрыть долг по аренде авто до 13:30 или авто будет заблокирован! Разблокировка авто возможна только до 16:30 в субботу и воскресенье, т.е. в рабочее время в выходные дни.  Приносим свои извинения, если Вы уже произвели оплату.\n\nС уважением, Команда автопроката \"Premium Park\"\n\nВ выходные дни вы можете звонить в отдел дебиторской задолженности по телефону +79241335400"
    }
    
    # Если файл не существует, создаем его со стандартными значениями
    if not os.path.exists(messages_file):
        try:
            with open(messages_file, 'w', encoding='utf-8') as f:
                json.dump(default_messages, f, ensure_ascii=False, indent=2)
            print(f"✅ Создан файл шаблонов сообщений {messages_file} со стандартными значениями")
        except Exception as e:
            print(f"❌ Ошибка при создании файла шаблонов сообщений: {e}")
            return default_messages
    
    # Загружаем шаблоны из файла
    try:
        with open(messages_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Ошибка при загрузке шаблонов сообщений: {e}")
        # Возвращаем шаблоны по умолчанию
        return default_messages


def load_settings():
    """
    Загружает настройки из файла. Если файл не существует, создает его со стандартными значениями.
    
    Returns:
        dict: Словарь с настройками
    """
    settings_file = os.path.join(os.path.dirname(__file__), 'settings.json')
    
    # Стандартные настройки
    default_settings = {
        "morning_balance_threshold": 0,
        "afternoon_balance_threshold": -500,
        "morning_time": "09:00",
        "afternoon_time": "13:00",
        "morning_days": [0, 1, 2, 3, 4, 5, 6],  # Все дни недели (0=понедельник, 6=воскресенье)
        "weekday_afternoon_days": [0, 1, 2, 3, 4],  # Понедельник-пятница
        "weekend_afternoon_days": [5, 6]  # Суббота-воскресенье
    }
    
    # Если файл не существует, создаем его со стандартными значениями
    if not os.path.exists(settings_file):
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(default_settings, f, ensure_ascii=False, indent=2)
            print(f"✅ Создан файл настроек {settings_file} со стандартными значениями")
        except Exception as e:
            print(f"❌ Ошибка при создании файла настроек: {e}")
            return default_settings
    
    # Загружаем настройки из файла
    try:
        with open(settings_file, 'r', encoding='utf-8') as f:
            loaded_settings = json.load(f)
            # Добавляем недостающие поля из дефолтных настроек
            for key, value in default_settings.items():
                if key not in loaded_settings:
                    loaded_settings[key] = value
            return loaded_settings
    except Exception as e:
        print(f"❌ Ошибка при загрузке настроек: {e}")
        # Возвращаем настройки по умолчанию
        return default_settings


def load_blacklist():
    """
    Загружает черный список из файла
    
    Returns:
        list: Список объектов {'phone': str, 'fio': str} или список номеров (для обратной совместимости)
    """
    blacklist_file = os.path.join(os.path.dirname(__file__), 'blacklist.json')
    try:
        with open(blacklist_file, 'r', encoding='utf-8') as f:
            blacklist = json.load(f)
            result = []
            for item in blacklist:
                if isinstance(item, dict):
                    # Новая структура: {'phone': '...', 'fio': '...'}
                    if 'phone' in item:
                        result.append({
                            'phone': normalize_phone(item['phone']),
                            'fio': item.get('fio', 'Неизвестно')
                        })
                elif isinstance(item, str):
                    # Старая структура: просто номер (для обратной совместимости)
                    phone = normalize_phone(item)
                    if phone:
                        result.append({
                            'phone': phone,
                            'fio': 'Неизвестно'
                        })
            return result
    except Exception as e:
        print(f"❌ Ошибка при загрузке черного списка: {e}")
        return []


def get_blacklist_phones():
    """
    Возвращает только список номеров телефонов из черного списка (для фильтрации)
    
    Returns:
        list: Список нормализованных номеров телефонов
    """
    blacklist = load_blacklist()
    return [item['phone'] if isinstance(item, dict) else item for item in blacklist]


def send_morning_reminder():
    """
    Отправляет утреннее напоминание водителям с балансом меньше порога
    """
    try:
        settings = load_settings()
        threshold = float(settings.get("morning_balance_threshold", 0))
        
        print(f"\n{'='*60}")
        print(f"🌅 Утреннее напоминание - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        drivers = get_drivers()
        if not drivers:
            print("❌ Не удалось получить данные о водителях")
            return
        
        filtered_drivers = filter_drivers(drivers, balance_threshold=threshold)
        
        if not filtered_drivers:
            print(f"✅ Нет водителей с балансом < {threshold}")
            return
        
        messages = load_messages()
        message = messages.get("morning", "")
        
        print(f"📤 Отправляем сообщения {len(filtered_drivers)} водителям (баланс < {threshold})...")
        for driver in filtered_drivers:
            try:
                print(f"  → {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']}")
                send_whatsapp_message(driver['phone'], message)
                time.sleep(1)  # Небольшая задержка между отправками
            except Exception as e:
                print(f"  ❌ Ошибка при отправке {driver['fio']}: {e}")
                continue  # Продолжаем отправку остальным
        
        print(f"✅ Утреннее напоминание завершено\n")
    except Exception as e:
        print(f"❌ Критическая ошибка в send_morning_reminder: {e}")
        import traceback
        traceback.print_exc()


def send_weekday_afternoon_reminder():
    """
    Отправляет напоминание в 13:00 в будние дни водителям с балансом меньше порога
    """
    try:
        settings = load_settings()
        threshold = float(settings.get("afternoon_balance_threshold", -500))
        
        print(f"\n{'='*60}")
        print(f"📅 Напоминание в будний день - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        drivers = get_drivers()
        if not drivers:
            print("❌ Не удалось получить данные о водителях")
            return
        
        filtered_drivers = filter_drivers(drivers, balance_threshold=threshold)
        
        if not filtered_drivers:
            print(f"✅ Нет водителей с балансом < {threshold}")
            return
        
        messages = load_messages()
        message = messages.get("weekday_afternoon", "")
        
        print(f"📤 Отправляем сообщения {len(filtered_drivers)} водителям (баланс < {threshold})...")
        for driver in filtered_drivers:
            try:
                print(f"  → {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']}")
                send_whatsapp_message(driver['phone'], message)
                time.sleep(1)
            except Exception as e:
                print(f"  ❌ Ошибка при отправке {driver['fio']}: {e}")
                continue  # Продолжаем отправку остальным
        
        print(f"✅ Напоминание в будний день завершено\n")
    except Exception as e:
        print(f"❌ Критическая ошибка в send_weekday_afternoon_reminder: {e}")
        import traceback
        traceback.print_exc()


def send_weekend_afternoon_reminder():
    """
    Отправляет напоминание в обед по выходным водителям с балансом меньше порога
    """
    try:
        settings = load_settings()
        threshold = float(settings.get("afternoon_balance_threshold", -500))
        
        print(f"\n{'='*60}")
        print(f"🏖️ Напоминание в выходной день - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        drivers = get_drivers()
        if not drivers:
            print("❌ Не удалось получить данные о водителях")
            return
        
        filtered_drivers = filter_drivers(drivers, balance_threshold=threshold)
        
        if not filtered_drivers:
            print(f"✅ Нет водителей с балансом < {threshold}")
            return
        
        messages = load_messages()
        message = messages.get("weekend_afternoon", "")
        
        print(f"📤 Отправляем сообщения {len(filtered_drivers)} водителям (баланс < {threshold})...")
        for driver in filtered_drivers:
            try:
                print(f"  → {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']}")
                send_whatsapp_message(driver['phone'], message)
                time.sleep(1)
            except Exception as e:
                print(f"  ❌ Ошибка при отправке {driver['fio']}: {e}")
                continue  # Продолжаем отправку остальным
        
        print(f"✅ Напоминание в выходной день завершено\n")
    except Exception as e:
        print(f"❌ Критическая ошибка в send_weekend_afternoon_reminder: {e}")
        import traceback
        traceback.print_exc()


def get_morning_recipients():
    """
    Возвращает список получателей для утреннего напоминания (без отправки)
    
    Returns:
        list: Список словарей с данными водителей {'fio': str, 'phone': str, 'balance': float}
    """
    try:
        settings = load_settings()
        threshold = float(settings.get("morning_balance_threshold", 0))
        
        drivers = get_drivers()
        if not drivers:
            return []
        
        filtered_drivers = filter_drivers(drivers, balance_threshold=threshold)
        return filtered_drivers
    except Exception as e:
        print(f"❌ Ошибка при получении списка получателей утреннего напоминания: {e}")
        return []


def get_weekday_afternoon_recipients():
    """
    Возвращает список получателей для напоминания в будний день (без отправки)
    
    Returns:
        list: Список словарей с данными водителей {'fio': str, 'phone': str, 'balance': float}
    """
    try:
        settings = load_settings()
        threshold = float(settings.get("afternoon_balance_threshold", -500))
        
        drivers = get_drivers()
        if not drivers:
            return []
        
        filtered_drivers = filter_drivers(drivers, balance_threshold=threshold)
        return filtered_drivers
    except Exception as e:
        print(f"❌ Ошибка при получении списка получателей напоминания в будний день: {e}")
        return []


def get_weekend_afternoon_recipients():
    """
    Возвращает список получателей для напоминания в выходной день (без отправки)
    
    Returns:
        list: Список словарей с данными водителей {'fio': str, 'phone': str, 'balance': float}
    """
    try:
        settings = load_settings()
        threshold = float(settings.get("afternoon_balance_threshold", -500))
        
        drivers = get_drivers()
        if not drivers:
            return []
        
        filtered_drivers = filter_drivers(drivers, balance_threshold=threshold)
        return filtered_drivers
    except Exception as e:
        print(f"❌ Ошибка при получении списка получателей напоминания в выходной день: {e}")
        return []


def get_filtered_drivers_info(balance_threshold: float):
    """
    Возвращает информацию об отфильтрованных водителях с указанием причин исключения
    
    Args:
        balance_threshold: Порог баланса
    
    Returns:
        dict: Словарь с категориями отфильтрованных водителей:
            - 'blacklist': водители в черном списке
            - 'not_working': водители не работают
            - 'skip_flag': водители с пометкой "не блокировать" или "не беспокоить"
            - 'no_phone': водители без телефона
    """
    try:
        drivers = get_drivers()
        if not drivers:
            return {
                'blacklist': [],
                'not_working': [],
                'skip_flag': [],
                'no_phone': []
            }
        
        blacklist_phones = get_blacklist_phones()
        filtered_info = {
            'blacklist': [],
            'not_working': [],
            'skip_flag': [],
            'no_phone': []
        }
        
        for driver in drivers:
            try:
                balance = float(driver.get('Balance', 0) or 0)
                
                # Проверяем только водителей с балансом меньше порога
                if balance >= balance_threshold:
                    continue
                
                fio = driver.get('FIO', '')
                phone = driver.get('PhoneNumber', '')
                phone_normalized = normalize_phone(phone) if phone else ''
                is_working = (str(driver.get('Status', '')).lower() == 'работает') and \
                            driver.get('NameConditionWork', '') != ''
                skip = 'не блокировать' in fio.lower() or 'не беспокоить' in fio.lower()
                
                # Категоризируем причины исключения
                if phone_normalized and phone_normalized in blacklist_phones:
                    filtered_info['blacklist'].append({
                        'fio': fio,
                        'phone': phone_normalized,
                        'balance': balance
                    })
                elif not phone or not phone_normalized:
                    filtered_info['no_phone'].append({
                        'fio': fio,
                        'phone': phone or 'Нет телефона',
                        'balance': balance
                    })
                elif skip:
                    filtered_info['skip_flag'].append({
                        'fio': fio,
                        'phone': phone_normalized,
                        'balance': balance
                    })
                elif not is_working:
                    filtered_info['not_working'].append({
                        'fio': fio,
                        'phone': phone_normalized,
                        'balance': balance,
                        'status': driver.get('Status', 'Неизвестно')
                    })
            except Exception:
                continue
        
        return filtered_info
    except Exception as e:
        print(f"❌ Ошибка при получении информации об отфильтрованных водителях: {e}")
        return {
            'blacklist': [],
            'not_working': [],
            'skip_flag': [],
            'no_phone': []
        }


def send_test_message(phone: str = None):
    """
    Тестовая функция для отправки сообщения на указанный номер
    
    Args:
        phone (str): Номер телефона для теста (если не указан, берется из .env)
    """
    if not phone:
        phone = TEST_PHONE
    
    if not phone:
        print("❌ Не указан номер телефона для теста")
        print("   Укажите номер в параметре функции или в .env как TEST_PHONE")
        return
    
    phone_normalized = normalize_phone(phone)
    
    message = "Тестовое сообщение от системы автоматических напоминаний Premium Park"
    
    print(f"\n{'='*60}")
    print(f"🧪 Тестовая отправка - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"📤 Отправляем тестовое сообщение на {phone_normalized}...")
    
    if send_whatsapp_message(phone_normalized, message):
        print("✅ Тестовое сообщение отправлено успешно!")
    else:
        print("❌ Ошибка при отправке тестового сообщения")
    print()


def setup_scheduler():
    """
    Настраивает планировщик задач
    """
    schedule.clear()
    
    # Загружаем настройки времени и дней
    settings = load_settings()
    morning_time = settings.get("morning_time", "09:00")
    afternoon_time = settings.get("afternoon_time", "13:00")
    
    # Получаем выбранные дни недели (0=понедельник, 6=воскресенье)
    morning_days = settings.get("morning_days", [0, 1, 2, 3, 4, 5, 6])
    weekday_afternoon_days = settings.get("weekday_afternoon_days", [0, 1, 2, 3, 4])
    weekend_afternoon_days = settings.get("weekend_afternoon_days", [5, 6])
    
    # Маппинг дней недели на методы schedule
    day_mapping = {
        0: schedule.every().monday,
        1: schedule.every().tuesday,
        2: schedule.every().wednesday,
        3: schedule.every().thursday,
        4: schedule.every().friday,
        5: schedule.every().saturday,
        6: schedule.every().sunday
    }
    
    day_names = {
        0: "понедельник",
        1: "вторник",
        2: "среда",
        3: "четверг",
        4: "пятница",
        5: "суббота",
        6: "воскресенье"
    }
    
    # Настраиваем утренние напоминания для выбранных дней
    for day in morning_days:
        if day in day_mapping:
            day_mapping[day].at(morning_time).do(send_morning_reminder)
    
    # Настраиваем дневные напоминания для будних дней
    for day in weekday_afternoon_days:
        if day in day_mapping:
            day_mapping[day].at(afternoon_time).do(send_weekday_afternoon_reminder)
    
    # Настраиваем дневные напоминания для выходных дней
    for day in weekend_afternoon_days:
        if day in day_mapping:
            day_mapping[day].at(afternoon_time).do(send_weekend_afternoon_reminder)
    
    # Формируем строки для вывода
    morning_days_str = ", ".join([day_names.get(d, str(d)) for d in sorted(morning_days)])
    weekday_days_str = ", ".join([day_names.get(d, str(d)) for d in sorted(weekday_afternoon_days)])
    weekend_days_str = ", ".join([day_names.get(d, str(d)) for d in sorted(weekend_afternoon_days)])
    
    print("✅ Планировщик задач настроен:")
    print(f"   - Утреннее напоминание: {morning_days_str} в {morning_time} (баланс < {settings.get('morning_balance_threshold', 0)})")
    print(f"   - Напоминание в будни: {weekday_days_str} в {afternoon_time} (баланс < {settings.get('afternoon_balance_threshold', -500)})")
    print(f"   - Напоминание в выходные: {weekend_days_str} в {afternoon_time} (баланс < {settings.get('afternoon_balance_threshold', -500)})")


def main():
    """
    Главная функция - запускает планировщик или выполняет тестовую отправку
    """
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "test":
            # Тестовая отправка
            phone = sys.argv[2] if len(sys.argv) > 2 else None
            send_test_message(phone)
            return
        elif command == "morning":
            # Ручной запуск утреннего напоминания
            send_morning_reminder()
            return
        elif command == "weekday":
            # Ручной запуск напоминания в будний день
            send_weekday_afternoon_reminder()
            return
        elif command == "weekend":
            # Ручной запуск напоминания в выходной день
            send_weekend_afternoon_reminder()
            return
        elif command == "help":
            print("""
Использование:
  python main.py              - Запуск планировщика задач
  python main.py test [номер] - Отправка тестового сообщения
  python main.py morning      - Ручной запуск утреннего напоминания
  python main.py weekday      - Ручной запуск напоминания в будний день
  python main.py weekend      - Ручной запуск напоминания в выходной день
  python main.py help         - Показать эту справку
            """)
            return
    
    # Запуск планировщика
    setup_scheduler()
    print(f"\n🔄 Планировщик запущен. Ожидание задач...")
    print(f"   Текущее время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Для остановки нажмите Ctrl+C\n")
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту
    except KeyboardInterrupt:
        print("\n\n👋 Планировщик остановлен")


if __name__ == "__main__":
    main()
