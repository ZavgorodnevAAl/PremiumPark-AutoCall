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
    if response.status_code == 200:
        data = response.json()
        with open('drivers_with_arenda.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print('Результат по аренде сохранён в drivers_with_arenda.json')
        # Фильтруем только водителей со статусом "Работает" и сортируем по SumDZ (долг по аренде)
        fields = [
            'ID', 'FIO', 'BirthDate', 'PhoneNumber', 'PhoneNumber2', 'Email', 'ActualAddress', 'INN', 'OGRN', 'SNILS',
            'PassportSerialNumber', 'PassportDepartmentName', 'PassportIssueDate', 'PassportDepartmentCode', 'PassportRegistrationAddress',
            'DriversLicenseSerialNumber', 'DriversLicenseIssueDate', 'DriversLicenseExpiryDate', 'AccountNumber', 'CorrAccount', 'BIK', 'Bank',
            'Status', 'Balance', 'ExternalCar', 'Car', 'PaymentType', 'QIWIWalletCardNumber', 'PaymentRecipient', 'Comment', 'DriverDateCreate',
            'NameConditionWork', 'DateDZ', 'SumDZ', 'CommentDZ', 'UserNameDZ', 'ConsolidBalancePaused', 'Supervisor', 'KIS_ART_DriverId'
        ]
        filtered = [d for d in data if str(d.get('Status', '')).strip().lower() == 'работает']
        filtered = sorted(filtered, key=lambda d: float(d.get('SumDZ', 0) or 0), reverse=True)
        print('\n--- Топ-10 водителей со статусом "Работает" с наибольшим долгом по аренде (SumDZ) ---')
        for d in filtered[:3]:
            print('\n'.join([f"{field}: {d.get(field, '')}" for field in fields]))
            print('-' * 40)
    else:
        print('Ошибка при получении данных по аренде:', response.text[:200])
except Exception as e:
    print(f'Ошибка при получении данных по аренде: {e}') 