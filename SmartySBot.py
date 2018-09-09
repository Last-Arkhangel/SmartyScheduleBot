# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import requests
import telebot
import datetime
import sys
import os
import settings
import core
import re
import json
import schedule_updater
import random
import hashlib
from WeatherManager import WeatherManager
from settings import KEYBOARD
from flask import Flask, request, render_template, jsonify, session

app = Flask(__name__, template_folder='site', static_folder='site/static', static_url_path='/fl/static')
app.secret_key = hashlib.md5(settings.ADMIN_PASSWORD.encode('utf-8')).hexdigest()

bot = telebot.TeleBot(settings.BOT_TOKEN, threaded=True)

keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
keyboard.row(KEYBOARD['TODAY'], KEYBOARD['TOMORROW'], KEYBOARD['FOR_A_WEEK'])
keyboard.row(KEYBOARD['FOR_A_TEACHER'], KEYBOARD['FOR_A_GROUP'])
keyboard.row(KEYBOARD['TIMETABLE'], KEYBOARD['WEATHER'], KEYBOARD['HELP'])

emoji_numbers = ['0⃣', '1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣']


def get_timetable(faculty='', teacher='', group='', sdate='', edate='', user_id=None):

    http_headers = {
            'User-Agent': settings.HTTP_USER_AGENT,
            'Accept': 'text/html',
    }

    try:
        post_data = {
            'faculty': faculty,
            'teacher': teacher.encode('windows-1251'),
            'group': group.encode('windows-1251'),
            'sdate': sdate,
            'edate': edate,
            'n': 700,
        }
    except Exception as ex:
        core.log(m='Error encoding request parameters: {}'.format(str(ex)))
        bot.send_message(user_id, 'Помилка надсилання запиту, вкажи коректні параметри (як мінімум перевір чи '
                                  'правильно вказана група, зробити це можна в Довідці)', reply_markup=keyboard)
        return False

    try:
        page = requests.post(settings.TIMETABLE_URL, post_data, headers=http_headers, timeout=8)
    except Exception as ex:  # Connection error to Dekanat site

        if settings.USE_CACHE:
            request_key = '{}{} : {} > {}'.format(group.lower(), teacher, sdate, edate)
            cached_timetable = core.Cache.get_from_cache(request_key)

            if cached_timetable:

                m = '\U000026A0 Встановити з\'єднання із сайтом Деканату не вдалося, тому показую розклад ' \
                    'станом на {} ' \
                    '(теоретично, його вже могли змінити)'.format(cached_timetable[0][2][11:])
                bot.send_message(user_id, m, reply_markup=keyboard)
                core.log(m='Розклад видано з кешу')
                return json.loads(cached_timetable[0][1])

        core.log(m='Помилка з\'єднання із сайтом Деканату.')
        bot.send_message(user_id, 'Помилка з\'єднання із сайтом Деканату. Спробуй пізніше.', reply_markup=keyboard)
        return False

    parsed_page = BeautifulSoup(page.content, 'html5lib')
    all_days_list = parsed_page.find_all('div', class_='col-md-6')[1:]
    all_days_lessons = []

    for one_day_table in all_days_list:
        all_days_lessons.append({
            'day': one_day_table.find('h4').find('small').text,
            'date': one_day_table.find('h4').text[:5],
            'lessons': [' '.join(lesson.text.split()) for lesson in one_day_table.find_all('td')[2::3]]
        })

    return all_days_lessons


def render_day_timetable(day_data):

    day_timetable = '.....::::: <b>\U0001F4CB {}</b> - <i>{}</i> :::::.....\n\n'.format(day_data['day'], day_data['date'])

    lessons = day_data['lessons']

    start_index = 0
    end_index = len(lessons) - 1

    for i in range(8):
        if lessons[i]:
            start_index = i
            break

    for i in range(end_index, -1, -1):
        if lessons[i]:
            end_index = i
            break

    timetable = ['9:00 - 10:20', '10:30 - 11:50', '12:10 - 13:30', '13:40 - 15:00',
                 '15:20 - 16:40 ', '16:50 - 18:10', '18:20 - 19:40', '-']

    for i in range(start_index, end_index + 1):
        if lessons[i]:
            day_timetable += '{} <i>{}</i> \n{}\n\n'.format(emoji_numbers[i+1], timetable[i], lessons[i])
        else:
            day_timetable += '{} <i>{}</i>\nВікно \U0001F483\U0001F57A\n\n'.format(emoji_numbers[i+1], timetable[i])

    return day_timetable


