from flask import Flask, render_template, request, jsonify, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import datetime
import random
import time
import smtplib

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- CONFIG ----------------
OTP_EXPIRY_SECONDS = 300
pending_users = {}

# 🔐 EMAIL CONFIG (use your own app password)
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
    data = request.get_json()

    name = data.get("name")
    email = data.get("email").lower()
    gender = data.get("gender")
    password = data.get("password")
    confirm = data.get("confirmPassword")

    if password != confirm:
        return jsonify({"success": False, "message": "Passwords do not match"})

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM USER WHERE EMAIL=?", (email,))
    if cur.fetchone():
        return jsonify({"success": False, "message": "Email already exists"})

    otp = str(random.randint(1000, 9999))

    pending_users[email] = {
        "name": name,
        "email": email,
        "gender": gender,
        "password": password,
        "otp": otp,
        "expires": time.time() + OTP_EXPIRY_SECONDS
    }

    # Send Email
    try:
        msg = f"Subject: OTP Verification\n\nYour OTP is {otp}"
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, email, msg)
        server.quit()
    except:
        print("OTP:", otp)

    return jsonify({"success": True})

# ---------------- VERIFY OTP ----------------
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    email = data.get("email")
    otp = data.get("otp")

    if email not in pending_users:
        return jsonify({"success": False})

    user = pending_users[email]

    if time.time() > user["expires"]:
        del pending_users[email]
        return jsonify({"success": False, "message": "OTP expired"})

    if otp != user["otp"]:
        return jsonify({"success": False, "message": "Wrong OTP"})

    conn = get_db()
    cur = conn.cursor()

    # Generate USER_ID
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
    if "email" not in session:
        return redirect("/login")

    return render_template("dashboard.html", user_email=session["email"])

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

# ---------------- GOALS (GET + POST FIXED) ----------------
@app.route("/goals", methods=["GET", "POST"])
def goals():
    if "user_id" not in session:
        return redirect("/login")

    # ✅ Page load
    if request.method == "GET":
        return render_template("goals.html")

    # ✅ AJAX POST
    try:
        user_id = session["user_id"]

        goal_name = request.form.get("goal_name")
        goal_amount = float(request.form.get("goal_amount") or 0)
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        status = request.form.get("goal_status")

        monthly = round(goal_amount / 12, 2) if goal_amount else 0
        duration = 12

        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute("SELECT MAX(GOAL_ID) FROM GOALS")
            result = cur.fetchone()[0]
            goal_id = 1 if result is None else result + 1

            cur.execute("""
                INSERT INTO GOALS (
                    GOAL_ID, USER_ID, GOAL_NAME, GOAL_AMOUNT,
                    START_DATE, END_DATE, STATUS, CREATED_AT
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                goal_id,
                user_id,
                goal_name,
                goal_amount,
                start_date,
                end_date,
                status,
                datetime.datetime.now()
            ))

            conn.commit()
        except:
            pass

        conn.close()

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