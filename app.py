from enum import member

from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps
from sqlalchemy import func

app = Flask(__name__)
app.secret_key = "piggy_vault_2026_xK9#mL2$nQ8@pR5HAiN2p"

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "group_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def member_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "member_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def log_action(about, info, read=False):
    # get group_id from either admin or member session
    group_id = session.get("group_id") or session.get("group_id_m")
    new_info = Info(
        about=about,
        info=info,
        date=datetime.now(),
        read=read,
        group_id=group_id
    )
    db.session.add(new_info)
    db.session.commit()

@app.after_request
def add_no_cache(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:@localhost/piggy_vault_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# ─── Models ───────────────────────────────────────────────────────────────────

class Position(db.Model):
    __tablename__ = 'positions'

    position_id = db.Column(db.Integer, primary_key=True)
    position_name = db.Column(db.String(30), nullable=False)

    users = db.relationship('User', backref='position', lazy=True)


class Group(db.Model):
    __tablename__ = 'groups'

    group_id = db.Column(db.Integer, primary_key=True)
    group_name = db.Column(db.String(100), nullable=False)
    country = db.Column(db.String(100))
    email = db.Column(db.String(100))
    username = db.Column(db.String(100))
    password = db.Column(db.String(255))   # fixed: was 100, too short for hash
    created_at = db.Column(db.Date)

    members = db.relationship('Member', backref='group', lazy=True)
    users = db.relationship('User', backref='group', lazy=True)
    attendances = db.relationship('Attendance', backref='group', lazy=True)
    loans = db.relationship('Loan', backref='group', lazy=True)
    info_items = db.relationship('Info', backref='group', lazy=True)


class Member(db.Model):
    __tablename__ = 'members'

    member_id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(30))
    last_name = db.Column(db.String(30))
    gender = db.Column(db.String(10))
    dob = db.Column(db.Date)
    email = db.Column(db.String(50))
    phone = db.Column(db.String(30), unique=True)
    password = db.Column(db.String(255))   # fixed: was 30, too short for hash

    group_id = db.Column(db.Integer, db.ForeignKey('groups.group_id'))

    attendances = db.relationship('Attendance', backref='member', lazy=True, cascade='all, delete-orphan')
    loans = db.relationship('Loan', backref='member', lazy=True, cascade='all, delete-orphan')
    users = db.relationship('User', backref='member', lazy=True, cascade='all, delete-orphan')


class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.member_id'))
    position_id = db.Column(db.Integer, db.ForeignKey('positions.position_id'))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.group_id'))

    username = db.Column(db.String(30), nullable=False)
    password = db.Column(db.String(255), nullable=False)   # fixed: was 30


class Attendance(db.Model):
    __tablename__ = 'attendance'

    attendance_id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.member_id'))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.group_id'))

    status = db.Column(db.String(30))
    saving = db.Column(db.Float(9, 2))
    support = db.Column(db.Float(9, 2))
    date = db.Column(db.Date)

class Loan(db.Model):
    __tablename__ = 'loans'

    loan_id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.member_id'))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.group_id'))

    amount = db.Column(db.Float(9, 2))           # original loan amount
    remaining_amount = db.Column(db.Float(9, 2)) # decreases with each payment
    date_issued = db.Column(db.Date)

class Info(db.Model):
    __tablename__ = 'info'

    info_id = db.Column(db.Integer, primary_key=True)
    about = db.Column(db.String(100))      # what was affected e.g. 'member', 'loan', 'attendance'
    info = db.Column(db.String(255))       # description e.g. 'hirwa armstrong was added'
    date = db.Column(db.DateTime)
    read = db.Column(db.Boolean, default=False)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.group_id'))

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/save_position", methods=["POST"])
@login_required
def save_position():
    new_position = Position(
        position_name=request.form.get("position_name")
    )
    db.session.add(new_position)
    db.session.commit()
    log_action("position", f"{new_position.position_name} position was added")
    return redirect(url_for("positions"))


@app.route("/pay_loan/<int:loan_id>")
@login_required
def pay_loan(loan_id):
    loan = Loan.query.get(loan_id)
    member = Member.query.get(loan.member_id)
    return render_template("pay_loan.html", loan=loan, member=member)


@app.route("/pay_loan_form/<int:loan_id>", methods=["POST"])
@login_required
def pay_loan_form(loan_id):
    payment = float(request.form.get("payment"))
    loan = Loan.query.get(loan_id)

    if loan:
        loan.remaining_amount = float(loan.remaining_amount) - payment  # ← fix here

        if loan.remaining_amount <= 0:
            loan.remaining_amount = 0

        db.session.commit()
    log_action("loan", f"payment of {payment} was made on loan id {loan_id}")
    return redirect(url_for("loan"))


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        group = Group.query.filter_by(username=username).first()

        if group and check_password_hash(group.password, password):
            session["group_id"] = group.group_id
            session["group_name"] = group.group_name
            session["country"] = group.country
            return redirect(url_for("dashboard"))
        else:
            error = "invalid username or password"

    return render_template("login.html", error=error, groups_list=Group.query.all())