@bot.message_handler(commands=['cu'])
def update_cache(message):

    user = core.User(message.chat)

    if len(message.text.split()) == 2:
        count = message.text.split()[1]
    else:
        count = 40

    if str(user.get_id()) not in settings.ADMINS_ID:
        bot.send_message(user.get_id(), 'Немає доступу :(')
        return

    bot.send_message(user.get_id(), 'Починаю оновлення розкладу.', reply_markup=keyboard, parse_mode='HTML')

    s = schedule_updater.update_cache(count)

    bot.send_message(user.get_id(), s, reply_markup=keyboard, parse_mode='HTML')


@bot.message_handler(commands=['ci'])
def cache_info(message):

    user = core.User(message.chat)

    cache_items_count = len(core.Cache.get_keys() or [])
    cache_requests = core.Cache.get_requests_to_cache()

    ans = 'В кеші <b>{}</b> записи(ів).\n' \
          'Кількість звернень: <b>{}</b>.\n'.format(cache_items_count, cache_requests[0][0])

    bot.send_message(user.get_id(), ans, reply_markup=keyboard, parse_mode='HTML')


@bot.message_handler(commands=['cc'])
def clear_cache(message):

    user = core.User(message.chat)

    if str(user.get_id()) not in settings.ADMINS_ID:
        bot.send_message(user.get_id(), 'Немає доступу :(')
        return

    core.Cache.clear_cache()

    bot.send_message(user.get_id(), 'Кеш був очищений.')


@bot.message_handler(commands=['log'])
def get_logs(message):

    user = core.User(message.chat)

    if str(user.get_id()) not in settings.ADMINS_ID:
        bot.send_message(user.get_id(), 'Немає доступу :(')
        return

    if len(message.text.split()) == 2:
        count = int(message.text.split()[1])
    else:
        count = 65

    with open(os.path.join(settings.BASE_DIR, 'bot_log.txt'), 'r', encoding="utf-8") as log_file:
        log_lines = log_file.readlines()

    logs = ''

    for line in log_lines[-count:]:
        logs += line

    bot.send_message(user.get_id(), logs, reply_markup=keyboard)


@bot.message_handler(commands=['start'])
def start_handler(message):

    msg = 'Хай, {} 😊. Я Бот розкладу для студентів ЖДУ ім.Івана Франка. Я можу показати твій розклад на сьогодні, ' \
          'на завтра, по викладачу, по групі і так далі. ' \
          'Для початку скажи мені свою групу (Напр. 44_і_д), ' \
          '<b>змінити ти її зможеш в пункті меню {}</b>'.format(message.chat.first_name, KEYBOARD['HELP'])

    sent = bot.send_message(chat_id=message.chat.id, text=msg, parse_mode='HTML')
    bot.register_next_step_handler(sent, set_group)


@bot.callback_query_handler(func=lambda call_back: call_back.data in ('Поточний', 'Наступний'))
def week_schedule_handler(call_back):

    user = core.User(call_back.message.chat)
    user_group = user.get_group()
    req = call_back.data

    today = datetime.date.today()
    current_week_day_number = today.isoweekday()
    diff_between_saturday_and_today = 6 - current_week_day_number
    last_week_day = today + datetime.timedelta(days=diff_between_saturday_and_today)

    next_week_first_day = today + datetime.timedelta(days=diff_between_saturday_and_today + 2)
    next_week_last_day = today + datetime.timedelta(days=diff_between_saturday_and_today + 7)

    if req == 'Поточний':
        timetable_data = get_timetable(group=user_group, sdate=today.strftime('%d.%m.%Y'),
                                       edate=last_week_day.strftime('%d.%m.%Y'), user_id=user.get_id())
    if req == 'Наступний':
        timetable_data = get_timetable(group=user_group, sdate=next_week_first_day.strftime('%d.%m.%Y'),
                                       edate=next_week_last_day.strftime('%d.%m.%Y'), user_id=user.get_id())

    timetable_for_week = ''

    if timetable_data:
        for timetable_day in timetable_data:
            timetable_for_week += render_day_timetable(timetable_day)

    elif isinstance(timetable_data, list) and not len(timetable_data):
        timetable_for_week = "На тиждень пар не знайдено."
        bot.delete_message(chat_id=user.get_id(), message_id=call_back.message.message_id)
        bot_send_message_and_post_check_group(user.get_id(), timetable_for_week, user_group)
        return

    bot.delete_message(chat_id=user.get_id(), message_id=call_back.message.message_id)
    bot.send_message(text=timetable_for_week[:4090], chat_id=user.get_id(),
                     parse_mode="HTML", reply_markup=keyboard)


