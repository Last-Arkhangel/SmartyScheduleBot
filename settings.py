# -*- coding: utf-8 -*-
import os
import json

# Database name
DATABASE = '***_SS_DB.sqlite'

# Telegram Bot token
BOT_TOKEN = os.getenv('SSB_TOKEN') or '********:*********'

# Admin password
ADMIN_PASSWORD = os.getenv('SSB_ADMIN_PASSWD') or '*******'

# Interval to polling telegram servers (Uses if USE_WEBHOOK sets False)
POLLING_INTERVAL = 2

# Timeout to polling telegram servers
POLLING_TIMEOUT = 5

# Use cache
USE_CACHE = os.getenv('SSB_USE_CACHE') or True

# Use webhook instead polling
USE_WEBHOOK = os.getenv('SSB_USE_WEBHOOK') or False

# Address bot running. For example https://mydomain.com
WEBHOOK_DOMAINS = {
    '1': 'https://**********.ua:8443',
    '2': 'https://**********.ua',
    '3': 'https://**********.ua',
}

# Path that telegram sends updates
WEBHOOK_PATH = ADMIN_PASSWORD

# In some VPS you may need to put here the IP addr
WEBHOOK_LISTEN = '192.168.1.1'  

# 443, 80, 88 or 8443 (port need to be 'open')
WEBHOOK_PORT = 8443

# Path to the ssl certificate
WEBHOOK_SSL_CERT = 'server.crt'

# Path to the ssl private key  
WEBHOOK_SSL_PRIV = 'server.key'  

# Debug 'sets False'
WEBHOOK_DEBUG = False

# Timetable URL
TIMETABLE_URL = os.getenv('SSB_TIMETABLE_URL') or 'https://********.ua/cgi-bin/timetable.cgi'

# Export URL
API_LINK = os.getenv('SSB_API_LINK') or 'https://********.ua/cgi-bin/timetable_export.cgi'

# Http user agent sends to requests
HTTP_USER_AGENT = '***_SS_Bot'

# Number of teachers to save
NUMBER_OF_TEACHERS_TO_SAVE = 4

# Show time to end
SHOW_TIME_TO_LESSON_END = True

# If it True, bot would send errors to admins in list below
SEND_ERRORS_TO_ADMIN = True

# Show lessons from the first even it isn`t.
# If it is True, "data/lessons_time.json" and "data/breaks_time.json" should exists
SHOW_LESSONS_FROM_THE_FIRST = True

# Admins IDS. My
ADMINS_ID = 123456789

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
     
    'HELP': '\U00002139 Довідка',
    'ADS': '\U0001F4E2 Оголошення',
    'AD_LIST': '\U0001F4F0 Список',
    'AD_ADD': '\U00002795 Додати',
    'AD_DEL': '\U0000274C Видалити',
    'CHANGE_GROUP': '\U00002699 Змінити групу',
    'MAIN_MENU': '\U0001F519 Меню',
    'INPUT_GROUP': '\U0000270F Ввести іншу групу',
}

if os.path.exists(os.path.join(BASE_DIR, 'data', 'lessons_time.json')):
    load_file = os.path.join(BASE_DIR, 'data', 'lessons_time.json')

    with open(load_file) as file:
        lessons_time = json.loads(file.read())

if os.path.exists(os.path.join(BASE_DIR, 'data', 'breaks_time.json')):
    load_file = os.path.join(BASE_DIR, 'data', 'breaks_time.json')

    with open(load_file) as file:
        breaks_time = json.loads(file.read())
