# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import requests
import telebot
import datetime
import os
import settings
import core
import re
import cache
import json
import copy
from WeatherManager import WeatherManager
from settings import KEYBOARD
from flask import Flask, request, render_template, jsonify

app = Flask(__name__, template_folder='site', static_folder='site/static', static_url_path='/fl/static')
bot = telebot.TeleBot(settings.BOT_TOKEN, threaded=False)

keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
keyboard.row(KEYBOARD['TODAY'], KEYBOARD['TOMORROW'], KEYBOARD['FOR_A_WEEK'])
keyboard.row(KEYBOARD['FOR_A_TEACHER'], KEYBOARD['TIMETABLE'], KEYBOARD['FOR_A_GROUP'])
keyboard.row(KEYBOARD['CHANGE_GROUP'], KEYBOARD['WEATHER'], KEYBOARD['HELP'])

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
        bot.send_message(user_id, 'Помилка надсилання запиту, вкажіть коректні параметри.', reply_markup=keyboard)
        return False

    if settings.USE_CACHE:
        request_key = 'G:{}|T:{}|SD:{}|ED:{}'.format(group.lower(), teacher, sdate, edate)
        cached_timetable = cache.Cache.get_from_cache(request_key)

        if cached_timetable:
            return json.loads(cached_timetable[0][1])

    try:
        page = requests.post(settings.TIMETABLE_URL, post_data, headers=http_headers, timeout=6)
    except Exception as ex:
        core.log(m='Error with Dekanat site connection: {}'.format(str(ex)))
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

    if all_days_lessons and settings.USE_CACHE:  # if timetable exists, put it to cache
        cached_all_days_lessons = copy.deepcopy(all_days_lessons)
        cached_all_days_lessons[0]['day'] += '*'
        _json = json.dumps(cached_all_days_lessons, sort_keys=True, ensure_ascii=False, separators=(',', ':'), indent=2)
        cache.Cache.put_in_cache(request_key, _json)

    return all_days_lessons


def render_day_timetable(day_data):

    day_timetable = '.....::::: <b>\U0001F4CB {}</b> {} :::::.....\n\n'.format(day_data['day'], day_data['date'])
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

    for i in range(start_index, end_index + 1):
        if lessons[i]:
            day_timetable += '{} {}\n\n'.format(emoji_numbers[i + 1], lessons[i])
        else:
            day_timetable += '{} Вікно \U0001F643\n\n'.format(emoji_numbers[i + 1])

    return day_timetable


@bot.message_handler(commands=['ci'])
def cache_info(message):

    user = core.User(message.chat)

    if str(user.get_id()) not in settings.ADMINS_ID:
        return

    cache_items_count = len(cache.Cache.get_keys() or '')

    bot.send_message(user.get_id(), 'In cache: {} units'.format(cache_items_count))


@bot.message_handler(commands=['cc'])
def clear_cache(message):

    user = core.User(message.chat)

    if str(user.get_id()) not in settings.ADMINS_ID:
        return

    cache.Cache.clear_cache()

    bot.send_message(user.get_id(), 'The cache has been successfully cleaned.')


@bot.message_handler(commands=['log'])
def get_logs(message):

    user = core.User(message.chat)

    if str(user.get_id()) not in settings.ADMINS_ID:
        return

    with open(os.path.join(settings.BASE_DIR, 'bot_log.txt'), 'r', encoding="utf-8") as log_file:
        log_lines = log_file.readlines()

    logs = ''

    for line in log_lines[-55:]:
        logs += line

    bot.send_message(user.get_id(), logs, reply_markup=keyboard)


@bot.message_handler(commands=['start'])
def start(message):
    sent = bot.send_message(message.chat.id, 'Йоу, {} 😊. Я Бот, який допоможе тобі швидко дізнаватись свій розклад '
                                             'прямо тут. Для початку '
                                             'скажи мені свою групу (Напр. 44_і_д)'.format(message.chat.first_name))
    bot.register_next_step_handler(sent, set_group)


