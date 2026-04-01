from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash,check_password_hash
import random
import time
import sqlite3
import datetime
import smtplib

app = Flask(__name__)

pending_users = {}
registered_users = {}
conn = sqlite3.connect("fintrackai.db")
cur = conn.cursor()
cur.execute("select * from user")
x = cur.fetchall()
reg = []
for i in x:
    reg.append(i[3].lower())

OTP_EXPIRY_SECONDS = 300  # 5 minutes


def generate_otp():
    return str(random.randint(1000, 9999))


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/signup")
def signup_page():
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        user_email = request.form.get("email", "").strip()
        user_password = request.form.get("password", "").strip()

        # Check email first
        conn = sqlite3.connect('fintrackai.db')
        cur = conn.cursor()
        cur.execute("SELECT EMAIL,PASSWORD FROM USER")
        x = dict(cur.fetchall())

        if user_email in x:
            # Check hashed password
            if check_password_hash(x[user_email], user_password):
                return render_template("dashboard.html", user_email=user_email)
            else:
                error = "Invalid password."
        else:
            error = "Invalid email."

    return render_template("login.html", error=error)

@app.route("/income", methods=["GET", "POST"])
def income():
    if request.method == "GET":
        return render_template("income.html")

    email = request.form.get("email", "").strip()
    income_type = request.form.get("income_type", "").strip()
    monthly_income = request.form.get("monthly_income", "").strip()
    additional_income_type = request.form.get("additional_income_type", "").strip()
    additional_monthly_income = request.form.get("additional_monthly_income", "").strip()
    dependants = request.form.get("dependants", "").strip()

    conn = sqlite3.connect('fintrackai.db')
    cur = conn.cursor()
    cur.execute("SELECT EMAIL,PASSWORD FROM USER")
    x = dict(cur.fetchall())

    if email not in x:
        return render_template("income.html", error="Email is required.")

    try:

        # Assumption: USER table contains EMAIL column
        cur.execute("SELECT USER_ID FROM USER WHERE EMAIL = ?", (email,))
        user_row = cur.fetchone()

        if not user_row:
            conn.close()
            return render_template("income.html", error="No user found with this email.")

        user_id = user_row[0]
        now = datetime.datetime.now()
        profile_id = cur.execute("SELECT max(PROFILE_ID) FROM INCOMEPROFILE")
        x = cur.fetchall()
        if x[0][0]==None:
            x = 1
        else:
            x = x[0][0]+1

        cur.execute("""
            INSERT INTO INCOMEPROFILE (
                PROFILE_ID,
                USER_ID,
                INCOME_TYPE,
                MONTHLY_INCOME,
                ADDITIONAL_INCOME_TYPE,
                ADDITIONAL_MONTHLY_INCOME,
                DEPENDANTS,
                CREATED_AT,
                UPDATED_AT
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            int(x),
            int(user_id),
            income_type,
            float(monthly_income),
            additional_income_type,
            float(additional_monthly_income),
            int(dependants),
            now,
            now
        ))

        conn.commit()
        conn.close()

        return render_template("income.html", success="Income profile saved successfully.")

    except sqlite3.IntegrityError as e:
        return render_template("income.html", error=f"Database integrity error: {str(e)}")

    except Exception as e:
        return render_template("income.html", error=f"Error: {str(e)}")

@app.route("/send-otp", methods=["POST"])
def send_otp():
    try:
        data = request.get_json()

        name = data.get("name", "").strip()
        email = data.get("email", "").strip().lower()
        gender = data.get("gender", "").strip()
        password = data.get("password", "")
        confirm_password = data.get("confirmPassword", "")

        if not name or not email or not gender or not password or not confirm_password:
            return jsonify({"success": False, "message": "All fields are required."}), 400

        if gender not in ["Male", "Female"]:
            return jsonify({"success": False, "message": "Invalid gender selected."}), 400

        if password != confirm_password:
            return jsonify({"success": False, "message": "Passwords do not match."}), 400

        if len(password) < 6:
            return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400
        print(email,reg)
        if email in reg:
            return jsonify({"success": False, "message": "User already registered with this email."}), 400

        otp = generate_otp()
        expires_at = time.time() + OTP_EXPIRY_SECONDS

        pending_users[email] = {
            "name": name,
            "email": email,
            "gender": gender,
            "password": password,
            "otp": otp,
            "expires_at": expires_at
        }

        print("\n" + "=" * 60)
        print(f"CORRECT OTP for {email}: {otp}")
        print("=" * 60 + "\n")
        sender_email = "shaswatmohapatra5@gmail.com"
        app_password = "ywah ukcd bnsp rubo"

        subject = "OTP Verification"
        body = f"Your OTP is: {otp}"
        message = f"Subject: {subject}\nTo: {email}\nFrom: {sender_email}\n\n{body}"

        server = smtplib.SMTP("smtp.gmail.com",587)
        server.starttls()
        server.login(sender_email,app_password)
        server.sendmail(sender_email,email,message)
        server.quit()

        return jsonify({
            "success": True,
            "message": "OTP generated successfully. Please enter OTP."
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data = request.get_json()

        email = data.get("email", "").strip().lower()
        otp = data.get("otp", "").strip()

        if not email or not otp:
            return jsonify({"success": False, "message": "Email and OTP are required."}), 400

        if email not in pending_users:
            return jsonify({"success": False, "message": "No pending signup found for this email."}), 400

        user_data = pending_users[email]

        if time.time() > user_data["expires_at"]:
            del pending_users[email]
            return jsonify({"success": False, "message": "OTP expired. Please sign up again."}), 400

        if otp != user_data["otp"]:
            return jsonify({"success": False, "message": "Incorrect OTP. User not registered."}), 400

        hashed_password = generate_password_hash(user_data["password"])

        registered_users[email] = {
            "name": user_data["name"],
            "email": user_data["email"],
            "gender": user_data["gender"],
            "password": hashed_password,
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        print(registered_users)
        conn = sqlite3.connect("fintrackai.db")
        cur = conn.cursor()
        cur.execute("select max(user_id) from user")
        x1 = cur.fetchall()
        cur.execute(f'''
            INSERT INTO USER VALUES({x1[0][0]+1},"{registered_users[email]['name']}",
            "{registered_users[email]['gender']}","{registered_users[email]['email']}",
            "{registered_users[email]['password']}","{datetime.datetime.now()}")
            ''')
        conn.commit()

        print(pending_users)
        
        cur.execute("select max(otp_id) from VERIFICATION")
        x2 = cur.fetchall()
        cur.execute(f'''
            INSERT INTO VERIFICATION VALUES({x2[0][0]+1},{x1[0][0]+1},
            {pending_users[email]['otp']},"{pending_users[email]['expires_at']}",
            "{datetime.datetime.now()}","VERIFIED")
            ''')
        conn.commit()

        del pending_users[email]

        return jsonify({
            "success": True,
            "message": "User registered successfully."
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


@app.route("/users", methods=["GET"])
def users():
    return jsonify({
        "success": True,
        "registered_users": registered_users
    }), 200


if __name__ == "__main__":
    app.run(debug=True)