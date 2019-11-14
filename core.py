import settings
import sqlite3
import os
import datetime
import json
import requests


class User:

    def __init__(self, chat=None, u_id=0):
        self.id = u_id or chat.id
        self.chat = chat

    def get_id(self):
        return self.id

    def get_group(self):

        query = "SELECT u_group FROM users WHERE t_id=?"

        result = DBManager.execute_query(query, (self.id,))

        if type(result) == bool:
            return False

        # TODO add return error code if there are problems getting the group
        # something like - if type(result) == bool: return -1

        self.update_user_metadata()

        return result[0][0]

    def get_users_count_from_group(self):

        user_group = self.get_group()

        query = "SELECT count(*) FROM users WHERE u_group = ?"

        result = DBManager.execute_query(query, (user_group,))

        return result[0][0]

    def update_group(self, group):

        log(self.chat, 'Оновлення групи {}'.format(group))

        group = group.lower()
        group = delete_html_tags(group)

        query = "UPDATE users SET u_group=? WHERE t_id=?"
        return DBManager.execute_query(query, (group, self.id))

    def registration(self, group):

        log(self.chat, 'Новий користувач: ({})'.format(group))

        group = group.lower()
        group = delete_html_tags(group)

        query = "INSERT INTO users (t_id, username, first_name, last_name, u_group, register_date) " \
                "VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))"

        return DBManager.execute_query(query,
                                       (self.id, self.chat.username, self.chat.first_name,
                                        self.chat.last_name, group))
    
    def update_user_metadata(self):

        query = "UPDATE users SET requests_count=requests_count+1, last_use_date=datetime('now', 'localtime')," \
                "first_name=?, last_name=?, username=? WHERE t_id=?"

        return DBManager.execute_query(query, (self.chat.first_name, self.chat.last_name, self.chat.username, self.id,))

    @classmethod
    def create_user_table_if_not_exists(cls):

        query = """CREATE TABLE IF NOT EXISTS users(
                      t_id TEXT PRIMARY KEY NOT NULL,
                      username TEXT,
                      first_name TEXT,
                      last_name TEXT,
                      u_group TEXT,
                      last_teacher TEXT,
                      register_date TEXT DEFAULT (datetime('now', 'localtime')),
                      last_use_date DEFAULT (datetime('now', 'localtime')),
                      requests_count INTEGER DEFAULT 0) WITHOUT ROWID"""

        return DBManager.execute_query(query)

    @classmethod
    def get_userinfo_by_id(cls, t_id):

        query = "SELECT * FROM users WHERE t_id=?"

        result = DBManager.execute_query(query, (t_id,))

        if type(result) == bool:
            return False

        return result[0]

    @classmethod
    def delete_user(cls, t_id):

        query = "DELETE FROM users WHERE t_id=?"

        return DBManager.execute_query(query, (t_id,))

    def get_user_requests_count(self):

        query = "SELECT requests_count FROM users WHERE t_id=?"

        return DBManager.execute_query(query, (self.get_id(),))[0][0]

    def set_last_teacher(self, teacher_name=''):

        query = "UPDATE users SET last_teacher=? WHERE t_id=?"

        return DBManager.execute_query(query, (teacher_name, self.get_id(),))

    def get_last_teacher(self):

        query = "SELECT last_teacher FROM users WHERE t_id=?"

        return DBManager.execute_query(query, (self.get_id(),))[0][0]

    @classmethod
    def get_users(cls):

        query = """SELECT * From users"""

        users_selection = DBManager.execute_query(query)

        users = []

        if not users_selection:
            return users

        for user in users_selection:
            users.append({
                'telegram_id': user[0],
                'username': user[1] or '-',
                'first_name': user[2],
                'last_name': user[3] or '-',
                'group': user[4],
                'last_teacher': user[5] or '-',
                'register_date': user[6],
                'last_use_date': user[7],
                'requests_count': user[8],
            })

        return users


