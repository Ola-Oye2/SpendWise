import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY")

app.config["SQLALCHEMY_DATABASE_URI"] = (f"mysql+pymysql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
                                         f"@{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}")
db = SQLAlchemy(app)

#DATABASE MODELS
class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    middle_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    phone_number = db.Column(db.String(20))
    password = db.Column(db.String(255))
    main_income_source = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    expenes = db.relationship("Expense", backref="user")

class Expense(db.Model):
    expense_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    amount = db.Column(db.Float)
    category = db.Column(db.String(50))
    type = db.Column(db.String(50))
    description = db.Column(db.String(100))
    date = db.Column(db.DateTime)

class Income(db.Model):
    income_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    amount = db.Column(db.Float)
    source = db.Column(db.String(50))
    description = db.Column(db.String(100))
    date = db.Column(db.DateTime)

class Budget(db.Model):
    __table_args__ = (db.UniqueConstraint("user_id","month",name="unique_user_month_budget"),)

    budget_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.user_id"))
    month = db.Column(db.String(10))
    total_amount = db.Column(db.Float)
    needs_limit = db.Column(db.Float)
    wants_limit = db.Column(db.Float)


with app.app_context():
    db.create_all()

#ALLOWED LISTS
allowed_categories = ["Food","Transportation","Housing","Education","Health","Shopping","Entertainment","Utilities","Personal Care","Other"]
allowed_types = ["Need", "Want"]