@app.route("/login_member", methods=["POST"])
def login_member():
    error = None
    phone = request.form.get("number")
    password = request.form.get("password")

    member = Member.query.filter_by(phone=phone).first()

    if member and check_password_hash(member.password, password):
        session.clear()  # clear any existing session data
        session["member_id"] = member.member_id
        session["member_name"] = f"{member.first_name} {member.last_name}"
        session["group_id_m"] = member.group_id
        return redirect(url_for("dashboard_member"))
    else:
        error = "invalid number or password"

    return render_template("login.html", error=error, groups_list=Group.query.all())

@app.route("/sign_up")
def sign_up():
    return render_template("sign_up.html")

@app.route("/dashboard")
@login_required
def dashboard():
    info_count = Info.query.filter_by(group_id=session.get("group_id")).filter(Info.read == False).count()
    member_count = Member.query.filter(Member.group_id == session.get("group_id")).count()
    loan_total = db.session.query(func.sum(Loan.amount))\
        .filter(Loan.group_id == session.get("group_id"))\
        .scalar() or 0
    saving_total = db.session.query(func.sum(Attendance.saving))\
        .filter(Attendance.group_id == session.get("group_id"))\
        .scalar() or 0
    loan_list = db.session.query(Loan, Member)\
        .outerjoin(Member, Loan.member_id == Member.member_id)\
        .filter(Loan.group_id == session["group_id"])\
        .order_by(Loan.date_issued.desc())\
        .limit(3)\
        .all()
    return render_template("dashboard.html", info_count=info_count, member_count=member_count, loan_total=loan_total, saving_total=saving_total, loan_list=loan_list)

@app.route("/dashboard_member")
@member_login_required
def dashboard_member():
    group = Group.query.get(session.get("group_id_m"))
    info_count = Info.query.filter_by(group_id=session.get("group_id_m")).filter(Info.read == False).count()
    member_count = Member.query.filter(Member.group_id == session.get("group_id_m")).count()
    loan_total = db.session.query(func.sum(Loan.amount))\
        .filter(Loan.member_id == session.get("member_id"))\
        .scalar() or 0
    saving_total = db.session.query(func.sum(Attendance.saving))\
        .filter(Attendance.member_id == session.get("member_id"))\
        .scalar() or 0
    loan_list = db.session.query(Loan, Member)\
        .outerjoin(Member, Loan.member_id == Member.member_id)\
        .filter(Loan.member_id == session["member_id"])\
        .order_by(Loan.date_issued.desc())\
        .limit(3)\
        .all()
    today = datetime.now().date()
    return render_template("dashboard_member.html", info_count=info_count, member_count=member_count, loan_total=loan_total, saving_total=saving_total, loan_list=loan_list, today=today, group=group)

@app.route("/members")
@login_required
def members():
    info_count = Info.query.filter_by(group_id=session.get("group_id")).filter(Info.read == False).count()
    members_list = Member.query.filter(Member.group_id == session.get("group_id")).all()
    return render_template("members.html", info_count=info_count, members_list=members_list)

@app.route("/attendance")
@login_required
def attendance():
    info_count = Info.query.filter_by(group_id=session.get("group_id")).filter(Info.read == False).count()
    members_list = Member.query.filter(Member.group_id == session.get("group_id")).all()
    attendance_list = Attendance.query.filter(Attendance.group_id == session.get("group_id")).all()
    return render_template("attendance.html", info_count=info_count, attendance_list=attendance_list, members_list=members_list)

@app.route("/all_attendance")
@login_required
def all_attendance():
    info_count = Info.query.filter_by(group_id=session.get("group_id")).filter(Info.read == False).count()
    attendance_list = db.session.query(Attendance, Member)\
    .outerjoin(Member, Attendance.member_id == Member.member_id)\
    .filter(Attendance.group_id == session["group_id"])\
    .order_by(Attendance.date.desc())\
    .all()
    members_list = Member.query.filter(Member.group_id == session.get("group_id")).all()
    return render_template("all_attendance_list.html", info_count=info_count, attendance_list=attendance_list, members_list=members_list)

