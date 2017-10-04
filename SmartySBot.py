# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import requests
import telebot
import datetime
import sqlite3
import os
import settings

#  __________________________________________________ROZKLAD__________________________________________________________


def get_rozklad(faculty='', teacher='', group='', sdate='', edate=''):

    med_url = 'http://46.219.3.50:8080/cgi-bin/timetable.cgi?n=700'
    med_groups = ['302сс/бак\n', ]

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

        log(m='Помилка в роботі із словником post_data - {}\n'.format(str(ex)))
        return False

    try:

        if group in med_groups:
            page = requests.post(med_url, post_data, headers=http_headers)
        else:
            page = requests.post(settings.TIMETABLE_URL, post_data, headers=http_headers, timeout=5)
    except Exception as ex:

        log(m='Помилка з підключенням - {}\n'.format(str(ex)))
        return False

    parsed_page = BeautifulSoup(page.content, 'html.parser')
    all_days_list = parsed_page.find_all('div', class_='col-md-6')[1:]
    all_days_lessons = []

    for day_table in all_days_list:
        all_days_lessons.append({
            'day': day_table.find('h4').find('small').text,
            'date': day_table.find('h4').text[:10],
            'lessons': [' '.join(lesson.text.split()) for lesson in day_table.find_all('td')[1::2]]
        })

    return all_days_lessons

#  ____________________________________________________BOT__________________________________________________________
connection = sqlite3.connect(os.path.join(settings.BASE_DIR, settings.DATABASE_NAME), check_same_thread=False)

bot = telebot.TeleBot(settings.BOT_TOKEN)

keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
keyboard.row('\U0001F4D7 Сьогодні', '\U0001F4D8 Завтра', '\U0001F4DA На тижні')
keyboard.row('\U0001F464 По викладачу', '\U0001F570 Час пар', '\U0001F465 По групі')
keyboard.row('\U00002699 Зм. групу', '\U0001F308 Погода', '\U0001f4ac Довідка')

emoji_numbers = ['0⃣', '1⃣', '2⃣', '3⃣', '4⃣', '5⃣', '6⃣', '7⃣', '8⃣', '9⃣']


def log(chat=None, m=''):

    now_time = datetime.datetime.now().strftime('%d-%m %H:%M:%S')

    with open(os.path.join(settings.BASE_DIR, 'bot_log.txt'), 'a') as log_file:
        if chat:
            log_file.write('[{}]: ({} {}) {}\n'.format(now_time, chat.first_name, chat.last_name, m))
        else:
            log_file.write('[{}]: (Server) {}\n'.format(now_time, m))

    if not chat:
        return

    try:
        cursor = connection.cursor()
        cursor.execute("""UPDATE users SET requests_count=requests_count+1, last_use_date=?, first_name=?, last_name=? 
        WHERE t_id=?""", (now_time, chat.first_name, chat.last_name, chat.id))
        connection.commit()
        cursor.close()

    except Exception as ex:
        log(m='Помилка при оновленні даних про користувача: ' + str(ex))


