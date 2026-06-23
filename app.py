import os
from datetime import datetime
from decimal import Decimal

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please login first to access banking services."
login_manager.login_message_category = "error"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default="customer")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.Integer, primary_key=True)
    account_holder = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    balance = db.Column(db.Numeric(12, 2), default=0.00)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("accounts.id"), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    account = db.relationship("Account", backref=db.backref("transactions", lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.before_request
def create_tables():
    db.create_all()


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if not full_name or not email or not password or not confirm_password:
            flash("All required fields must be filled.", "error")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Password and confirm password do not match.", "error")
            return redirect(url_for("register"))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered. Please login.", "error")
            return redirect(url_for("login"))

        hashed_password = generate_password_hash(password)

        new_user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            password_hash=hashed_password,
            role="customer"
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if not email or not password:
            flash("Email and password are required.", "error")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, password):
            flash("Invalid email or password.", "error")
            return redirect(url_for("login"))

        if not user.is_active:
            flash("Your account is blocked. Please contact bank support.", "error")
            return redirect(url_for("login"))

        login_user(user)
        flash("Login successful.", "success")

        next_page = request.args.get("next")
        if next_page and next_page.startswith("/"):
            return redirect(next_page)

        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logout successful.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    total_accounts = Account.query.count()
    total_transactions = Transaction.query.count()
    recent_transactions = Transaction.query.order_by(Transaction.id.desc()).limit(5).all()

    return render_template(
        "dashboard.html",
        total_accounts=total_accounts,
        total_transactions=total_transactions,
        recent_transactions=recent_transactions
    )


@app.route("/")
@login_required
def home():
    accounts = Account.query.order_by(Account.id.desc()).all()
    transactions = Transaction.query.order_by(Transaction.id.desc()).limit(10).all()
    return render_template("index.html", accounts=accounts, transactions=transactions)


@app.route("/create-account", methods=["POST"])
@login_required
def create_account():
    account_holder = request.form.get("account_holder")
    account_number = request.form.get("account_number")
    initial_balance = request.form.get("initial_balance", "0")

    if not account_holder or not account_number:
        flash("Account holder name and account number are required.", "error")
        return redirect(url_for("home"))

    existing_account = Account.query.filter_by(account_number=account_number).first()

    if existing_account:
        flash("Account number already exists.", "error")
        return redirect(url_for("home"))

    try:
        balance = Decimal(initial_balance)
    except Exception:
        flash("Invalid initial balance.", "error")
        return redirect(url_for("home"))

    if balance < 0:
        flash("Initial balance cannot be negative.", "error")
        return redirect(url_for("home"))

    new_account = Account(
        account_holder=account_holder,
        account_number=account_number,
        balance=balance
    )

    db.session.add(new_account)
    db.session.commit()

    flash("Bank account created successfully.", "success")
    return redirect(url_for("home"))


@app.route("/deposit", methods=["POST"])
@login_required
def deposit():
    account_number = request.form.get("account_number")
    amount = request.form.get("amount")

    account = Account.query.filter_by(account_number=account_number).first()

    if not account:
        flash("Account not found.", "error")
        return redirect(url_for("home"))

    try:
        deposit_amount = Decimal(amount)
    except Exception:
        flash("Invalid deposit amount.", "error")
        return redirect(url_for("home"))

    if deposit_amount <= 0:
        flash("Deposit amount must be greater than zero.", "error")
        return redirect(url_for("home"))

    account.balance += deposit_amount

    transaction = Transaction(
        account_id=account.id,
        transaction_type="Deposit",
        amount=deposit_amount
    )

    db.session.add(transaction)
    db.session.commit()

    flash("Amount deposited successfully.", "success")
    return redirect(url_for("home"))


@app.route("/withdraw", methods=["POST"])
@login_required
def withdraw():
    account_number = request.form.get("account_number")
    amount = request.form.get("amount")

    account = Account.query.filter_by(account_number=account_number).first()

    if not account:
        flash("Account not found.", "error")
        return redirect(url_for("home"))

    try:
        withdraw_amount = Decimal(amount)
    except Exception:
        flash("Invalid withdraw amount.", "error")
        return redirect(url_for("home"))

    if withdraw_amount <= 0:
        flash("Withdraw amount must be greater than zero.", "error")
        return redirect(url_for("home"))

    if account.balance < withdraw_amount:
        flash("Insufficient balance.", "error")
        return redirect(url_for("home"))

    account.balance -= withdraw_amount

    transaction = Transaction(
        account_id=account.id,
        transaction_type="Withdraw",
        amount=withdraw_amount
    )

    db.session.add(transaction)
    db.session.commit()

    flash("Amount withdrawn successfully.", "success")
    return redirect(url_for("home"))


@app.route("/health")
def health():
    return "Banking app is running successfully.", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)