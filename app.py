from flask import Flask, request, redirect, session, render_template_string
import sqlite3, random, time, smtplib, os
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
app.secret_key = "change_this_secret"

DB = "db.sqlite3"

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "Emerson08com"

DEFAULT_DRIVER_LOGIN = "driver"
DEFAULT_DRIVER_PASSWORD = "Driver08"


def db():
    return sqlite3.connect(DB)


def init_db():
    c = db()
    cur = c.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT,
        code TEXT,
        verified INTEGER DEFAULT 0,
        last_send INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS drivers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        login TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS stations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bookings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        station TEXT,
        created_at TEXT
    )
    """)

    for station in ["Лобня", "Физтех", "Селигерская", "Катуар", "Подосинки"]:
        cur.execute("INSERT OR IGNORE INTO stations(name) VALUES(?)", (station,))

    cur.execute(
        "INSERT OR IGNORE INTO drivers(login,password) VALUES(?,?)",
        (DEFAULT_DRIVER_LOGIN, DEFAULT_DRIVER_PASSWORD)
    )

    c.commit()
    c.close()


init_db()


def send_email(to, subject, text):
    if not EMAIL_USER or not EMAIL_PASS:
        print(f"EMAIL TO {to}: {subject} — {text}")
        return

    msg = MIMEText(text, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to, msg.as_string())


def layout(content):
    return render_template_string(f"""
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Запись на автобус</title>
<style>
body {{
    margin:0;
    font-family:Arial, sans-serif;
    background:#0f172a;
    color:white;
}}
.top {{
    position:fixed;
    top:15px;
    right:15px;
}}
.menu {{
    position:relative;
    display:inline-block;
}}
.menu-btn {{
    background:#334155;
}}
.menu-content {{
    display:none;
    position:absolute;
    right:0;
    background:#1e293b;
    min-width:220px;
    border-radius:12px;
    padding:10px;
    box-shadow:0 10px 25px rgba(0,0,0,.4);
}}
.menu:hover .menu-content {{
    display:block;
}}
.container {{
    max-width:760px;
    margin:90px auto;
    padding:25px;
    background:#111827;
    border-radius:18px;
    box-shadow:0 10px 30px rgba(0,0,0,.35);
}}
input, select {{
    width:90%;
    padding:13px;
    margin:8px;
    border-radius:10px;
    border:0;
}}
button {{
    padding:12px 18px;
    margin:8px;
    border:0;
    border-radius:10px;
    background:#22c55e;
    color:white;
    font-weight:bold;
}}
button.red {{
    background:#ef4444;
}}
button.blue {{
    background:#2563eb;
}}
a {{
    color:white;
    text-decoration:none;
}}
.card {{
    background:#1e293b;
    padding:15px;
    margin:10px;
    border-radius:12px;
}}
table {{
    width:100%;
    border-collapse:collapse;
}}
td, th {{
    border-bottom:1px solid #334155;
    padding:10px;
}}
</style>
</head>
<body>
<div class="top">
    <div class="menu">
        <button class="menu-btn">☰ Вход</button>
        <div class="menu-content">
            <a href="/admin_login"><button class="blue">Вход Администратора</button></a>
            <a href="/driver_login"><button class="blue">Вход Водителя</button></a>
        </div>
    </div>
</div>
<div class="container">
{content}
</div>
</body>
</html>
""")


@app.route("/")
def home():
    return layout("""
<h1>🚍 Запись на автобус</h1>
<p>Регистрация, вход и запись на автобус.</p>
<a href="/register"><button>Регистрация</button></a>
<a href="/login"><button>Войти</button></a>
""")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()

        code = str(random.randint(100000, 999999))

        c = db()
        cur = c.cursor()

        existing = cur.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            c.close()
            return layout("<h2>Такая почта уже зарегистрирована</h2><a href='/login'><button>Войти</button></a>")

        cur.execute(
            "INSERT INTO users(name,email,code,verified,last_send) VALUES(?,?,?,?,?)",
            (name, email, code, 0, int(time.time()))
        )
        c.commit()
        c.close()

        send_email(email, "Код подтверждения", f"Ваш код подтверждения: {code}")

        session["verify_email"] = email
        return redirect("/verify_register")

    return layout("""
