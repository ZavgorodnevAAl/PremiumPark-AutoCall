#!/usr/bin/env python3
"""
Простой скрипт для отправки WhatsApp сообщений
"""

import os
import requests
import json
from dotenv import load_dotenv
import time

# Загружаем переменные окружения
# Ищем .env в текущей директории (app)
env_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)  # Fallback на поиск в текущей директории

def send_whatsapp_message(recipient: str, message: str):
    """
    Отправляет сообщение в WhatsApp
    
    Args:
        recipient (str): Номер телефона получателя
        message (str): Текст сообщения
    """
    # Получаем данные из .env
    profile_id = os.getenv("PROFILE_ID")
    authorization = os.getenv("AUTHORIZATION")
    print(profile_id, authorization)
    
    if not profile_id or not authorization:
        print("""❌ Ошибка: PROFILE_ID или AUTHORIZATION не найдены в .env файле
        Создайте файл .env с содержимым:
        PROFILE_ID=ваш_profile_id
        AUTHORIZATION=ваш_токен_авторизации
        """)
        return
    
    # URL для API
    url = f"https://wappi.pro/api/sync/message/send?profile_id={profile_id}"
    
    # Заголовки запроса
    headers = {
        'accept': 'application/json',
        'Authorization': authorization,
        'Content-Type': 'application/json'
    }
    
    # Данные для отправки
    data = {
        'body': message,
        'recipient': recipient
    }
    
    try:
        print(f"📤 Отправляем сообщение на номер {recipient}...")
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print("✅ Сообщение отправлено успешно!")
            result = response.json()
            print(f"Ответ API: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ Ошибка API: {response.status_code}")
            print(f"Ответ: {response.text}")
            
    except Exception as e:
        print(f"❌ Ошибка при отправке: {e}")

if __name__ == "__main__":
    # Пример использования
    recipient = "79990000000"  # Замените на реальный номер
    message = "Тестовое сообщение от системы Premium Park"
    send_whatsapp_message(recipient, message)