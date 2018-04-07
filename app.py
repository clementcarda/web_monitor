from flask import Flask,render_template, request, g, session, url_for, redirect, flash
import mysql.connector
from passlib.hash import argon2
import threading
from testURLS import testAllURLS

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

@app.route('/logs/<id>')
def logs(id):
    db = getDB()
    db.execute('''SELECT exec_time, status FROM logs WHERE url_id = {0}'''.format(id))
    logs = db.fetchall()
    db.execute('''SELECT url FROM monitor WHERE id = {0}'''.format(id))
    url = db.fetchone()

    return render_template('default/logs.html', logs=logs, url=url[0])

@app.route('/del/<id>')
def deleteURL(id):
    db = getDB()
    db.execute('''DELETE FROM monitor WHERE id = {}'''.format(id))
    commit()
    return redirect(url_for('homepage'))


if __name__ == '__main__':

    t1 = threading.Thread(target=testAllURLS).start()

    # app.run(debug=True, host='0.0.0.0')
    app.run()
