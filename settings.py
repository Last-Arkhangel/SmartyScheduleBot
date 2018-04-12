# -*- coding: utf-8 -*-
import os

# Bot version
VERSION = '8.3'

# Database name
DATABASE = 'SmartyS_DB.sqlite'

# Telegram Bot token
BOT_TOKEN = '<token>'

# OpenWeatherMap.org token
OPEN_WEATHER_MAP_TOKEN = '<token>'

# Interval to polling telegram servers (Uses if USE_WEBHOOK sets False)
POLLING_INTERVAL = 1

# Use cache
USE_CACHE = False

# Use webhook instead polling
USE_WEBHOOK = True

# Address bot running. For example https://mydomain.com
WEBHOOK_URL = '/<url>'

# Path that telegram sends updates
WEBHOOK_PATH = '/fl/'

# Timetable URL
TIMETABLE_URL = 'https://dekanat.zu.edu.ua/cgi-bin/timetable.cgi'

# Http user agent sends to requests
HTTP_USER_AGENT = 'Telegram-SmartySBot'

# If it True, bot would send errors to admins in list below
SEND_ERRORS_TO_ADMIN = True

# Admins IDS
ADMINS_ID = ['204560928', '203448442']

# Base folder
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Keyboard buttons
KEYBOARD = {
    'TODAY': '\U0001F4D7 Сьогодні',
    'TOMORROW': '\U0001F4D8 Завтра',
    'FOR_A_WEEK': '\U0001F4DA На тиждень',
    'FOR_A_TEACHER': '\U0001F464 По викладачу',
    'TIMETABLE': '\U0001F552 Час пар',
    'FOR_A_GROUP': '\U0001F465 По групі',
    'WEATHER': '\U0001F308 Погода',
    'HELP': '\U0001F4AC Довідка',

    'CHANGE_GROUP': '\U00002699 Зм. групу',
    'MAIN_MENU': '\U0001F519 Меню',
    'BOT_CHANEL': '\U0001F4A1',
}