#ROUTES
@app.route("/form", methods=["GET","POST"])
def form():
    if request.method == "POST":
        username = request.form["username"]
        amount = float(request.form["amount"])
        category = request.form["category"]
        description = request.form["description"]
        return render_template("result.html", username=username, amount=amount, category=category, description= description)
    return render_template("form.html")
    
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == 'POST':
        first_name = request.form["first_name"]
        middle_name = request.form["middle_name"]
        last_name = request.form["last_name"]
        email = request.form["email"]
        phone_number = request.form["phone_number"]
        password = request.form["password"]
        hashed_password = generate_password_hash(password)
        main_income_source = request.form["main_income_source"]

        new_user = User(
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            password=hashed_password,
            main_income_source=main_income_source
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/profile")
def profile():
    if "user_id" not in session:
        flash("Please log in to view your profile.", "warning")
        return redirect(url_for("login"))

    user = User.query.get_or_404(session["user_id"])

    return render_template("profile.html", user=user)

@app.route("/profile/edit", methods=["GET", "POST"])
def edit_profile():
    if "user_id" not in session:
        flash("Please log in to edit your profile.", "warning")
        return redirect(url_for("login"))

    user = User.query.get_or_404(session["user_id"])

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        middle_name = request.form.get("middle_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone_number = request.form.get("phone_number", "").strip()
        main_income_source = request.form.get("main_income_source", "").strip()

        if not first_name or not last_name or not email:
            flash("First name, last name, and email are required.", "danger")
            return render_template("edit_profile.html", user=user, form_data=request.form)

        # Check whether another account already uses this email.
        existing_user = User.query.filter(
            User.email == email,
            User.user_id != user.user_id
        ).first()

        if existing_user:
            flash("That email address is already associated with another account.", "danger")
            return render_template("edit_profile.html", user=user, form_data=request.form)

        user.first_name = first_name
        user.middle_name = middle_name or None
        user.last_name = last_name
        user.email = email
        user.phone_number = phone_number or None
        user.main_income_source = main_income_source or None

        try:
            db.session.commit()
            flash("Your profile has been updated successfully.", "success")
            return redirect(url_for("profile"))

        except IntegrityError:
            db.session.rollback()
            flash("We couldn't save your changes. Please check the email address and try again.","danger")
            return render_template("edit_profile.html", user=user, form_data=request.form)

    return render_template("edit_profile.html", user=user, form_data={})

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == 'POST':
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password,password):
            session["user_id"] = user.user_id
            return redirect(url_for("dashboard"))

        return "Invalid email or password"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.pop("user_id",None)
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    incomes = Income.query.filter_by(
        user_id = session["user_id"]
    ).all()

    expenses = Expense.query.filter_by(
        user_id = session["user_id"]
    ).all()

    total_income = sum(income.amount for income in incomes)
    total_expenses = sum(expense.amount for expense in expenses)

    balance = total_income - total_expenses

    return render_template("dashboard.html", total_income=total_income, total_expenses=total_expenses, balance=balance)


@app.route("/add-income", methods=["GET", "POST"])
def add_income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        # Return to the form without losing entered values.
        if request.form.get("action") == "back":
            return render_template(
                "add_income.html",
                amount=request.form.get("amount", ""),
                source=request.form.get("source", ""),
                description=request.form.get("description", ""),
                date=request.form.get("date", "")
            )

        amount_raw = request.form.get("amount", "").strip()
        source = request.form.get("source", "").strip()
        description = request.form.get("description", "")
        date = request.form.get("date", "").strip()

        # Remove thousands separators before converting to a number.
        amount_input = amount_raw.replace(",", "")

        try:
            amount = float(amount_input)
        except ValueError:
            flash("Please enter a valid amount", "error")
            return render_template(
                "add_income.html",
                amount=amount_raw,
                source=source,
                description=description,
                date=date
            )

        if amount <= 0:
            flash("Amount must be greater than 0", "error")
            return render_template(
                "add_income.html",
                amount=amount_raw,
                source=source,
                description=description,
                date=date
            )

        if not date:
            flash("Please enter a date", "error")
            return render_template(
                "add_income.html",
                amount=amount_raw,
                source=source,
                description=description,
                date=date
            )

        if not source:
            flash("Income source cannot be empty", "error")
            return render_template(
                "add_income.html",
                amount=amount_raw,
                source=source,
                description=description,
                date=date
            )

        return render_template("confirm_income.html", amount=amount, amount_input=amount_raw, source=source, description=description, date=date)

    return render_template("add_income.html")


@app.route("/confirm-income", methods=["POST"])
def confirm_income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    amount_raw = request.form.get("amount", "").strip()
    source = request.form.get("source", "").strip()
    description = request.form.get("description", "").strip()
    date = request.form.get("date", "").strip()

    # Remove commas before converting the amount.
    amount_input = amount_raw.replace(",", "")

    try:
        amount = float(amount_input)
    except ValueError:
        flash("Please enter a valid amount", "error")
        return render_template("add_income.html", amount=amount_raw, source=source, description=description, date=date)

    if amount <= 0:
        flash("Amount must be greater than 0", "error")
        return render_template("add_income.html", amount=amount_raw, source=source, description=description, date=date)

    if not source:
        flash("Income source cannot be empty", "error")
        return render_template("add_income.html", amount=amount_raw, source=source, description=description, date=date)

    if not date:
        flash("Please enter a date", "error")
        return render_template("add_income.html", amount=amount_raw, source=source, description=description, date=date)

    new_income = Income(
        user_id=session["user_id"],
        amount=amount,
        source=source,
        description=description,
        date=date
    )

    db.session.add(new_income)
    db.session.commit()

    flash("Income added successfully!", "success")

    return redirect(url_for("dashboard"))


@app.route("/view-income")
def view_income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    incomes = Income.query.filter_by(
        user_id = session["user_id"]
    ).all()

    return render_template("view_income.html", incomes=incomes)

@app.route("/edit-income/<int:income_id>", methods=["GET","POST"])
def edit_income(income_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    income = Income.query.filter_by(
        income_id = income_id,
        user_id = session["user_id"]
    ).first()

    if income is None:
        flash("Income not found","error")
        return redirect(url_for("view_income"))

    if request.method == "POST":
        amount_input = request.form.get("amount","").strip()
        source = request.form.get("source","").strip()
        description = request.form.get("description","").strip()
        date = request.form.get("date","").strip()

        try:
            amount = float(amount_input)
        except ValueError:
            flash("Please enter a valid amount","error")
            return render_template("edit_income.html",income=income)
        
        if amount <= 0:
            flash("Amount must be greater than 0","error")
            return render_template("edit_income.html",income=income)

        if not source:
            flash("Income source cannot be empty","error")
            return render_template("edit_income.html",income=income)

        if not date:
            flash("Please select a date","error")
            return render_template("edit_income.html",income=income)

        income.amount = amount
        income.source = source
        income.description = description
        income.date = date

        db.session.commit()

        flash("Income updated successfully!","success")
        return redirect(url_for("view_income"))

    return render_template("edit_income.html",income=income)

@app.route("/delete-income/<int:income_id>", methods=["POST"])
def delete_income(income_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    income = Income.query.filter_by(
        income_id = income_id,
        user_id = session["user_id"]
    ).first()

    if income is None:
        flash("Income not found","error")
        return redirect(url_for("view_income"))

    db.session.delete(income)
    db.session.commit()

    flash("Income deleted successfully!","success")
    return redirect(url_for("view_income"))



@app.route("/add-expense", methods=["GET", "POST"])
def add_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        amount_input = request.form.get("amount", "").strip()
        category = request.form.get("category", "")
        expense_type = request.form.get("type", "")
        description = request.form.get("description", "").strip()
        date = request.form.get("date", "").strip()

        # Preserve all entered values when the user goes back to edit.
        if request.form.get("action") == "back":
            return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)

        # Convert the formatted amount into a number safely.
        try:
            amount = float(amount_input.replace(",", ""))
        except (ValueError, AttributeError):
            flash("Please enter a valid amount.", "error")
            return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)

        if amount <= 0:
            flash("Amount must be greater than 0.", "error")
            return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)

        if category not in allowed_categories:
            flash("Please select a valid category.", "error")
            return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)

        if expense_type not in allowed_types:
            flash("Please select a valid expense type.", "error")
            return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)


        # Check that the date exists and is in YYYY-MM-DD format.
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except (ValueError, TypeError):
            flash("Please enter a valid date.", "error")
            return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)


        return render_template("confirm_expense.html", amount=amount, amount_input=amount_input, category=category, type=expense_type, description=description, date=date)

    return render_template("add_expense.html")



