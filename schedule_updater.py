# -*- coding: utf-8 -*-
from bs4 import BeautifulSoup
import copy
import core
import json
import time
import settings
import datetime
import requests


def get_timetable_to_cache(faculty='', teacher='', group='', sdate='', edate=''):

    http_headers = {
            'User-Agent': 'Telegram-SmartySBot CacheUpdater',
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
        core.log(m='Помилка у кодуванні post_data словника при оновленні кешу.: {}'.format(str(ex)))
        return False

    try:
        page = requests.post(settings.TIMETABLE_URL, post_data, headers=http_headers, timeout=12)
    except Exception as ex:  # Connection error to Dekanat site
        core.log(m='Помилка з\'єднання із сайтом Деканату під час оновлення кешу')
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

    if all_days_lessons:
        cached_all_days_lessons = copy.deepcopy(all_days_lessons)
        cached_all_days_lessons[0]['day'] += '*'
        _json = json.dumps(cached_all_days_lessons, sort_keys=True, ensure_ascii=False, separators=(',', ':'), indent=2)
        request_key = '{}{} : {} > {}'.format(group.lower(), teacher, sdate, edate)
        core.Cache.put_in_cache(request_key, _json)

    return all_days_lessons


def update_cache(groups_limit=3000):

    query = 'SELECT u_group, count(*) FROM users ' \
            'GROUP BY u_group ORDER BY count(*) DESC LIMIT {}'.format(groups_limit)

    groups = core.DBManager.execute_query(query)

    start_time = time.time()
    today = datetime.date.today().strftime('%d.%m.%Y')

    ans = 'Завантажено розклад для {} груп:\n\n'.format(len(groups))

    for group in groups:
        timetable = get_timetable_to_cache(group=group[0], sdate=today, edate=today)
        if timetable or isinstance(timetable, list):
            if not len(timetable):
                ans += '\U00002705 \U0001F534 {} - {}\n'.format(group[0], group[1])  # No lessons
            else:
                ans += '\U00002705 \U0001F535 {} - {}\n'.format(group[0], group[1])
        else:
            ans += '\U0000274E {} - {}\n'.format(group[0], group[1])


    ans += '\n\U0001F552 <b>Час:</b> {} с.'.format(round(time.time() - start_time, 2))
    core.log(m='Завантаження кешу. Кількість груп: {}, час: {}'.format(len(groups), round(time.time() - start_time, 2)))

    return ans