def bot_send_message_and_post_check_group(chat_id='', text='', user_group='', parse_mode='HTML'):

    if not core.is_group_valid(user_group):
        possible_groups = core.get_possible_groups(user_group)
        text += '\n\nТвоєї групи <b>{}</b> немає в базі розкладу, ' \
                'тому перевір правильність вводу.'.format(user_group)

        if possible_groups:
            text += '\n<b>Можливі варіанти:</b>\n'
            for possible_group in possible_groups:
                text += '{}\n'.format(possible_group.get('group'))

        text += '\nЩоб змінити групу жми {} > {}'.format(KEYBOARD['HELP'], KEYBOARD['CHANGE_GROUP'])

    bot.send_message(chat_id=chat_id, text=text, parse_mode=parse_mode, reply_markup=keyboard)


def set_group(message):

    user = core.User(message.chat)
    group = message.text

    if group in list(KEYBOARD.values()):
        msg = 'Введи назву групи'
        sent = bot.send_message(message.chat.id, msg, parse_mode='HTML')
        bot.register_next_step_handler(sent, set_group)
        return

    if group == 'Відміна':
        current_user_group = user.get_group()
        bot.send_message(message.chat.id, 'Добре, залишимо групу {}.'.format(current_user_group), reply_markup=keyboard)
        return

    if not core.is_group_valid(group):

        possible_groups = core.get_possible_groups(group)
        msg = 'Групу <b>{}</b> я зберіг, але її немає в базі розкладу. ' \
              'Тому якщо розклад не буде відображатись - перевір правильність вводу.\n\n' \
              '<i>Щоб змінити групу жми: </i>{} > {}\n'.format(group, KEYBOARD['HELP'], KEYBOARD['CHANGE_GROUP'])

        if possible_groups:
            msg += '<b>Можливі варіанти:</b>\n'
            for possible_group in possible_groups:
                msg += '{}\n'.format(possible_group.get('group'))

    else:
        msg = 'Добро 👍, буду показувати розклад для групи {}.'.format(group)

    user.update_group(group) if user.get_group() else user.registration(group)

    bot.send_message(message.chat.id, msg, reply_markup=keyboard, parse_mode='HTML')


def show_teachers(chat_id, name):

    in_week = datetime.date.today() + datetime.timedelta(days=7)

    in_week_day = in_week.strftime('%d.%m.%Y')
    today = datetime.date.today().strftime('%d.%m.%Y')

    rozklad_data = get_timetable(teacher=name, sdate=today, edate=in_week_day, user_id=chat_id)

    if rozklad_data:
        rozklad_for_week = 'Розклад на тиждень у <b>{}</b>:\n\n'.format(name)
        for rozklad_day in rozklad_data:
            rozklad_for_week += render_day_timetable(rozklad_day)
    else:
        rozklad_for_week = 'На тиждень пар у викладача <b>{}</b> не знайдено.'.format(name)

    bot.send_message(chat_id, rozklad_for_week, reply_markup=keyboard, parse_mode='HTML')


def select_teacher_from_request(message):  # ф-я викликається коли є 2 і більше викладачі з таким прізвищем

    if message.text == 'Назад':
        bot.send_message(message.chat.id, 'Окей)', reply_markup=keyboard)
        return

    show_teachers(message.chat.id, message.text)


def select_teachers(message):

    core.log(message.chat, '> (по викладачу) {}'.format(message.text))
    tchrs = []

    try:
        with open(os.path.join(settings.BASE_DIR, 'teachers.txt'), 'r', encoding="utf-8") as file:
            all_teachers = json.loads(file.read())
    except Exception as ex:
        bot.send_message(message.chat.id, 'Даний функціонал тимчасово не працює.', reply_markup=keyboard)
        core.log(m='Помилка із файлом викладачів: {}'.format(str(ex)))
        return

    for teacher in all_teachers:
        if teacher.split()[0].upper() == message.text.upper().split()[0]:
            tchrs.append(teacher)

    if not tchrs:
        msg = 'Не можу знайти викладача з прізвищем <b>{}</b>. Якщо при вводі була допущена помилка ' \
              '- знову натисни в меню кнопку "{}" і введи заново.'.format(message.text, KEYBOARD['FOR_A_TEACHER'])

        bot.send_message(message.chat.id, msg, reply_markup=keyboard, parse_mode='HTML')
        return

    if len(tchrs) == 1:
        show_teachers(message.chat.id, tchrs[0])
        return

    if len(tchrs) > 1:

        teachers_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for teacher in tchrs:
            teachers_keyboard.row(teacher)

        teachers_keyboard.row('Назад')
        sent = bot.send_message(message.chat.id, 'Вибери викладача:', reply_markup=teachers_keyboard)
        bot.register_next_step_handler(sent, select_teacher_from_request)
        return


