from flask import Flask, request, redirect, session
import sqlite3, random, time
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret"

DB = "db.sqlite3"

def db():
    return sqlite3.connect(DB)

def init():
    c = db()
    cur = c.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        name TEXT,
        email TEXT,
        code TEXT,
        role TEXT DEFAULT 'user',
        last_send INTEGER DEFAULT 0
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS stations(
        name TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS bookings(
        name TEXT,
        station TEXT
    )""")

    c.commit()
    c.close()

    # станции по умолчанию
    stations = ["Лобня","Физтех","Селигерская","Катуар","Подосинки"]
    c = db()
    cur = c.cursor()
    for s in stations:
        cur.execute("INSERT OR IGNORE INTO stations(name) VALUES(?)",(s,))
    c.commit()
    c.close()

init()

def send_code(email, code):
    print(f"CODE {email}: {code}")  # потом подключим SMTP

# ---------------- LOGIN ----------------

@app.route("/", methods=["GET","POST"])
def login():
    if request.method == "POST":
        name = request.form["name"]

        c = db()
        cur = c.cursor()
        user = cur.execute("SELECT email,last_send FROM users WHERE name=?", (name,)).fetchone()

        if not user:
            return "Нет пользователя"

        email, last = user

        if time.time() - last < 30:
            return "Подожди 30 сек"

        code = str(random.randint(1000,9999))
        cur.execute("UPDATE users SET code=?, last_send=? WHERE name=?", (code,int(time.time()),name))
        c.commit()

        send_code(email, code)
        session["name"] = name

        return redirect("/verify")

    return '''
    <h2>Вход</h2>
    <form method="post">
        ФИО: <input name="name">
        <button>Далее</button>
    </form>
    '''

# ---------------- VERIFY ----------------

@app.route("/verify", methods=["GET","POST"])
def verify():
    if request.method == "POST":
        code = request.form["code"]
        name = session.get("name")

        c = db()
        cur = c.cursor()
        user = cur.execute("SELECT code,role FROM users WHERE name=?", (name,)).fetchone()

        if user and user[0] == code:
            session["auth"] = True
            session["role"] = user[1]
            return redirect("/dashboard")

        return "Неверный код"

    return '''
    <h2>Код из почты</h2>
    <form method="post">
        <input name="code">
        <button>Войти</button>
    </form>
    '''

# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if not session.get("auth"):
        return redirect("/")

    role = session.get("role")

    if role == "admin":
        return redirect("/admin")

    return '''
    <h2>Запись</h2>
    <form method="post" action="/book">
        Станция: <input name="station">
        <button>Записаться</button>
    </form>
    '''

# ---------------- BOOK ----------------

@app.route("/book", methods=["POST"])
def book():
    now = datetime.now().hour

    if now < 17 or now >= 20:
        return "Запись закрыта"

    c = db()
    cur = c.cursor()

    count = cur.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]

    if count >= 7:
        return "Извините, но вы не успели записаться"

    cur.execute("INSERT INTO bookings VALUES (?,?)",
                (session.get("name"), request.form["station"]))

    c.commit()

    return "Вы записались"

# ---------------- ADMIN ----------------

@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return "Нет доступа"

    return '''
    <h2>Админ</h2>

    <form method="post" action="/add_user">
        ФИО <input name="name">
        Email <input name="email">
        <button>Добавить</button>
    </form>

    <form method="post" action="/add_station">
        Станция <input name="station">
        <button>Добавить</button>
23:51
</form>
    '''

@app.route("/add_user", methods=["POST"])
def add_user():
    c = db()
    cur = c.cursor()
    cur.execute("INSERT INTO users(name,email) VALUES (?,?)",
                (request.form["name"], request.form["email"]))
    c.commit()
    return redirect("/admin")

@app.route("/add_station", methods=["POST"])
def add_station():
    c = db()
    cur = c.cursor()
    cur.execute("INSERT INTO stations(name) VALUES (?)",
                (request.form["station"],))
    c.commit()
    return redirect("/admin")

# ---------------- RUN ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
