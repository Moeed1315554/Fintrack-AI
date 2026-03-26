from flask import Flask, render_template, request, jsonify
from werkzeug.security import generate_password_hash
import random
import time
import sqlite3
import datetime

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