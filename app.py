import os
from datetime import datetime
from decimal import Decimal

from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

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


@app.before_request
def create_tables():
    db.create_all()


@app.route("/")
def home():
    accounts = Account.query.order_by(Account.id.desc()).all()
    transactions = Transaction.query.order_by(Transaction.id.desc()).limit(10).all()
    return render_template("index.html", accounts=accounts, transactions=transactions)


@app.route("/create-account", methods=["POST"])
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