@app.route("/confirm-expense", methods=["POST"])
def confirm_expense():
    if "user_id" not in session:
        return redirect(url_for("login"))

    amount_input = request.form.get("amount", "").strip()
    category = request.form.get("category", "")
    expense_type = request.form.get("type", "")
    description = request.form.get("description", "").strip()
    date = request.form.get("date", "").strip()

    # Convert the amount safely.
    try:
        amount = float(amount_input.replace(",", ""))
    except (ValueError, AttributeError):
        flash("Please enter a valid amount.", "error")
        return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)

    if amount <= 0:
        flash("Amount must be greater than 0.", "error")
        return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)

    if category not in allowed_categories:
        flash("Please select a valid category.", "error")
        return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)

    if expense_type not in allowed_types:
        flash("Please select a valid expense type.", "error")
        return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)

    try:
        datetime.strptime(date, "%Y-%m-%d")
    except (ValueError, TypeError):
        flash("Please enter a valid date.", "error")
        return render_template("add_expense.html", amount_input=amount_input, category=category, type=expense_type, description=description, date=date)

    new_expense = Expense(
        user_id=session["user_id"],
        amount=amount,
        category=category,
        type=expense_type,
        description=description,
        date=date
    )

    db.session.add(new_expense)
    db.session.commit()

    flash("Expense added successfully!", "success")
    return redirect(url_for("dashboard"))


@app.route("/view-expenses")
def view_expenses():
    if "user_id" not in session:
        return redirect(url_for("login"))

    search = request.args.get("search","").strip()
    category = request.args.get("category","").strip()
    expense_type = request.args.get("type","").strip()
    start_date = request.args.get("start_date","").strip() 
    end_date = request.args.get("end_date","").strip() 
    
    query = Expense.query.filter_by(user_id = session["user_id"])

    if search:
        query = query.filter(Expense.description.ilike(f"%{search}%"))

    if category:
        query = query.filter(Expense.category == category)

    if expense_type:
        query = query.filter(Expense.type == expense_type)

    if start_date:
        query = query.filter(Expense.date >= start_date)

    if end_date:
        query = query.filter(Expense.date <= end_date)

    expenses = query.all()

    return render_template("view_expenses.html", expenses=expenses, search=search, category=category, expense_type=expense_type, start_date=start_date, end_date=end_date)

