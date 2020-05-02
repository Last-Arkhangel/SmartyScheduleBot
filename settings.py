# -*- coding: utf-8 -*-
import os

# Database name
DATABASE = 'SmartyS_DB.sqlite'

# Telegram Bot token
BOT_TOKEN = '<token>'

# OpenWeatherMap.org token
OPEN_WEATHER_MAP_TOKEN = '<token>'

# Admin password
ADMIN_PASSWORD = '<pass>'

# Interval to polling telegram servers (Uses if USE_WEBHOOK sets False)
POLLING_INTERVAL = 2

# Use cache
USE_CACHE = True

# Use webhook instead polling
USE_WEBHOOK = False

# Address bot running. For example https://mydomain.com
WEBHOOK_DOMAINS = {
    '1': 'https://openbiblio.zu.edu.ua',
    '2': 'https://bot.zu.edu.ua:8443',
    '3': 'https://koocherov.pythonanywhere.com',
}

# Path that telegram sends updates
WEBHOOK_PATH = ADMIN_PASSWORD

# Timetable URL
TIMETABLE_URL = 'https://dekanat.zu.edu.ua/cgi-bin/timetable.cgi'

# Export URL
API_LINK = 'https://dekanat.zu.edu.ua/cgi-bin/timetable_export.cgi'

# Http user agent sends to requests
HTTP_USER_AGENT = 'Telegram-SmartySBot'

# Number of teachers to save
NUMBER_OF_TEACHERS_TO_SAVE = 4

# Limit how many days can contain one message. When user gets timetable by dates
LIMIT_OF_DAYS_PER_ONE_MESSAGE_IN_TO_DATE_TIMETABLE = 6

# Show time to end
SHOW_TIME_TO_LESSON_END = True

# If it True, bot would send errors to admins in list below
SEND_ERRORS_TO_ADMIN = True

# Show lessons from the first even it isn`t
SHOW_LESSONS_FROM_THE_FIRST = True

# Admins IDS. My, Vlad, Mum, Yaroslav
ADMINS_ID = ['204560928', '203448442', '525808450', '947097358']

# Base folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Keyboard buttons
KEYBOARD = {
    'TODAY': '\U0001F4D8 Сьогодні',
    'TOMORROW': '\U0001F4D9 Завтра',
    'FOR_A_WEEK': '\U0001F4DA Тиждень',
    'FOR_A_TEACHER': '\U0001F464 По викл.',
    'TIMETABLE': '\U0001F552 Час пар',
    'FOR_A_GROUP': '\U0001F465 По групі',
    'WEATHER': '\U0001F30D Погода',
    'HELP': '\U00002139 Довідка',
    'ADS': '\U0001F4E2 Оголошення',
    'AD_LIST': '\U0001F4F0 Список',
    'AD_ADD': '\U00002795 Додати',
    'AD_DEL': '\U0000274C Видалити',
    'CHANGE_GROUP': '\U00002699 Зм. групу',
    'MAIN_MENU': '\U0001F519 Меню',
    'INPUT_GROUP': '\U0000270F Ввести іншу групу',
}

lessons_time = ({
                    'start_time': (9, 0),
                    'end_time': (10, 20)
                },
                {
                    'start_time': (10, 30),
                    'end_time': (11, 50)
                },
                {
                    'start_time': (12, 10),
                    'end_time': (13, 30)
                },
                {
                    'start_time': (13, 40),
                    'end_time': (15, 0)
                },
                {
                    'start_time': (15, 20),
                    'end_time': (16, 40)
                },
                {
                    'start_time': (16, 50),
                    'end_time': (18, 10)
                },
                {
                    'start_time': (18, 20),
                    'end_time': (19, 40)
                })

breaks_time = ({
                   'start_time': (10, 20),
                   'end_time': (10, 30)
               },
               {
                   'start_time': (11, 50),
                   'end_time': (12, 10)
               },
               {
                   'start_time': (13, 30),
                   'end_time': (13, 40)
               },
               {
                   'start_time': (15, 00),
                   'end_time': (15, 20)
               },
               {
                   'start_time': (16, 40),
                   'end_time': (16, 50)
               },
               {
                   'start_time': (18, 10),
                   'end_time': (18, 20)
               })
