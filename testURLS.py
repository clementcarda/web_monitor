import mysql.connector
import secret_config
import requests
from datetime import datetime
import time
from slackclient import SlackClient

mysql_connection = mysql.connector.connect(
    host = secret_config.DATABASE_HOST,
    user = secret_config.DATABASE_USER,
    password = secret_config.DATABASE_PASSWORD,
    database = secret_config.DATABASE_NAME)

def testAllURLS():
    while True:
        cursor = mysql_connection.cursor()
        cursor.execute('''SELECT id, url, url_status, nb_error, last_call FROM monitor''')
        urls = cursor.fetchall()

        for url in urls:

            r = requests.get(url[1])
            status = int(r.status_code)

            url_id = int(url[0])
            url_name = str(url[1])

            cursor.execute('''INSERT INTO logs (exec_time, status, url_id) VALUES (NOW(), {0}, {1})'''.format(status, url_id))
            cursor.execute('''UPDATE monitor SET url_status = {0} WHERE id = {1}'''.format(status, url_id))

            if status == 200:
                cursor.execute('''UPDATE monitor SET nb_error = 0 WHERE id = {0}'''.format(url_id))
            else:
                needToCall = False
                cursor.execute('''SELECT nb_error FROM monitor WHERE id = {0}'''.format(url_id))
                nb_error = int(cursor.fetchone()[0])+1
                cursor.execute('''UPDATE monitor SET nb_error = {0} WHERE id = {1}'''.format(nb_error, url_id))
                last_call = url[4]

                if last_call is None:
                    needToCall = True
                else:
                    duree = datetime.now() - last_call
                    if duree.seconds//3600 >= 2:
                        needToCall = True

                if needToCall and url[3] >= 3:
                    sendSlackMessage(status, url_name)
                    cursor.execute('''UPDATE monitor SET last_call = NOW() WHERE id = {0}'''.format(url_id))

        mysql_connection.commit()
        cursor.close()

        time.sleep(120)

def sendSlackMessage(status, url):
    slack_token = secret_config.SLACK_TOKEN
    sc = SlackClient(slack_token)

    text = 'une erreur {0} est survenue sur l\'url {1}'.format(status, url)
    sc.api_call(
        'chat.postMessage',
        channel='CA0FXNPT3',
        text=text
    )