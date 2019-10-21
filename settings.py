# -*- coding: utf-8 -*-
import os

# Bot version
VERSION = '10.0'

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
USE_WEBHOOK = True

# Address bot running. For example https://mydomain.com
WEBHOOK_URL = '/<url>'

# Path that telegram sends updates
WEBHOOK_PATH = '/fl/'

# Timetable URL
TIMETABLE_URL = 'https://dekanat.zu.edu.ua/cgi-bin/timetable.cgi'

# Http user agent sends to requests
HTTP_USER_AGENT = 'Telegram-SmartySBot v.{}'.format(VERSION)

# If it True, bot would send errors to admins in list below
SEND_ERRORS_TO_ADMIN = True

# Show lessons from the first even it isn`t
SHOW_LESSONS_FROM_THE_FIRST = False

# Admins IDS. My, Vlad, Mum, Yaroslav
ADMINS_ID = ['204560928', '203448442', '525808450', '947097358']

# Base folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Keyboard buttons
KEYBOARD = {
    'TODAY': '\U0001F4D8 Сьогодні',
    'TOMORROW': '\U0001F4D9 Завтра',
    'FOR_A_WEEK': '\U0001F4DA Тиждень',
    'FOR_A_TEACHER': '\U0001F464 По викладачу',
    'TIMETABLE': '\U0001F552 Час пар',
    'FOR_A_GROUP': '\U0001F465 По групі',
    'WEATHER': '\U0001F30D Погода',
    'HELP': '\U0001F4AC Довідка',
    'ADS': '\U0001F4E2 Оголошення',
    'AD_LIST': '\U0001F4F0 Список',
    'AD_ADD': '\U00002795 Додати',
    'AD_DEL': '\U0000274C Видалити',
    'CHANGE_GROUP': '\U00002699 Зм. групу',
    'MAIN_MENU': '\U0001F519 Меню',
}