def show_other_group(message):

    group = message.text
    core.log(message.chat, '> (по групі) {}'.format(group))
    bot.send_chat_action(message.chat.id, "typing")

    if group == KEYBOARD['MAIN_MENU']:
        bot.send_message(message.chat.id, 'Окей', reply_markup=keyboard, parse_mode='HTML')
        return

    if not core.is_group_valid(group):

        possible_groups = core.get_possible_groups(group)
        msg = 'Групи <b>{}</b> немає в базі розкладу.\n'.format(group)

        if possible_groups:

            msg += '<b>Можливі варіанти:</b>\n'
            groups_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)

            groups_kb.row(KEYBOARD['MAIN_MENU'])

            for group in possible_groups:
                msg += '{}\n'.format(group.get('group'))
                groups_kb.row(group.get('group'))

            sent = bot.send_message(message.chat.id, msg, parse_mode='HTML', reply_markup=groups_kb)
            bot.register_next_step_handler(sent, show_other_group)
            return

        bot.send_message(message.chat.id, msg, reply_markup=keyboard, parse_mode='HTML')
        return

    in_week = datetime.date.today() + datetime.timedelta(days=7)
    in_week_day = in_week.strftime('%d.%m.%Y')
    today = datetime.date.today().strftime('%d.%m.%Y')

    timetable_data = get_timetable(group=group, sdate=today, edate=in_week_day, user_id=message.chat.id)
    timetable_for_week = '<b>Розклад на тиждень для групи {}:</b>\n\n'.format(message.text)

    if timetable_data:
        for timetable_day in timetable_data:
            timetable_for_week += render_day_timetable(timetable_day)
    elif isinstance(timetable_data, list) and not len(timetable_data):
        timetable_for_week = 'На тиждень пар для групи {} не знайдено.'.format(group)
    else:
        return

    bot.send_message(message.chat.id, timetable_for_week[:4090], parse_mode='HTML', reply_markup=keyboard)


@app.route('/fl/login', methods=['POST', 'GET'])
def admin_login():

    if session.get('login'):
        return admin_metrics()

    if request.method == 'GET':
        return render_template('login.html')

    req_ip = request.remote_addr
    req_agent = request.user_agent

    data = {
        'parse_mode': 'HTML',
        'chat_id': '204560928',
    }

    if request.method == 'POST' and request.form.get('password') == settings.ADMIN_PASSWORD:
        session['login'] = True

        data['text'] = 'Авторизація в панелі адміністратора.\n<b>IP: </b>{}\n<b>UA: </b>{}'.format(req_ip, req_agent)
        requests.get('https://api.telegram.org/bot{}/sendMessage'.format(settings.BOT_TOKEN), params=data)

        return admin_metrics()

    else:

        data['text'] = 'Неправильний пароль під час авторизації в панелі адміністратора.\n' \
                       '<b>IP: </b>{}\n<b>UA: </b>{}'.format(req_ip, req_agent)
        requests.get('https://api.telegram.org/bot{}/sendMessage'.format(settings.BOT_TOKEN), params=data)

        return 'Bad password'


@app.route('/fl/logout')
def admin_logout():

    if session.get('login'):
        session['login'] = False
    return admin_login()


@app.route('/fl/metrics')
def admin_metrics():

    if not session.get('login'):
        return admin_login()

    all_users_count = core.MetricsManager.get_all_users_count()
    all_groups_count = core.MetricsManager.get_all_groups_count()
    users_registered_week = core.MetricsManager.get_number_of_users_registered_during_the_week()
    active_today_users_count = core.MetricsManager.get_active_today_users_count()
    active_yesterday_users_count = core.MetricsManager.get_active_yesterday_users_count()
    active_week_users_count = core.MetricsManager.get_active_week_users_count()

    try:
        forecast_update_date = os.path.getmtime(os.path.join(settings.BASE_DIR, 'groups.txt'))
        groups_update_time = datetime.datetime.fromtimestamp(forecast_update_date).strftime('%d.%m.%Y %H:%M')
    except Exception:
        groups_update_time = '-'

    try:
        forecast_update_date = os.path.getmtime(os.path.join(settings.BASE_DIR, 'teachers.txt'))
        teachers_update_time = datetime.datetime.fromtimestamp(forecast_update_date).strftime('%d.%m.%Y %H:%M')
    except Exception:
        teachers_update_time = '-'

    metrics_values = {
        'all_users_count': all_users_count,
        'all_groups_count': all_groups_count,
        'users_registered_week': users_registered_week,
        'active_today_users_count': active_today_users_count,
        'active_yesterday_users_count': active_yesterday_users_count,
        'active_week_users_count': active_week_users_count,

        'groups_update_time': groups_update_time,
        'teachers_update_time': teachers_update_time,
    }

    return render_template('metrics.html', data=metrics_values)