@bot.callback_query_handler(func=lambda call_back: call_back.data in ('Поточний', 'Наступний'))
def week_schedule_handler(call_back):

    user = core.User(call_back.message.chat)
    user_group = user.get_group()
    request = call_back.data

    today = datetime.date.today()
    current_week_day_number = today.isoweekday()
    diff_between_friday_and_today = 5 - current_week_day_number
    last_week_day = today + datetime.timedelta(days=diff_between_friday_and_today)

    next_week_first_day = today + datetime.timedelta(days=diff_between_friday_and_today + 3)
    next_week_last_day = today + datetime.timedelta(days=diff_between_friday_and_today + 7)

    if request == 'Поточний':

        if diff_between_friday_and_today < 0:  # TODO Del this condition
            bot.edit_message_text(text='Цей навчальний тиждень закінчивсь, дивись наступний.',
                                  chat_id=user.get_id(), message_id=call_back.message.message_id, parse_mode="HTML")
            return

        timetable_data = get_timetable(group=user_group, sdate=today.strftime('%d.%m.%Y'),
                                       edate=last_week_day.strftime('%d.%m.%Y'), user_id=user.get_id())
    if request == 'Наступний':
        timetable_data = get_timetable(group=user_group, sdate=next_week_first_day.strftime('%d.%m.%Y'),
                                       edate=next_week_last_day.strftime('%d.%m.%Y'), user_id=user.get_id())

    timetable_for_week = ''

    if timetable_data:
        for timetable_day in timetable_data:
            timetable_for_week += render_day_timetable(timetable_day)

        if len(timetable_for_week) > 5000:
            msg = "Перевищена кількість допустимих символів ({} із 5000).".format(len(timetable_for_week))
            bot.send_message(user.get_id(), msg, parse_mode='HTML', reply_markup=keyboard)
            return

    elif isinstance(timetable_data, list) and not len(timetable_data):
        timetable_for_week = "На тиждень пар не знайдено."
    else:
        return

    bot.edit_message_text(text=timetable_for_week, chat_id=user.get_id(),
                          message_id=call_back.message.message_id, parse_mode="HTML")


def set_group(message):

    user = core.User(message.chat)
    group = message.text

    if group == 'Відміна':
        current_user_group = user.get_group()
        bot.send_message(message.chat.id, 'Добре, залишимо групу {}.'.format(current_user_group), reply_markup=keyboard)
        return

    if ' ' in group:
        bot.send_message(message.chat.id, 'Група вказується без пробілів. А точно так, як на сайті.',
                         reply_markup=keyboard)
        return

    if user.get_group():
        user.update_group(group)
    else:
        user.registration(group)

    bot.send_message(message.chat.id, 'Чудово 👍, відтепер я буду показувати розклад для групи {}.'.
                     format(group), reply_markup=keyboard)


def get_teachers_name(surname):

    rez = []

    for teacher in settings.TEACHERS:
        if teacher.split()[0].upper() == surname.upper():
            rez.append(teacher)

    return rez


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

    tchrs = get_teachers_name(message.text)

    if not tchrs:
        bot.send_message(message.chat.id, 'Не можу знайти викладача з таким прізвищем.',
                         reply_markup=keyboard)

    if len(tchrs) == 1:
        show_teachers(message.chat.id, tchrs[0])

    if len(tchrs) > 1:

        teachers_keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for teacher in tchrs:
            teachers_keyboard.row(teacher)

        teachers_keyboard.row('Назад')
        sent = bot.send_message(message.chat.id, 'Вибери викладача:', reply_markup=teachers_keyboard)
        bot.register_next_step_handler(sent, select_teacher_from_request)


