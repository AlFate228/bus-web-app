from flask import Flask, request, redirect, session, render_template_string
import sqlite3, random, smtplib, os
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
app.secret_key = "bus_app_secret"

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
        verified INTEGER DEFAULT 0
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

    for s in ["Лобня", "Физтех", "Селигерская", "Катуар", "Подосинки"]:
        cur.execute("INSERT OR IGNORE INTO stations(name) VALUES(?)", (s,))

    cur.execute(
        "INSERT OR IGNORE INTO drivers(login,password) VALUES(?,?)",
        (DEFAULT_DRIVER_LOGIN, DEFAULT_DRIVER_PASSWORD)
    )

    c.commit()
    c.close()


init_db()


def send_email(to, subject, text):
    if not EMAIL_USER or not EMAIL_PASS:
        print(f"EMAIL DEV MODE -> {to}: {text}")
        return

    try:
        msg = MIMEText(text, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, [to], msg.as_string())

    except Exception as e:
        print("EMAIL ERROR:", e)


def layout(content):
    logout_btn = '<a href="/logout" class="sheet-link danger">Выйти</a>' if session.get("role") else ""

    return render_template_string(f"""
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Запись на автобус</title>
<style>
* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    min-height: 100vh;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
    background: linear-gradient(180deg, #0f172a, #020617);
    color: white;
}}

.top-menu {{
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 100;
}}

.menu-toggle {{
    width: 46px;
    height: 46px;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,.18);
    background: rgba(255,255,255,.12);
    color: white;
    font-size: 22px;
    backdrop-filter: blur(20px);
    cursor: pointer;
}}

.sheet {{
    display: none;
    position: absolute;
    right: 0;
    top: 58px;
    width: 230px;
    padding: 12px;
    border-radius: 22px;
    background: rgba(30, 41, 59, .82);
    backdrop-filter: blur(22px);
    box-shadow: 0 20px 50px rgba(0,0,0,.45);
}}

.top-menu:hover .sheet {{
    display: block;
}}

.sheet-link {{
    display: block;
    width: 100%;
    margin: 7px 0;
    padding: 13px;
    border-radius: 15px;
    background: rgba(255,255,255,.13);
    color: white;
    text-decoration: none;
    text-align: center;
    font-weight: 700;
}}

.sheet-link.blue {{
    background: #007aff;
}}

.sheet-link.danger {{
    background: #ff3b30;
}}

.container {{
    width: 92%;
    max-width: 900px;
    margin: 90px auto 30px;
    padding: 24px;
    border-radius: 30px;
    background: rgba(255,255,255,.08);
    backdrop-filter: blur(24px);
    box-shadow: 0 25px 70px rgba(0,0,0,.38);
    text-align: center;
}}

.small-container {{
    max-width: 440px;
}}

h1, h2, h3 {{
    margin-top: 0;
}}

input, select {{
    width: 100%;
    max-width: 420px;
    padding: 16px;
    margin: 8px 0;
    border: none;
    border-radius: 16px;
    font-size: 16px;
}}

button, .btn {{
    display: inline-block;
    width: 100%;
    max-width: 420px;
    padding: 15px;
    margin: 8px 0;
    border: none;
    border-radius: 16px;
    background: #34c759;
    color: white;
    font-size: 16px;
    font-weight: 700;
    text-decoration: none;
    cursor: pointer;
}}

.btn-blue {{
    background: #007aff;
}}

.btn-red {{
    background: #ff3b30;
}}

.grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    gap: 16px;
    text-align: left;
}}

.card {{
    background: rgba(255,255,255,.1);
    border: 1px solid rgba(255,255,255,.12);
    border-radius: 22px;
    padding: 18px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    margin-top: 12px;
    font-size: 14px;
}}

th, td {{
    padding: 10px;
    border-bottom: 1px solid rgba(255,255,255,.14);
    text-align: left;
}}

.badge {{
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    background: rgba(52,199,89,.22);
    color: #86efac;
    font-size: 12px;
}}

.empty {{
    color: #cbd5e1;
}}
</style>
</head>
<body>

<div class="top-menu">
    <button class="menu-toggle">☰</button>
    <div class="sheet">
        {logout_btn}
        <a href="/admin_login" class="sheet-link blue">Вход Администратора</a>
        <a href="/driver_login" class="sheet-link blue">Вход Водителя</a>
        <a href="/" class="sheet-link">Главная</a>
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
<p>Зарегистрируйтесь, подтвердите почту и запишитесь на автобус.</p>
<a href="/register" class="btn">Регистрация</a>
<a href="/login" class="btn btn-blue">Вход пользователя</a>
""")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        code = str(random.randint(100000, 999999))

        c = db()
        cur = c.cursor()

        exists = cur.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if exists:
            c.close()
            return layout("""
<h2>Эта почта уже зарегистрирована</h2>
<a href="/login" class="btn btn-blue">Войти</a>
""")

        cur.execute(
            "INSERT INTO users(name,email,code,verified) VALUES(?,?,?,0)",
            (name, email, code)
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
    <button>Отправить код</button>
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
        c.close()

        if user and user[0] == code:
            session["password_email"] = email
            return redirect("/set_password")

        return layout("""
<h2>Неверный код</h2>
<a href="/verify_register" class="btn btn-blue">Попробовать снова</a>
""")

    return layout("""
<h2>Код подтверждения</h2>
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
            return layout("""
<h2>Пароли не совпадают</h2>
<a href="/set_password" class="btn btn-blue">Назад</a>
""")

        c = db()
        cur = c.cursor()
        cur.execute("UPDATE users SET password=?, verified=1 WHERE email=?", (p1, email))
        c.commit()
        c.close()

        session.clear()

        return layout("""
<h2>Аккаунт создан ✅</h2>
<a href="/login" class="btn btn-blue">Войти</a>
""")

    return layout("""
<h2>Придумайте пароль</h2>
<form method="post">
    <input type="password" name="password1" placeholder="Пароль" required>
    <input type="password" name="password2" placeholder="Повторите пароль" required>
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

        if user:
            session["role"] = "user"
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            return redirect("/dashboard")

        return layout("""
<h2>Неверная почта или пароль</h2>
<a href="/login" class="btn btn-blue">Назад</a>
""")

    return layout("""
<h2>Вход пользователя</h2>
<form method="post">
    <input type="email" name="email" placeholder="Почта" required>
    <input type="password" name="password" placeholder="Пароль" required>
    <button>Войти</button>
</form>
""")


@app.route("/dashboard")
def dashboard():
    if session.get("role") != "user":
        return redirect("/login")

    c = db()
    cur = c.cursor()

    booked = cur.execute(
        "SELECT station, created_at FROM bookings WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    stations = cur.execute("SELECT name FROM stations ORDER BY name").fetchall()

    c.close()

    if booked:
        return layout(f"""
<h2>Вы уже записаны ✅</h2>
<div class="card">
    <p><b>ФИО:</b> {session.get("user_name")}</p>
    <p><b>Станция:</b> {booked[0]}</p>
    <p><b>Время записи:</b> {booked[1]}</p>
</div>
<a href="/logout" class="btn btn-red">Выйти</a>
""")

    options = "".join([f"<option value='{s[0]}'>{s[0]}</option>" for s in stations])

    return layout(f"""
<h2>Запись на автобус</h2>
<p>Запись доступна с <b>17:00</b> до <b>20:00</b>. Всего 7 мест.</p>
<form method="post" action="/book">
    <select name="station" required>{options}</select>
    <button>Записаться</button>
</form>
<a href="/logout" class="btn btn-red">Выйти</a>
""")


@app.route("/book", methods=["POST"])
def book():
    if session.get("role") != "user":
        return redirect("/login")

    now = datetime.now().hour

    if now < 17 or now >= 20:
        return layout("""
<h2>Запись закрыта</h2>
<p>Запись доступна только с 17:00 до 20:00.</p>
<a href="/dashboard" class="btn btn-blue">Назад</a>
""")

    c = db()
    cur = c.cursor()

    already = cur.execute(
        "SELECT id FROM bookings WHERE user_id=?",
        (session["user_id"],)
    ).fetchone()

    if already:
        c.close()
        return redirect("/dashboard")

    count = cur.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]

    if count >= 7:
        c.close()
        return layout("""
<h2>Извините, но вы не успели записаться</h2>
<a href="/dashboard" class="btn btn-blue">Назад</a>
""")

    cur.execute(
        "INSERT INTO bookings(user_id,station,created_at) VALUES(?,?,?)",
        (
            session["user_id"],
            request.form["station"],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )

    c.commit()
    c.close()

    return redirect("/dashboard")


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["login"] == ADMIN_LOGIN and request.form["password"] == ADMIN_PASSWORD:
            session.clear()
            session["role"] = "admin"
            return redirect("/admin")

        return layout("""
<h2>Неверный логин или пароль</h2>
<a href="/admin_login" class="btn btn-blue">Назад</a>
""")

    return layout("""
<h2>Вход Администратора</h2>
<form method="post">
    <input name="login" placeholder="Логин" required>
    <input type="password" name="password" placeholder="Пароль" required>
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
        ORDER BY bookings.id ASC
    """).fetchall()

    c.close()

    booking_rows = "".join([
        f"<tr><td>{b[0]}</td><td>{b[1]}</td><td>{b[2]}</td><td>{b[3]}</td></tr>"
        for b in bookings
    ]) or "<tr><td colspan='4' class='empty'>Пока никто не записался</td></tr>"

    user_rows = "".join([
        f"<tr><td>{u[1]}</td><td>{u[2]}</td><td>{'Да' if u[3] else 'Нет'}</td><td><a href='/admin/delete_user/{u[0]}' class='btn btn-red'>Удалить</a></td></tr>"
        for u in users
    ]) or "<tr><td colspan='4' class='empty'>Пользователей нет</td></tr>"

    driver_rows = "".join([
        f"<tr><td>{d[1]}</td><td><a href='/admin/delete_driver/{d[0]}' class='btn btn-red'>Удалить</a></td></tr>"
        for d in drivers
    ]) or "<tr><td colspan='2' class='empty'>Водителей нет</td></tr>"

    station_rows = "".join([
        f"<tr><td>{s[1]}</td><td><a href='/admin/delete_station/{s[0]}' class='btn btn-red'>Удалить</a></td></tr>"
        for s in stations
    ])

    return layout(f"""
<h1>Админ-панель</h1>

<div class="grid">
    <div class="card">
        <h3>Добавить пользователя</h3>
        <form method="post" action="/admin/add_user">
            <input name="name" placeholder="ФИО" required>
            <input type="email" name="email" placeholder="Email" required>
            <input name="password" placeholder="Пароль" required>
            <button>Добавить</button>
        </form>
    </div>

    <div class="card">
        <h3>Добавить водителя</h3>
        <form method="post" action="/admin/add_driver">
            <input name="login" placeholder="Логин" required>
            <input name="password" placeholder="Пароль" required>
            <button>Добавить водителя</button>
        </form>
    </div>

    <div class="card">
        <h3>Добавить станцию</h3>
        <form method="post" action="/admin/add_station">
            <input name="station" placeholder="Название станции" required>
            <button>Добавить станцию</button>
        </form>
    </div>
</div>

<div class="card">
    <h2>Кто записался</h2>
    <table>
        <tr><th>ФИО</th><th>Email</th><th>Станция</th><th>Время</th></tr>
        {booking_rows}
    </table>
</div>

<div class="card">
    <h2>Все пользователи</h2>
    <table>
        <tr><th>ФИО</th><th>Email</th><th>Подтверждён</th><th>Действие</th></tr>
        {user_rows}
    </table>
</div>

<div class="card">
    <h2>Водители</h2>
    <table>
        <tr><th>Логин</th><th>Действие</th></tr>
        {driver_rows}
    </table>
</div>

<div class="card">
    <h2>Станции</h2>
    <table>
        <tr><th>Станция</th><th>Действие</th></tr>
        {station_rows}
    </table>
</div>

<a href="/logout" class="btn btn-red">Выйти</a>
""")


@app.route("/admin/add_user", methods=["POST"])
def admin_add_user():
    if session.get("role") != "admin":
        return redirect("/admin_login")

    c = db()
    cur = c.cursor()

    cur.execute(
        "INSERT OR IGNORE INTO users(name,email,password,verified) VALUES(?,?,?,1)",
        (
            request.form["name"].strip(),
            request.form["email"].strip().lower(),
            request.form["password"]
        )
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
        (request.form["login"].strip(), request.form["password"])
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
    cur.execute("INSERT OR IGNORE INTO stations(name) VALUES(?)", (request.form["station"].strip(),))
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
        login = request.form["login"].strip()
        password = request.form["password"]

        c = db()
        cur = c.cursor()

        driver = cur.execute(
            "SELECT id FROM drivers WHERE login=? AND password=?",
            (login, password)
        ).fetchone()

        c.close()

        if driver:
            session.clear()
            session["role"] = "driver"
            session["driver_login"] = login
            return redirect("/driver")

        return layout("""
<h2>Неверный логин или пароль</h2>
<a href="/driver_login" class="btn btn-blue">Назад</a>
""")

    return layout("""
<h2>Вход Водителя</h2>
<form method="post">
    <input name="login" placeholder="Логин" required>
    <input type="password" name="password" placeholder="Пароль" required>
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
        SELECT users.name, bookings.station, bookings.created_at
        FROM bookings
        JOIN users ON users.id = bookings.user_id
        ORDER BY bookings.id ASC
        LIMIT 7
    """).fetchall()

    c.close()

    rows = "".join([
        f"""
        <div class="card">
            <h3>{b[0]}</h3>
            <p><b>Станция:</b> {b[1]}</p>
            <p><b>Время записи:</b> {b[2]}</p>
        </div>
        """
        for b in bookings
    ]) or "<p class='empty'>Пока никто не записался</p>"

    return layout(f"""
<h1>Список пассажиров</h1>
<p>Водитель видит только тех, кто едет.</p>
{rows}
<a href="/logout" class="btn btn-red">Выйти</a>
""")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