@app.route('/fl/del_user/<user_id>')
def admin_del_user(user_id):

    if not session.get('login'):
        return admin_login()

    data = {}

    u = core.User.get_userinfo_by_id(user_id)
    core.User.delete_user(user_id)

    if u:
        data['message'] = 'Користувач <b>{} {}</b> був успішно видалений. <br> ' \
                          '<b>група:</b> {}, <b>реєстрація:</b> {}, ' \
                          '<b>остання активність:</b> {}'.format(u[2], u[3] or '', u[4], u[5], u[6])
    else:
        data['message'] = 'Такого користувача не знайдено.'

    users = core.MetricsManager.get_users()
    data['users'] = users

    return render_template('users.html', data=data)


@app.route('/fl/users')
def admin_users():

    if not session.get('login'):
        return admin_login()

    data = {
        'users': core.MetricsManager.get_users()
    }

    return render_template('users.html', data=data)


@app.route('/fl/send_message', methods=['POST', 'GET'])
def admin_send_message():

    if not session.get('login'):
        return admin_login()

    telegram_id = request.form.get('usr-id')
    text = str(request.form.get('text')).strip()

    data = {
        'chat_id': telegram_id,
        'parse_mode': 'HTML',
        'text': '\U0001f916 <b>Бот</b>:\n\n' + text
    }

    r = requests.get('https://api.telegram.org/bot{}/sendMessage'.format(settings.BOT_TOKEN), params=data).json()

    if r.get('ok'):
        data['message'] = 'Відправлено: <b>{}</b>'.format(text)
    else:
        data['message'] = 'Помилка {}: {}'.format(r.get('error_code'), r.get('description'))

    return admin_user_statistics(telegram_id, data['message'])


@app.route('/fl/statistics_by_types_during_the_week')
def statistics_by_types_during_the_week():

    stats = core.MetricsManager.get_statistics_by_types_during_the_week()

    return jsonify(data=stats)


@app.route('/fl/last_days_statistics')
def last_days_statistics():

    days_statistics = core.MetricsManager.get_last_days_statistics()

    stats = {'labels': [], 'data': []}

    def sort_by_date(input_str):
        return datetime.datetime.strptime(input_str + '.' + str(datetime.date.today().year), '%d.%m.%Y')

    # Sorting by dates
    for day_stat in sorted(days_statistics, key=sort_by_date):

        stats['labels'].append(day_stat)
        stats['data'].append(days_statistics[day_stat])

    return jsonify(data=stats)


@app.route('/fl/last_hours_statistics')
def last_hours_statistics():

    today_hours_statistics = core.MetricsManager.get_hours_statistics()
    yesterday_hours_statistics = core.MetricsManager.get_hours_statistics(day_delta=1)
    two_days_ago_statistics = core.MetricsManager.get_hours_statistics(day_delta=2)

    stats = {'labels': [], 'stats_data': {'today': [], 'yesterday': [], 'two_days_ago': []}}

    def sort_by_date(input_str):
        return datetime.datetime.strptime(input_str, '%Y-%m-%d %H:%M')

    [stats['labels'].append('{}:00'.format(hour) ) for hour in range(24)]

    for day_stat in sorted(today_hours_statistics, key=sort_by_date):
        stats['stats_data']['today'].append(today_hours_statistics[day_stat])

    for day_stat in sorted(yesterday_hours_statistics, key=sort_by_date):
        stats['stats_data']['yesterday'].append(yesterday_hours_statistics[day_stat])

    for day_stat in sorted(two_days_ago_statistics, key=sort_by_date):
        stats['stats_data']['two_days_ago'].append(two_days_ago_statistics[day_stat])

    return jsonify(data=stats)

@app.route('/fl/update_groups')
def admin_update_groups():

    if not session.get('login'):
        return admin_login()

    updated = core.update_all_groups()

    if updated:
        msg = 'Список груп оновлено. Завантажено {} груп.<br>'.format(len(updated))
        msg += str(updated)
        return msg
    return 'Помилка при оновленні'


@app.route('/fl/update_teachers')
def admin_update_teachers():

    if not session.get('login'):
        return admin_login()

    updated = core.update_all_teachers()

    if updated:
        msg = 'Список викладачів оновлено. Завантажено {} імен.<br>'.format(len(updated))
        msg += str(updated)
        return msg
    return 'Помилка при оновленні'


