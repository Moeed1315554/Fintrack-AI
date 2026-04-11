from flask import Flask, render_template, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import datetime
import random
import time
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- CONFIG ----------------
OTP_EXPIRY_SECONDS = 300
pending_users = {}

# 🔐 GMAIL CONFIG (USE YOUR APP PASSWORD)
SENDER_EMAIL = "mdmoeed1315554@gmail.com"
APP_PASSWORD = "ghvi lyjq zknu agoi"

# ---------------- DB ----------------
def get_db():
    return sqlite3.connect("fintrackai.db")

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- SIGNUP PAGE ----------------
@app.route("/signup")
def signup_page():
    return render_template("signup.html")

# ---------------- SEND OTP ----------------
@app.route("/send-otp", methods=["POST"])
def send_otp():
    try:
        data = request.get_json()

        name = data.get("name")
        email = data.get("email")
        password = data.get("password")
        gender = data.get("gender")

        otp = str(random.randint(1000, 9999))

        pending_users[email] = {
            "name": name,
            "email": email,
            "password": password,
            "gender": gender,
            "otp": otp,
            "expires_at": time.time() + OTP_EXPIRY_SECONDS
        }

        # ✅ GMAIL SMTP
        msg = MIMEText(f"Your OTP is: {otp}")
        msg["Subject"] = "FinTrack AI OTP"
        msg["From"] = SENDER_EMAIL
        msg["To"] = email

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, email, msg.as_string())
        server.quit()

        print("OTP SENT:", otp)

        return jsonify({"success": True})

    except Exception as e:
        print("SEND OTP ERROR:", str(e))
        return jsonify({"success": False, "message": str(e)})

# ---------------- VERIFY OTP ----------------
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get("email")
        otp = data.get("otp")

        if email not in pending_users:
            return jsonify({"success": False, "message": "No signup found"})

        user = pending_users[email]

        if time.time() > user["expires_at"]:
            del pending_users[email]
            return jsonify({"success": False, "message": "OTP expired"})

        if otp != user["otp"]:
            return jsonify({"success": False, "message": "Wrong OTP"})

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT MAX(USER_ID) FROM USER")
        result = cur.fetchone()[0]
        user_id = 1 if result is None else result + 1

        cur.execute("""
            INSERT INTO USER (USER_ID, USER_NAME, GENDER, EMAIL, PASSWORD_HASH, CREATED_AT)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            user["name"],
            user["gender"],
            user["email"],
            generate_password_hash(user["password"]),
            datetime.datetime.now()
        ))

        conn.commit()
        conn.close()

        del pending_users[email]

        return jsonify({"success": True})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email")
    password = request.form.get("password")

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT USER_ID, PASSWORD_HASH FROM USER WHERE EMAIL=?", (email,))
    user = cur.fetchone()
    conn.close()

    if user and check_password_hash(user[1], password):
        session["user_id"] = user[0]
        session["email"] = email
        return redirect("/dashboard")

    return render_template("login.html", error="Invalid credentials")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

# ---------------- INCOME ----------------
@app.route("/income", methods=["GET", "POST"])
def income():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "GET":
        return render_template("income.html")

    try:
        now = datetime.datetime.now()
        user_id = session["user_id"]

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT MAX(PROFILE_ID) FROM INCOMEPROFILE")
        result = cur.fetchone()[0]
        profile_id = 1 if result is None else result + 1

        cur.execute("""
            INSERT INTO INCOMEPROFILE (
                PROFILE_ID, USER_ID, INCOME_TYPE, MONTHLY_INCOME,
                ADDITIONAL_INCOME_TYPE, ADDITIONAL_MONTHLY_INCOME,
                DEPENDANTS, CREATED_AT, UPDATED_AT
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id,
            user_id,
            request.form.get("income_type"),
            float(request.form.get("monthly_income") or 0),
            request.form.get("additional_income_type"),
            float(request.form.get("additional_monthly_income") or 0),
            int(request.form.get("dependants") or 0),
            now,
            now
        ))

        conn.commit()
        conn.close()

        return render_template("income.html", success="Saved successfully")

    except Exception as e:
        return render_template("income.html", error=str(e))

# ---------------- EXPENSE ----------------
@app.route("/expense", methods=["GET", "POST"])
def expense():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "GET":
        return render_template("expense.html")

    try:
        now = datetime.datetime.now()

        conn = get_db()
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO EXPENSEPROFILE (
                USER_ID, GROCERIES, TRAVEL, MEDFIT, LEP,
                MONTHLY_RENT, M_BILLS, FASHION,
                ENTERTAINMENT, EDUCATION, EMSAVING,
                MISCELLANEOUS, CREATED_AT
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            float(request.form.get("groceries") or 0),
            float(request.form.get("travel") or 0),
            float(request.form.get("medfit") or 0),
            float(request.form.get("lep") or 0),
            float(request.form.get("monthly_rent") or 0),
            float(request.form.get("m_bills") or 0),
            float(request.form.get("fashion") or 0),
            float(request.form.get("entertainment") or 0),
            float(request.form.get("education") or 0),
            float(request.form.get("emsaving") or 0),
            float(request.form.get("miscellaneous") or 0),
            now
        ))

        conn.commit()
        conn.close()

        return render_template("expense.html", success="Saved successfully")

    except Exception as e:
        return render_template("expense.html", error=str(e))

# ---------------- GOALS ----------------
@app.route("/goals", methods=["GET", "POST"])
def goals():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "GET":
        return render_template("goals.html")

    try:
        goal_amount = float(request.form.get("goal_amount") or 0)

        monthly = round(goal_amount / 12, 2)
        duration = 12

        return jsonify({
            "success": True,
            "monthlytarget": monthly,
            "durationinmonth": duration
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True, port=5050)