@bot.message_handler(content_types=["text"])
def main_menu(message):

    bot.send_chat_action(message.chat.id, "typing")

    user = core.User(message.chat)
    user_group = user.get_group()
    request = message.text

    if user_group:

        # Reversed keys and values in dictionary
        request_code = {v: k for k, v in KEYBOARD.items()}.get(request, 'OTHER')
        core.MetricsManager.track(user.get_id(), request_code, user_group)

        core.log(message.chat, '> {}'.format(message.text))

        if request == KEYBOARD['TODAY']:  # Today

            timetable_data = get_timetable(group=user_group, user_id=user.get_id())

            if timetable_data:
                timetable_for_today = render_day_timetable(timetable_data[0])
            elif isinstance(timetable_data, list) and not len(timetable_data):
                timetable_for_today = "На сьогодні пар не знайдено."
            else:
                return

            bot.send_message(user.get_id(), timetable_for_today, parse_mode='HTML', reply_markup=keyboard)

        elif request == KEYBOARD['TOMORROW']:  # Tomorrow

            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            tom_day = tomorrow.strftime('%d.%m.%Y')

            timetable_data = get_timetable(group=user_group, sdate=tom_day, edate=tom_day, user_id=user.get_id())

            if timetable_data:
                timetable_for_tomorrow = render_day_timetable(timetable_data[0])
            elif isinstance(timetable_data, list) and not len(timetable_data):
                timetable_for_tomorrow = "На завтра пар не знайдено."
            else:
                return

            bot.send_message(user.get_id(), timetable_for_tomorrow, parse_mode='HTML', reply_markup=keyboard)

        elif request == KEYBOARD['FOR_A_WEEK']:  # For a week

            if datetime.date.today().isoweekday() in (6, 7):  # If current day is Saturday or Sunday

                timetable_for_week = ''
                today = datetime.date.today()
                current_week_day_number = today.isoweekday()
                diff_between_friday_and_today = 5 - current_week_day_number
                next_week_first_day = today + datetime.timedelta(days=diff_between_friday_and_today + 3)
                next_week_last_day = today + datetime.timedelta(days=diff_between_friday_and_today + 7)

                timetable_data = get_timetable(group=user_group, sdate=next_week_first_day.strftime('%d.%m.%Y'),
                                               edate=next_week_last_day.strftime('%d.%m.%Y'), user_id=user.get_id())

                if timetable_data:
                    for timetable_day in timetable_data:
                        timetable_for_week += render_day_timetable(timetable_day)

                    if len(timetable_for_week) > 5000:
                        msg = "Перевищена кількість допустимих символів ({} із 5000).".format(len(timetable_for_week))
                        bot.send_message(user.get_id(), msg, parse_mode='HTML', reply_markup=keyboard)
                        return

                elif isinstance(timetable_data, list) and not len(timetable_data):
                    timetable_for_week = "На тиждень, з {} по {} пар не знайдено.".format(
                        next_week_first_day.strftime('%d.%m'), next_week_last_day.strftime('%d.%m'))

                bot.send_message(text=timetable_for_week, chat_id=user.get_id(),
                                 reply_markup=keyboard, parse_mode="HTML")

                return

            week_type_keyboard = telebot.types.InlineKeyboardMarkup()
            week_type_keyboard.row(
                *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
                  name in ["Поточний", "Наступний"]]
            )

            bot.send_message(user.get_id(), 'На який тиждень?', reply_markup=week_type_keyboard)

        elif request == KEYBOARD['TIMETABLE']:

            img = open(os.path.join(settings.BASE_DIR, 'timetable.png'), 'rb')

            bot.send_photo(user.get_id(), img, reply_markup=keyboard)

        elif request == KEYBOARD['CHANGE_GROUP']:

            user_group = user.get_group()

            cancel_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            cancel_kb.row('Відміна')

            msg = 'Твоя група: {}\nЩоб змінити введи нову групу'.format(user_group)

            sent = bot.send_message(message.chat.id, msg, parse_mode='HTML', reply_markup=cancel_kb)
            bot.register_next_step_handler(sent, set_group)

        elif request == KEYBOARD['HELP']:

            try:
                forecast_update_date = os.path.getmtime(os.path.join(settings.BASE_DIR, 'forecast.txt'))
                mod_time = datetime.datetime.fromtimestamp(forecast_update_date).strftime('%H:%M')

            except Exception:
                mod_time = '-'

            msg = "Для пошуку по датам : <b>15.05</b> або <b>15.05-22.05</b> або <b>1.1.18-10.1.18</b>\n\n" \
                  "<b>Версія:</b> {}\n<b>Оновлення погоди:</b> {}\n" \
                  "<b>Розробник:</b> @Koocherov\n"

            bot.send_message(message.chat.id, msg.format(settings.VERSION, mod_time),
                             reply_markup=keyboard, parse_mode='HTML')

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
                      '\nЯкщо розклад не приходить введи меншу кількість днів ' \
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

                if len(timetable_for_days) > 5000:
                    msg = "Введи меншу кількість днів." \
                          " Перевищена кількість допустимих символів ({} із 5000).".format(len(timetable_for_days))
                    bot.send_message(user.get_id(), msg, parse_mode='HTML', reply_markup=keyboard)
                    return

            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введи дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nЯкщо розклад не приходить введи меншу кількість днів.' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не треба</b> '
                timetable_for_days = 'На <b>{} - {}</b>, для групи <b>{}</b> пар не знайдено.\n\n{}'.format(s_date,
                                                                                                            e_date,
                                                                                                            user_group,
                                                                                                            msg)
            else:
                return

            bot.send_message(user.get_id(), timetable_for_days, parse_mode='HTML', reply_markup=keyboard)

        elif re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', request):

            date = request
            timetable_data = get_timetable(group=user_group, edate=date, sdate=date, user_id=user.get_id())

            if timetable_data:
                timetable_for_date = render_day_timetable(timetable_data[0])
            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введи дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nЯкщо розклад не приходить введи меншу кількість днів ' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не треба</b> ' \

                timetable_for_date = 'На <b>{}</b>, для групи <b>{}</b> пар не знайдено.\n\n{}'.format(date,
                                                                                                       user_group,
                                                                                                       msg)
            else:
                return

            bot.send_message(message.chat.id, timetable_for_date, parse_mode='HTML', reply_markup=keyboard)

        elif re.search(r'^(\d{1,2})\.(\d{1,2})\.(\d{2,4})-(\d{1,2})\.(\d{1,2})\.(\d{2,4})$', request):

            s_date = request.split('-')[0]
            e_date = request.split('-')[1]
            timetable_for_days = ''
            timetable_data = get_timetable(group=user_group, sdate=s_date, edate=e_date, user_id=user.get_id())

            if timetable_data:
                for timetable_day in timetable_data:
                    timetable_for_days += render_day_timetable(timetable_day)

                if len(timetable_for_days) > 5000:
                    msg = "Введи меншу кількість днів." \
                          " Перевищена кількість допустимих символів ({} із 5000).".format(len(timetable_for_days))
                    bot.send_message(user.get_id(), msg, parse_mode='HTML', reply_markup=keyboard)
                    return

            elif isinstance(timetable_data, list) and not len(timetable_data):
                msg = 'Щоб подивитися розклад на конкретний день, введи дату в такому форматі:' \
                      '\n<b>05.03</b> або <b>5.3</b>\nПо кільком дням: \n<b>5.03-15.03</b>\n' \
                      '\nЯкщо розклад не приходить введи меншу кількість днів.' \
                      '\nДата вводиться без пробілів (день.місяць)<b> рік вводити не треба</b> '
                timetable_for_days = 'На <b>{} - {}</b>, для групи <b>{}</b> пар не знайдено.\n\n{}'.format(s_date,
                                                                                                            e_date,
                                                                                                            user_group,
                                                                                                            msg)
            else:
                return

            bot.send_message(user.get_id(), timetable_for_days, parse_mode='HTML', reply_markup=keyboard)

        else:
            bot.send_message(user.get_id(), '\U0001F914', reply_markup=keyboard)

    else:
        bot.send_message(message.chat.id, 'Щоб вказати групу жми -> /start')