@app.route('/fl/user/<user_id>')
def admin_user_statistics(user_id, msg=''):

    if not session.get('login'):
        return admin_login()

    data = {
        'user': core.User.get_userinfo_by_id(user_id),
        'actions': core.MetricsManager.get_stats_by_user_id(user_id),
        'message': msg
    }

    return render_template('user_stat.html', data=data)


@app.route('/fl/upd_cache_cron')
def admin_update_cache():

    bot.send_message('204560928', 'Починаю оновлення розкладу через крон.', reply_markup=keyboard, parse_mode='HTML')
    core.log(m='Оновлення розкладу через крон')

    msg = schedule_updater.update_cache(60)

    bot.send_message('204560928', msg, reply_markup=keyboard, parse_mode='HTML')

    core.log(m='Розклад по крону оновлено. ')
    msg = '<!doctype html>\n<head><meta charset="utf-8"><head>\n<body>' + msg + '</body></html>'

    return msg


@app.route('/fl/run')
def index():

    if not session.get('login'):
        return admin_login()

    core.User.create_user_table_if_not_exists()
    core.MetricsManager.create_metrics_table_if_not_exists()
    core.Cache.create_cache_table_if_not_exists()
    bot.delete_webhook()
    bot.set_webhook(settings.WEBHOOK_URL + settings.WEBHOOK_PATH, max_connections=1)
    bot.send_message('204560928', 'Running...')
    core.log(m='Запуск через url. Веб-хук встановлено: {}.'.format(bot.get_webhook_info().url))
    return 'ok'


