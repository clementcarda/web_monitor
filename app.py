from flask import Flask,render_template, request, g, session, url_for, redirect
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



@app.teardown_appcontext
def closeDB(error):
    if hasattr(g, 'db'):
        g.db.close()

#Pages
@app.route('/')
def hello_world():
    if session.get('user'):
        return session.get('user')[0]
    return 'toto'

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if session.get('user'):
        return redirect(url_for('hello_world'))

    if request.method == 'GET':
        return render_template('security/register.html')
    elif request.method == 'POST':
        email = str(request.form.get('email'))
        password = str(request.form.get('password'))
        password = argon2.hash(password)

        db = getDB()
        db.execute('INSERT INTO user (email, password, is_admin) VALUES (%(email)s, %(password)s, FALSE )', {'email': email, 'password': password})
        commit()

        return test('toto')



@app.route('/login/', methods=['GET', 'POST'])
def login():
    email = str(request.form.get('email'))
    password = str(request.form.get('password'))

    db = getDB()
    db.execute('SELECT email, password, is_admin FROM user WHERE email = %(email)s', {'email': email})
    users = db.fetchall()

    valid_user = False
    for user in users:
        if argon2.verify(password, user[1]):
            valid_user = user

    if valid_user:
        session['user'] = valid_user
        return redirect(url_for('hello_world'))

    return render_template('security/login.html')

@app.route('/logout/')
def logout():
    session.clear()
    return redirect(url_for('hello_world'))


@app.route('/test/')
def test(data):
    return data

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
