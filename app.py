from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()
from werkzeug.security import generate_password_hash, check_password_hash
from recommendation import target
import random
import time
import sqlite3
import datetime
import os

app = Flask(__name__)

pending_users = {}
registered_users = {}

OTP_EXPIRY_SECONDS = 300  # 5 minutes

# ─── Helper: get a fresh DB connection ────────────────────────────────────────
def get_db():
    conn = sqlite3.connect("fintrackai.db")
    conn.row_factory = sqlite3.Row
    return conn


def generate_otp():
    return str(random.randint(1000, 9999))


# ─── Home ──────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")


# ─── Signup page ───────────────────────────────────────────────────────────────
@app.route("/signup")
def signup_page():
    return render_template("signup.html")


# ─── Login ─────────────────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        user_email = request.form.get("email", "").strip()
        user_password = request.form.get("password", "").strip()

        conn = get_db()
        cur = conn.cursor()

        # FIX: parameterised query instead of fetching all rows
        cur.execute(
            "SELECT PASSWORD_HASH FROM USER WHERE EMAIL = ?", (user_email,)
        )
        row = cur.fetchone()
        conn.close()

        if row:
            if check_password_hash(row["PASSWORD_HASH"], user_password):
                return render_template("dashboard.html", user_email=user_email)
            else:
                error = "Invalid password."
        else:
            error = "Invalid email."

    return render_template("login.html", error=error)


# ─── Income ────────────────────────────────────────────────────────────────────
@app.route("/income", methods=["GET", "POST"])
def income():
    if request.method == "GET":
        return render_template("income.html")

    email                   = request.form.get("email", "").strip()
    income_type             = request.form.get("income_type", "").strip()
    monthly_income          = request.form.get("monthly_income", "").strip()
    additional_income_type  = request.form.get("additional_income_type", "").strip()
    additional_monthly_income = request.form.get("additional_monthly_income", "").strip()
    dependants              = request.form.get("dependants", "").strip()

    if not email:
        return render_template("income.html", error="Email is required.")

    try:
        conn = get_db()
        cur  = conn.cursor()

        cur.execute("SELECT USER_ID FROM USER WHERE EMAIL = ?", (email,))
        user_row = cur.fetchone()

        if not user_row:
            conn.close()
            return render_template("income.html", error="No user found with this email.")

        user_id = user_row["USER_ID"]
        now     = datetime.datetime.now()

        # FIX: safe MAX + handle NULL (empty table)
        cur.execute("SELECT COALESCE(MAX(PROFILE_ID), 0) FROM INCOMEPROFILE")
        profile_id = cur.fetchone()[0] + 1

        cur.execute("""
            INSERT INTO INCOMEPROFILE (
                PROFILE_ID, USER_ID, INCOME_TYPE,
                MONTHLY_INCOME, ADDITIONAL_INCOME_TYPE,
                ADDITIONAL_MONTHLY_INCOME, DEPENDANTS,
                CREATED_AT, UPDATED_AT
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            profile_id,
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
    except ValueError:
        return render_template("income.html", error="Please enter valid numeric values.")
    except Exception as e:
        return render_template("income.html", error=f"Error: {str(e)}")


# ─── Expense ───────────────────────────────────────────────────────────────────
@app.route("/expense", methods=["GET", "POST"])
def expense():
    if request.method == "GET":
        return render_template("expense.html")

    email         = request.form.get("email", "").strip()
    groceries     = request.form.get("groceries", "").strip()
    travel        = request.form.get("travel", "").strip()
    medfit        = request.form.get("medfit", "").strip()
    lep           = request.form.get("lep", "").strip()
    monthly_rent  = request.form.get("monthly_rent", "").strip()
    m_bills       = request.form.get("m_bills", "").strip()
    fashion       = request.form.get("fashion", "").strip()
    entertainment = request.form.get("entertainment", "").strip()
    education     = request.form.get("education", "").strip()
    emsaving      = request.form.get("emsaving", "").strip()
    miscellaneous = request.form.get("miscellaneous", "").strip()

    if not email:
        return render_template("expense.html", error="Email is required.")

    try:
        conn = get_db()
        cur  = conn.cursor()

        cur.execute("SELECT USER_ID FROM USER WHERE EMAIL = ?", (email,))
        user_row = cur.fetchone()

        if not user_row:
            conn.close()
            return render_template("expense.html", error="No user found with this email.")

        user_id = user_row["USER_ID"]

        # FIX: safe MAX + handle NULL
        cur.execute("SELECT COALESCE(MAX(EXPENSE_ID), 0) FROM EXPENSEPROFILE")
        expense_id = cur.fetchone()[0] + 1

        cur.execute("""
            INSERT INTO EXPENSEPROFILE (
                EXPENSE_ID, USER_ID,
                GROCERIES, TRAVEL, MEDFIT, LEP,
                MONTHLY_RENT, M_BILLS, FASHION,
                ENTERTAINMENT, EDUCATION, EMSAVING,
                MISCELLANEOUS, CREATED_AT
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            expense_id,
            int(user_id),
            float(groceries),
            float(travel),
            float(medfit),
            float(lep),
            float(monthly_rent),
            float(m_bills),
            float(fashion),
            float(entertainment),
            float(education),
            float(emsaving),
            float(miscellaneous),
            datetime.datetime.now()
        ))

        conn.commit()
        conn.close()
        return render_template("expense.html", success="Expense profile saved successfully.")

    except sqlite3.IntegrityError as e:
        return render_template("expense.html", error=f"Database integrity error: {str(e)}")
    except ValueError:
        return render_template("expense.html", error="Please enter valid numeric values in all amount fields.")
    except Exception as e:
        return render_template("expense.html", error=f"Error: {str(e)}")


