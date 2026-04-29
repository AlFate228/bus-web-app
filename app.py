from flask import Flask, request, redirect, session, render_template_string
import sqlite3, random, time, smtplib, os
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

DB = "db.sqlite3"

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "Emerson08com"

DRIVER_LOGIN = "driver"
DRIVER_PASSWORD = "Driver08"


def db():
    return sqlite3.connect(DB)


def init_db():
    c = db()
    cur = c.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT, password TEXT, code TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS bookings(id INTEGER PRIMARY KEY, name TEXT, station TEXT)")

    c.commit()
    c.close()


init_db()


def send_email(to, subject, text):
    try:
        if not EMAIL_USER or not EMAIL_PASS:
            print(f"[DEV MODE] Код: {text}")
            return

        msg = MIMEText(text)
        msg["Subject"] = subject
        msg["From"] = EMAIL_USER
        msg["To"] = to

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.sendmail(EMAIL_USER, to, msg.as_string())

    except Exception as e:
        print("EMAIL ERROR:", e)


def layout(content):
    logout = '<a href="/logout"><button class="danger">Выйти</button></a>' if session.get("role") else ""

    return render_template_string(f"""
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body {{
    margin:0;
    font-family:-apple-system;
    background:#0f172a;
    color:white;
}}

.container {{
    width:90%;
    max-width:420px;
    margin:80px auto;
    text-align:center;
}}

input, select {{
    width:90%;
    padding:14px;
    margin:6px;
    border-radius:12px;
    border:none;
}}

button {{
    width:90%;
    padding:14px;
    margin:6px;
    border-radius:12px;
    border:none;
    background:#22c55e;
    color:white;
    font-weight:bold;
}}

.blue {{background:#007aff}}
.danger {{background:#ff3b30}}

.menu {{
    position:fixed;
    top:10px;
    right:10px;
}}

.menu-content {{
    background:#1e293b;
    padding:10px;
    border-radius:12px;
}}

</style>
</head>

<body>

<div class="menu">
<div class="menu-content">
{logout}
<a href="/admin_login"><button class="blue">Админ</button></a>
<a href="/driver_login"><button class="blue">Водитель</button></a>
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
<h1>🚍 Запись</h1>
<a href="/register"><button>Регистрация</button></a>
<a href="/login"><button>Вход</button></a>
""")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]

        code = str(random.randint(1000, 9999))

        c = db()
        cur = c.cursor()
        cur.execute("INSERT INTO users(name,email,code) VALUES(?,?,?)", (name, email, code))
        c.commit()

        send_email(email, "Код", code)

        session["email"] = email
        return redirect("/verify")

    return layout("""
<h2>Регистрация</h2>
<form method="post">
<input name="name" placeholder="ФИО">
<input name="email" placeholder="Email">
<button>Получить код</button>
</form>
""")


@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        code = request.form["code"]

        c = db()
        cur = c.cursor()
        user = cur.execute("SELECT code FROM users WHERE email=?", (session["email"],)).fetchone()

        if user and user[0] == code:
            return redirect("/set_password")

    return layout("""
<h2>Введите код</h2>
<form method="post">
<input name="code">
<button>Далее</button>
</form>
""")


@app.route("/set_password", methods=["GET", "POST"])
def set_password():
    if request.method == "POST":
        p1 = request.form["p1"]
        p2 = request.form["p2"]

        if p1 != p2:
            return "Пароли не совпадают"

        c = db()
        cur = c.cursor()
        cur.execute("UPDATE users SET password=? WHERE email=?", (p1, session["email"]))
        c.commit()

        return redirect("/login")

    return layout("""
<h2>Пароль</h2>
<form method="post">
<input type="password" name="p1" placeholder="Пароль">
<input type="password" name="p2" placeholder="Повтор">
<button>Сохранить</button>
</form>
""")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        c = db()
        cur = c.cursor()
        user = cur.execute("SELECT name FROM users WHERE email=? AND password=?", (email, password)).fetchone()

        if user:
            session["name"] = user[0]
            session["role"] = "user"
            return redirect("/dashboard")

    return layout("""
<h2>Вход</h2>
<form method="post">
<input name="email">
<input type="password" name="password">
<button>Войти</button>
</form>
""")


@app.route("/dashboard")
def dashboard():
    return layout("""
<h2>Запись</h2>
<form method="post" action="/book">
<select name="station">
<option>Лобня</option>
<option>Физтех</option>
<option>Селигерская</option>
<option>Катуар</option>
<option>Подосинки</option>
</select>
<button>Записаться</button>
</form>
""")


@app.route("/book", methods=["POST"])
def book():
    now = datetime.now().hour

    if now < 17 or now >= 20:
        return "Закрыто"

    c = db()
    cur = c.cursor()

    count = cur.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]

    if count >= 7:
        return "Нет мест"

    cur.execute("INSERT INTO bookings(name,station) VALUES(?,?)", (session["name"], request.form["station"]))
    c.commit()

    return "Вы записаны"


@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["login"] == ADMIN_LOGIN and request.form["password"] == ADMIN_PASSWORD:
            session["role"] = "admin"
            return redirect("/admin")

    return layout("""
<h2>Админ</h2>
<form method="post">
<input name="login">
<input type="password" name="password">
<button>Войти</button>
</form>
""")


@app.route("/admin")
def admin():
    c = db()
    data = c.execute("SELECT name,station FROM bookings").fetchall()

    rows = "".join([f"<p>{d[0]} - {d[1]}</p>" for d in data])

    return layout(f"""
<h2>Админка</h2>
{rows}
""")


@app.route("/driver_login", methods=["GET", "POST"])
def driver_login():
    if request.method == "POST":
        if request.form["login"] == DRIVER_LOGIN and request.form["password"] == DRIVER_PASSWORD:
            session["role"] = "driver"
            return redirect("/driver")

    return layout("""
<h2>Водитель</h2>
<form method="post">
<input name="login">
<input type="password" name="password">
<button>Войти</button>
</form>
""")


@app.route("/driver")
def driver():
    c = db()
    data = c.execute("SELECT name,station FROM bookings").fetchall()

    rows = "".join([f"<p>{d[0]} - {d[1]}</p>" for d in data])

    return layout(f"""
<h2>Список</h2>
{rows}
""")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
