# AutoCall 1C API Client

## Описание

Простое приложение для тестового запроса к API 1C (получение списка водителей).

## Установка и запуск

1. Создайте виртуальное окружение и активируйте его:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Создайте файл `.env` в корне проекта со следующим содержимым:
   ```env
   LOGIN=ваш_логин
   PASSWORD=ваш_пароль
   ```
4. Запустите приложение:
   ```bash
   python main.py
   ``` 