# ─── Goals ─────────────────────────────────────────────────────────────────────
@app.route("/goals", methods=["GET", "POST"])
def goals():
    if request.method == "GET":
        return render_template("goals.html")

    try:
        email       = request.form.get("email", "").strip()
        goal_name   = request.form.get("goal_name", "").strip()
        goal_amount = request.form.get("goal_amount", "").strip()
        start_date  = request.form.get("start_date", "").strip()
        end_date    = request.form.get("end_date", "").strip()
        goal_status = request.form.get("goal_status", "").strip()

        if not all([email, goal_name, goal_amount, start_date, end_date, goal_status]):
            return jsonify({"success": False, "error": "All fields are required."})

        goal_amount = float(goal_amount)

        ob  = target(email)
        res = ob.monthly_target(goal_amount)

        # FIX: handle error tuple returned by monthly_target
        if isinstance(res[0], str):
            return jsonify({"success": False, "error": res[0]})

        monthly_saving_t, duration_in_month = res

        conn = get_db()
        cur  = conn.cursor()

        cur.execute("SELECT USER_ID FROM USER WHERE EMAIL = ?", (email,))
        user = cur.fetchone()

        if not user:
            conn.close()
            return jsonify({"success": False, "error": "User not found."})

        user_id = user["USER_ID"]

        # Generate unique GOALID
        while True:
            goal_id = random.randint(10000, 99999)
            cur.execute("SELECT 1 FROM GOALS WHERE GOALID = ?", (goal_id,))
            if not cur.fetchone():
                break

        now = datetime.datetime.now()

        cur.execute("""
            INSERT INTO GOALS (
                GOALID, USER_ID, GOAL_NAME,
                START_DATE, END_DATE, GOAL_AMOUNT,
                MONTHLY_SAVING_T, GOAL_STATUS,
                CREATED_AT, UPDATED_AT
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            goal_id,
            user_id,
            goal_name,
            start_date,
            end_date,
            goal_amount,
            monthly_saving_t,
            goal_status,
            now,
            now
        ))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "monthlytarget": monthly_saving_t,
            "durationinmonth": duration_in_month
        })

    except ValueError:
        return jsonify({"success": False, "error": "Please enter valid numeric values and valid dates."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ─── Send OTP ──────────────────────────────────────────────────────────────────
@app.route("/send-otp", methods=["POST"])
def send_otp():
    try:
        import requests as http_requests

        data     = request.get_json()
        name     = data.get("name", "").strip()
        email    = data.get("email", "").strip().lower()
        gender   = data.get("gender")
        password = data.get("password")

        if not name or not email:
            return jsonify({"message": "Name and email required"}), 400

        # FIX: check if email is already registered before sending OTP
        conn = get_db()
        cur  = conn.cursor()
        cur.execute("SELECT 1 FROM USER WHERE EMAIL = ?", (email,))
        if cur.fetchone():
            conn.close()
            return jsonify({"message": "Email already registered."}), 400
        conn.close()

        otp = generate_otp()

        pending_users[email] = {
            "name": name,
            "gender": gender,
            "email": email,
            "password": password,
            "otp": otp,
            "expires_at": time.time() + OTP_EXPIRY_SECONDS
        }

        api_key      = os.getenv("MAIL_API")
        sender_email = os.getenv("SENDER_MAIL")

        if not api_key or not sender_email:
            return jsonify({"message": "Email service not configured"}), 500

        response = http_requests.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": api_key,
                "content-type": "application/json"
            },
            json={
                "sender": {"name": "FinTrack AI", "email": sender_email},
                "to": [{"email": email, "name": name}],
                "subject": "Your OTP Code",
                "htmlContent": f"<h2>Your OTP is: {otp}</h2>"
            }
        )

        if response.status_code not in [200, 201]:
            return jsonify({"message": "Failed to send OTP", "error": response.text}), 500

        return jsonify({"message": "OTP sent successfully"}), 200

    except Exception as e:
        return jsonify({"message": f"Error: {str(e)}"}), 500


# ─── Verify OTP & Register User ────────────────────────────────────────────────
@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    try:
        data  = request.get_json()
        email = data.get("email", "").strip().lower()
        otp   = data.get("otp", "").strip()

        if not email or not otp:
            return jsonify({"success": False, "message": "Email and OTP are required."}), 400

        if email not in pending_users:
            return jsonify({"success": False, "message": "No pending signup found for this email."}), 400

        user_data = pending_users[email]

        if time.time() > user_data["expires_at"]:
            del pending_users[email]
            return jsonify({"success": False, "message": "OTP expired. Please sign up again."}), 400

        if otp != user_data["otp"]:
            return jsonify({"success": False, "message": "Incorrect OTP."}), 400

        hashed_password = generate_password_hash(user_data["password"])

        conn = get_db()
        cur  = conn.cursor()

        # FIX: safe MAX with COALESCE to avoid NoneType crash on empty table
        cur.execute("SELECT COALESCE(MAX(USER_ID), 0) FROM USER")
        new_user_id = cur.fetchone()[0] + 1

        # FIX: parameterised INSERT — no f-string injection risk
        cur.execute(
            "INSERT INTO USER (USER_ID, USER_NAME, GENDER, EMAIL, PASSWORD_HASH, CREATED_AT) VALUES (?, ?, ?, ?, ?, ?)",
            (
                new_user_id,
                user_data["name"],
                user_data["gender"],
                user_data["email"],
                hashed_password,
                datetime.datetime.now()
            )
        )
        conn.commit()

        # FIX: safe MAX for OTP_ID
        cur.execute("SELECT COALESCE(MAX(OTP_ID), 0) FROM VERIFICATION")
        new_otp_id = cur.fetchone()[0] + 1

        cur.execute(
            "INSERT INTO VERIFICATION (OTP_ID, USER_ID, EMAIL_OTP, OTP_EXP, OTP_CREATION, OTP_STATUS) VALUES (?, ?, ?, ?, ?, ?)",
            (
                new_otp_id,
                new_user_id,
                int(user_data["otp"]),
                user_data["expires_at"],
                datetime.datetime.now(),
                "VERIFIED"
            )
        )
        conn.commit()
        conn.close()

        registered_users[email] = {
            "name": user_data["name"],
            "email": user_data["email"],
            "gender": user_data["gender"],
            "registered_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        del pending_users[email]

        return jsonify({"success": True, "message": "User registered successfully."}), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"Error: {str(e)}"}), 500


# ─── Analytics ─────────────────────────────────────────────────────────────────
@app.route("/analytics", methods=["GET"])
def analytics():
    return render_template("analytics.html")


@app.route("/analytics-data", methods=["POST"])
def analytics_data():
    try:
        data  = request.get_json()
        email = data.get("email", "").strip()

        if not email:
            return jsonify({"success": False, "error": "Email is required."})

        conn = get_db()
        cur  = conn.cursor()

        cur.execute("SELECT USER_ID FROM USER WHERE EMAIL = ?", (email,))
        user = cur.fetchone()

        if not user:
            conn.close()
            return jsonify({"success": False, "error": "No user found with this email."})

        user_id = user["USER_ID"]

        # Latest income profile
        cur.execute("""
            SELECT MONTHLY_INCOME, ADDITIONAL_MONTHLY_INCOME,
                   DEPENDANTS, INCOME_TYPE, ADDITIONAL_INCOME_TYPE
            FROM INCOMEPROFILE
            WHERE USER_ID = ?
            ORDER BY CREATED_AT DESC
            LIMIT 1
        """, (user_id,))
        income_row = cur.fetchone()

        if not income_row:
            conn.close()
            return jsonify({"success": False, "error": "Income profile not found for this user."})

        income_data = {
            "monthly_income":            float(income_row["MONTHLY_INCOME"] or 0),
            "additional_monthly_income": float(income_row["ADDITIONAL_MONTHLY_INCOME"] or 0),
            "dependants":                int(income_row["DEPENDANTS"] or 0),
            "income_type":               income_row["INCOME_TYPE"],
            "additional_income_type":    income_row["ADDITIONAL_INCOME_TYPE"]
        }

        # Latest expense profile
        cur.execute("""
            SELECT GROCERIES, TRAVEL, MEDFIT, LEP,
                   MONTHLY_RENT, M_BILLS, FASHION,
                   ENTERTAINMENT, EDUCATION, EMSAVING, MISCELLANEOUS
            FROM EXPENSEPROFILE
            WHERE USER_ID = ?
            ORDER BY CREATED_AT DESC
            LIMIT 1
        """, (user_id,))
        expense_row = cur.fetchone()

        if not expense_row:
            conn.close()
            return jsonify({"success": False, "error": "Expense profile not found for this user."})

        expense_data = {
            "groceries":     float(expense_row["GROCERIES"] or 0),
            "travel":        float(expense_row["TRAVEL"] or 0),
            "medfit":        float(expense_row["MEDFIT"] or 0),
            "lep":           float(expense_row["LEP"] or 0),
            "monthly_rent":  float(expense_row["MONTHLY_RENT"] or 0),
            "m_bills":       float(expense_row["M_BILLS"] or 0),
            "fashion":       float(expense_row["FASHION"] or 0),
            "entertainment": float(expense_row["ENTERTAINMENT"] or 0),
            "education":     float(expense_row["EDUCATION"] or 0),
            "emsaving":      float(expense_row["EMSAVING"] or 0),
            "miscellaneous": float(expense_row["MISCELLANEOUS"] or 0)
        }

        total_income  = income_data["monthly_income"] + income_data["additional_monthly_income"]
        total_expense = sum(expense_data.values())
        free_cash     = total_income - total_expense

        # FIX: parameterised query (was using f-string with user_id directly)
        cur.execute("""
            SELECT GOAL_NAME, GOAL_AMOUNT, MONTHLY_SAVING_T,
                   GOAL_STATUS, START_DATE, END_DATE
            FROM GOALS
            WHERE USER_ID = ?
            ORDER BY CREATED_AT DESC
        """, (user_id,))

        goal_rows         = cur.fetchall()
        goals_list        = []
        total_goal_amount = 0.0
        goal_summary      = {"ACTIVE": 0, "PAUSED": 0, "ACHIEVED": 0, "EXPIRED": 0, "INACTIVE": 0}

        for row in goal_rows:
            ga     = float(row["GOAL_AMOUNT"] or 0)
            total_goal_amount += ga
            status = row["GOAL_STATUS"]
            if status in goal_summary:
                goal_summary[status] += 1

            goals_list.append({
                "goal_name":       row["GOAL_NAME"],
                "goal_amount":     ga,
                "monthly_saving_t": float(row["MONTHLY_SAVING_T"] or 0),
                "goal_status":     status,
                "start_date":      row["START_DATE"],
                "end_date":        row["END_DATE"]
            })

        conn.close()

        return jsonify({
            "success":          True,
            "income_data":      income_data,
            "expense_data":     expense_data,
            "goals":            goals_list,
            "goal_summary":     goal_summary,
            "total_income":     round(total_income, 2),
            "total_expense":    round(total_expense, 2),
            "free_cash":        round(free_cash, 2),
            "total_goal_amount": round(total_goal_amount, 2)
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ─── Misc ──────────────────────────────────────────────────────────────────────
@app.route("/users", methods=["GET"])
def users():
    return jsonify({"success": True, "registered_users": registered_users}), 200


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5500)