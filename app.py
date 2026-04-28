from flask import Flask, request, redirect, session, render_template_string
import sqlite3, random, time
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

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

    cur.execute("CREATE TABLE IF NOT EXISTS stations(name TEXT UNIQUE)")
    cur.execute("CREATE TABLE IF NOT EXISTS bookings(name TEXT, station TEXT)")

    stations = ["Лобня","Физтех","Селигерская","Катуар","Подосинки"]
    for s in stations:
        cur.execute("INSERT OR IGNORE INTO stations VALUES(?)",(s,))

    c.commit()
    c.close()

init()

# ---------- UI ----------
base = """
<html>
<head>
<style>
body{font-family:Arial;background:#0f172a;color:#fff;text-align:center}
.container{margin-top:80px}
input,button{padding:10px;margin:5px;border-radius:6px;border:none}
button{background:#22c55e;color:#fff;cursor:pointer}
.top{
position:fixed;
top:10px;
right:10px;
}
</style>
</head>
<body>

<div class="top">
<a href="/admin_login"><button>Админ</button></a>
<a href="/driver_login"><button>Водитель</button></a>
</div>

<div class="container">
%s
</div>
</body>
</html>
"""

def send_code(email, code):
    print("CODE:", code)

# ---------- HOME ----------
@app.route("/")
def home():
    return render_template_string(base % """
    <h1>🚍 Bus Booking</h1>
    <a href="/login"><button>Войти</button></a>
    <a href="/register"><button>Регистрация</button></a>
    """)

# ---------- REGISTER ----------
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        c = db()
        cur = c.cursor()
        cur.execute("INSERT INTO users(name,email) VALUES (?,?)",
                    (request.form["name"], request.form["email"]))
        c.commit()
        return redirect("/login")

    return render_template_string(base % """
    <h2>Регистрация</h2>
    <form method="post">
    ФИО<br><input name="name"><br>
    Email<br><input name="email"><br>
    <button>Создать</button>
    </form>
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
        user = cur.execute("SELECT code,role FROM users WHERE name=?", (name,)).fetchone()

        if user and user[0] == code:
            session["auth"] = True
            session["role"] = user[1]
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
    if not session.get("auth"):
        return redirect("/")

    c = db()
00:25
stations = c.execute("SELECT name FROM stations").fetchall()
    options = "".join([f"<option>{s[0]}</option>" for s in stations])

    return render_template_string(base % f"""
    <h2>Выбор станции</h2>
    <form method="post" action="/book">
    <select name="station">{options}</select><br>
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

    if count >= 7:
        return "Извините, мест нет"

    cur.execute("INSERT INTO bookings VALUES (?,?)",
                (session.get("name"), request.form["station"]))
    c.commit()

    return "Вы записаны"

# ---------- ADMIN LOGIN ----------
@app.route("/admin_login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        if request.form["login"] == "admin" and request.form["password"] == "Emerson08com":
            session["role"] = "admin"
            return redirect("/admin")

    return render_template_string(base % """
    <h2>Вход админа</h2>
    <form method="post">
    Логин <input name="login"><br>
    Пароль <input name="password" type="password"><br>
    <button>Войти</button>
    </form>
    """)

# ---------- ADMIN PANEL ----------
@app.route("/admin", methods=["GET","POST"])
def admin():
    if session.get("role") != "admin":
        return "Нет доступа"

    return render_template_string(base % """
    <h2>Админка</h2>

    <form method="post" action="/add_user">
    ФИО <input name="name">
    Email <input name="email">
    <button>Добавить</button>
    </form>

    <form method="post" action="/add_station">
    <input name="station">
    <button>Добавить станцию</button>
    </form>
    """)

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

# ---------- DRIVER LOGIN ----------
@app.route("/driver_login", methods=["GET","POST"])
def driver_login():
    if request.method == "POST":
        if request.form["login"] == "driver" and request.form["password"] == "Driver08":
            session["role"] = "driver"
            return redirect("/driver")

    return render_template_string(base % """
    <h2>Вход водителя</h2>
    <form method="post">
    Логин <input name="login"><br>
    Пароль <input name="password" type="password"><br>
    <button>Войти</button>
    </form>
    """)

# ---------- DRIVER PANEL ----------
@app.route("/driver")
def driver():
    if session.get("role") != "driver":
        return "Нет доступа"

    c = db()
    data = c.execute("SELECT name, station FROM bookings").fetchall()

    rows = "".join([f"<p>{d[0]} — {d[1]}</p>" for d in data])

    return render_template_string(base % f"""
    <h2>Список пассажиров</h2>
    {rows}
    """)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
