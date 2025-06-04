import mysql.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from datetime import datetime
import json
from flask import Flask, render_template, request, session, redirect, url_for, jsonify

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Replace with a strong secret key

# Connecting to MySQL database
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="ragul.cs22",
    database="atm_system",
)
cursor = db.cursor()

def hash_string(string):
    digest = hashes.Hash(hashes.SHA256(), backend=default_backend())
    digest.update(string.encode("utf-8"))
    hashed_string = digest.finalize()
    return hashed_string.hex()

def insert_transaction(account_number, transaction_type, amount):
    current_time = datetime.now()
    query = "INSERT INTO transactions (account_number, type, amount, time) VALUES (%s, %s, %s, %s)"
    values = (account_number, transaction_type, amount, current_time)
    cursor.execute(query, values)
    db.commit()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            name = data.get("name")
            account_number = data.get("account_number")
            pin = data.get("pin")
            email = data.get("email")  # optional
        else:
            name = request.form["name"]
            account_number = request.form["account_number"]
            pin = request.form["pin"]
            email = request.form.get("email")
            
        query = "SELECT * FROM users WHERE account_number = %s"
        cursor.execute(query, (account_number,))
        user = cursor.fetchone()
        if user is not None:
            error_message = "User with the same account number already registered!"
            if request.is_json:
                return jsonify(success=False, message=error_message), 400
            return render_template("register.html", error_message=error_message)
        
        hashed_pin = hash_string(pin)
        query = "INSERT INTO users (name, account_number, pin, balance, email) VALUES (%s, %s, %s, %s, %s)"
        values = (name, account_number, hashed_pin, 0, email)
        cursor.execute(query, values)
        db.commit()
        success_message = "Registration successful! Please log in."
        if request.is_json:
            return jsonify(success=True, message=success_message, redirect="/login")
        return render_template("register.html", success_message=success_message)
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        # Check if the request is JSON
        if request.is_json:
            data = request.get_json()
            account_number = data.get("account_number")
            pin = data.get("pin")
        else:
            account_number = request.form["account_number"]
            pin = request.form["pin"]
            
        hashed_pin = hash_string(pin)
        query = "SELECT * FROM users WHERE account_number = %s AND pin = %s"
        cursor.execute(query, (account_number, hashed_pin))
        user = cursor.fetchone()
        if user is None:
            error_message = "Invalid account number or PIN!"
            if request.is_json:
                return jsonify(success=False, message=error_message), 400
            return render_template("login.html", error_message=error_message)
        
        session["account_number"] = account_number
        
        if request.is_json:
            return jsonify(success=True, message="Login successful!", redirect="/dashboard")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    if "account_number" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

# Deposit Route: Supports JSON (AJAX) and Form Submission
@app.route("/deposit", methods=["GET", "POST"])
def deposit():
    if "account_number" not in session:
        if request.is_json:
            return jsonify(success=False, message="Not logged in"), 401
        return redirect(url_for("login"))
    if request.method == "POST":
        account_number = session["account_number"]
        # Check if the request is JSON (from AJAX) or a form submission
        if request.is_json:
            data = request.get_json()
            try:
                amount = float(data.get("amount"))
            except (ValueError, TypeError):
                return jsonify(success=False, message="Invalid amount!")
            pin = data.get("pin")
        else:
            try:
                amount = float(request.form["amount"])
            except ValueError:
                error_message = "Invalid amount!"
                return render_template("deposit.html", error_message=error_message)
            pin = request.form["pin"]
        hashed_pin = hash_string(pin)
        query = "SELECT pin, balance FROM users WHERE account_number = %s"
        cursor.execute(query, (account_number,))
        user = cursor.fetchone()
        if user is None:
            error_message = "Invalid account!"
            if request.is_json:
                return jsonify(success=False, message=error_message)
            return render_template("deposit.html", error_message=error_message)
        stored_pin, balance = user[0], user[1]
        if hashed_pin != stored_pin:
            error_message = "Invalid PIN!"
            if request.is_json:
                return jsonify(success=False, message=error_message)
            return render_template("deposit.html", error_message=error_message)
        new_balance = balance + amount
        query = "UPDATE users SET balance = %s WHERE account_number = %s"
        cursor.execute(query, (new_balance, account_number))
        db.commit()
        insert_transaction(account_number, "Deposit", amount)
        success_message = f"Rs. {amount} deposited successfully!"
        if request.is_json:
            return jsonify(success=True, message=success_message)
        return render_template("deposit.html", success_message=success_message)
    return render_template("deposit.html")

