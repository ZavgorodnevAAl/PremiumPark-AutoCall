import os
import requests
import json
import base64
from dotenv import load_dotenv

load_dotenv(override=True)

LOGIN = os.getenv('LOGIN')
PASSWORD = os.getenv('PASSWORD')

if not LOGIN or not PASSWORD:
    print('Ошибка: не заданы LOGIN или PASSWORD в .env файле')
    exit(1)

# Создаем заголовок авторизации с правильной кодировкой кириллицы
credentials = f"{LOGIN}:{PASSWORD}"
encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
headers = {
    'Authorization': f'Basic {encoded_credentials}',
    'Content-Type': 'application/json'
}

# Получаем задолженности по аренде через POST /hs/Driver/v1/Get
try:
    url = 'https://1c.0nalog.com:1710/E-Global/hs/Driver/v1/Get'
    response = requests.post(url, headers=headers, json={})
    print(f'POST {url} -> Status code: {response.status_code}')
    ff = []
    c = []
    if response.status_code == 200:
        data = response.json()
        with open('drivers_with_arenda.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print('Результат по аренде сохранён в drivers_with_arenda.json')
        # Печатаем ФИО и баланс водителей с балансом меньше -1000
        print('\n--- Водители с балансом меньше -1000 ---')
        found = False
        for d in data:
            try:
                balance = float(d.get('Balance', 0) or 0)
                is_working = (str(d.get('Status', '')).lower() in ('работает')) and \
                             d.get('NameConditionWork', '') != ''
                skip = 'не блокировать' in d.get('FIO', '').lower() or \
                       'не беспокоить' in d.get('FIO', '').lower()
            except Exception:
                balance = 0
                is_working = False
                skip = True

            if balance < -1000 and is_working and not skip:
                fio = d.get('FIO', '')
                print(f"{fio}: {balance}")
                found = True
        if not found:
            print("Нет водителей с балансом меньше -1000.")
    else:
        print('Ошибка при получении данных по аренде:', response.text[:200])
except Exception as e:
    print(f'Ошибка при получении данных по аренде: {e}') 