@app.route(settings.WEBHOOK_PATH, methods=['POST', 'GET'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "!", 200


@bot.message_handler(content_types=["text"])
def main_menu(message):

    bot.send_chat_action(message.chat.id, "typing")

    user = core.User(message.chat)
    user_group = user.get_group()
    request = message.text

    if user_group:

        def is_date_request_or_other():

            if re.search(r'^(\d{1,2})\.(\d{1,2})$', request) or \
               re.search(r'^(\d{1,2})\.(\d{1,2})-(\d{1,2})\.(\d{1,2})$', request) or \
               re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', request) or \
               re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})-(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', request):

                return 'FOR_A_DATE'

            return 'OTHER'

        # Reversed keys and values in dictionary
        request_code = {v: k for k, v in KEYBOARD.items()}.get(request, is_date_request_or_other())
        core.MetricsManager.track(user.get_id(), request_code, user_group)

        core.log(message.chat, '> {}'.format(message.text))

        if request == KEYBOARD['TODAY']:  # Today

            today = datetime.date.today().strftime('%d.%m.%Y')

            timetable_data = get_timetable(group=user_group, user_id=user.get_id(), sdate=today, edate=today)

            if timetable_data:
                timetable_for_today = render_day_timetable(timetable_data[0])
                bot.send_message(user.get_id(), timetable_for_today, parse_mode='HTML', reply_markup=keyboard)

            elif isinstance(timetable_data, list) and not len(timetable_data):
                timetable_for_today = "На сьогодні пар не знайдено."
                bot_send_message_and_post_check_group(user.get_id(), timetable_for_today, user_group)
                return

        elif request == KEYBOARD['TOMORROW']:  # Tomorrow

            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            tom_day = tomorrow.strftime('%d.%m.%Y')

            timetable_data = get_timetable(group=user_group, sdate=tom_day, edate=tom_day, user_id=user.get_id())

            if timetable_data:
                timetable_for_tomorrow = render_day_timetable(timetable_data[0])
                bot.send_message(user.get_id(), timetable_for_tomorrow, parse_mode='HTML', reply_markup=keyboard)

            elif isinstance(timetable_data, list) and not len(timetable_data):
                timetable_for_tomorrow = "На завтра пар не знайдено."
                bot_send_message_and_post_check_group(user.get_id(), timetable_for_tomorrow, user_group)
                return

        elif request == KEYBOARD['FOR_A_WEEK']:  # For a week

            if datetime.date.today().isoweekday() in (5, 6, 7):  # пт, сб, нд

                timetable_for_week = ''
                today = datetime.date.today()
                current_week_day_number = today.isoweekday()
                diff_between_saturday_and_today = 6 - current_week_day_number
                next_week_first_day = today + datetime.timedelta(days=diff_between_saturday_and_today + 2)
                next_week_last_day = today + datetime.timedelta(days=diff_between_saturday_and_today + 7)

                timetable_data = get_timetable(group=user_group, sdate=next_week_first_day.strftime('%d.%m.%Y'),
                                               edate=next_week_last_day.strftime('%d.%m.%Y'), user_id=user.get_id())

                if timetable_data:
                    for timetable_day in timetable_data:
                        timetable_for_week += render_day_timetable(timetable_day)

                    bot.send_message(text=timetable_for_week[:4090], chat_id=user.get_id(),
                                     reply_markup=keyboard, parse_mode="HTML")
                    return

                elif isinstance(timetable_data, list) and not len(timetable_data):
                    timetable_for_week = "На тиждень, з {} по {} пар не знайдено.".format(
                        next_week_first_day.strftime('%d.%m'), next_week_last_day.strftime('%d.%m'))

                    bot_send_message_and_post_check_group(user.get_id(), timetable_for_week, user_group)
                    return

            week_type_keyboard = telebot.types.InlineKeyboardMarkup()
            week_type_keyboard.row(
                *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
                  name in ["Поточний", "Наступний"]]
            )

            bot.send_message(user.get_id(), 'На який тиждень?', reply_markup=week_type_keyboard)

        elif request == KEYBOARD['TIMETABLE']:

            t = ''
            t += '{} - 9:00 - 10:20\n'.format(emoji_numbers[1])
            t += '{} - 10:30 - 11:50\n'.format(emoji_numbers[2])
            t += '{} - 12:10 - 13:30\n'.format(emoji_numbers[3])
            t += '{} - 13:40 - 15:00\n'.format(emoji_numbers[4])
            t += '{} - 15:20 - 16:40 \n'.format(emoji_numbers[5])
            t += '{} - 16:50 - 18:10 \n'.format(emoji_numbers[6])
            t += '{} - 18:20 - 19:40 \n'.format(emoji_numbers[7])

            bot.send_message(user.get_id(), t, reply_markup=keyboard)

        elif request == KEYBOARD['CHANGE_GROUP']:

            user_group = user.get_group()

            cancel_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            cancel_kb.row('Відміна')

            msg = 'Твоя група: {}\nЩоб змінити введи нову групу'.format(user_group)

            sent = bot.send_message(message.chat.id, msg, parse_mode='HTML', reply_markup=cancel_kb)
            bot.register_next_step_handler(sent, set_group)

        elif request == KEYBOARD['HELP']:

            requests_count = user.get_user_requests_count()

            try:
                forecast_update_date = os.path.getmtime(os.path.join(settings.BASE_DIR, 'forecast.txt'))
                mod_time = datetime.datetime.fromtimestamp(forecast_update_date).strftime('%H:%M')

            except Exception:
                mod_time = '-'

            msg = "Для пошуку по датам : <b>15.05</b>, <b>15.05-22.05</b>, <b>1.1.18-10.1.18</b>\n\n" \
                  "<b>Група:</b> <code>{}</code>\n" \
                  "<b>Запитів:</b> <code>{}</code>\n\n" \
                  "<b>Версія:</b> <code>{}</code>\n" \
                  "<b>Канал:</b> @zdu_news\n" \
                  "<b>Розробник:</b> @Koocherov\n"

            kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            kb.row(KEYBOARD['MAIN_MENU'])
            kb.row(KEYBOARD['CHANGE_GROUP'])

            bot.send_message(message.chat.id, msg.format(user.get_group(), requests_count, settings.VERSION, mod_time),
                             reply_markup=kb, parse_mode='HTML')

        elif request == KEYBOARD['FOR_A_GROUP']:
            sent = bot.send_message(message.chat.id,
                                    'Для того щоб подивитись розклад будь якої групи на тиждень введи її назву')
            bot.register_next_step_handler(sent, show_other_group)

        elif request == KEYBOARD['WEATHER']:

            try:

                weather_manager = WeatherManager()
                weather_manager.process_weather()

                with open(os.path.join(settings.BASE_DIR, 'forecast.txt'), 'r', encoding="utf-8") as forecast_file:
                    forecast = forecast_file.read()

                bot.send_message(message.chat.id, forecast, reply_markup=keyboard, parse_mode='HTML')

            except Exception:
                bot.send_message(message.chat.id, 'Погоду не завантажено.', reply_markup=keyboard, parse_mode='HTML')

        elif request == KEYBOARD['FOR_A_TEACHER']:

            sent = bot.send_message(message.chat.id,
                                    'Для того щоб подивитись розклад викладача на поточний тиждень - '
                                    'введи його прізвище.')
            bot.register_next_step_handler(sent, select_teachers)

        elif re.search(r'^(\d{1,2})\.(\d{1,2})$', request):

            date = request + '.' + str(datetime.date.today().year)
            timetable_data = get_timetable(group=user_group, edate=date, sdate=date, user_id=user.get_id())

            if timetable_data:
                timetable_for_date = render_day_timetable(timetable_data[0])

            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введи дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не треба</b> ' \

                timetable_for_date = 'На <b>{}</b>, для групи <b>{}</b> пар не знайдено.\n\n{}'.format(date,
                                                                                                       user_group,
                                                                                                       msg)
            else:
                return

            bot.send_message(message.chat.id, timetable_for_date, parse_mode='HTML', reply_markup=keyboard)

        elif re.search(r'^(\d{1,2})\.(\d{1,2})-(\d{1,2})\.(\d{1,2})$', request):

            s_date = message.text.split('-')[0] + '.' + str(datetime.date.today().year)
            e_date = message.text.split('-')[1] + '.' + str(datetime.date.today().year)
            timetable_for_days = ''
            timetable_data = get_timetable(group=user_group, sdate=s_date, edate=e_date, user_id=user.get_id())

            if timetable_data:
                for timetable_day in timetable_data:
                    timetable_for_days += render_day_timetable(timetable_day)

            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введи дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не треба</b> '
                timetable_for_days = 'На <b>{} - {}</b>, для групи <b>{}</b> пар не знайдено.\n\n{}'.format(s_date,
                                                                                                            e_date,
                                                                                                            user_group,
                                                                                                            msg)

            bot.send_message(user.get_id(), timetable_for_days[:4090], parse_mode='HTML', reply_markup=keyboard)

        elif re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', request):

            date = request
            timetable_data = get_timetable(group=user_group, edate=date, sdate=date, user_id=user.get_id())

            if timetable_data:
                timetable_for_date = render_day_timetable(timetable_data[0])
            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введи дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не треба</b> ' \

                timetable_for_date = 'На <b>{}</b>, для групи <b>{}</b> пар не знайдено.\n\n{}'.format(date,
                                                                                                       user_group,
                                                                                                       msg)

            bot.send_message(message.chat.id, timetable_for_date, parse_mode='HTML', reply_markup=keyboard)

        elif re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})-(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', request):

            s_date = request.split('-')[0]
            e_date = request.split('-')[1]
            timetable_for_days = ''
            timetable_data = get_timetable(group=user_group, sdate=s_date, edate=e_date, user_id=user.get_id())

            if timetable_data:
                for timetable_day in timetable_data:
                    timetable_for_days += render_day_timetable(timetable_day)

            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введи дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не треба</b> '
                timetable_for_days = 'На <b>{} - {}</b>, для групи <b>{}</b> пар не знайдено.\n\n{}'.format(s_date,
                                                                                                            e_date,
                                                                                                            user_group,
                                                                                                            msg)

            bot.send_message(user.get_id(), timetable_for_days[:4090], parse_mode='HTML', reply_markup=keyboard)

        elif request == KEYBOARD['MAIN_MENU']:
            bot.send_message(user.get_id(), 'Ок', reply_markup=keyboard)

        elif request.find('дякую') != -1 or request.find('Дякую') != -1:
            bot.send_message(user.get_id(), 'будь-ласка)', reply_markup=keyboard)

        else:
            answers = ['м?', 'хм.. \U0001F914', 'не розумію(', 'вибери потрібне в меню', 'моя твоя не понімать']
            bot.send_message(user.get_id(), random.choice(answers), reply_markup=keyboard)

    else:
        bot.send_message(user.get_id(), 'Не знайшов твою групу. Введи /start, і вкажи її.')


def main():

    core.User.create_user_table_if_not_exists()
    core.Cache.create_cache_table_if_not_exists()
    core.MetricsManager.create_metrics_table_if_not_exists()

    bot.delete_webhook()

    if settings.USE_WEBHOOK:
        try:
            bot.set_webhook(settings.WEBHOOK_URL + settings.WEBHOOK_PATH, max_connections=1)
            core.log(m='Веб-хук встановлено: {}'.format(bot.get_webhook_info().url))

        except Exception as ex:
            core.log(m='Помилка під час встановлення веб-хуку: {}'.format(str(ex)))

    try:
        core.log(m='Запуск...')
        bot.polling(none_stop=True, interval=settings.POLLING_INTERVAL)

    except Exception as ex:

        core.log(m='Помилка під час роботи: {}\n'.format(str(ex)))
        bot.stop_polling()

        if settings.SEND_ERRORS_TO_ADMIN:
            for admin in settings.ADMINS_ID:
                data = {
                    'chat_id': admin,
                    'text': 'Щось пішло не так.\n {}'.format(str(ex))
                }

                requests.get('https://api.telegram.org/bot{}/sendMessage'.format(settings.BOT_TOKEN), params=data)


if __name__ == "__main__":
    app.run(debug=True) if len(sys.argv) > 1 else main()