@app.route("/edit-expense/<int:expense_id>", methods=["GET","POST"])
def edit_expense(expense_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = Expense.query.filter_by(
        expense_id = expense_id,
        user_id = session["user_id"]
    ).first()

    if expense is None:
        flash("Expense not found","error")
        return redirect(url_for("view_expenses"))

    if request.method == "POST":
        amount_input = request.form.get("amount","").strip()
        category = request.form.get("category","").strip()
        expense_type = request.form.get("type","").strip()
        description = request.form.get("description","").strip()
        date = request.form.get("date","").strip()

        try:
            amount = float(amount_input)
        except ValueError:
            flash("Please enter a valid amount","error")
            return render_template("edit_expense.html",expense=expense)
        
        if amount <= 0:
            flash("Amount must be greater than 0","error")
            return render_template("edit_expense.html",expense=expense)

        if category not in allowed_categories:
            flash("Please select a valid category","error")
            return render_template("edit_expense.html",expense=expense)

        if expense_type not in allowed_types:
            flash("Please select a valid expense type","error")
            return render_template("edit_expense.html",expense=expense)

        if not date:
            flash("Please select a date","error")
            return render_template("edit_expense.html",expense=expense)

        expense.amount = amount
        expense.category = category
        expense.type = expense_type
        expense.description = description
        expense.date = date

        db.session.commit()

        flash("Expense updated successfully!","success")
        return redirect(url_for("view_expenses"))

    return render_template("edit_expense.html",expense=expense)


@app.route("/delete-expense/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    expense = Expense.query.filter_by(
        expense_id = expense_id,
        user_id = session["user_id"]
    ).first()

    if expense is None:
        flash("Expense not found","error")
        return redirect(url_for("view_expenses"))

    db.session.delete(expense)
    db.session.commit()

    flash("Expense deleted successfully!","success")
    return redirect(url_for("view_expenses"))


@app.route("/add-budget", methods=["GET","POST"])
def add_budget():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        month = request.form.get("month","").strip()
        total_amount_input = request.form.get("total_amount","").strip()
        needs_limit_input = request.form.get("needs_limit","").strip()
        wants_limit_input = request.form.get("wants_limit","").strip()

        if request.form.get("action") == "back":
            return render_template(
                "add_budget.html",
                month=month,
                total_amount=total_amount_input,
                needs_limit=needs_limit_input,
                wants_limit=wants_limit_input
            )

        if not month:
            flash("Please select a month.","error")
            return render_template("add_budget.html", month=month, total_amount=total_amount_input, needs_limit=needs_limit_input, wants_limit=wants_limit_input)

        try:
            total_amount = float(total_amount_input)
            needs_limit = float(needs_limit_input)
            wants_limit = float(wants_limit_input)
        except ValueError:
            flash("Please enter valid amounts","error")
            return render_template("add_budget.html", month=month, total_amount=total_amount_input, needs_limit=needs_limit_input, wants_limit=wants_limit_input)

        if total_amount <= 0:
            flash("Total budget must be greater than zero.","error")
            return render_template("add_budget.html", month=month, total_amount=total_amount_input, needs_limit=needs_limit_input, wants_limit=wants_limit_input)
        if needs_limit<0 or wants_limit<0:
            flash("Needs and Wants limits cannot be negative.","error")
            return render_template("add_budget.html", month=month, total_amount=total_amount_input, needs_limit=needs_limit_input, wants_limit=wants_limit_input)
        if needs_limit + wants_limit > total_amount:
            flash("Needs and Wants limits cannot be greater than the total budget.","error")
            return render_template("add_budget.html", month=month, total_amount=total_amount_input, needs_limit=needs_limit_input, wants_limit=wants_limit_input)

        existing_budget = Budget.query.filter_by(user_id=session["user_id"],month=month).first()

        if existing_budget:
            flash("You already have a budget for this month. You can edit the existing budget instead.","error")
            return render_template("add_budget.html")

        unallocated = total_amount - (needs_limit + wants_limit)
        
        return render_template("review_budget.html", month=month, total_amount=total_amount, needs_limit=needs_limit, wants_limit=wants_limit, unallocated=unallocated)
    return render_template("add_budget.html")

@app.route("/confirm-budget", methods=["POST"])
def confirm_budget():
    if "user_id" not in session:
        return redirect(url_for("login"))

    month = request.form.get("month","").strip()
    total_amount= float(request.form.get("total_amount",0))
    needs_limit= float(request.form.get("needs_limit",0))
    wants_limit= float(request.form.get("wants_limit",0))

    budget = Budget(
        user_id=session["user_id"],
        month=month,
        total_amount=total_amount,
        needs_limit=needs_limit,
        wants_limit=wants_limit
        )

    db.session.add(budget)
    db.session.commit()

    flash("Budget addedd successfully.","success")
    return redirect(url_for("dashboard"))


@app.route("/view-budgets")
def view_budgets():
    if "user_id" not in session:
        return redirect(url_for("login"))

    budgets = Budget.query.filter_by(user_id=session["user_id"]).order_by(Budget.month.desc()).all()

    return render_template("view_budgets.html", budgets=budgets)

@app.route("/view-budget/<int:budget_id>")
def view_budget(budget_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    budget = Budget.query.filter_by(
        budget_id=budget_id,
        user_id=session["user_id"]
    ).first()

    if budget is None:
        flash("Budget not found","error")
        return redirect(url_for("view_budgets"))

    first_day = datetime.strptime(budget.month, "%Y-%m").date()
    next_month = (first_day + timedelta(days=32)).replace(day=1)
    last_day = next_month - timedelta(days=1)
    
    monthly_expenses = Expense.query.filter(
        Expense.user_id == session["user_id"],
        Expense.date >= first_day,
        Expense.date <= last_day
    ).all()
    
    total_spent = sum(expense.amount for expense in monthly_expenses)
    remaining = budget.total_amount - total_spent
    percentage_used = min((total_spent/budget.total_amount)*100,100)

    needs_spent = sum(
        expense.amount
        for expense in monthly_expenses
        if expense.type == "Need"
    )

    wants_spent = sum(
        expense.amount
        for expense in monthly_expenses
        if expense.type == "Want"
    )

    budget_exceeded = total_spent > budget.total_amount
    budget_warning = (percentage_used >= 80 and not budget_exceeded)
    needs_exceeded = needs_spent > budget.needs_limit
    wants_exceeded = wants_spent > budget.wants_limit
    unallocated = budget.total_amount -(budget.needs_limit + budget.wants_limit)

    return render_template("view_budget.html", budget=budget, total_spent=total_spent, remaining=remaining, percentage_used=percentage_used, needs_spent=needs_spent, wants_spent=wants_spent, budget_exceeded=budget_exceeded, budget_warning=budget_warning, needs_exceeded=needs_exceeded, wants_exceeded=wants_exceeded, unallocated=unallocated)
    

@app.route("/edit-budget/<int:budget_id>", methods=["GET","POST"])
def edit_budget(budget_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    budget = Budget.query.filter_by(
        budget_id=budget_id, 
        user_id=session["user_id"]
    ).first()

    if budget is None:
        flash("Budget not found","error")
        return redirect(url_for("view_budgets"))

    if request.method == "POST":
        month = request.form.get("month","").strip()
        total_amount_input = request.form.get("total_amount","").strip()
        needs_limit_input = request.form.get("needs_limit","").strip()
        wants_limit_input = request.form.get("wants_limit","").strip()

        try:
            total_amount = float(total_amount_input)
            needs_limit = float(needs_limit_input)
            wants_limit = float(wants_limit_input)
        except ValueError:
            flash("Please enter valid amounts","error")
            return render_template("edit_budget.html", budget=budget)

        if not month:
            flash("Please select a month.","error")
            return render_template("edit_budget.html", budget=budget)

        if total_amount <= 0:
            flash("Total budget must be greater than zero.","error")
            return render_template("edit_budget.html", budget=budget)

        if needs_limit<0 or wants_limit<0:
            flash("Needs and Wants limits cannot be negative.","error")
            return render_template("edit_budget.html", budget=budget)

        if needs_limit + wants_limit > total_amount:
            flash("Needs and Wants limits cannot be greater than the total budget.","error")
            return render_template("edit_budget.html", budget=budget)

        budget.month = month
        budget.total_amount = total_amount
        budget.needs_limit = needs_limit
        budget.wants_limit = wants_limit

        db.session.commit()

        flash("Budget updated successfully","success")
        return redirect(url_for("view_budgets"))

    return render_template("edit_budget.html", budget=budget)

@app.route("/financial-summary")
def financial_summary():
    if "user_id" not in session:
        return redirect(url_for("login"))

    incomes = Income.query.filter_by(user_id = session["user_id"]).all()
    expenses = Expense.query.filter_by(user_id = session["user_id"]).all()

    #OVERALL TOTALS
    total_income = sum(income.amount for income in incomes)
    total_expenses = sum(expense.amount for expense in expenses)
    balance = total_income - total_expenses

    #SPENDING BY TYPE
    total_needs = sum(
        expense.amount
        for expense in expenses
        if expense.type == "Need"
    )

    total_wants = sum(
        expense.amount
        for expense in expenses
        if expense.type == "Want"
    )

    #MONTHLY SUMMARY
    monthly_summary = {}

    #ADD INCOME TO MONTHLY SUMMARY
    for income in incomes:
        month = income.date.strftime("%Y-%m")

        if month not in monthly_summary:
            monthly_summary[month] = {
                "income":0,
                "expenses":0
            }

        monthly_summary[month]["income"] += income.amount

    #ADD EXPENSES TO MONTHLY SUMMARY
    for expense in expenses:
        month = expense.date.strftime("%Y-%m")

        if month not in monthly_summary:
            monthly_summary[month] = {
                "income":0,
                "expenses":0
            }

        monthly_summary[month]["expenses"] += expense.amount
        
    #CALCULATE MONTHLY BALANCE
    for month in monthly_summary:
        monthly_summary[month]["balance"] = (monthly_summary[month]["income"] - monthly_summary[month]["expenses"])

    #SORT MONTHS FROM NEWEST TO OLDEST
    monthly_summary = dict(
        sorted(
            monthly_summary.items(),
            reverse=True
        )
    )

    return render_template("financial_summary.html", total_income=total_income, total_expenses=total_expenses, balance=balance, total_needs=total_needs, total_wants=total_wants, monthly_summary=monthly_summary)


@app.route("/spending-analysis")
def spending_analysis():
    if "user_id" not in session:
        return redirect(url_for("login"))

    expenses = Expense.query.filter_by(user_id = session["user_id"]).all()

    current_month = datetime.now().strftime("%Y-%m")

    current_budget = Budget.query.filter_by(
        user_id=session["user_id"],
        month=current_month
    ).first()

    current_month_spending = 0

    for expense in expenses:
        if expense.date.strftime("%Y-%m") == current_month:
            current_month_spending += expense.amount

    remaining_budget = 0

    if current_budget:
        remaining_budget = current_budget.total_amount - current_month_spending

    budget_percentage = 0

    if current_budget and current_budget.total_amount > 0:
        budget_percentage = (current_month_spending / current_budget.total_amount) * 100

    budget_warning = False

    if budget_percentage >= 65:
        budget_warning = True

    total_spending = sum(expense.amount for expense in expenses)

    expense_count = len(expenses)

    if expense_count > 0:
        average_expense = total_spending / expense_count
    else:
        average_expense = 0

    if expense_count > 0:
        largest_expense = max(expense.amount for expense in expenses)
    else:
        largest_expense = 0

    spending_by_category = {}

    for expense in expenses:
        category = expense.category

        if category not in spending_by_category:
            spending_by_category[category] = 0

        spending_by_category[category] += expense.amount

    spending_by_category = dict(
        sorted(
            spending_by_category.items(),
            key=lambda item: item[1],
            reverse=True
        )
    )

    if spending_by_category:
        top_category = max(spending_by_category, key=spending_by_category.get)
        top_category_amount = spending_by_category[top_category]
    else:
        top_category = "None"
        top_category_amount = 0

    total_needs = sum(
        expense.amount 
        for expense in expenses 
        if expense.type == "Need"
    )

    total_wants = sum(
        expense.amount 
        for expense in expenses 
        if expense.type == "Want"
    )

    if total_spending > 0:
        needs_percentage = (total_needs / total_spending) * 100
        wants_percentage = (total_wants / total_spending) * 100
    else:
        needs_percentage = 0
        wants_percentage = 0

    monthly_spending = {}

    for expense in expenses:
        month = expense.date.strftime("%Y-%m")

        if month not in monthly_spending:
            monthly_spending[month] = 0

        monthly_spending[month] += expense.amount

    return render_template("spending_analysis.html", total_spending=total_spending, expense_count=expense_count, average_expense=average_expense, largest_expense=largest_expense, spending_by_category=spending_by_category, total_needs=total_needs, total_wants=total_wants, needs_percentage=needs_percentage, wants_percentage=wants_percentage, monthly_spending=monthly_spending, top_category=top_category, top_category_amount=top_category_amount, current_budget=current_budget, current_month_spending=current_month_spending, remaining_budget=remaining_budget, budget_percentage=budget_percentage, budget_warning=budget_warning)

if __name__ == "__main__":
    app.run(debug=True)