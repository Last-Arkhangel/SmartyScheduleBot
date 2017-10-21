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
import flask

app = flask.Flask(__name__)
bot = telebot.TeleBot(settings.BOT_TOKEN, threaded=False)

keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
keyboard.row('\U0001F4D7 Сьогодні', '\U0001F4D8 Завтра', '\U0001F4DA На тиждень')
keyboard.row('\U0001F464 По викладачу', '\U0001F570 Час пар', '\U0001F465 По групі')
keyboard.row('\U00002699 Зм. групу', '\U0001F308 Погода', '\U0001f4ac Довідка')

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
        page = requests.post(settings.TIMETABLE_URL, post_data, headers=http_headers, timeout=4)
    except Exception as ex:
        core.log(m='Error with Dekanat site connection: {}'.format(str(ex)))
        bot.send_message(user_id, 'Помилка з\'єднання із сайтом Деканату. Спробуй пізніше.', reply_markup=keyboard)
        return False

    parsed_page = BeautifulSoup(page.content, 'html.parser')
    all_days_list = parsed_page.find_all('div', class_='col-md-6')[1:]
    all_days_lessons = []

    for one_day_table in all_days_list:
        all_days_lessons.append({
            'day': one_day_table.find('h4').find('small').text,
            'date': one_day_table.find('h4').text[:5],
            'lessons': [' '.join(lesson.text.split()) for lesson in one_day_table.find_all('td')[1::2]]
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
    end_index = 7

    for i in range(8):
        if lessons[i]:
            start_index = i
            break

    for i in range(7, -1, -1):
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
def start(message):

    user = core.User(message.chat)

    cache_items_count = len(cache.Cache.get_keys() or '')

    bot.send_message(user.get_id(), 'In cache: {} rows'.format(cache_items_count))


@bot.message_handler(commands=['cc'])
def start(message):

    user = core.User(message.chat)

    cache.Cache.clear_cache()

    bot.send_message(user.get_id(), 'Cache have been cleared.')


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

        if diff_between_friday_and_today < 0:
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

        core.log(message.chat, '> {}'.format(message.text))

        if request == '\U0001F4D7 Сьогодні':

            timetable_data = get_timetable(group=user_group, user_id=user.get_id())

            if timetable_data:
                timetable_for_today = render_day_timetable(timetable_data[0])
            elif isinstance(timetable_data, list) and not len(timetable_data):
                timetable_for_today = "На сьогодні пар не знайдено."
            else:
                return

            bot.send_message(user.get_id(), timetable_for_today, parse_mode='HTML', reply_markup=keyboard)

        elif request == '\U0001F4D8 Завтра':

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

        elif request == '\U0001F4DA На тижні' or request == '\U0001F4DA На тиждень':

            week_type_keyboard = telebot.types.InlineKeyboardMarkup()
            week_type_keyboard.row(
                *[telebot.types.InlineKeyboardButton(text=name, callback_data=name) for
                  name in ["Поточний", "Наступний"]]
            )

            bot.send_message(user.get_id(), 'На який саме?', reply_markup=week_type_keyboard)

        elif request == '\U0001F570 Час пар':
            lessons_time = "<b>Час пар:</b>\n" \
                           "{} 08:30-09:50\n{} 10:00-11:20\n" \
                           "{} 11:40-13:00\n{} 13:10-14:30\n" \
                           "{} 14:40-16:00\n{} 16:20-17:40 \n" \
                           "{} 17:50-19:10\n{} 19:20-20:40".format(emoji_numbers[1], emoji_numbers[2], emoji_numbers[3],
                                                                   emoji_numbers[4], emoji_numbers[5], emoji_numbers[6],
                                                                   emoji_numbers[7], emoji_numbers[8])

            bot.send_message(user.get_id(), lessons_time, parse_mode='HTML', reply_markup=keyboard)

        elif request == '\U00002699 Зм. групу':

            user_group = user.get_group()

            cancel_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            cancel_kb.row('Відміна')

            msg = 'Твоя група: {}\nЩоб змінити введи нову групу'.format(user_group)

            sent = bot.send_message(message.chat.id, msg, parse_mode='HTML', reply_markup=cancel_kb)
            bot.register_next_step_handler(sent, set_group)

        elif request == '\U0001f4ac Довідка':

            try:
                forecast_update_date = os.path.getmtime(os.path.join(settings.BASE_DIR, 'forecast.txt'))
                mod_time = datetime.datetime.fromtimestamp(forecast_update_date).strftime('%H:%M')

            except Exception:
                mod_time = '-'

            msg = "Для пошуку розкладу по конкретним датам вводь:\n " \
                  "<b> 15.05</b> - по дню\n <b> 15.05-22.05</b> - по кільком дням\n" \
                  "__________________________\n" \
                  "Якщо ти маєш пропозиції щодо покращення, повідомлення про помилки " \
                  "пиши сюди:\n <b>Телеграм:</b> @Koocherov \n <b>VK:</b> vk.com/koocherov\n" \
                  "__________________________\n<b>Версія:</b> {}\n<b>Оновлення погоди:</b> {}"

            bot.send_message(message.chat.id, msg.format(settings.VERSION, mod_time),
                             reply_markup=keyboard, parse_mode='HTML')

        elif request == '\U0001F465 По групі':
            sent = bot.send_message(message.chat.id,
                                    'Для того щоб подивитись розклад будь якої групи на тиждень введи її назву')
            bot.register_next_step_handler(sent, show_other_group)

        elif request == '\U0001F308 Погода':

            try:
                with open(os.path.join(settings.BASE_DIR, 'forecast.txt'), 'r') as forecast_file:
                    forecast = forecast_file.read()

                bot.send_message(message.chat.id, forecast, reply_markup=keyboard, parse_mode='HTML')
            except Exception:

                bot.send_message(message.chat.id, 'Погоду не завантажено.', reply_markup=keyboard, parse_mode='HTML')

        elif request == '\U0001F464 По викладачу':

            sent = bot.send_message(message.chat.id,
                                    'Для того щоб подивитись розклад викладача на поточний тиждень - '
                                    'введи його прізвище.',
                                    reply_markup=keyboard)
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
                timetable_for_days = 'На <b>{} - {}</b>, для групи <b>{}</b> пар не знайдено.\n\n{}'.format(s_date, e_date,
                                                                                                            user_group, msg)
            else:
                return

            bot.send_message(user.get_id(), timetable_for_days, parse_mode='HTML', reply_markup=keyboard)

        else:
            bot.send_message(user.get_id(), '\U0001F440', reply_markup=keyboard)

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


@app.route('/')
def index():
    return 'index'


@app.route(settings.WEBHOOK_PATH, methods=['POST'])
def webhook():
    json_string = flask.request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])

    return "!", 200


def main():

    core.User.create_user_table_if_not_exists()
    bot.delete_webhook()

    if settings.USE_CACHE:
        cache.Cache.create_cache_table_if_not_exists()
        # cache.Cache.clear_cache()

    if settings.USE_WEBHOOK:
        try:
            bot.set_webhook(settings.WEBHOOK_URL+settings.WEBHOOK_PATH)
            core.log(m='Webhook is setting: {}'.format(bot.get_webhook_info().url))
            return

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


main()