def show_other_group(message):

    group = message.text

    if ' ' in group:
        bot.send_message(message.chat.id, 'В назві групи не може бути пробілів.',
                         reply_markup=keyboard)
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

    bot.send_message(message.chat.id, timetable_for_week, parse_mode='HTML', reply_markup=keyboard)


@app.route('/fl/metrics')
def admin_metrics():

    all_users_count = core.MetricsManager.get_all_users_count()
    all_groups_count = core.MetricsManager.get_all_groups_count()
    users_registered_week = core.MetricsManager.get_number_of_users_registered_during_the_week()
    active_today_users_count = core.MetricsManager.get_active_today_users_count()
    active_yesterday_users_count = core.MetricsManager.get_active_yesterday_users_count()
    active_week_users_count = core.MetricsManager.get_active_week_users_count()

    metrics_values = {
        'all_users_count': all_users_count,
        'all_groups_count': all_groups_count,
        'users_registered_week': users_registered_week,
        'active_today_users_count': active_today_users_count,
        'active_yesterday_users_count': active_yesterday_users_count,
        'active_week_users_count': active_week_users_count,
    }

    return render_template('metrics.html', data=metrics_values)


@app.route('/fl/statistics_by_types_during_the_week')
def statistics_by_types_during_the_week():

    stats = core.MetricsManager.get_statistics_by_types_during_the_week()

    return jsonify(data=stats)


