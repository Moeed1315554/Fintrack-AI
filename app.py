from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import random
import time
import sqlite3
import datetime
import smtplib

app = Flask(__name__)

OTP_EXPIRY_SECONDS = 300
pending_users = {}

# ---------------- DB CONNECTION ----------------
def get_db():
    return sqlite3.connect("fintrackai.db")


# ---------------- OTP ----------------
def generate_otp():
    return str(random.randint(1000, 9999))


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/signup")
def signup_page():
    return render_template("signup.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT PASSWORD_HASH FROM USER WHERE EMAIL=?", (email,))
        user = cur.fetchone()

        if user:
            if check_password_hash(user[0], password):
                return render_template("dashboard.html", user_email=email)
            else:
                error = "Invalid password"
        else:
            error = "Invalid email"

        conn.close()

    return render_template("login.html", error=error)


# ---------------- SIGNUP SEND OTP ----------------
@app.route("/send-otp", methods=["POST"])
def send_otp():
    try:
        data = request.get_json()

        name = data.get("name")
        email = data.get("email").lower()
        gender = data.get("gender")
        password = data.get("password")
        confirm_password = data.get("confirmPassword")

        if password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match"}), 400

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT EMAIL FROM USER WHERE EMAIL=?", (email,))
        if cur.fetchone():
            return jsonify({"success": False, "message": "Email already exists"}), 400

        otp = generate_otp()

        pending_users[email] = {
            "name": name,
            "email": email,
            "gender": gender,
            "password": password,
            "otp": otp,
            "expires_at": time.time() + OTP_EXPIRY_SECONDS
        }

        # EMAIL SEND
        sender_email = "your_email@gmail.com"
        app_password = "your_app_password"

        message = f"Subject: OTP\n\nYour OTP is {otp}"

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, email, message)
        server.quit()

        return jsonify({"success": True, "message": "OTP sent"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ---------------- VERIFY OTP ----------------
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json()

        email = data.get("email")
        otp = data.get("otp")

        if email not in pending_users:
            return jsonify({"success": False, "message": "No signup found"}), 400

        user = pending_users[email]

        if time.time() > user["expires_at"]:
            return jsonify({"success": False, "message": "OTP expired"}), 400

        if otp != user["otp"]:
            return jsonify({"success": False, "message": "Wrong OTP"}), 400

        hashed_password = generate_password_hash(user["password"])

        conn = get_db()
        cur = conn.cursor()

        # AUTO ID (IMPORTANT FIX)
        cur.execute("""
            INSERT INTO USER (NAME, GENDER, EMAIL, PASSWORD_HASH, CREATED_AT)
            VALUES (?, ?, ?, ?, ?)
        """, (
            user["name"],
            user["gender"],
            user["email"],
            hashed_password,
            datetime.datetime.now()
        ))

        conn.commit()
        conn.close()

        del pending_users[email]

        return jsonify({"success": True, "message": "User registered"})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ---------------- INCOME ----------------
@app.route("/income", methods=["GET", "POST"])
def income():
    if request.method == "GET":
        return render_template("income.html")

    try:
        email = request.form.get("email")

        conn = get_db()
        cur = conn.cursor()

        cur.execute("SELECT USER_ID FROM USER WHERE EMAIL=?", (email,))
        user = cur.fetchone()

        if not user:
            return render_template("income.html", error="User not found")

        user_id = user[0]

        cur.execute("""
            INSERT INTO INCOMEPROFILE (
                USER_ID, INCOME_TYPE, MONTHLY_INCOME,
                ADDITIONAL_INCOME_TYPE, ADDITIONAL_MONTHLY_INCOME,
                DEPENDANTS, CREATED_AT, UPDATED_AT
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            request.form.get("income_type"),
            float(request.form.get("monthly_income")),
            request.form.get("additional_income_type"),
            float(request.form.get("additional_monthly_income")),
            int(request.form.get("dependants")),
            datetime.datetime.now(),
            datetime.datetime.now()
        ))

        conn.commit()
        conn.close()

        return render_template("income.html", success="Saved successfully")

    except Exception as e:
        return render_template("income.html", error=str(e))


if __name__ == "__main__":
    app.run(debug=True)