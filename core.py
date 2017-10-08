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

        self.update_user_metadata()

        return result[0][0]

    def update_group(self, group):

        query = "UPDATE users SET u_group=? WHERE t_id=?"
        return DBManager.execute_query(query, (group, self.id))

    def registration(self, group):

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
                      register_date TEXT DEFAULT CURRENT_TIMESTAMP,
                      last_use_date DEFAULT CURRENT_TIMESTAMP,
                      requests_count INTEGER DEFAULT 0) WITHOUT ROWID"""

        return DBManager.execute_query(query)


class DBManager:

    connection = sqlite3.connect(os.path.join(settings.BASE_DIR, settings.DATABASE), check_same_thread=False)

    @classmethod
    def execute_query(cls, query, *args):  # returns result or true if success, or false if something go wrong

        try:
            cursor = cls.connection.cursor()
            cursor.execute(query, *args)
            cls.connection.commit()
            query_result = cursor.fetchall()
            cursor.close()

            if query_result:
                return query_result
            return False

        except sqlite3.Error as ex:

            log(m='Query error: {}'.format(str(ex)))
            return -1


def log(chat=None, m=''):

    now_time = datetime.datetime.now().strftime('%d-%m %H:%M:%S')

    with open(os.path.join(settings.BASE_DIR, 'bot_log.txt'), 'a') as log_file:
        if chat:
            log_file.write('[{}]: ({} {}) {}\n'.format(now_time, chat.first_name, chat.last_name, m))
        else:
            log_file.write('[{}]: (Server) {}\n'.format(now_time, m))
