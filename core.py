import settings
import sqlite3
import os
import datetime


class User:

    def __init__(self, chat):
        self.id = chat.id
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

    def update_group(self, group):

        log(self.chat, 'Has changed group to {}'.format(group))

        query = "UPDATE users SET u_group=? WHERE t_id=?"
        return DBManager.execute_query(query, (group, self.id))

    def registration(self, group):

        log(self.chat, 'Has been registered ({})'.format(group))

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
                      register_date TEXT DEFAULT (datetime('now', 'localtime')),
                      last_use_date DEFAULT (datetime('now', 'localtime')),
                      requests_count INTEGER DEFAULT 0) WITHOUT ROWID"""

        return DBManager.execute_query(query)


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

            log(m='Query error: {}'.format(str(ex)))
            return -1


def log(chat=None, m=''):

    now_time = datetime.datetime.now().strftime('%d-%m %H:%M:%S')

    with open(os.path.join(settings.BASE_DIR, 'bot_log.txt'), 'a', encoding="utf-8") as log_file:
        if chat:
            log_file.write('[{}]: ({} {}) {}\n'.format(now_time, chat.first_name, chat.last_name, m))
        else:
            log_file.write('[{}]: (Server) {}\n'.format(now_time, m))


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
    def get_users(cls):

        query = """SELECT * From users"""

        users_selection = DBManager.execute_query(query)

        users = []

        for user in users_selection:
            users.append({
                'telegram_id': user[0],
                'username': user[1] or '-',
                'first_name': user[2],
                'last_name': user[3] or '-',
                'group': user[4],
                'register_date': user[5],
                'last_use_date': user[6],
                'requests_count': user[7],
            })

        return users