<h2>Регистрация</h2>
<form method="post">
    <input name="name" placeholder="ФИО" required>
    <input name="email" type="email" placeholder="Рабочая почта" required>
    <button>Получить код</button>
</form>
""")


@app.route("/verify_register", methods=["GET", "POST"])
def verify_register():
    email = session.get("verify_email")
    if not email:
        return redirect("/register")

    if request.method == "POST":
        code = request.form["code"].strip()

        c = db()
        cur = c.cursor()
        user = cur.execute("SELECT code FROM users WHERE email=?", (email,)).fetchone()

        if user and user[0] == code:
            session["password_email"] = email
            c.close()
            return redirect("/set_password")

        c.close()
        return layout("<h2>Неверный код</h2><a href='/verify_register'><button>Попробовать снова</button></a>")

    return layout("""
<h2>Подтверждение почты</h2>
<form method="post">
    <input name="code" placeholder="Код из почты" required>
    <button>Подтвердить</button>
</form>
""")


@app.route("/set_password", methods=["GET", "POST"])
def set_password():
    email = session.get("password_email")
    if not email:
        return redirect("/register")

    if request.method == "POST":
        p1 = request.form["password1"]
        p2 = request.form["password2"]

        if p1 != p2:
            return layout("<h2>Пароли не совпадают</h2><a href='/set_password'><button>Назад</button></a>")

        c = db()
        cur = c.cursor()
        cur.execute("UPDATE users SET password=?, verified=1 WHERE email=?", (p1, email))
        c.commit()
        c.close()

        session.clear()
        return layout("<h2>Аккаунт создан ✅</h2><a href='/login'><button>Войти</button></a>")

    return layout("""
<h2>Придумайте пароль</h2>
<form method="post">
    <input name="password1" type="password" placeholder="Пароль" required>
    <input name="password2" type="password" placeholder="Повторите пароль" required>
    <button>Сохранить</button>
</form>
""")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]

        c = db()
        cur = c.cursor()
        user = cur.execute(
            "SELECT id,name FROM users WHERE email=? AND password=? AND verified=1",
            (email, password)
        ).fetchone()
        c.close()

        if not user:
            return layout("<h2>Неверная почта или пароль</h2><a href='/login'><button>Назад</button></a>")

        session["user_id"] = user[0]
        session["user_name"] = user[1]
        session["role"] = "user"
        return redirect("/dashboard")

    return layout("""
<h2>Вход пользователя</h2>
<form method="post">
    <input name="email" type="email" placeholder="Почта" required>
    <input name="password" type="password" placeholder="Пароль" required>
    <button>Войти</button>
</form>
""")


@app.route("/dashboard")
def dashboard():
    if session.get("role") != "user":
        return redirect("/login")

    c = db()
    cur = c.cursor()
    stations = cur.execute("SELECT name FROM stations ORDER BY name").fetchall()
    booked = cur.execute("SELECT station FROM bookings WHERE user_id=?", (session["user_id"],)).fetchone()
    c.close()

    if booked:
        return layout(f"""
<h2>Вы уже записаны ✅</h2>
<p>Станция: <b>{booked[0]}</b></p>
<a href="/logout"><button>Выйти</button></a>
""")

    options = "".join([f"<option value='{s[0]}'>{s[0]}</option>" for s in stations])

    return layout(f"""
<h2>Запись на автобус</h2>
<p>Запись доступна с 17:00 до 20:00</p>
<form method="post" action="/book">
    <select name="station" required>{options}</select>
    <button>Записаться</button>