def create_database():

    cursor = connection.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
                      t_id TEXT PRIMARY KEY NOT NULL,
                      username TEXT,
                      first_name TEXT,
                      last_name TEXT,
                      u_group TEXT,
                      register_date TEXT,
                      last_use_date TEXT,
                      requests_count INTEGER DEFAULT 0) WITHOUT ROWID""")
    connection.commit()
    cursor.close()


def get_user_group(user_id):

    try:
        cursor = connection.cursor()
        cursor.execute("""SELECT u_group FROM users WHERE t_id=?""", (user_id,))
        connection.commit()
        user_group = cursor.fetchone()
        cursor.close()
    except Exception as ex:
        connection.rollback()
        log(m='Помилка при отриманні групи - {}'.format(str(ex)))
        return False

    if not user_group:
        return False
    return user_group[0]


def add_or_update_user_to_db(chat, group):

    if not get_user_group(chat.id):

        now_time = datetime.datetime.now().strftime('%d-%m-%Y %H:%M:%S')
        try:
            cursor = connection.cursor()
            cursor.execute("INSERT INTO users (t_id, username, first_name, last_name, u_group, register_date) "
                           "VALUES (?, ?, ?, ?, ?, ?)",
                           (chat.id, chat.username, chat.first_name, chat.last_name, group, now_time))
            connection.commit()
            cursor.close()

            log(chat=chat, m='вказав свою групу - {}'.format(group))

        except Exception as ex:
            connection.rollback()
            log(m='Помилка при додаванні користувача - {}'.format(str(ex)))

    else:

        try:
            cursor = connection.cursor()
            cursor.execute("""UPDATE users SET u_group=? WHERE t_id=?""", (group, chat.id))
            connection.commit()
            cursor.close()
            log(chat=chat, m='змінив свою групу на - {}'.format(group))

        except Exception as ex:
            connection.rollback()
            log(m='Помилка при оновленні групи користувача - {}'.format(str(ex)))


def show_day_rozklad(day_data):

    rozklad = '.....::::: <b>\U0001F4CB {}</b> ({}) :::::.....\n\n'.format(day_data['day'], day_data['date'][:-5:])

    lessons = day_data['lessons']

    for i in range(8):
        if lessons[i]:
            s_index = i
            break

    for i in range(7, -1, -1):
        if lessons[i]:
            e_index = i
            break

    for i in range(s_index, e_index + 1):
        if lessons[i]:
            rozklad += '{} {}\n\n'.format(emoji_numbers[i + 1], lessons[i])
        else:
            rozklad += '{} Вікно \U0001F643\n\n'.format(emoji_numbers[i + 1])

    return rozklad


@bot.message_handler(commands=['start'])
def start(message):
    sent = bot.send_message(message.chat.id, 'Йоу, {} 😊. Я Бот який допоможе тобі швидко дізнаватись свій розклад прямо тут.'
                                             ' Для початку скажи мені свою групу (Напр. 44_і_д)'.format(message.chat.first_name))
    bot.register_next_step_handler(sent, set_group)


def set_group(message):

    if message.text == 'Відміна':
        user_group = get_user_group(message.chat.id)
        bot.send_message(message.chat.id, 'Добре, залишимо групу {}.'.format(user_group), reply_markup=keyboard)
        return

    if ' ' in message.text:
        bot.send_message(message.chat.id, 'Група вказується без пробілів. А точно так, як на сайті.',
                         reply_markup=keyboard)
        return

    add_or_update_user_to_db(message.chat, message.text)

    bot.send_message(message.chat.id, 'Чудово 👍, відтепер я буду показувати розклад для групи {}.'.
                     format(message.text), reply_markup=keyboard)


@bot.message_handler(regexp='^(\d{1,2})\.(\d{1,2})$')
def to_date(message):

    group = get_user_group(message.chat.id)

    if not group:
        bot.send_message(message.chat.id, 'Щоб вказати групу жми -> /start')
        return

    date = message.text + '.' + settings.YEAR
    rozklad_data = get_rozklad(group=group, edate=date, sdate=date)

    log(chat=message.chat, m='Розклад по даті {}'.format(date))

    if rozklad_data:
        rozklad_for_date = show_day_rozklad(rozklad_data[0])
    else:
        msg = 'Щоб подивитися розклад на конкретний день, введи дату в одному із таких форматів:' \
              '\n<b>05.03</b>\n<b>27.03</b>\n<b>5.3</b>' \
              '\nДля відображення по кільком дням (рекомендується не більше 8 днів підряд):\n<b>20.03-22.03</b>\n' \
              '\n<i>Вводиться без пробілів (день.місяць)</i><b> рік вводити не треба</b> ' \
              '<i>Якщо розклад по кільком дням не працює - введіть меншу кількість днів.</i>'
        rozklad_for_date = 'На <b>{}</b>, для групи <b>{}</b> пар не знайдено.\n\n{}'.format(date, group, msg)

    bot.send_message(message.chat.id, rozklad_for_date, parse_mode='HTML', reply_markup=keyboard)


@bot.message_handler(regexp='^(\d{1,2})\.(\d{1,2})-(\d{1,2})\.(\d{1,2})$')
def from_date_to_date(message):

    group = get_user_group(message.chat.id)

    if not group:
        bot.send_message(message.chat.id, 'Щоб вказати групу жми -> /start')
        return

    _sdate = message.text.split('-')[0] + '.' + settings.YEAR
    _edate = message.text.split('-')[1] + '.' + settings.YEAR

    rozklad_data = get_rozklad(group=group, sdate=_sdate, edate=_edate)

    rozklad_for_days = ''

    log(chat=message.chat, m='Розклад по датах {}'.format(message.text))

    if rozklad_data:
        for rozklad_day in rozklad_data:
            rozklad_for_days += show_day_rozklad(rozklad_day)

    else:
        msg = 'Щоб подивитися розклад на конкретний день, введи дату в одному із таких форматів:' \
              '\n<b>05.03</b>\n<b>27.03</b>\n<b>5.3</b>' \
              '\nДля відображення по кільком дням (рекомендується не більше 8 днів підряд):\n<b>20.03-22.03</b>\n' \
              '\n<i>Вводиться без пробілів (день.місяць)</i><b> рік вводити не треба.</b> ' \
              '<i>Якщо розклад по кільком дням не працює - введіть меншу кількість днів.</i>'
        rozklad_for_days = 'На <b>{}-{}</b>, для групи <b>{}</b> пар не знайдено.\n\n{}'.format(_sdate, _edate,
                                                                                                group, msg)

    bot.send_message(message.chat.id, rozklad_for_days, parse_mode='HTML', reply_markup=keyboard)


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

    rozklad_data = get_rozklad(teacher=name, sdate=today, edate=in_week_day)

    rozklad_for_week = ''

    if rozklad_data:
        rozklad_for_week = 'Розклад на тиждень у <b>{}</b>:\n\n'.format(name)
        for rozklad_day in rozklad_data:
            rozklad_for_week += show_day_rozklad(rozklad_day)
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

    if get_user_group(message.chat.id):

        log(message.chat, '> {}'.format(message.text))

        if message.text == '\U0001F4D7 Сьогодні':
            group = get_user_group(message.chat.id)
            rozklad_data = get_rozklad(group=group)

            if rozklad_data:
                rozklad_for_today = show_day_rozklad(rozklad_data[0])
            else:
                rozklad_for_today = "На сьогодні пар не знайдено."

            bot.send_message(message.chat.id, rozklad_for_today, parse_mode='HTML', reply_markup=keyboard)

        elif message.text == '\U0001F4D8 Завтра':

            tomorrow = datetime.date.today() + datetime.timedelta(days=1)
            tom_day = tomorrow.strftime('%d.%m.%Y')

            group = get_user_group(message.chat.id)
            rozklad_data = get_rozklad(group=group, sdate=tom_day, edate=tom_day)

            if rozklad_data:
                rozklad_for_tom = show_day_rozklad(rozklad_data[0])
            else:
                rozklad_for_tom = 'На завтра пар не знайдено.'

            bot.send_message(message.chat.id, rozklad_for_tom, parse_mode='HTML', reply_markup=keyboard)

        elif message.text == '\U0001F4DA На тижні':

            in_week = datetime.date.today() + datetime.timedelta(days=7)

            in_week_day = in_week.strftime('%d.%m.%Y')
            today = datetime.date.today().strftime('%d.%m.%Y')

            group = get_user_group(message.chat.id)
            rozklad_data = get_rozklad(group=group, sdate=today, edate=in_week_day)

            rozklad_for_week = ''

            if rozklad_data:
                for rozklad_day in rozklad_data:
                    rozklad_for_week += show_day_rozklad(rozklad_day)
            else:
                rozklad_for_week = 'На тиждень пар не знайдено.'

            if len(rozklad_for_week) < 4100:
                bot.send_message(message.chat.id, rozklad_for_week, parse_mode='HTML', reply_markup=keyboard)

            else:
                rozklad_for_week = ''

                for rozklad_day in rozklad_data[1:]:
                    rozklad_for_week += show_day_rozklad(rozklad_day)

                bot.send_message(message.chat.id, rozklad_for_week, parse_mode='HTML', reply_markup=keyboard)

        elif message.text == '\U0001F570 Час пар':
            lessons_time = "<b>Час пар:</b>\n" \
                           "{} 08:30-09:50\n{} 10:00-11:20\n" \
                           "{} 11:40-13:00\n{} 13:10-14:30\n" \
                           "{} 14:40-16:00\n{} 16:20-17:40 \n" \
                           "{} 17:50-19:10\n{} 19:20-20:40".format(emoji_numbers[1], emoji_numbers[2], emoji_numbers[3],
                                                                   emoji_numbers[4], emoji_numbers[5], emoji_numbers[6],
                                                                   emoji_numbers[7], emoji_numbers[8])

            bot.send_message(message.chat.id, lessons_time, parse_mode='HTML', reply_markup=keyboard)

        elif message.text == '\U00002699 Зм. групу':

            user_group = get_user_group(message.chat.id)

            cancel_kb = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            cancel_kb.row('Відміна')

            msg = 'Твоя група: {}\nЩоб змінити введи нову групу'.format(user_group)

            sent = bot.send_message(message.chat.id, msg, parse_mode='HTML', reply_markup=cancel_kb)
            bot.register_next_step_handler(sent, set_group)

        elif message.text == '\U0001f4ac Довідка':

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

            bot.send_message(message.chat.id, msg.format(settings.VERSION, mod_time), reply_markup=keyboard, parse_mode='HTML')

        elif message.text == '\U0001F465 По групі':
            sent = bot.send_message(message.chat.id,
                                    'Для того щоб подивитись розклад будь якої групи на тиждень введи її назву',
                                    reply_markup=keyboard)
            bot.register_next_step_handler(sent, show_other_group)

        elif message.text == '\U0001F4C5 По даті':

            msg = 'Щоб подивитися розклад на конкретний день, введи дату в одному із таких форматів:' \
                  '\n<b>05.03</b>\n<b>27.03</b>\n<b>5.3</b>' \
                  '\nДля відображення по кільком дням (рекомендується не більше 8 днів підряд):\n<b>20.03-22.03</b>\n' \
                  '\n<i>Вводиться без пробілів (день.місяць) </i><b>рік вводити не треба</b>. ' \
                  '<i>Якщо розклад по кільком дням не працює - введіть меншу кількість днів.</i>'

            bot.send_message(message.chat.id, msg, reply_markup=keyboard, parse_mode='HTML')

        elif message.text == '\U0001F308 Погода':

            try:
                with open(os.path.join(settings.BASE_DIR, 'forecast.txt'), 'r') as forecast_file:
                    forecast = forecast_file.read()

                bot.send_message(message.chat.id, forecast, reply_markup=keyboard, parse_mode='HTML')
            except Exception:

                bot.send_message(message.chat.id, 'Погоду не завантажено.', reply_markup=keyboard, parse_mode='HTML')

        elif message.text == '\U0001F464 По викладачу':

            sent = bot.send_message(message.chat.id,
                                    'Для того щоб подивитись розклад викладача на поточний тиждень - '
                                    'введи його прізвище.',
                                    reply_markup=keyboard)
            bot.register_next_step_handler(sent, select_teachers)

        else:
            bot.send_message(message.chat.id, '\U0001F440')

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

    rozklad_data = get_rozklad(group=group, sdate=today, edate=in_week_day)

    rozklad_for_week = '<b>Розклад на тиждень групи {}:</b>\n\n'.format(message.text)

    if rozklad_data:
        for rozklad_day in rozklad_data:
            rozklad_for_week += show_day_rozklad(rozklad_day)
    else:
        rozklad_for_week = 'На тиждень пар для групи {} не знайдено.'.format(group)

    if len(rozklad_for_week) < 4100:
        bot.send_message(message.chat.id, rozklad_for_week, parse_mode='HTML', reply_markup=keyboard)

    else:
        rozklad_for_week = ''

        for rozklad_day in rozklad_data[1:]:
            rozklad_for_week += show_day_rozklad(rozklad_day)

        bot.send_message(message.chat.id, rozklad_for_week, parse_mode='HTML', reply_markup=keyboard)


#  ____________________________________________________SERVER__________________________________________________________


if __name__ == '__main__':

    create_database()

    try:
        log(m='Запуск..')
        bot.polling(none_stop=True, interval=settings.POLLING_INTERVAL)

    except Exception as ex:

        log(m='Помилка - {}\n'.format(str(ex)))
        bot.stop_polling()

        if settings.SEND_ERRORS_TO_ADMIN:
            for admin in settings.ADMINS_ID:
                data = {
                    'chat_id': admin,
                    'text': 'Something go wrong.\nError: {}'.format(str(ex))
                }

                requests.get('https://api.telegram.org/bot{}/sendMessage'.format(settings.BOT_TOKEN), params=data)