@app.route("/all_attendance_member")
@member_login_required
def all_attendance_member():
    group = Group.query.get(session.get("group_id_m"))
    info_count = Info.query.filter_by(group_id=session.get("group_id")).filter(Info.read == False).count()
    attendance_list = db.session.query(Attendance, Member)\
    .outerjoin(Member, Attendance.member_id == Member.member_id)\
    .filter(Attendance.member_id == session.get("member_id"))\
    .order_by(Attendance.date.desc())\
    .all()
    members_list = Member.query.filter(Member.group_id == session.get("group_id")).all()
    return render_template("all_attendance_list_member.html", info_count=info_count, attendance_list=attendance_list, members_list=members_list, group=group)

@app.route("/loan")
@login_required
def loan():
    info_count = Info.query.filter_by(group_id=session.get("group_id")).filter(Info.read == False).count()
    loan_list = db.session.query(Loan, Member)\
    .outerjoin(Member, Loan.member_id == Member.member_id)\
    .filter(Loan.group_id == session["group_id"])\
    .all()
    today = datetime.now().date()
    return render_template("loan.html", info_count=info_count, loan_list=loan_list, today=today)

@app.route("/loan_member")
@member_login_required
def loan_member():
    group = Group.query.get(session.get("group_id_m"))
    info_count = Info.query.filter_by(group_id=session.get("group_id_m")).filter(Info.read == False).count()
    loan_list = db.session.query(Loan, Member)\
    .outerjoin(Member, Loan.member_id == Member.member_id)\
    .filter(Loan.member_id == session.get("member_id"))\
    .all()
    today = datetime.now().date()
    return render_template("loan_member.html", info_count=info_count, loan_list=loan_list, today=today, group=group)

@app.route("/managers")
@login_required
def managers():
    info_count = Info.query.filter_by(group_id=session.get("group_id")).filter(Info.read == False).count()
    return render_template("managers.html", info_count=info_count, managers_list=Group.query.filter(Group.group_id == session.get("group_id")).all())

@app.route("/managers_member")
@member_login_required
def managers_member():
    group = Group.query.get(session.get("group_id_m"))
    info_count = Info.query.filter_by(group_id=session.get("group_id")).filter(Info.read == False).count()
    members_list = Member.query.filter(Member.member_id == session.get("member_id")).all()
    return render_template("managers_member.html", info_count=info_count, members_list=members_list, group=group)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/info")
@login_required
def info():
    info_list = Info.query.filter(Info.group_id == session.get("group_id"))\
        .order_by(Info.date.desc()).all()
    info_count = Info.query.filter_by(group_id=session.get("group_id"))\
        .filter(Info.read == False).count()
    return render_template("info.html", info_list=info_list, info_count=info_count)


@app.route("/positions")
@login_required
def positions():
    info_count = Info.query.filter_by(group_id=session.get("group_id")).filter(Info.read == False).count()
    return render_template("positions.html", info_count=info_count, positions_list=Position.query.all())


@app.route("/add_loan")
@login_required
def add_loan():
    members_list = Member.query.filter(Member.group_id == session.get("group_id")).all()
    today = datetime.now().strftime("%Y-%m-%d")
    return render_template("add_loan.html", members_list=members_list, today=today)


@app.route("/add_member")
@login_required
def add_member():
    return render_template("add_member.html")


@app.route("/add_position")
@login_required
def add_position():
    return render_template("add_position.html")


@app.route("/edit_loan/<int:loan_id>")
@login_required
def edit_loan(loan_id):
    loan = Loan.query.get(loan_id)
    members_list = Member.query.filter_by(group_id=session["group_id"]).all()
    return render_template("edit_loan.html", loan=loan, members_list=members_list)


@app.route("/update_loan/<int:loan_id>", methods=["POST"])
@login_required
def update_loan(loan_id):
    loan = Loan.query.get(loan_id)
    loan.member_id = request.form.get("member_id")
    loan.amount = float(request.form.get("amount"))
    loan.remaining_amount = float(request.form.get("amount"))
    loan.date_issued = datetime.strptime(request.form.get("date_issued"), "%Y-%m-%d").date()
    db.session.commit()
    log_action("loan", f"loan of {loan.amount} was updated")
    return redirect(url_for("loan"))


@app.route("/add_user")
@login_required
def add_user():
    return render_template("add_user.html")

@app.route("/edit_member/<int:member_id>")
@login_required
def edit_member(member_id):
    member = Member.query.get(member_id)
    return render_template("edit_member.html", member=member)

@app.route("/edit_member_self/<int:member_id>")
@member_login_required
def edit_member_self(member_id):
    member = Member.query.get(member_id)
    return render_template("edit_member_self.html", member=member)