@app.route('/fl/last_days_statistics')
def last_days_statistics():

    days_statistics = core.MetricsManager.get_last_days_statistics()

    stats = {'labels': [], 'data': []}

    # Sorting by dates
    for day_stat in sorted(days_statistics):

        stats['labels'].append(day_stat)
        stats['data'].append(days_statistics[day_stat])

    return jsonify(data=stats)


@app.route('/fl/run')
def index():
    core.User.create_user_table_if_not_exists()
    core.MetricsManager.create_metrics_table_if_not_exists()
    bot.delete_webhook()
    bot.set_webhook(settings.WEBHOOK_URL + settings.WEBHOOK_PATH, max_connections=1)
    bot.send_message('204560928', 'Running...')
    core.log(m='Webhook is setting: {} by run url'.format(bot.get_webhook_info().url))
    return 'ok'


@app.route(settings.WEBHOOK_PATH, methods=['POST', 'GET'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "!", 200


def main():

    core.User.create_user_table_if_not_exists()
    cache.Cache.create_cache_table_if_not_exists()
    core.MetricsManager.create_metrics_table_if_not_exists()

    bot.delete_webhook()

    if settings.USE_WEBHOOK:
        try:
            bot.set_webhook(settings.WEBHOOK_URL + settings.WEBHOOK_PATH, max_connections=1)
            core.log(m='Webhook is setting: {}'.format(bot.get_webhook_info().url))

        except Exception as ex:
            core.log(m='Error while setting webhook: {}'.format(str(ex)))

    try:
        core.log(m='Running..')
        bot.polling(none_stop=True, interval=settings.POLLING_INTERVAL)

    except Exception as ex:

        core.log(m='Working error: {}\n'.format(str(ex)))
        bot.stop_polling()

        if settings.SEND_ERRORS_TO_ADMIN:
            for admin in settings.ADMINS_ID:
                data = {
                    'chat_id': admin,
                    'text': 'Something go wrong.\nError: {}'.format(str(ex))
                }

                requests.get('https://api.telegram.org/bot{}/sendMessage'.format(settings.BOT_TOKEN), params=data)


if __name__ == "__main__":
    main()
    #app.run(debug=True)