</form>
<a href="/logout"><button class="red">Выйти</button></a>
""")


@app.route("/book", methods=["POST"])
def book():
    if session.get("role") != "user":
        return redirect("/login")

    now = datetime.now().hour
    if now < 17 or now >= 20:
        return layout("<h2>Запись закрыта</h2><p>Записаться можно с 17:00 до 20:00.</p>")

    c = db()
    cur = c.cursor()

    already = cur.execute("SELECT id FROM bookings WHERE user_id=?", (session["user_id"],)).fetchone()
    if already:
        c.close()
        return redirect("/dashboard")

    count = cur.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
    if count >= 7:
        c.close()
        return layout("<h2>Извините, но вы не успели записаться</h2>")

    cur.execute(
        "INSERT INTO bookings(user_id,station,created_at) VALUES(?,?,?)",
        (session["user_id"], request.form["station"], datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    c.commit()
    c.close()

    return layout("<h2>Вы успешно записались ✅</h2><a href='/dashboard'><button>Назад</button></a>")


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["login"] == ADMIN_LOGIN and request.form["password"] == ADMIN_PASSWORD:
            session["role"] = "admin"
            return redirect("/admin")
        return layout("<h2>Неверный логин или пароль</h2><a href='/admin_login'><button>Назад</button></a>")

    return layout("""
<h2>Вход Администратора</h2>
<form method="post">
    <input name="login" placeholder="Логин" required>
    <input name="password" type="password" placeholder="Пароль" required>
    <button>Войти</button>
</form>
""")


@app.route("/admin")
def admin():
    if session.get("role") != "admin":
        return redirect("/admin_login")

    c = db()
    cur = c.cursor()

    users = cur.execute("SELECT id,name,email,verified FROM users ORDER BY id DESC").fetchall()
    drivers = cur.execute("SELECT id,login FROM drivers ORDER BY id DESC").fetchall()
    stations = cur.execute("SELECT id,name FROM stations ORDER BY name").fetchall()
    bookings = cur.execute("""
        SELECT users.name, users.email, bookings.station, bookings.created_at
        FROM bookings
        JOIN users ON users.id = bookings.user_id
        ORDER BY bookings.id
    """).fetchall()

    c.close()

    users_rows = "".join([
        f"<tr><td>{u[1]}</td><td>{u[2]}</td><td>{'Да' if u[3] else 'Нет'}</td><td><a href='/admin/delete_user/{u[0]}'><button class='red'>Удалить</button></a></td></tr>"
        for u in users
    ])

    drivers_rows = "".join([
        f"<tr><td>{d[1]}</td><td><a href='/admin/delete_driver/{d[0]}'><button class='red'>Удалить</button></a></td></tr>"
        for d in drivers
    ])

    stations_rows = "".join([
        f"<tr><td>{s[1]}</td><td><a href='/admin/delete_station/{s[0]}'><button class='red'>Удалить</button></a></td></tr>"
        for s in stations
    ])

    bookings_rows = "".join([
        f"<tr><td>{b[0]}</td><td>{b[1]}</td><td>{b[2]}</td><td>{b[3]}</td></tr>"
        for b in bookings
    ])

    return layout(f"""
<h1>Админ-панель</h1>

<h2>Кто записался</h2>
<table>
<tr><th>ФИО</th><th>Email</th><th>Станция</th><th>Время</th></tr>
{bookings_rows}
</table>

<h2>Добавить пользователя</h2>
<form method="post" action="/admin/add_user">
    <input name="name" placeholder="ФИО" required>
    <input name="email" type="email" placeholder="Email" required>
    <input name="password" placeholder="Пароль" required>
    <button>Добавить</button>
</form>

<h2>Все пользователи</h2>
<table>
<tr><th>ФИО</th><th>Email</th><th>Подтверждён</th><th>Действие</th></tr>
{users_rows}
</table>

<h2>Добавить водителя</h2>
<form method="post" action="/admin/add_driver">
    <input name="login" placeholder="Логин водителя" required>
    <input name="password" placeholder="Пароль водителя" required>
    <button>Добавить водителя</button>
</form>

<h2>Водители</h2>
<table>
<tr><th>Логин</th><th>Действие</th></tr>
{drivers_rows}
</table>

<h2>Станции</h2>
<form method="post" action="/admin/add_station">
    <input name="station" placeholder="Название станции" required>
    <button>Добавить станцию</button>
