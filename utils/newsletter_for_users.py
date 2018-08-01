import requests
import time
import sqlite3


def write_log(message):

    with open('file_log.txt', 'a') as f:
        f.write(message + '\n')

TOKEN = '<TOKEN>'
connection = sqlite3.connect('SmartyS_DB.sqlite', check_same_thread=False)

cursor = connection.cursor()
cursor.execute("""SELECT * FROM users""")
connection.commit()
users_list = cursor.fetchall()
cursor.close()

ignore_users = ['', '']

msg = 'Hello'

i = 1

for u_id in users_list:

    if u_id[0] not in ignore_users:
        r = requests.get('https://api.telegram.org/bot{}/sendMessage?chat_id={}&text={}'.
                         format(TOKEN, u_id[0], msg))

        m = ("({} / {}) - {} {} {} [{}]".format(i, len(users_list), u_id[0], u_id[2], u_id[3] or '', r.status_code))
        time.sleep(0.15)

    else:
        m = "({} / {}) - {} {} {} [Ignore]".format(i, len(users_list), u_id[0], u_id[2], u_id[3] or '')

    print(m)
    write_log(m)
    i = i + 1