class DBManager:

    @classmethod
    def execute_query(cls, query, *args):  # returns result or true if success, or false when something go wrong

        try:
            connection = sqlite3.connect(os.path.join(settings.BASE_DIR, settings.DATABASE), check_same_thread=False)

            cursor = connection.cursor()
            cursor.execute(query, *args)
            connection.commit()
            query_result = cursor.fetchall()
            cursor.close()
            connection.close()

            if query_result:
                return query_result
            return False

        except sqlite3.Error as ex:

            log(msg='Query error: {}'.format(str(ex)))
            return -1


def log(chat=None, msg='', is_error=False):

    now_time = datetime.datetime.now().strftime('%d-%m %H:%M:%S')

    filename = 'error_log.txt' if is_error else 'bot_log.txt'

    with open(os.path.join(settings.BASE_DIR, filename), 'a', encoding="utf-8") as log_file:
        if chat:
            log_file.write('[{}]: ({} {}) {}\n'.format(now_time, chat.first_name, chat.last_name, msg))
        else:
            log_file.write('[{}]: (Server) {}\n'.format(now_time, msg))


def delete_html_tags(s):

    if s:
        return s.replace('>', '').replace('<', '')


def datetime_to_string(input_seconds=0):
    input_seconds = int(input_seconds)

    minutes, seconds = divmod(input_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    hours_array = ['', "1 год.", "2 год."]

    if seconds < 60 and not hours and not minutes:
        return "ще трішки"
    else:
        total_time = hours_array[hours], str(minutes), "хв."

    total_time_str = ' '.join(total_time)
    return total_time_str.strip()


class Cache:

    @classmethod
    def drop_cache_table(cls):

        query = 'DROP TABLE cache'

        return DBManager.execute_query(query)

    @classmethod
    def create_cache_table_if_not_exists(cls):

        query = """CREATE TABLE IF NOT EXISTS cache(
                          key TEXT PRIMARY KEY NOT NULL,
                          data TEXT DEFAULT CURRENT_TIMESTAMP,
                          creation_time DEFAULT (datetime('now', 'localtime')),
                          requests INTEGER DEFAULT 0)
                          WITHOUT ROWID"""

        return DBManager.execute_query(query)

    @classmethod
    def get_from_cache(cls, key):

        query = "SELECT * FROM cache WHERE key=?"

        r = DBManager.execute_query(query, (key,))
        if r:
            cls.recount_requests_to_cache(key)

        return r

    @classmethod
    def recount_requests_to_cache(cls, key):

        query = "UPDATE cache SET requests=requests+1 WHERE key=?"
        return DBManager.execute_query(query, (key,))

    @classmethod
    def put_in_cache(cls, key, data):

        query = "INSERT or IGNORE INTO cache (key, data) VALUES (?, ?)"
        return DBManager.execute_query(query, (key, data))

    @classmethod
    def get_keys(cls):

        query = "SELECT key FROM cache"
        return DBManager.execute_query(query, )

    @classmethod
    def clear_cache(cls):

        query = "DELETE FROM cache"
        return DBManager.execute_query(query, )

    @classmethod
    def get_requests_to_cache(cls):

        query = "SELECT SUM(requests) FROM cache"
        return DBManager.execute_query(query, )


class MetricsManager:

    @classmethod
    def create_metrics_table_if_not_exists(cls):

        query = """CREATE TABLE IF NOT EXISTS metrics(
                      request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      telegram_id TEXT,
                      request_type TEXT,
                      user_group TEXT,
                      request_datetime DEFAULT (datetime('now', 'localtime')))"""

        return DBManager.execute_query(query)

    @classmethod
    def track(cls, telegram_id='0', request_type=0, user_group=''):

        query = """INSERT INTO metrics (
        telegram_id, 
        request_type, 
        user_group) VALUES (?, ?, ?)"""

        return DBManager.execute_query(query, (telegram_id, request_type, user_group))

    @classmethod
    def get_all_users_count(cls):

        query = "SELECT COUNT(*) FROM users"

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_all_groups_count(cls):

        query = "SELECT COUNT (DISTINCT u_group) FROM users"

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_active_today_users_count(cls):

        query = """SELECT COUNT (DISTINCT telegram_id) 
        FROM metrics 
        WHERE request_datetime > datetime('now', 'localtime', 'start of day')"""

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_active_yesterday_users_count(cls):

        query = """SELECT COUNT (DISTINCT telegram_id) 
        FROM metrics 
        WHERE request_datetime > datetime('now', 'localtime','start of day', '-1 day') 
        and request_datetime < datetime('now', 'localtime', 'start of day')"""

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_active_week_users_count(cls):

        query = """SELECT COUNT (DISTINCT telegram_id)
        FROM metrics 
        WHERE request_datetime > datetime('now', 'localtime', 'start of day', '-7 day') 
        and request_datetime < datetime('now', 'localtime', 'start of day', '+1 day')"""

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_number_of_users_registered_during_the_week(cls):

        query = """SELECT COUNT(*)
        FROM users 
        WHERE register_date > datetime('now','localtime', 'start of day', '-7 day') 
        and register_date < datetime('now', 'localtime', 'start of day', '+1 day')
        """

        return DBManager.execute_query(query)[0][0]

    @classmethod
    def get_statistics_by_types_during_the_week(cls):

        query = """SELECT request_type, count(request_id) as 'count' FROM metrics 
        WHERE request_datetime > datetime('now','localtime', 'start of day', '-7 day')
        and request_datetime < datetime('now', 'localtime', 'start of day', '+1 day')
        GROUP BY request_type"""

        result = DBManager.execute_query(query)

        if result:
            return dict(result)

        return {}

    @classmethod
    def get_last_days_statistics(cls):

        statistic = {}
        today = datetime.date.today()

        for i in range(15):
            previous_day = today - datetime.timedelta(days=i)
            previous_day_str = previous_day.strftime('%Y-%m-%d')

            query = """SELECT COUNT(*)
            FROM metrics
            WHERE request_datetime > datetime('{}')
            and request_datetime < datetime('{}', '+1 days')""".format(previous_day_str,
                                                                       previous_day_str)

            statistic[previous_day.strftime('%d.%m')] = DBManager.execute_query(query)[0][0]

        return statistic

    @classmethod
    def get_hours_statistics(cls, day_delta=0):

        statistic = {}
        day = datetime.date.today() - datetime.timedelta(days=day_delta)

        for i in range(24):
            hour = '0' + str(i) if i < 10 else i
            previous_hour_str = day.strftime('%Y-%m-%d {}:%M'.format(hour))

            query = """SELECT COUNT(*)
            FROM metrics
            WHERE request_datetime > datetime('{}')
            and request_datetime < datetime('{}', '+1 hours')""".format(previous_hour_str,
                                                                        previous_hour_str)

            statistic[previous_hour_str] = DBManager.execute_query(query)[0][0]

        return statistic

    @classmethod
    def get_stats_by_user_id(cls, user_id):

        query = """SELECT * From metrics WHERE telegram_id = ?"""

        user_actions_raw = DBManager.execute_query(query, (user_id, ))
        user_actions = []

        if not user_actions_raw:
            return user_actions.append({
                'action_id': '-',
                'action_type': '-',
                'action_group': '-',
                'action_date': '-',
            })

        for action in user_actions_raw:
            user_actions.append({
                'action_id': action[0],
                'action_type': settings.KEYBOARD.get(action[2], '-'),
                'action_group': action[3],
                'action_date': action[4],
            })

        return user_actions


def update_all_groups():

    params = {
        'n': '701',
        'lev': '142',
        'faculty': '0',
        'query': '',
    }

    response = requests.get(settings.TIMETABLE_URL, params).json()

    if isinstance(response, dict):
        tmp_groups = response.get('suggestions', [])
    else:
        tmp_groups = []

    groups = []

    [groups.append(g.lower()) for g in tmp_groups]

    with open(os.path.join(settings.BASE_DIR, 'groups.txt'), 'w', encoding="utf-8") as file:
        file.write(json.dumps(groups, sort_keys=True, ensure_ascii=False, separators=(',', ':'), indent=2))

    return groups


def is_group_valid(user_group=''):

    user_group = user_group.lower().strip()

    try:
        with open(os.path.join(settings.BASE_DIR, 'groups.txt'), 'r', encoding='utf-8') as file:
            all_groups = json.loads(file.read())

        return user_group in all_groups

    except Exception as ex:
        log(msg='Помилка перевірки валідності групи: {}'.format(str(ex)))

    return True


def get_possible_groups(user_group='', variants=4):

    def get_tanimoto_koef(s1, s2):
        a, b, c = len(s1), len(s2), 0.0

        for sym in s1:
            if sym in s2:
                c += 1

        return c / (a + b - c)

    possible_groups = []

    with open(os.path.join(settings.BASE_DIR, 'groups.txt'), 'r', encoding="utf-8") as file:
        all_groups = json.loads(file.read())

    for group in all_groups:
        tanimoto_koef = get_tanimoto_koef(user_group, group)
        if tanimoto_koef > 0.5:
            possible_groups.append({
                'k': tanimoto_koef,
                'group': group
            })

    sorted_groups = sorted(possible_groups, key=lambda d: d['k'], reverse=True)

    return sorted_groups[:variants]


def update_all_teachers():

    params = {
        'n': '701',
        'lev': '141',
        'faculty': '0',
        'query': '',
    }

    response = requests.get(settings.TIMETABLE_URL, params).json()

    if isinstance(response, dict):
        teachers = response.get('suggestions', [])
    else:
        teachers = []

    with open(os.path.join(settings.BASE_DIR, 'teachers.txt'), 'w', encoding="utf-8") as file:
        file.write(json.dumps(teachers, sort_keys=True, ensure_ascii=False, separators=(',', ':'), indent=2))

    return teachers


def is_teacher_valid(fullname):

    fullname = fullname.title().strip()

    try:
        with open(os.path.join(settings.BASE_DIR, 'teachers.txt'), 'r', encoding='utf-8') as file:
            all_teachers = json.loads(file.read())

        return fullname in all_teachers

    except Exception as ex:
        log(msg='Помилка валідації призвіща викладача: {}'.format(str(ex)))

    return True


class AdService:

    @classmethod
    def add_advertisement(cls, user_id, username, text):

        if not text:
            return False

        text = delete_html_tags(text)

        query = """INSERT INTO ads (
        user_id, 
        username,
        ad_text) VALUES (?, ?, ?)"""

        if str(user_id) not in settings.ADMINS_ID:
            text = text[:120]

        DBManager.execute_query(query, (user_id, username, text))

        if str(user_id) in settings.ADMINS_ID:
            cls.set_vip_by_id(user_id, 1)

        return True

    @classmethod
    def render_ads(cls):

        ads = cls.get_ads() or []
        vip_ads = cls.get_ads(is_vip=True) or []

        ads_rendered = ''

        if not ads and not vip_ads:
            return 'Тут поки пусто.'

        for vip_ad in vip_ads:

            username = vip_ad[0]
            text = vip_ad[1]

            ads_rendered += '\U0001F525 <b>@{}</b>\n{}\n\n'.format(username, text)

        for ad in ads:

            username = ad[0]
            text = ad[1]

            ads_rendered += '\U00002139 <b>@{}</b>\n{}\n\n'.format(username, text)

        return ads_rendered

    @staticmethod
    def get_ads(is_vip=False):

        query = 'SELECT username, ad_text, creation_datetime FROM ads'

        if is_vip:
            query += ' WHERE is_vip = 1 '
        else:
            query += ' WHERE is_vip != 1 '

        query += ' ORDER BY creation_datetime'

        ads = DBManager.execute_query(query,)

        return ads

    @staticmethod
    def create_ad_service_table_if_not_exists():

        query = """CREATE TABLE IF NOT EXISTS ads(
                      ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id TEXT,
                      username TEXT,
                      ad_text TEXT,
                      is_vip TEXT DEFAULT 0,
                      creation_datetime DEFAULT (datetime('now', 'localtime')))"""

        return DBManager.execute_query(query)

    @staticmethod
    def check_if_user_have_ad(user_id):

        query = """SELECT * FROM ads WHERE user_id = ?"""

        return DBManager.execute_query(query, (user_id,))

    @staticmethod
    def delete_user_ad(user_id):

        query = "DELETE FROM ads WHERE user_id=?"

        return DBManager.execute_query(query, (user_id,))

    @staticmethod
    def set_vip_by_id(user_id, vip_status):

        query = "UPDATE ads SET is_vip = ? WHERE user_id = ?"

        return DBManager.execute_query(query, (vip_status, user_id,))