</form>
<table>
<tr><th>Станция</th><th>Действие</th></tr>
{stations_rows}
</table>

<a href="/logout"><button class="red">Выйти</button></a>
""")


@app.route("/admin/add_user", methods=["POST"])
def admin_add_user():
    if session.get("role") != "admin":
        return redirect("/admin_login")

    c = db()
    cur = c.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO users(name,email,password,verified) VALUES(?,?,?,1)",
        (request.form["name"], request.form["email"].lower(), request.form["password"])
    )
    c.commit()
    c.close()
    return redirect("/admin")


@app.route("/admin/delete_user/<int:user_id>")
def admin_delete_user(user_id):
    if session.get("role") != "admin":
        return redirect("/admin_login")

    c = db()
    cur = c.cursor()
    cur.execute("DELETE FROM bookings WHERE user_id=?", (user_id,))
    cur.execute("DELETE FROM users WHERE id=?", (user_id,))
    c.commit()
    c.close()
    return redirect("/admin")


@app.route("/admin/add_driver", methods=["POST"])
def admin_add_driver():
    if session.get("role") != "admin":
        return redirect("/admin_login")

    c = db()
    cur = c.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO drivers(login,password) VALUES(?,?)",
        (request.form["login"], request.form["password"])
    )
    c.commit()
    c.close()
    return redirect("/admin")


@app.route("/admin/delete_driver/<int:driver_id>")
def admin_delete_driver(driver_id):
    if session.get("role") != "admin":
        return redirect("/admin_login")

    c = db()
    cur = c.cursor()
    cur.execute("DELETE FROM drivers WHERE id=?", (driver_id,))
    c.commit()
    c.close()
    return redirect("/admin")


@app.route("/admin/add_station", methods=["POST"])
def admin_add_station():
    if session.get("role") != "admin":
        return redirect("/admin_login")

    c = db()
    cur = c.cursor()
    cur.execute("INSERT OR IGNORE INTO stations(name) VALUES(?)", (request.form["station"],))
    c.commit()
    c.close()
    return redirect("/admin")


@app.route("/admin/delete_station/<int:station_id>")
def admin_delete_station(station_id):
    if session.get("role") != "admin":
        return redirect("/admin_login")

    c = db()
    cur = c.cursor()
    cur.execute("DELETE FROM stations WHERE id=?", (station_id,))
    c.commit()
    c.close()
    return redirect("/admin")


@app.route("/driver_login", methods=["GET", "POST"])
def driver_login():
    if request.method == "POST":
        login = request.form["login"]
        password = request.form["password"]

        c = db()
        cur = c.cursor()
        driver = cur.execute(
            "SELECT id FROM drivers WHERE login=? AND password=?",
            (login, password)
        ).fetchone()
        c.close()

        if driver:
            session["role"] = "driver"
            session["driver_login"] = login
            return redirect("/driver")

        return layout("<h2>Неверный логин или пароль</h2><a href='/driver_login'><button>Назад</button></a>")

    return layout("""
<h2>Вход Водителя</h2>
<form method="post">
    <input name="login" placeholder="Логин" required>
    <input name="password" type="password" placeholder="Пароль" required>
    <button>Войти</button>
</form>
""")


@app.route("/driver")
def driver():
    if session.get("role") != "driver":
        return redirect("/driver_login")

    c = db()
    cur = c.cursor()
    bookings = cur.execute("""
        SELECT users.name, bookings.station
        FROM bookings
        JOIN users ON users.id = bookings.user_id
        ORDER BY bookings.id
        LIMIT 7
    """).fetchall()
    c.close()

    rows = "".join([f"<div class='card'><b>{b[0]}</b><br>Станция: {b[1]}</div>" for b in bookings])

    return layout(f"""
<h1>Список пассажиров</h1>
<p>Водитель видит тех, кто едет.</p>
{rows if rows else "<p>Пока никто не записался</p>"}
<a href="/logout"><button class="red">Выйти</button></a>
""")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
