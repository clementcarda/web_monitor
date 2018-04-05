from flask import Flask,render_template, request, g, session, url_for, redirect, flash
import mysql.connector
from passlib.hash import argon2
import requests
from slackclient import SlackClient
from datetime import datetime

app = Flask(__name__)
app.config.from_object('config')
app.config.from_object('secret_config')

#Database functions
def connectDB():
    g.mysql_connection = mysql.connector.connect(
        host = app.config['DATABASE_HOST'],
        user = app.config['DATABASE_USER'],
        password = app.config['DATABASE_PASSWORD'],
        database = app.config['DATABASE_NAME']
    )

    g.mysql_cursor = g.mysql_connection.cursor()
    return g.mysql_cursor

def getDB():
    if not hasattr(g, 'db'):
        g.db = connectDB()
    return g.db

def commit():
    g.mysql_connection.commit()

def getUser(email):
    user = None

    db = getDB()
    db.execute('SELECT id, email, password, is_admin FROM user WHERE email = %(email)s', {'email': email})
    res = db.fetchone()


    if res is not None:
        user = res
    return user

def logIn(user_data):
    user = getUser(user_data['email'])

    if user is not None:
        valid_user = False
        if argon2.verify(user_data['password'], user[2]):
            valid_user = user

        if valid_user:
            session['user'] = valid_user
            return redirect(url_for('homepage'))

    flash('bad credential')
    return render_template('security/login.html')

def testAllURLS():
    db = getDB()
    db.execute('''SELECT id, url FROM monitor''')
    urls = db.fetchall()
    for url in urls:
        r = requests.get(url[1])

        status = int(r.status_code)
        url_id = int(url[0])

        db.execute('''INSERT INTO logs (exec_time, status, url_id) VALUES (NOW(), {0}, {1})'''.format(status, url_id))
        db.execute('''UPDATE monitor SET url_status = {0} WHERE id = {1}'''.format(status, url_id))

        if status == 200:
            db.execute('''UPDATE monitor SET nb_error = 0 WHERE id = {0}'''.format(url_id))
        else:
            db.execute('''SELECT nb_error FROM monitor WHERE id = {0}'''.format(url_id))
            nb_error = int(db.fetchone()[0])+1
            db.execute('''UPDATE monitor SET nb_error = {0} WHERE id = {1}'''.format(nb_error, url_id))
    commit()

def sendSlackMessage():
    slack_token = app.config['SLACK_TOKEN']
    sc = SlackClient(slack_token)

    db = getDB()
    db.execute('''SELECT id, url, url_status, nb_error, last_call FROM monitor''')
    urls = db.fetchall()

    for url in urls:
        valid_call = False
        last_call = url[4]
        duree = datetime.now() - last_call
        if duree.seconds//3600 >= 2:
            valid_call = True

        if url[3] >= 3 and valid_call:

            text = 'une erreur {0} est survenue sur l\'url {1}'.format(url[2], url[1])
            sc.api_call(
                'chat.postMessage',
                channel='CA0FXNPT3',
                text=text
            )

            db.execute('''UPDATE monitor SET last_call = NOW() WHERE id = {0}'''.format(int(url[0])))
    commit()

def getHeader(url):
    r = requests.get(url)
    db = getDB()
    db.execute('''UPDATE monitor SET url_status = {0} WHERE url = "{1}"'''.format(int(r.status_code), url))
    commit()
    return r

@app.teardown_appcontext
def closeDB(error):
    if hasattr(g, 'db'):
        g.db.close()

#####Pages#####

#homepage
@app.route('/')
def homepage():
    user = False
    urls = None
    if session.get('user'):
        user = session.get('user')
        db = getDB()
        db.execute('''SELECT * FROM monitor WHERE user_id = {0}'''.format(user[0]))
        urls = db.fetchall()
    return render_template('default/homepage.html', user=user, urls=urls)

#User
@app.route('/register/', methods=['GET', 'POST'])
def register():
    if session.get('user'):
        return redirect(url_for('homepage'))

    elif request.method == 'GET':
        return render_template('security/register.html')

    elif request.method == 'POST':
        email = str(request.form.get('email'))
        password = str(request.form.get('password'))
        hash_pass = str(argon2.hash(password))

        user = getUser(email)
        if user is None:
            db = getDB()
            db.execute('''INSERT INTO user (email, password, is_admin) VALUES ("{0}", "{1}", FALSE )'''.format(
                email, hash_pass))
            commit()

            user_data = {'email': email, 'password': password}
            return logIn(user_data)

        else:
            flash('this email already in use')
            return render_template('security/register.html')

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if session.get('user'):
        return redirect(url_for('homepage'))
    elif request.method == 'GET':
        return render_template('security/login.html')

    elif request.method == 'POST':
        email = str(request.form.get('email'))
        password = str(request.form.get('password'))

        user_data = {'email': email, 'password': password}
        return logIn(user_data)

@app.route('/logout/')
def logout():
    session.clear()
    return redirect(url_for('homepage'))

#Web Monitoring
@app.route('/add_url/', methods=['GET', 'POST'])
def addURL():
    if session.get('user'):
        if request.method == 'GET':
            return render_template('monitor/add_url.html')
        elif request.method == 'POST':
            url = str(request.form.get('url'))
            user_id = int(session.get('user')[0])

            db = getDB()
            db.execute('''INSERT INTO monitor (url, user_id) VALUES ("{0}", {1})'''.format(url, user_id))
            commit()
            flash('URL has been added')
            return redirect(url_for('homepage'))
    else:
        return redirect(url_for('homepage'))
@app.route('/header/')
def header():
    testAllURLS()
    sendSlackMessage()

    return redirect(url_for('homepage'))



if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')