# Withdrawal Route
@app.route("/withdrawal", methods=["GET", "POST"])
def withdrawal():
    if "account_number" not in session:
        if request.is_json:
            return jsonify(success=False, message="Not logged in"), 401
        return redirect(url_for("login"))
    if request.method == "POST":
        account_number = session["account_number"]
        if request.is_json:
            data = request.get_json()
            try:
                amount = float(data.get("amount"))
            except (ValueError, TypeError):
                return jsonify(success=False, message="Invalid amount!")
            pin = data.get("pin")
        else:
            try:
                amount = float(request.form["amount"])
            except ValueError:
                error_message = "Invalid amount!"
                return render_template("withdrawal.html", error_message=error_message)
            pin = request.form["pin"]
        hashed_pin = hash_string(pin)
        query = "SELECT pin, balance FROM users WHERE account_number = %s"
        cursor.execute(query, (account_number,))
        user = cursor.fetchone()
        if user is None:
            error_message = "Invalid account!"
            if request.is_json:
                return jsonify(success=False, message=error_message)
            return render_template("withdrawal.html", error_message=error_message)
        stored_pin, balance = user[0], user[1]
        if hashed_pin != stored_pin:
            error_message = "Invalid PIN!"
            if request.is_json:
                return jsonify(success=False, message=error_message)
            return render_template("withdrawal.html", error_message=error_message)
        if amount > balance:
            error_message = "Insufficient balance!"
            if request.is_json:
                return jsonify(success=False, message=error_message)
            return render_template("withdrawal.html", error_message=error_message)
        new_balance = balance - amount
        query = "UPDATE users SET balance = %s WHERE account_number = %s"
        cursor.execute(query, (new_balance, account_number))
        db.commit()
        insert_transaction(account_number, "Withdrawal", amount)
        success_message = f"Rs. {amount} withdrawn successfully!"
        if request.is_json:
            return jsonify(success=True, message=success_message)
        return render_template("withdrawal.html", success_message=success_message)
    return render_template("withdrawal.html")

# Balance Inquiry Route
@app.route("/balance", methods=["GET", "POST"])
def balance():
    if "account_number" not in session:
        if request.is_json:
            return jsonify(success=False, message="Not logged in"), 401
        return redirect(url_for("login"))
    if request.method == "POST":
        account_number = session["account_number"]
        if request.is_json:
            data = request.get_json()
            pin = data.get("pin")
        else:
            pin = request.form["pin"]
        hashed_pin = hash_string(pin)
        query = "SELECT pin, balance FROM users WHERE account_number = %s"
        cursor.execute(query, (account_number,))
        user = cursor.fetchone()
        if user is None:
            error_message = "Invalid account!"
            if request.is_json:
                return jsonify(success=False, message=error_message)
            return render_template("balance.html", error_message=error_message)
        stored_pin, balance_value = user[0], user[1]
        if hashed_pin != stored_pin:
            error_message = "Invalid PIN!"
            if request.is_json:
                return jsonify(success=False, message=error_message)
            return render_template("balance.html", error_message=error_message)
        balance_message = f"Your balance is Rs. {balance_value}"
        if request.is_json:
            return jsonify(success=True, message=balance_message)
        return render_template("balance.html", balance_message=balance_message)
    return render_template("balance.html")

@app.route("/pin_change", methods=["GET", "POST"])
def pin_change():
    if "account_number" not in session:
        if request.is_json:
            return jsonify(success=False, message="Not logged in"), 401
        return redirect(url_for("login"))
    if request.method == "POST":
        account_number = session["account_number"]
        # Check if request is JSON; otherwise, use form data
        if request.is_json:
            data = request.get_json()
            old_pin = data.get("old_pin")
            new_pin = data.get("new_pin")
        else:
            old_pin = request.form["old_pin"]
            new_pin = request.form["new_pin"]

        hashed_old_pin = hash_string(old_pin)
        hashed_new_pin = hash_string(new_pin)

        query = "SELECT * FROM users WHERE account_number = %s AND pin = %s"
        cursor.execute(query, (account_number, hashed_old_pin))
        user = cursor.fetchone()
        if user is None:
            error_message = "Invalid account or old PIN!"
            if request.is_json:
                return jsonify(success=False, message=error_message), 400
            return render_template("pin_change.html", pin_message=error_message)

        query = "UPDATE users SET pin = %s WHERE account_number = %s"
        cursor.execute(query, (hashed_new_pin, account_number))
        db.commit()

        success_message = "PIN changed successfully!"
        if request.is_json:
            return jsonify(success=True, message=success_message)
        return render_template("pin_change.html", pin_message=success_message)
    return render_template("pin_change.html")


@app.route("/transaction_history", methods=["GET"])
def transaction_history():
    if "account_number" not in session:
        return redirect(url_for("login"))
    account_number = session["account_number"]
    query = "SELECT time, type, amount FROM transactions WHERE account_number = %s ORDER BY time DESC"
    cursor.execute(query, (account_number,))
    transactions = cursor.fetchall()
    transaction_list = []
    for transaction in transactions:
        transaction_list.append({
            "time": transaction[0].strftime("%Y-%m-%d %H:%M:%S"),
            "type": transaction[1],
            "amount": float(transaction[2])
        })
    return render_template("transaction_history.html", transaction_history=transaction_list)

@app.route("/logout")
def logout():
    session.pop("account_number", None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)