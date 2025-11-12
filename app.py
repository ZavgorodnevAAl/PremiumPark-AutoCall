#!/usr/bin/env python3
"""
Веб-интерфейс для управления автоматической отправкой напоминаний
"""

import streamlit as st
import json
import os
import threading
import time
from datetime import datetime
import schedule
from main import (
    send_morning_reminder,
    send_weekday_afternoon_reminder,
    send_weekend_afternoon_reminder,
    send_test_message,
    send_whatsapp_message,
    normalize_phone,
    load_messages,
    load_settings,
    load_blacklist,
    get_drivers,
    filter_drivers
)

# Настройка страницы
st.set_page_config(
    page_title="Premium Park - Автоматические напоминания",
    page_icon="🚗",
    layout="wide"
)

# Инициализация session state
if 'scheduler_running' not in st.session_state:
    st.session_state.scheduler_running = False
if 'scheduler_thread' not in st.session_state:
    st.session_state.scheduler_thread = None
if 'messages_saved' not in st.session_state:
    st.session_state.messages_saved = False
if 'settings_saved' not in st.session_state:
    st.session_state.settings_saved = False
if 'blacklist_updated' not in st.session_state:
    st.session_state.blacklist_updated = False


def save_messages(messages_dict):
    """Сохраняет шаблоны сообщений в файл"""
    messages_file = os.path.join(os.path.dirname(__file__), 'messages.json')
    try:
        with open(messages_file, 'w', encoding='utf-8') as f:
            json.dump(messages_dict, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Ошибка при сохранении: {e}")
        return False


def save_settings(settings_dict):
    """Сохраняет настройки в файл"""
    settings_file = os.path.join(os.path.dirname(__file__), 'settings.json')
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(settings_dict, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Ошибка при сохранении: {e}")
        return False


def save_blacklist(blacklist_list):
    """Сохраняет черный список в файл"""
    blacklist_file = os.path.join(os.path.dirname(__file__), 'blacklist.json')
    try:
        with open(blacklist_file, 'w', encoding='utf-8') as f:
            json.dump(blacklist_list, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Ошибка при сохранении: {e}")
        return False


def setup_schedule():
    """Настраивает расписание задач"""
    schedule.clear()
    schedule.every().day.at("09:00").do(send_morning_reminder)
    schedule.every().monday.at("13:00").do(send_weekday_afternoon_reminder)
    schedule.every().tuesday.at("13:00").do(send_weekday_afternoon_reminder)
    schedule.every().wednesday.at("13:00").do(send_weekday_afternoon_reminder)
    schedule.every().thursday.at("13:00").do(send_weekday_afternoon_reminder)
    schedule.every().friday.at("13:00").do(send_weekday_afternoon_reminder)
    schedule.every().saturday.at("13:00").do(send_weekend_afternoon_reminder)
    schedule.every().sunday.at("13:00").do(send_weekend_afternoon_reminder)


def run_scheduler():
    """Запускает планировщик в отдельном потоке"""
    setup_schedule()
    
    while st.session_state.scheduler_running:
        schedule.run_pending()
        time.sleep(60)


def start_scheduler():
    """Запускает планировщик"""
    if not st.session_state.scheduler_running:
        st.session_state.scheduler_running = True
        st.session_state.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        st.session_state.scheduler_thread.start()
        st.success("✅ Планировщик запущен!")
        st.rerun()


def stop_scheduler():
    """Останавливает планировщик"""
    if st.session_state.scheduler_running:
        st.session_state.scheduler_running = False
        schedule.clear()
        st.success("⏹️ Планировщик остановлен!")
        st.rerun()


# Заголовок
st.title("🚗 Premium Park - Автоматические напоминания")
st.markdown("---")

# Боковая панель с навигацией
st.sidebar.title("📋 Меню")
page = st.sidebar.radio(
    "Выберите раздел:",
    ["Главная", "Отправка рассылок", "Тестовая отправка", "Редактор шаблонов", "Настройки", "Черный список", "Статус планировщика"]
)

# Главная страница
if page == "Главная":
    st.header("Добро пожаловать!")
    st.markdown("""
    ### Возможности системы:
    
    - ✅ **Автоматическая отправка напоминаний** по расписанию
    - 📤 **Ручная отправка рассылок** в любое время
    - 🧪 **Тестовая отправка** на указанный номер
    - ✏️ **Редактирование шаблонов** сообщений
    
    ### Расписание автоматических рассылок:
    
    - **Утреннее напоминание**: Каждый день в 09:00 (баланс < 0)
    - **Напоминание в будни**: Понедельник-Пятница в 13:00 (баланс < -500)
    - **Напоминание в выходные**: Суббота-Воскресенье в 13:00 (баланс < -500)
    
    ### Как использовать:
    
    1. Перейдите в раздел **"Статус планировщика"** для запуска автоматических рассылок
    2. Используйте **"Отправка рассылок"** для ручной отправки
    3. Редактируйте шаблоны сообщений в разделе **"Редактор шаблонов"**
    """)

# Статус планировщика
elif page == "Статус планировщика":
    st.header("⚙️ Управление планировщиком")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ Запустить планировщик", type="primary", use_container_width=True):
            start_scheduler()
    
    with col2:
        if st.button("⏹️ Остановить планировщик", use_container_width=True):
            stop_scheduler()
    
    st.markdown("---")
    
    # Статус
    if st.session_state.scheduler_running:
        st.success("🟢 Планировщик работает")
        st.info("""
        **Активные задачи:**
        - Утреннее напоминание: каждый день в 09:00
        - Напоминание в будни: Пн-Пт в 13:00
        - Напоминание в выходные: Сб-Вс в 13:00
        """)
    else:
        st.warning("🔴 Планировщик остановлен")
        st.info("Нажмите кнопку 'Запустить планировщик' для начала автоматических рассылок")
    
    # Следующие запуски
    st.markdown("### 📅 Следующие запланированные запуски:")
    
    if st.session_state.scheduler_running:
        setup_schedule()
        jobs = schedule.jobs
        if jobs:
            next_runs = sorted([job.next_run for job in jobs if job.next_run])
            if next_runs:
                st.write(f"**Ближайший запуск**: {next_runs[0].strftime('%Y-%m-%d %H:%M:%S')}")
                st.write(f"**Всего задач**: {len(jobs)}")
            else:
                st.write("Нет запланированных задач")
        else:
            st.write("Нет запланированных задач")
    else:
        st.info("Запустите планировщик, чтобы увидеть расписание")

# Отправка рассылок
elif page == "Отправка рассылок":
    st.header("📤 Ручная отправка рассылок")
    
    # Загружаем текущие настройки для отображения
    settings = load_settings()
    morning_threshold = settings.get("morning_balance_threshold", 0)
    afternoon_threshold = settings.get("afternoon_balance_threshold", -500)
    
    st.markdown("""
    Выберите тип рассылки для отправки прямо сейчас:
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🌅 Утреннее напоминание", type="primary", use_container_width=True):
            with st.spinner("Отправка утреннего напоминания..."):
                try:
                    result_container = st.empty()
                    send_morning_reminder()
                    result_container.success("✅ Утреннее напоминание отправлено! Проверьте консоль для деталей.")
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
        st.caption(f"Баланс < {morning_threshold}")
    
    with col2:
        if st.button("📅 Напоминание (будни)", type="primary", use_container_width=True):
            with st.spinner("Отправка напоминания для будних дней..."):
                try:
                    result_container = st.empty()
                    send_weekday_afternoon_reminder()
                    result_container.success("✅ Напоминание отправлено! Проверьте консоль для деталей.")
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
        st.caption(f"Баланс < {afternoon_threshold}")
    
    with col3:
        if st.button("🏖️ Напоминание (выходные)", type="primary", use_container_width=True):
            with st.spinner("Отправка напоминания для выходных дней..."):
                try:
                    result_container = st.empty()
                    send_weekend_afternoon_reminder()
                    result_container.success("✅ Напоминание отправлено! Проверьте консоль для деталей.")
                except Exception as e:
                    st.error(f"❌ Ошибка: {e}")
        st.caption(f"Баланс < {afternoon_threshold}")
    
    st.markdown("---")
    
    # Просмотр списка водителей
    if st.button("👥 Показать список водителей с задолженностью"):
        with st.spinner("Загрузка данных..."):
            drivers = get_drivers()
            if drivers:
                st.subheader(f"Водители с балансом < {morning_threshold}:")
                filtered_morning = filter_drivers(drivers, balance_threshold=float(morning_threshold))
                if filtered_morning:
                    for driver in filtered_morning:
                        st.write(f"- **{driver['fio']}** ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                else:
                    st.info(f"Нет водителей с балансом < {morning_threshold}")
                
                st.subheader(f"Водители с балансом < {afternoon_threshold}:")
                filtered_afternoon = filter_drivers(drivers, balance_threshold=float(afternoon_threshold))
                if filtered_afternoon:
                    for driver in filtered_afternoon:
                        st.write(f"- **{driver['fio']}** ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                else:
                    st.info(f"Нет водителей с балансом < {afternoon_threshold}")
            else:
                st.error("Не удалось загрузить данные о водителях")

# Тестовая отправка
elif page == "Тестовая отправка":
    st.header("🧪 Тестовая отправка")
    
    st.markdown("""
    Отправьте тестовое сообщение на указанный номер телефона для проверки работы системы.
    """)
    
    phone = st.text_input(
        "Номер телефона",
        placeholder="79991234567 или +79991234567",
        help="Введите номер телефона в любом формате"
    )
    
    message = st.text_area(
        "Текст сообщения",
        value="Тестовое сообщение от системы автоматических напоминаний Premium Park",
        height=100
    )
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if st.button("📤 Отправить тест", type="primary", use_container_width=True):
            if phone:
                phone_normalized = normalize_phone(phone)
                with st.spinner(f"Отправка на {phone_normalized}..."):
                    if send_whatsapp_message(phone_normalized, message):
                        st.success(f"✅ Сообщение отправлено на {phone_normalized}!")
                    else:
                        st.error("❌ Ошибка при отправке сообщения")
            else:
                st.warning("⚠️ Введите номер телефона")

# Настройки
elif page == "Настройки":
    st.header("⚙️ Настройки порогов баланса")
    
    st.markdown("""
    Здесь вы можете изменить пороги баланса, при которых отправляются напоминания.
    """)
    
    settings = load_settings()
    
    # Показываем сообщение о сохранении, если оно было
    if st.session_state.settings_saved:
        st.success("✅ **Настройки успешно сохранены!**")
        st.session_state.settings_saved = False  # Сбрасываем флаг после показа
        st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🌅 Утреннее напоминание")
        morning_threshold = st.number_input(
            "Порог баланса для утреннего напоминания",
            value=float(settings.get("morning_balance_threshold", 0)),
            step=1.0,
            format="%.2f",
            help="Водители с балансом меньше этого значения получат утреннее напоминание"
        )
        st.info(f"Текущее значение: **{morning_threshold}**")
    
    with col2:
        st.subheader("📅 Напоминание в обед (будни и выходные)")
        afternoon_threshold = st.number_input(
            "Порог баланса для напоминания в обед",
            value=float(settings.get("afternoon_balance_threshold", -500)),
            step=1.0,
            format="%.2f",
            help="Водители с балансом меньше этого значения получат напоминание в обед"
        )
        st.info(f"Текущее значение: **{afternoon_threshold}**")
    
    st.markdown("---")
    
    # Кнопка сохранения
    if st.button("💾 Сохранить настройки", type="primary", use_container_width=True):
        new_settings = {
            "morning_balance_threshold": morning_threshold,
            "afternoon_balance_threshold": afternoon_threshold
        }
        if save_settings(new_settings):
            st.session_state.settings_saved = True
            st.rerun()

# Черный список
elif page == "Черный список":
    st.header("🚫 Черный список")
    
    st.markdown("""
    Здесь вы можете управлять черным списком номеров телефонов. 
    Водители из черного списка **никогда не будут получать** автоматические рассылки.
    """)
    
    # Показываем сообщение об обновлении, если оно было
    if st.session_state.blacklist_updated:
        st.success("✅ **Черный список обновлен!**")
        st.session_state.blacklist_updated = False
        st.markdown("---")
    
    # Загружаем текущий черный список
    blacklist = load_blacklist()
    
    # Показываем текущий список
    st.subheader("📋 Текущий черный список")
    if blacklist:
        st.write(f"**Всего номеров в черном списке:** {len(blacklist)}")
        for i, phone in enumerate(blacklist, 1):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{i}. {phone}")
            with col2:
                if st.button("🗑️ Удалить", key=f"delete_{i}"):
                    blacklist.remove(phone)
                    if save_blacklist(blacklist):
                        st.session_state.blacklist_updated = True
                        st.rerun()
    else:
        st.info("Черный список пуст")
    
    st.markdown("---")
    
    # Добавление нового номера
    st.subheader("➕ Добавить номер в черный список")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_phone = st.text_input(
            "Номер телефона",
            placeholder="79991234567 или +79991234567",
            help="Введите номер телефона в любом формате",
            key="new_phone_input"
        )
    
    with col2:
        st.write("")  # Отступ
        st.write("")  # Отступ
        if st.button("➕ Добавить", type="primary", use_container_width=True):
            if new_phone:
                phone_normalized = normalize_phone(new_phone)
                if phone_normalized:
                    if phone_normalized not in blacklist:
                        blacklist.append(phone_normalized)
                        if save_blacklist(blacklist):
                            st.session_state.blacklist_updated = True
                            st.rerun()
                    else:
                        st.warning(f"⚠️ Номер {phone_normalized} уже в черном списке")
                else:
                    st.error("❌ Неверный формат номера телефона")
            else:
                st.warning("⚠️ Введите номер телефона")
    
    st.markdown("---")
    
    # Быстрое добавление из списка водителей
    st.subheader("🔍 Добавить из списка водителей")
    
    if st.button("👥 Показать список водителей для добавления"):
        with st.spinner("Загрузка данных..."):
            drivers = get_drivers()
            if drivers:
                # Показываем всех работающих водителей
                working_drivers = []
                for driver in drivers:
                    try:
                        is_working = (str(driver.get('Status', '')).lower() == 'работает') and \
                                    driver.get('NameConditionWork', '') != ''
                        phone = driver.get('PhoneNumber', '')
                        if is_working and phone:
                            phone_normalized = normalize_phone(phone)
                            if phone_normalized and phone_normalized not in blacklist:
                                working_drivers.append({
                                    'fio': driver.get('FIO', ''),
                                    'phone': phone_normalized,
                                    'balance': float(driver.get('Balance', 0) or 0)
                                })
                    except Exception:
                        continue
                
                if working_drivers:
                    st.write(f"**Найдено водителей:** {len(working_drivers)}")
                    for driver in working_drivers:
                        col1, col2, col3 = st.columns([3, 2, 1])
                        with col1:
                            st.write(f"**{driver['fio']}**")
                        with col2:
                            st.write(f"📱 {driver['phone']} | 💰 {driver['balance']:.2f} ₽")
                        with col3:
                            if st.button("➕ Добавить", key=f"add_{driver['phone']}"):
                                blacklist.append(driver['phone'])
                                if save_blacklist(blacklist):
                                    st.session_state.blacklist_updated = True
                                    st.rerun()
                else:
                    st.info("Нет доступных водителей для добавления")
            else:
                st.error("Не удалось загрузить данные о водителях")

# Редактор шаблонов
elif page == "Редактор шаблонов":
    st.header("✏️ Редактор шаблонов сообщений")
    
    st.markdown("""
    Здесь вы можете редактировать шаблоны сообщений, которые отправляются автоматически.
    """)
    
    messages = load_messages()
    settings = load_settings()
    morning_threshold = settings.get("morning_balance_threshold", 0)
    afternoon_threshold = settings.get("afternoon_balance_threshold", -500)
    
    # Утреннее сообщение
    st.subheader("🌅 Утреннее напоминание")
    st.caption(f"Отправляется каждый день в 09:00 водителям с балансом < {morning_threshold}")
    morning_text = st.text_area(
        "Текст утреннего напоминания",
        value=messages.get("morning", ""),
        height=150,
        key="morning"
    )
    
    st.markdown("---")
    
    # Сообщение для будних дней
    st.subheader("📅 Напоминание для будних дней")
    st.caption(f"Отправляется в понедельник-пятницу в 13:00 водителям с балансом < {afternoon_threshold}")
    weekday_text = st.text_area(
        "Текст напоминания для будних дней",
        value=messages.get("weekday_afternoon", ""),
        height=200,
        key="weekday"
    )
    
    st.markdown("---")
    
    # Сообщение для выходных дней
    st.subheader("🏖️ Напоминание для выходных дней")
    st.caption(f"Отправляется в субботу-воскресенье в 13:00 водителям с балансом < {afternoon_threshold}")
    weekend_text = st.text_area(
        "Текст напоминания для выходных дней",
        value=messages.get("weekend_afternoon", ""),
        height=200,
        key="weekend"
    )
    
    st.markdown("---")
    
    # Показываем сообщение о сохранении, если оно было
    if st.session_state.messages_saved:
        st.success("✅ **Шаблоны успешно сохранены!**")
        st.session_state.messages_saved = False  # Сбрасываем флаг после показа
        st.markdown("---")
    
    # Кнопка сохранения
    if st.button("💾 Сохранить шаблоны", type="primary", use_container_width=True):
        new_messages = {
            "morning": morning_text,
            "weekday_afternoon": weekday_text,
            "weekend_afternoon": weekend_text
        }
        if save_messages(new_messages):
            st.session_state.messages_saved = True
            st.rerun()

# Футер
st.markdown("---")
st.caption(f"Текущее время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

