from flask import Flask, request, redirect, session, render_template_string
import sqlite3, random, time, smtplib, os
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

DB = "db.sqlite3"

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def db():
    return sqlite3.connect(DB)

def init():
    c = db()
    cur = c.cursor()

    cur.execute("CREATE TABLE IF NOT EXISTS users(name TEXT,email TEXT,code TEXT,last_send INTEGER DEFAULT 0)")
    cur.execute("CREATE TABLE IF NOT EXISTS bookings(name TEXT,station TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS result_sent(done INTEGER)")

    cur.execute("INSERT OR IGNORE INTO result_sent VALUES(0)")

    c.commit()
    c.close()

init()

def send_email(to, subject, text):
    msg = MIMEText(text)
    msg["Subject"] = subject
    msg["From"] = EMAIL_USER
    msg["To"] = to

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, to, msg.as_string())

def send_code(email, code):
    send_email(email, "Код входа", f"Ваш код: {code}")

# ---------- UI ----------
base = """
<html>
<head>
<style>
body{font-family:Arial;background:#0f172a;color:#fff;text-align:center}
.container{margin-top:80px}
input,button{padding:10px;margin:5px;border-radius:6px;border:none}
button{background:#22c55e;color:#fff;cursor:pointer}
.top{position:fixed;top:10px;right:10px;}
</style>
</head>
<body>

<div class="top">
<a href="/admin"><button>Админ</button></a>
<a href="/driver"><button>Водитель</button></a>
</div>

<div class="container">
%s
</div>
</body>
</html>
"""

# ---------- HOME ----------
@app.route("/")
def home():
    return render_template_string(base % """
    <h1>🚍 Запись на автобус</h1>
    <a href="/login"><button>Войти</button></a>
    """)

# ---------- LOGIN ----------
@app.route("/login", methods=["GET","POST"])
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

    return render_template_string(base % """
    <h2>Вход</h2>
    <form method="post">
    ФИО<br><input name="name"><br>
    <button>Получить код</button>
    </form>
    """)

# ---------- VERIFY ----------
@app.route("/verify", methods=["GET","POST"])
def verify():
    if request.method == "POST":
        code = request.form["code"]
        name = session.get("name")

        c = db()
        cur = c.cursor()
        user = cur.execute("SELECT code FROM users WHERE name=?", (name,)).fetchone()

        if user and user[0] == code:
            session["auth"] = True
            return redirect("/dashboard")

        return "Неверный код"

    return render_template_string(base % """
    <h2>Введите код</h2>
    <form method="post">
    <input name="code">
    <button>Войти</button>
    </form>
    """)

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    return render_template_string(base % """
    <h2>Запись</h2>
    <form method="post" action="/book">
    Станция <input name="station">
    <button>Записаться</button>
    </form>
    """)

# ---------- BOOK ----------
@app.route("/book", methods=["POST"])
def book():
    now = datetime.now().hour

    if now < 17 or now >= 20:
        return "Запись закрыта"

    c = db()
    cur = c.cursor()

    count = cur.execute("SELECT COUNT(*) FROM bookings").fetchone()[0]
app.run
app.run - This website is for sale! - app Resources and Information.
This website is for sale! app.run is your first and best source for information about app. Here you will also find topics relating to issues of general interest. We hope you find what ...
00:37
if count >= 7:
        return "Извините, мест нет"

    cur.execute("INSERT INTO bookings VALUES (?,?)",
                (session.get("name"), request.form["station"]))
    c.commit()

    return "Вы записаны"

# ---------- AUTO RESULT ----------
@app.before_request
def auto_send_results():
    now = datetime.now().hour

    c = db()
    cur = c.cursor()

    done = cur.execute("SELECT done FROM result_sent").fetchone()[0]

    if now >= 20 and done == 0:
        users = cur.execute("SELECT name,email FROM users").fetchall()
        winners = cur.execute("SELECT name FROM bookings LIMIT 7").fetchall()
        winners = [w[0] for w in winners]

        for u in users:
            if u[0] in winners:
                send_email(u[1], "Результат", "Вы записаны на автобус")
            else:
                send_email(u[1], "Результат", "Вы не успели записаться")

        cur.execute("UPDATE result_sent SET done=1")
        c.commit()

# ---------- DRIVER ----------
@app.route("/driver")
def driver():
    if datetime.now().hour < 20:
        return "Список будет после 20:00"

    c = db()
    data = c.execute("SELECT name,station FROM bookings").fetchall()

    rows = "".join([f"<p>{d[0]} — {d[1]}</p>" for d in data])

    return render_template_string(base % f"""
    <h2>Список пассажиров</h2>
    {rows}
    """)

# ---------- ADMIN ----------
@app.route("/admin")
def admin():
    return render_template_string(base % """
    <h2>Админка</h2>
    """)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