@app.route("/update_member_self/<int:member_id>", methods=["POST"])
@member_login_required
def update_member_self(member_id):
    member = Member.query.get(member_id)

    member.first_name = request.form.get("first_name")
    member.last_name = request.form.get("last_name")
    member.gender = request.form.get("gender")
    member.dob = datetime.strptime(request.form.get("dob"), "%Y-%m-%d").date()
    member.email = request.form.get("email")
    member.phone = request.form.get("phone")

    db.session.commit()
    log_action("member", f"{member.first_name} {member.last_name} was updated")
    return redirect(url_for("managers_member"))

@app.route("/update_member/<int:member_id>", methods=["POST"])
@login_required
def update_member(member_id):
    member = Member.query.get(member_id)

    member.first_name = request.form.get("first_name")
    member.last_name = request.form.get("last_name")
    member.gender = request.form.get("gender")
    member.dob = datetime.strptime(request.form.get("dob"), "%Y-%m-%d").date()
    member.email = request.form.get("email")
    member.phone = request.form.get("phone")

    db.session.commit()
    log_action("member", f"{member.first_name} {member.last_name} was updated")
    return redirect(url_for("members"))

@app.route("/edit_manager/<int:group_id>")
@login_required
def edit_manager(group_id):
    manager = Group.query.get(group_id)
    return render_template("edit_manager.html", manager=manager)

@app.route("/update_manager/<int:group_id>", methods=["POST"])
@login_required
def update_manager(group_id):
    group = Group.query.get(group_id)

    group.group_name = request.form.get("group_name")
    group.country = request.form.get("country")
    group.email = request.form.get("email")
    group.username = request.form.get("username")

    new_password = request.form.get("password")
    if new_password:  # only update if not empty
        group.password = generate_password_hash(new_password)

    db.session.commit()
    log_action("group", f"group '{group.group_name}' was updated")

    return redirect(url_for("managers"))

@app.route("/delete_member/<int:member_id>")
@login_required
def delete_member(member_id):
    member = Member.query.get(member_id)
    if member:
        db.session.delete(member)
        db.session.commit()
        log_action("member", f"{member.first_name} {member.last_name} was deleted")
    return redirect(url_for("members"))

@app.route("/mark_as_read/<int:info_id>")
@login_required
def mark_as_read(info_id):
    item = Info.query.get(info_id)
    if item:
        item.read = True
        db.session.commit()
    return redirect(url_for("info"))

# ─── Save Routes ──────────────────────────────────────────────────────────────

@app.route("/save_group", methods=["POST"])
def save_group():
    new_group = Group(
        group_name=request.form.get("group_name"),
        country=request.form.get("country"),
        email=request.form.get("email"),
        username=request.form.get("username"),
        password=generate_password_hash(request.form.get("password")),
        created_at=datetime.now().date()
    )
    db.session.add(new_group)
    db.session.commit()
    return redirect(url_for("home"))

@app.route("/save_attendance", methods=["POST"])
@login_required
def save_attendance():
    member_ids = request.form.getlist("member_id")
    statuses = request.form.getlist("status")
    savings = request.form.getlist("saving")
    supports = request.form.getlist("support")
    date_str = request.form.get("date")
    date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()

    for i in range(len(member_ids)):
        new_attendance = Attendance(
            member_id=member_ids[i],
            group_id=session.get("group_id"),
            status=statuses[i],
            saving=savings[i],
            support=supports[i],
            date=date
        )
        db.session.add(new_attendance)

    db.session.commit()
    log_action("attendance", f"attendance was recorded for {len(member_ids)} members on {date}")
    return redirect(url_for("attendance"))

@app.route("/save_member", methods=["POST"])
@login_required
def save_member():
    new_member = Member(
        first_name=request.form.get("first_name"),
        last_name=request.form.get("last_name"),
        gender=request.form.get("gender"),
        dob=datetime.strptime(request.form.get("dob"), "%Y-%m-%d").date(),  # fixed: parse string to date
        email=request.form.get("email"),
        phone=request.form.get("phone"),
        password=generate_password_hash(request.form.get("password")),
        group_id=session.get("group_id")
    )
    db.session.add(new_member)
    db.session.commit()
    log_action("member", f"{new_member.first_name} {new_member.last_name} was added")
    return redirect(url_for("members"))

@app.route("/save_loan", methods=["POST"])
@login_required
def save_loan():
    amount = float(request.form.get("amount"))
    new_loan = Loan(
        member_id=request.form.get("member_id"),
        group_id=session.get("group_id"),
        amount=amount,
        remaining_amount=amount,  # starts equal to amount
        date_issued=datetime.now().date(),
    )
    member_details = Member.query.get(new_loan.member_id)
    db.session.add(new_loan)
    db.session.commit()
    log_action("loan", f"loan of {amount} was issued to {member_details.first_name} {member_details.last_name}")
    return redirect(url_for("loan"))


# ─── Run ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        db.create_all()   # creates all tables if they don't exist
    app.run(debug=True)