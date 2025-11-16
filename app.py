#!/usr/bin/env python3
"""
Веб-интерфейс для управления автоматической отправкой напоминаний
"""

import streamlit as st
import json
import os
import threading
import time
from datetime import datetime, timedelta
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
    filter_drivers,
    get_morning_recipients,
    get_weekday_afternoon_recipients,
    get_weekend_afternoon_recipients,
    get_filtered_drivers_info
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
if 'scheduler_status_changed' not in st.session_state:
    st.session_state.scheduler_status_changed = False
if 'last_refresh_time' not in st.session_state:
    st.session_state.last_refresh_time = time.time()
if 'messages_saved' not in st.session_state:
    st.session_state.messages_saved = False
if 'settings_saved' not in st.session_state:
    st.session_state.settings_saved = False
if 'blacklist_updated' not in st.session_state:
    st.session_state.blacklist_updated = False
if 'env_saved' not in st.session_state:
    st.session_state.env_saved = False
if 'show_drivers_list' not in st.session_state:
    st.session_state.show_drivers_list = False
if 'drivers_list_data' not in st.session_state:
    st.session_state.drivers_list_data = []
if 'drivers_search' not in st.session_state:
    st.session_state.drivers_search = ""

# Используем кэширование для сохранения глобального состояния между перезагрузками
@st.cache_resource
def get_scheduler_state():
    """Возвращает глобальное состояние планировщика, которое сохраняется между перезагрузками"""
    return {
        'running': False,
        'lock': threading.Lock(),
        'thread': None
    }


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
        # Загружаем существующие настройки, если файл существует
        existing_settings = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    existing_settings = json.load(f)
            except:
                pass
        
        # Объединяем существующие настройки с новыми
        existing_settings.update(settings_dict)
        
        # Сохраняем объединенные настройки
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(existing_settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Ошибка при сохранении: {e}")
        return False


def save_blacklist(blacklist_list):
    """Сохраняет черный список в файл"""
    blacklist_file = os.path.join(os.path.dirname(__file__), 'blacklist.json')
    try:
        # Убеждаемся, что все элементы имеют структуру {'phone': str, 'fio': str}
        formatted_list = []
        for item in blacklist_list:
            if isinstance(item, dict):
                formatted_list.append(item)
            else:
                # Если это просто строка (номер), преобразуем в объект
                formatted_list.append({
                    'phone': normalize_phone(item) if isinstance(item, str) else item,
                    'fio': 'Неизвестно'
                })
        with open(blacklist_file, 'w', encoding='utf-8') as f:
            json.dump(formatted_list, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Ошибка при сохранении: {e}")
        return False


def load_env():
    """Загружает переменные из .env файла"""
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    env_vars = {}
    if os.path.exists(env_file):
        try:
            with open(env_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip()
                        # Убираем кавычки, если они есть
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        env_vars[key.strip()] = value
        except Exception as e:
            st.error(f"Ошибка при чтении .env: {e}")
    return env_vars


def save_env(env_vars):
    """Сохраняет переменные в .env файл"""
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    try:
        with open(env_file, 'w', encoding='utf-8') as f:
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
        st.error(f"Ошибка при сохранении .env: {e}")
        return False


def setup_schedule():
    """Настраивает расписание задач"""
    schedule.clear()
    
    # Загружаем настройки времени и дней
    settings = load_settings()
    morning_time = settings.get("morning_time", "09:00")
    afternoon_time = settings.get("afternoon_time", "13:00")
    
    # Получаем выбранные дни недели (0=понедельник, 6=воскресенье)
    morning_days = settings.get("morning_days", [0, 1, 2, 3, 4, 5, 6])
    weekday_afternoon_days = settings.get("weekday_afternoon_days", [0, 1, 2, 3, 4])
    weekend_afternoon_days = settings.get("weekend_afternoon_days", [5, 6])
    
    # Функция для получения метода планировщика по дню недели
    def get_day_schedule(day):
        """Возвращает новый объект schedule для указанного дня"""
        day_methods = {
            0: schedule.every().monday,
            1: schedule.every().tuesday,
            2: schedule.every().wednesday,
            3: schedule.every().thursday,
            4: schedule.every().friday,
            5: schedule.every().saturday,
            6: schedule.every().sunday
        }
        return day_methods.get(day)
    
    # Настраиваем утренние напоминания для выбранных дней
    # ВАЖНО: создаём НОВЫЙ объект schedule для каждой задачи!
    for day in morning_days:
        day_schedule = get_day_schedule(day)
        if day_schedule:
            day_schedule.at(morning_time).do(send_morning_reminder)
    
    # Настраиваем дневные напоминания для будних дней
    for day in weekday_afternoon_days:
        day_schedule = get_day_schedule(day)
        if day_schedule:
            day_schedule.at(afternoon_time).do(send_weekday_afternoon_reminder)
    
    # Настраиваем дневные напоминания для выходных дней
    for day in weekend_afternoon_days:
        day_schedule = get_day_schedule(day)
        if day_schedule:
            day_schedule.at(afternoon_time).do(send_weekend_afternoon_reminder)




def run_scheduler():
    """Запускает планировщик в отдельном потоке"""
    scheduler_state = get_scheduler_state()
    setup_schedule()
    
    while True:
        try:
            with scheduler_state['lock']:
                if not scheduler_state['running']:
                    break
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            # Логируем ошибку, но продолжаем работу планировщика
            print(f"[SCHEDULER ERROR] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Ошибка в планировщике: {e}")
            import traceback
            traceback.print_exc()
            # Ждем минуту перед следующей попыткой
            time.sleep(60)


def get_scheduler_status():
    """Возвращает статус планировщика"""
    scheduler_state = get_scheduler_state()
    with scheduler_state['lock']:
        return scheduler_state['running']


def start_scheduler():
    """Запускает планировщик"""
    scheduler_state = get_scheduler_state()
    with scheduler_state['lock']:
        if not scheduler_state['running']:
            scheduler_state['running'] = True
            st.session_state.scheduler_running = True
            st.session_state.scheduler_status_changed = True
            scheduler_state['thread'] = threading.Thread(target=run_scheduler, daemon=True)
            scheduler_state['thread'].start()
            st.rerun()


def stop_scheduler():
    """Останавливает планировщик"""
    scheduler_state = get_scheduler_state()
    with scheduler_state['lock']:
        if scheduler_state['running']:
            scheduler_state['running'] = False
            st.session_state.scheduler_running = False
            st.session_state.scheduler_status_changed = True
            schedule.clear()
            st.rerun()


# Заголовок
st.title("🚗 Premium Park - Автоматические напоминания")
st.markdown("---")

# Боковая панель с навигацией
st.sidebar.title("📋 Меню")
page = st.sidebar.radio(
    "Выберите раздел:",
    ["Главная", "Отправка рассылок", "Тестовая отправка", "Редактор шаблонов", "Настройки", "Черный список", "Настройки API", "Статус планировщика"]
)

# Индикатор статуса планировщика в sidebar
st.sidebar.markdown("---")
scheduler_status = get_scheduler_status()
if scheduler_status:
    st.sidebar.success("🟢 Планировщик запущен")
else:
    st.sidebar.warning("🔴 Планировщик остановлен")
st.sidebar.markdown("---")

# Сохраняем текущую страницу и сбрасываем таймер при смене страницы
if 'current_page' not in st.session_state:
    st.session_state.current_page = page
elif st.session_state.current_page != page:
    st.session_state.current_page = page
    st.session_state.last_refresh_time = time.time()  # Сбрасываем таймер при смене страницы

# Главная страница
if page == "Главная":
    st.header("Добро пожаловать!")
    st.markdown("""
    ### Возможности системы:
    
    - ✅ **Автоматическая отправка напоминаний** по расписанию
    - 📤 **Ручная отправка рассылок** в любое время
    - 🧪 **Тестовая отправка** на указанный номер
    - ✏️ **Редактирование шаблонов** сообщений
    
    ### Как использовать:
    
    1. Перейдите в раздел **"Статус планировщика"** для запуска автоматических рассылок
    2. Используйте **"Отправка рассылок"** для ручной отправки
    3. Редактируйте шаблоны сообщений в разделе **"Редактор шаблонов"**
    """)

# Статус планировщика
elif page == "Статус планировщика":
    st.header("⚙️ Управление планировщиком")
    
    # Синхронизируем состояние с глобальной переменной
    scheduler_status = get_scheduler_status()
    if scheduler_status != st.session_state.get('scheduler_running', False):
        st.session_state.scheduler_running = scheduler_status
    
    # Настраиваем расписание для отображения
    # НО только если планировщик не запущен, чтобы не сбросить его задачи
    if not scheduler_status:
        setup_schedule()
    
    # Показываем сообщение об изменении статуса
    if st.session_state.scheduler_status_changed:
        if st.session_state.scheduler_running:
            st.success("✅ Планировщик успешно запущен!")
        else:
            st.success("⏹️ Планировщик успешно остановлен!")
        st.session_state.scheduler_status_changed = False
    
    # Одна кнопка, которая меняется в зависимости от состояния
    if st.session_state.scheduler_running:
        if st.button("⏹️ Остановить планировщик", type="primary", use_container_width=True):
            stop_scheduler()
    else:
        if st.button("▶️ Запустить планировщик", type="primary", use_container_width=True):
            start_scheduler()
    
    st.markdown("---")
    
    # Статус
    if st.session_state.scheduler_running:
        st.success("🟢 Планировщик работает")
        
        # Загружаем настройки времени для отображения
        settings = load_settings()
        morning_time = settings.get("morning_time", "09:00")
        afternoon_time = settings.get("afternoon_time", "13:00")

    else:
        st.warning("🔴 Планировщик остановлен")
        st.info("Нажмите кнопку 'Запустить планировщик' для начала автоматических рассылок")
    
    st.markdown("---")
    
    # Кнопки для просмотра получателей
    st.markdown("### 👥 Просмотр получателей рассылок")
    st.markdown("Проверьте, кому будут отправлены сообщения при следующем запуске:")
    
    # Загружаем настройки для порогов
    settings = load_settings()
    morning_threshold = settings.get("morning_balance_threshold", 0)
    afternoon_threshold = settings.get("afternoon_balance_threshold", -500)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("🌅 Утреннее напоминание")
        if st.button("👁️ Показать получателей", key="scheduler_show_morning", use_container_width=True):
            with st.spinner("Загрузка списка получателей..."):
                messages = load_messages()
                message_text = messages.get("morning", "")
                recipients = get_morning_recipients()
                if recipients:
                    st.subheader(f"📋 Получатели утреннего напоминания ({len(recipients)} чел.)")
                    st.caption(f"Порог баланса: < {morning_threshold}")
                    st.markdown("**📝 Текст сообщения:**")
                    st.text_area("", value=message_text, height=100, disabled=True, key="scheduler_morning_message")
                    st.markdown("**👥 Список получателей:**")
                    for driver in recipients:
                        st.write(f"- **{driver['fio']}** ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                else:
                    st.info(f"Нет получателей с балансом < {morning_threshold}")
                
                # Показываем отфильтрованных водителей
                filtered_info = get_filtered_drivers_info(morning_threshold)
                total_filtered = sum(len(v) for v in filtered_info.values())
                if total_filtered > 0:
                    with st.expander(f"🚫 Отфильтровано ({total_filtered} чел.)", expanded=False):
                        if filtered_info['blacklist']:
                            st.write(f"**В черном списке ({len(filtered_info['blacklist'])}):**")
                            for driver in filtered_info['blacklist']:
                                st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                        if filtered_info['not_working']:
                            st.write(f"**Не работают ({len(filtered_info['not_working'])}):**")
                            for driver in filtered_info['not_working']:
                                st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽ (Статус: {driver.get('status', 'Неизвестно')})")
                        if filtered_info['skip_flag']:
                            st.write(f"**С пометкой 'не блокировать/не беспокоить' ({len(filtered_info['skip_flag'])}):**")
                            for driver in filtered_info['skip_flag']:
                                st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                        if filtered_info['no_phone']:
                            st.write(f"**Без телефона ({len(filtered_info['no_phone'])}):**")
                            for driver in filtered_info['no_phone']:
                                st.write(f"- {driver['fio']} - Баланс: {driver['balance']:.2f} ₽")
    
    with col2:
        st.subheader("📅 Напоминание (будни)")
        if st.button("👁️ Показать получателей", key="scheduler_show_weekday", use_container_width=True):
            with st.spinner("Загрузка списка получателей..."):
                messages = load_messages()
                message_text = messages.get("weekday_afternoon", "")
                recipients = get_weekday_afternoon_recipients()
                if recipients:
                    st.subheader(f"📋 Получатели напоминания в будни ({len(recipients)} чел.)")
                    st.caption(f"Порог баланса: < {afternoon_threshold}")
                    st.markdown("**📝 Текст сообщения:**")
                    st.text_area("", value=message_text, height=100, disabled=True, key="scheduler_weekday_message")
                    st.markdown("**👥 Список получателей:**")
                    for driver in recipients:
                        st.write(f"- **{driver['fio']}** ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                else:
                    st.info(f"Нет получателей с балансом < {afternoon_threshold}")
                
                # Показываем отфильтрованных водителей
                filtered_info = get_filtered_drivers_info(afternoon_threshold)
                total_filtered = sum(len(v) for v in filtered_info.values())
                if total_filtered > 0:
                    with st.expander(f"🚫 Отфильтровано ({total_filtered} чел.)", expanded=False):
                        if filtered_info['blacklist']:
                            st.write(f"**В черном списке ({len(filtered_info['blacklist'])}):**")
                            for driver in filtered_info['blacklist']:
                                st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                        if filtered_info['not_working']:
                            st.write(f"**Не работают ({len(filtered_info['not_working'])}):**")
                            for driver in filtered_info['not_working']:
                                st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽ (Статус: {driver.get('status', 'Неизвестно')})")
                        if filtered_info['skip_flag']:
                            st.write(f"**С пометкой 'не блокировать/не беспокоить' ({len(filtered_info['skip_flag'])}):**")
                            for driver in filtered_info['skip_flag']:
                                st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                        if filtered_info['no_phone']:
                            st.write(f"**Без телефона ({len(filtered_info['no_phone'])}):**")
                            for driver in filtered_info['no_phone']:
                                st.write(f"- {driver['fio']} - Баланс: {driver['balance']:.2f} ₽")
    
    with col3:
        st.subheader("🏖️ Напоминание (выходные)")
        if st.button("👁️ Показать получателей", key="scheduler_show_weekend", use_container_width=True):
            with st.spinner("Загрузка списка получателей..."):
                messages = load_messages()
                message_text = messages.get("weekend_afternoon", "")
                recipients = get_weekend_afternoon_recipients()
                if recipients:
                    st.subheader(f"📋 Получатели напоминания в выходные ({len(recipients)} чел.)")
                    st.caption(f"Порог баланса: < {afternoon_threshold}")
                    st.markdown("**📝 Текст сообщения:**")
                    st.text_area("", value=message_text, height=100, disabled=True, key="scheduler_weekend_message")
                    st.markdown("**👥 Список получателей:**")
                    for driver in recipients:
                        st.write(f"- **{driver['fio']}** ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                else:
                    st.info(f"Нет получателей с балансом < {afternoon_threshold}")
                
                # Показываем отфильтрованных водителей
                filtered_info = get_filtered_drivers_info(afternoon_threshold)
                total_filtered = sum(len(v) for v in filtered_info.values())
                if total_filtered > 0:
                    with st.expander(f"🚫 Отфильтровано ({total_filtered} чел.)", expanded=False):
                        if filtered_info['blacklist']:
                            st.write(f"**В черном списке ({len(filtered_info['blacklist'])}):**")
                            for driver in filtered_info['blacklist']:
                                st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                        if filtered_info['not_working']:
                            st.write(f"**Не работают ({len(filtered_info['not_working'])}):**")
                            for driver in filtered_info['not_working']:
                                st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽ (Статус: {driver.get('status', 'Неизвестно')})")
                        if filtered_info['skip_flag']:
                            st.write(f"**С пометкой 'не блокировать/не беспокоить' ({len(filtered_info['skip_flag'])}):**")
                            for driver in filtered_info['skip_flag']:
                                st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                        if filtered_info['no_phone']:
                            st.write(f"**Без телефона ({len(filtered_info['no_phone'])}):**")
                            for driver in filtered_info['no_phone']:
                                st.write(f"- {driver['fio']} - Баланс: {driver['balance']:.2f} ₽")
    
    st.markdown("---")
    
    # Следующие запуски
    st.markdown("### 📅 Следующие запланированные запуски:")
    
    # Отладочная информация
    jobs = schedule.jobs
    st.write(f"🔍 **Отладка**: Всего задач в расписании: {len(jobs)}")
    
    # Показываем информацию о каждой задаче
    for i, job in enumerate(jobs, 1):
        st.write(f"  Задача {i}: {job.job_func.__name__ if hasattr(job.job_func, '__name__') else 'unknown'} - следующий запуск: {job.next_run}")
    
    if jobs:
        next_runs = sorted([job.next_run for job in jobs if job.next_run])
        if next_runs:
            # Ближайший запуск
            nearest = next_runs[0]
            now = datetime.now()
            time_until = nearest - now
            
            # Форматируем время до запуска
            hours = int(time_until.total_seconds() // 3600)
            minutes = int((time_until.total_seconds() % 3600) // 60)
            
            if hours > 24:
                days = hours // 24
                hours = hours % 24
                time_str = f"{days} дн. {hours} ч. {minutes} мин."
            elif hours > 0:
                time_str = f"{hours} ч. {minutes} мин."
            else:
                time_str = f"{minutes} мин."
            
            st.success(f"⏰ **Ближайший запуск**: {nearest.strftime('%d.%m.%Y в %H:%M')} (через {time_str})")
            
            st.markdown("---")
            st.markdown("**Следующие запуски:**")
            
            # Показываем следующие 10 запусков
            for i, next_run in enumerate(next_runs[:10], 1):
                day_name = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'][next_run.weekday()]
                time_until_this = next_run - now
                hours_until = int(time_until_this.total_seconds() // 3600)
                
                if hours_until > 24:
                    days_until = hours_until // 24
                    time_info = f"(через {days_until} дн.)"
                elif hours_until > 0:
                    time_info = f"(через {hours_until} ч.)"
                else:
                    mins_until = int(time_until_this.total_seconds() // 60)
                    time_info = f"(через {mins_until} мин.)"
                
                st.write(f"{i}. {day_name}, {next_run.strftime('%d.%m.%Y')} в **{next_run.strftime('%H:%M')}** {time_info}")
            
            # Кнопка обновления (ВНЕ цикла!)
            st.markdown("---")
            if st.button("🔄 Обновить страницу", use_container_width=True, key="refresh_scheduler"):
                st.session_state.last_refresh_time = time.time()
                st.rerun()
        else:
            st.write("Нет запланированных задач")
        
        # Автоматическое обновление страницы каждые 30 секунд (только на этой странице)
        if page == "Статус планировщика":
            current_time = time.time()
            time_since_refresh = current_time - st.session_state.last_refresh_time
            
            if time_since_refresh >= 30:
                st.session_state.last_refresh_time = current_time
                time.sleep(0.1)  # Небольшая задержка для плавности
                st.rerun()
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
        st.subheader("🌅 Утреннее напоминание")
        col1_btn1, col1_btn2 = st.columns(2)
        with col1_btn1:
            if st.button("🌅 Отправить", type="primary", use_container_width=True, key="send_morning"):
                with st.spinner("Отправка утреннего напоминания..."):
                    try:
                        result_container = st.empty()
                        send_morning_reminder()
                        result_container.success("✅ Утреннее напоминание отправлено! Проверьте консоль для деталей.")
                    except Exception as e:
                        st.error(f"❌ Ошибка: {e}")
        with col1_btn2:
            if st.button("👁️ Показать", key="show_morning", use_container_width=True):
                with st.spinner("Загрузка списка получателей..."):
                    messages = load_messages()
                    message_text = messages.get("morning", "")
                    recipients = get_morning_recipients()
                    if recipients:
                        st.subheader(f"📋 Получатели утреннего напоминания ({len(recipients)} чел.)")
                        st.markdown("**📝 Текст сообщения:**")
                        st.text_area("", value=message_text, height=100, disabled=True, key="manual_morning_message")
                        st.markdown("**👥 Список получателей:**")
                        for driver in recipients:
                            st.write(f"- **{driver['fio']}** ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                    else:
                        st.info(f"Нет получателей с балансом < {morning_threshold}")
                    
                    # Показываем отфильтрованных водителей
                    filtered_info = get_filtered_drivers_info(morning_threshold)
                    total_filtered = sum(len(v) for v in filtered_info.values())
                    if total_filtered > 0:
                        with st.expander(f"🚫 Отфильтровано ({total_filtered} чел.)", expanded=False):
                            if filtered_info['blacklist']:
                                st.write(f"**В черном списке ({len(filtered_info['blacklist'])}):**")
                                for driver in filtered_info['blacklist']:
                                    st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                            if filtered_info['not_working']:
                                st.write(f"**Не работают ({len(filtered_info['not_working'])}):**")
                                for driver in filtered_info['not_working']:
                                    st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽ (Статус: {driver.get('status', 'Неизвестно')})")
                            if filtered_info['skip_flag']:
                                st.write(f"**С пометкой 'не блокировать/не беспокоить' ({len(filtered_info['skip_flag'])}):**")
                                for driver in filtered_info['skip_flag']:
                                    st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                            if filtered_info['no_phone']:
                                st.write(f"**Без телефона ({len(filtered_info['no_phone'])}):**")
                                for driver in filtered_info['no_phone']:
                                    st.write(f"- {driver['fio']} - Баланс: {driver['balance']:.2f} ₽")
        st.caption(f"Баланс < {morning_threshold}")
    
    with col2:
        st.subheader("📅 Напоминание (будни)")
        col2_btn1, col2_btn2 = st.columns(2)
        with col2_btn1:
            if st.button("📅 Отправить", type="primary", use_container_width=True, key="send_weekday"):
                with st.spinner("Отправка напоминания для будних дней..."):
                    try:
                        result_container = st.empty()
                        send_weekday_afternoon_reminder()
                        result_container.success("✅ Напоминание отправлено! Проверьте консоль для деталей.")
                    except Exception as e:
                        st.error(f"❌ Ошибка: {e}")
        with col2_btn2:
            if st.button("👁️ Показать", key="show_weekday", use_container_width=True):
                with st.spinner("Загрузка списка получателей..."):
                    messages = load_messages()
                    message_text = messages.get("weekday_afternoon", "")
                    recipients = get_weekday_afternoon_recipients()
                    if recipients:
                        st.subheader(f"📋 Получатели напоминания в будни ({len(recipients)} чел.)")
                        st.markdown("**📝 Текст сообщения:**")
                        st.text_area("", value=message_text, height=100, disabled=True, key="manual_weekday_message")
                        st.markdown("**👥 Список получателей:**")
                        for driver in recipients:
                            st.write(f"- **{driver['fio']}** ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                    else:
                        st.info(f"Нет получателей с балансом < {afternoon_threshold}")
                    
                    # Показываем отфильтрованных водителей
                    filtered_info = get_filtered_drivers_info(afternoon_threshold)
                    total_filtered = sum(len(v) for v in filtered_info.values())
                    if total_filtered > 0:
                        with st.expander(f"🚫 Отфильтровано ({total_filtered} чел.)", expanded=False):
                            if filtered_info['blacklist']:
                                st.write(f"**В черном списке ({len(filtered_info['blacklist'])}):**")
                                for driver in filtered_info['blacklist']:
                                    st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                            if filtered_info['not_working']:
                                st.write(f"**Не работают ({len(filtered_info['not_working'])}):**")
                                for driver in filtered_info['not_working']:
                                    st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽ (Статус: {driver.get('status', 'Неизвестно')})")
                            if filtered_info['skip_flag']:
                                st.write(f"**С пометкой 'не блокировать/не беспокоить' ({len(filtered_info['skip_flag'])}):**")
                                for driver in filtered_info['skip_flag']:
                                    st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                            if filtered_info['no_phone']:
                                st.write(f"**Без телефона ({len(filtered_info['no_phone'])}):**")
                                for driver in filtered_info['no_phone']:
                                    st.write(f"- {driver['fio']} - Баланс: {driver['balance']:.2f} ₽")
        st.caption(f"Баланс < {afternoon_threshold}")
    
    with col3:
        st.subheader("🏖️ Напоминание (выходные)")
        col3_btn1, col3_btn2 = st.columns(2)
        with col3_btn1:
            if st.button("🏖️ Отправить", type="primary", use_container_width=True, key="send_weekend"):
                with st.spinner("Отправка напоминания для выходных дней..."):
                    try:
                        result_container = st.empty()
                        send_weekend_afternoon_reminder()
                        result_container.success("✅ Напоминание отправлено! Проверьте консоль для деталей.")
                    except Exception as e:
                        st.error(f"❌ Ошибка: {e}")
        with col3_btn2:
            if st.button("👁️ Показать", key="show_weekend", use_container_width=True):
                with st.spinner("Загрузка списка получателей..."):
                    messages = load_messages()
                    message_text = messages.get("weekend_afternoon", "")
                    recipients = get_weekend_afternoon_recipients()
                    if recipients:
                        st.subheader(f"📋 Получатели напоминания в выходные ({len(recipients)} чел.)")
                        st.markdown("**📝 Текст сообщения:**")
                        st.text_area("", value=message_text, height=100, disabled=True, key="manual_weekend_message")
                        st.markdown("**👥 Список получателей:**")
                        for driver in recipients:
                            st.write(f"- **{driver['fio']}** ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                    else:
                        st.info(f"Нет получателей с балансом < {afternoon_threshold}")
                    
                    # Показываем отфильтрованных водителей
                    filtered_info = get_filtered_drivers_info(afternoon_threshold)
                    total_filtered = sum(len(v) for v in filtered_info.values())
                    if total_filtered > 0:
                        with st.expander(f"🚫 Отфильтровано ({total_filtered} чел.)", expanded=False):
                            if filtered_info['blacklist']:
                                st.write(f"**В черном списке ({len(filtered_info['blacklist'])}):**")
                                for driver in filtered_info['blacklist']:
                                    st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                            if filtered_info['not_working']:
                                st.write(f"**Не работают ({len(filtered_info['not_working'])}):**")
                                for driver in filtered_info['not_working']:
                                    st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽ (Статус: {driver.get('status', 'Неизвестно')})")
                            if filtered_info['skip_flag']:
                                st.write(f"**С пометкой 'не блокировать/не беспокоить' ({len(filtered_info['skip_flag'])}):**")
                                for driver in filtered_info['skip_flag']:
                                    st.write(f"- {driver['fio']} ({driver['phone']}) - Баланс: {driver['balance']:.2f} ₽")
                            if filtered_info['no_phone']:
                                st.write(f"**Без телефона ({len(filtered_info['no_phone'])}):**")
                                for driver in filtered_info['no_phone']:
                                    st.write(f"- {driver['fio']} - Баланс: {driver['balance']:.2f} ₽")
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
    st.header("⚙️ Настройки рассылок")
    
    st.markdown("""
    Здесь вы можете изменить пороги баланса и время отправки напоминаний.
    """)
    
    settings = load_settings()
    
    # Показываем сообщение о сохранении, если оно было
    if st.session_state.settings_saved:
        st.success("✅ **Настройки успешно сохранены!**")
        
        # Показываем кнопку перезапуска планировщика, если он работает
        if st.session_state.scheduler_running:
            st.warning("⚠️ Планировщик работает. Перезапустите его для применения новых настроек времени.")
            col_restart1, col_restart2 = st.columns([1, 3])
            with col_restart1:
                if st.button("🔄 Перезапустить планировщик", type="secondary", use_container_width=True):
                    stop_scheduler()
                    time.sleep(0.5)
                    start_scheduler()
        
        st.session_state.settings_saved = False  # Сбрасываем флаг после показа
        st.markdown("---")
    
    # Пороги баланса
    st.subheader("💰 Пороги баланса")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🌅 Утреннее напоминание**")
        morning_threshold = st.number_input(
            "Порог баланса для утреннего напоминания",
            value=float(settings.get("morning_balance_threshold", 0)),
            step=1.0,
            format="%.2f",
            help="Водители с балансом меньше этого значения получат утреннее напоминание"
        )
        st.info(f"Текущее значение: **{morning_threshold}**")
    
    with col2:
        st.markdown("**📅 Напоминание в обед (будни и выходные)**")
        afternoon_threshold = st.number_input(
            "Порог баланса для напоминания в обед",
            value=float(settings.get("afternoon_balance_threshold", -500)),
            step=1.0,
            format="%.2f",
            help="Водители с балансом меньше этого значения получат напоминание в обед"
        )
        st.info(f"Текущее значение: **{afternoon_threshold}**")
    
    st.markdown("---")
    
    # Время отправки
    st.subheader("⏰ Время отправки")
    
    col3, col4 = st.columns(2)
    
    with col3:
        st.markdown("**🌅 Утреннее напоминание**")
        morning_time = st.time_input(
            "Время отправки утреннего напоминания",
            value=datetime.strptime(settings.get("morning_time", "09:00"), "%H:%M").time(),
            help="Время отправки утреннего напоминания каждый день"
        )
        st.info(f"Текущее время: **{morning_time.strftime('%H:%M')}**")
    
    with col4:
        st.markdown("**📅 Напоминание в обед**")
        afternoon_time = st.time_input(
            "Время отправки дневного напоминания",
            value=datetime.strptime(settings.get("afternoon_time", "13:00"), "%H:%M").time(),
            help="Время отправки напоминания в будни и выходные"
        )
        st.info(f"Текущее время: **{afternoon_time.strftime('%H:%M')}**")
    
    st.markdown("---")
    
    # Выбор дней недели для рассылок
    st.subheader("📅 Дни недели для рассылок")
    st.markdown("Выберите дни недели, когда будут отправляться рассылки:")
    
    day_names = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье"
    }
    
    col_days1, col_days2, col_days3 = st.columns(3)
    
    with col_days1:
        st.markdown("**🌅 Утреннее напоминание**")
        morning_days = settings.get("morning_days", [0, 1, 2, 3, 4, 5, 6])
        selected_morning_days = []
        for day_num, day_name in day_names.items():
            if st.checkbox(day_name, value=day_num in morning_days, key=f"morning_{day_num}"):
                selected_morning_days.append(day_num)
    
    with col_days2:
        st.markdown("**📅 Напоминание (будни)**")
        weekday_afternoon_days = settings.get("weekday_afternoon_days", [0, 1, 2, 3, 4])
        selected_weekday_days = []
        for day_num, day_name in day_names.items():
            if st.checkbox(day_name, value=day_num in weekday_afternoon_days, key=f"weekday_{day_num}"):
                selected_weekday_days.append(day_num)
    
    with col_days3:
        st.markdown("**🏖️ Напоминание (выходные)**")
        weekend_afternoon_days = settings.get("weekend_afternoon_days", [5, 6])
        selected_weekend_days = []
        for day_num, day_name in day_names.items():
            if st.checkbox(day_name, value=day_num in weekend_afternoon_days, key=f"weekend_{day_num}"):
                selected_weekend_days.append(day_num)
    
    st.markdown("---")
    
    # Кнопка сохранения
    if st.button("💾 Сохранить настройки", type="primary", use_container_width=True):
        new_settings = {
            "morning_balance_threshold": morning_threshold,
            "afternoon_balance_threshold": afternoon_threshold,
            "morning_time": morning_time.strftime("%H:%M"),
            "afternoon_time": afternoon_time.strftime("%H:%M"),
            "morning_days": sorted(selected_morning_days),
            "weekday_afternoon_days": sorted(selected_weekday_days),
            "weekend_afternoon_days": sorted(selected_weekend_days)
        }
        if save_settings(new_settings):
            st.session_state.settings_saved = True
            # Автоматически перезапускаем планировщик, если он запущен
            if st.session_state.scheduler_running:
                stop_scheduler()
                time.sleep(0.5)
                start_scheduler()
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
    
    # Поиск по черному списку
    if 'blacklist_search' not in st.session_state:
        st.session_state.blacklist_search = ""
    
    blacklist_search = st.text_input(
        "🔍 Поиск по ФИО или номеру телефона",
        value=st.session_state.blacklist_search,
        key="blacklist_search_input",
        placeholder="Введите ФИО или номер телефона..."
    )
    st.session_state.blacklist_search = blacklist_search.lower()
    
    # Фильтруем черный список по поисковому запросу
    filtered_blacklist = blacklist
    if st.session_state.blacklist_search:
        filtered_blacklist = [
            item for item in blacklist
            if st.session_state.blacklist_search in item.get('fio', '').lower() or 
               st.session_state.blacklist_search in item.get('phone', '')
        ]
    
    if filtered_blacklist:
        st.write(f"**Всего номеров в черном списке:** {len(filtered_blacklist)} (из {len(blacklist)})")
        for i, item in enumerate(filtered_blacklist, 1):
            # Поддерживаем обратную совместимость
            if isinstance(item, dict):
                phone = item.get('phone', '')
                fio = item.get('fio', 'Неизвестно')
            else:
                phone = item
                fio = 'Неизвестно'
            
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"{i}. **{fio}** - 📱 {phone}")
            with col2:
                if st.button("🗑️ Удалить", key=f"delete_{phone}"):
                    blacklist.remove(item)
                    if save_blacklist(blacklist):
                        st.session_state.blacklist_updated = True
                        st.rerun()
    else:
        if st.session_state.blacklist_search:
            st.info(f"По запросу '{blacklist_search}' ничего не найдено")
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
                    # Проверяем, не в черном списке ли уже
                    blacklist_phones = [item.get('phone') if isinstance(item, dict) else item for item in blacklist]
                    if phone_normalized not in blacklist_phones:
                        # Пытаемся найти ФИО по номеру из списка водителей
                        fio = 'Неизвестно'
                        try:
                            drivers = get_drivers()
                            for driver in drivers:
                                driver_phone = normalize_phone(driver.get('PhoneNumber', ''))
                                if driver_phone == phone_normalized:
                                    fio = driver.get('FIO', 'Неизвестно')
                                    break
                        except:
                            pass
                        
                        blacklist.append({'phone': phone_normalized, 'fio': fio})
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
    
    col_btn, col_search = st.columns([1, 2])
    with col_btn:
        if st.button("👥 Показать список водителей", use_container_width=True):
            if not st.session_state.show_drivers_list:
                # Загружаем данные только при первом показе
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
                                    # Проверяем, не в черном списке ли уже
                                    blacklist_phones = [item.get('phone') if isinstance(item, dict) else item for item in blacklist]
                                    if phone_normalized and phone_normalized not in blacklist_phones:
                                        working_drivers.append({
                                            'fio': driver.get('FIO', ''),
                                            'phone': phone_normalized,
                                            'balance': float(driver.get('Balance', 0) or 0)
                                        })
                            except Exception:
                                continue
                        st.session_state.drivers_list_data = working_drivers
                    else:
                        st.error("Не удалось загрузить данные о водителях")
                        st.session_state.drivers_list_data = []
            st.session_state.show_drivers_list = not st.session_state.show_drivers_list
            st.rerun()
    
    # Показываем список водителей, если флаг установлен
    if st.session_state.show_drivers_list:
        # Поиск по списку
        search_query = st.text_input(
            "🔍 Поиск по ФИО или номеру телефона",
            value=st.session_state.drivers_search,
            key="drivers_search_input",
            placeholder="Введите ФИО или номер телефона..."
        )
        st.session_state.drivers_search = search_query.lower()
        
        # Фильтруем список по поисковому запросу
        filtered_drivers = st.session_state.drivers_list_data
        if st.session_state.drivers_search:
            filtered_drivers = [
                d for d in st.session_state.drivers_list_data
                if st.session_state.drivers_search in d['fio'].lower() or 
                   st.session_state.drivers_search in d['phone']
            ]
        
        if filtered_drivers:
            st.write(f"**Найдено водителей:** {len(filtered_drivers)} (из {len(st.session_state.drivers_list_data)})")
            st.markdown("---")
            for driver in filtered_drivers:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{driver['fio']}**")
                with col2:
                    st.write(f"📱 {driver['phone']} | 💰 {driver['balance']:.2f} ₽")
                with col3:
                    if st.button("➕ Добавить", key=f"add_{driver['phone']}"):
                        # Загружаем актуальный черный список перед добавлением
                        current_blacklist = load_blacklist()
                        blacklist_phones = [item.get('phone') if isinstance(item, dict) else item for item in current_blacklist]
                        if driver['phone'] not in blacklist_phones:
                            current_blacklist.append({
                                'phone': driver['phone'],
                                'fio': driver['fio']
                            })
                            if save_blacklist(current_blacklist):
                                # Удаляем водителя из отображаемого списка без перезагрузки API
                                st.session_state.drivers_list_data = [
                                    d for d in st.session_state.drivers_list_data 
                                    if d['phone'] != driver['phone']
                                ]
                                st.session_state.blacklist_updated = True
                                st.rerun()
                        else:
                            st.warning("⚠️ Уже в черном списке")
            st.markdown("---")
        else:
            if st.session_state.drivers_search:
                st.info(f"По запросу '{search_query}' ничего не найдено")
            else:
                st.info("Нет доступных водителей для добавления")

# Настройки API
elif page == "Настройки API":
    st.header("🔐 Настройки API")
    
    st.markdown("""
    Здесь вы можете настроить данные для подключения к API 1C и WhatsApp API.
    Эти настройки хранятся в файле `.env`.
    """)
    
    # Показываем сообщение о сохранении, если оно было
    if st.session_state.env_saved:
        st.success("✅ **Настройки API успешно сохранены!**")
        st.info("⚠️ Перезапустите приложение, чтобы изменения вступили в силу.")
        st.session_state.env_saved = False
        st.markdown("---")
    
    # Загружаем текущие настройки
    env_vars = load_env()
    
    # Данные для API 1C
    st.subheader("📋 Данные для API 1C")
    st.caption("Логин и пароль для подключения к системе 1C")
    
    login = st.text_input(
        "Логин",
        value=env_vars.get('LOGIN', ''),
        help="Логин для доступа к API 1C",
        type="default"
    )
    
    password = st.text_input(
        "Пароль",
        value=env_vars.get('PASSWORD', ''),
        help="Пароль для доступа к API 1C",
        type="password"
    )
    
    st.markdown("---")
    
    # Данные для WhatsApp API
    st.subheader("📱 Данные для WhatsApp API (wappi.pro)")
    st.caption("Настройки для отправки сообщений через wappi.pro")
    
    profile_id = st.text_input(
        "PROFILE_ID",
        value=env_vars.get('PROFILE_ID', ''),
        help="ID профиля в системе wappi.pro"
    )
    
    authorization = st.text_input(
        "AUTHORIZATION (токен)",
        value=env_vars.get('AUTHORIZATION', ''),
        help="Токен авторизации для wappi.pro",
        type="password"
    )
    
    st.markdown("---")
    
    # Тестовый номер
    st.subheader("🧪 Тестовый номер (опционально)")
    st.caption("Номер телефона для тестовой отправки сообщений")
    
    test_phone = st.text_input(
        "TEST_PHONE",
        value=env_vars.get('TEST_PHONE', ''),
        help="Номер телефона в формате 79991234567 или +79991234567",
        placeholder="79991234567"
    )
    
    st.markdown("---")
    
    # Проверка заполненности обязательных полей
    required_fields = ['LOGIN', 'PASSWORD', 'PROFILE_ID', 'AUTHORIZATION']
    missing_fields = [field for field in required_fields if not env_vars.get(field)]
    
    if missing_fields:
        st.warning(f"⚠️ Не заполнены обязательные поля: {', '.join(missing_fields)}")
    
    # Кнопка сохранения
    if st.button("💾 Сохранить настройки API", type="primary", use_container_width=True):
        new_env = {
            'LOGIN': login,
            'PASSWORD': password,
            'PROFILE_ID': profile_id,
            'AUTHORIZATION': authorization,
            'TEST_PHONE': test_phone
        }
        
        # Проверка обязательных полей
        if not all([new_env.get(field) for field in required_fields]):
            st.error("❌ Заполните все обязательные поля!")
        else:
            if save_env(new_env):
                st.session_state.env_saved = True
                st.rerun()

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

