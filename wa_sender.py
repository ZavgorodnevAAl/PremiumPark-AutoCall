#!/usr/bin/env python3
"""
Скрипт для отправки сообщений в WhatsApp через API wappi.pro
"""

import os
import requests
import json
from dotenv import load_dotenv
from typing import Optional

# Загружаем переменные окружения из .env файла
load_dotenv(override=True)

class WhatsAppSender:
    """Класс для отправки сообщений в WhatsApp"""
    
    def __init__(self):
        self.base_url = "https://wappi.pro/api/sync/message/send"
        self.profile_id = os.getenv("PROFILE_ID")
        self.authorization = os.getenv("AUTHORIZATION")
        
        if not self.profile_id:
            raise ValueError("PROFILE_ID не найден в .env файле")
        if not self.authorization:
            raise ValueError("AUTHORIZATION не найден в .env файле")
    
    def send_message(self, recipient: str, body: str) -> dict:
        """
        Отправляет сообщение в WhatsApp
        
        Args:
            recipient (str): Номер телефона получателя (в формате 79990570617)
            body (str): Текст сообщения
            
        Returns:
            dict: Ответ от API
        """
        url = f"{self.base_url}?profile_id={self.profile_id}"
        
        headers = {
            'accept': 'application/json',
            'Authorization': self.authorization,
            'Content-Type': 'application/json'
        }
        
        data = {
            'body': body,
            'recipient': recipient
        }
        
        try:
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при отправке сообщения: {e}")
            return {"error": str(e)}
    
    def send_test_message(self, recipient: str = "79990570617") -> dict:
        """
        Отправляет тестовое сообщение
        
        Args:
            recipient (str): Номер телефона получателя
            
        Returns:
            dict: Ответ от API
        """
        return self.send_message(recipient, "Тестовое сообщение")

def main():
    """Основная функция для демонстрации работы скрипта"""
    try:
        # Создаем экземпляр отправителя
        sender = WhatsAppSender()
        
        print("WhatsApp Sender инициализирован успешно!")
        print(f"Profile ID: {sender.profile_id}")
        print(f"Authorization: {sender.authorization[:20]}...")
        
        # Пример отправки тестового сообщения
        print("\nОтправляем тестовое сообщение...")
        result = sender.send_test_message()
        
        if "error" not in result:
            print("✅ Сообщение отправлено успешно!")
            print(f"Ответ API: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print("❌ Ошибка при отправке сообщения")
            print(f"Детали: {result}")
            
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        print("Убедитесь, что в .env файле указаны PROFILE_ID и AUTHORIZATION")
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")

if __name__ == "__main__":
    main() 