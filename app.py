from flask import Flask,render_template, request, g, session, url_for, redirect, flash
import mysql.connector
from passlib.hash import argon2

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
    db.execute('SELECT email, password, is_admin FROM user WHERE email = %(email)s', {'email': email})
    res = db.fetchone()


    if res is not None:
        user = res
    return user

def logIn(user_data):
    user = getUser(user_data['email'])

    if user is not None:
        valid_user = False
        if argon2.verify(user_data['password'], user[1]):
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

#Pages
@app.route('/')
def homepage():
    user = False
    if session.get('user'):
        user = session.get('user')
    return render_template('default/homepage.html', user=user)

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
