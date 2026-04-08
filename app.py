from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random, smtplib, os
from email.mime.text import MIMEText
import africastalking

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "shuleaudits2024secure")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///shuleaudits.db"
db = SQLAlchemy(app)

# ─── Africa's Talking Setup ───────────────────────────────────────
AT_USERNAME = os.environ.get("AT_USERNAME", "sandbox")
AT_API_KEY  = os.environ.get("AT_API_KEY", "sandbox")
africastalking.initialize(AT_USERNAME, AT_API_KEY)
sms = africastalking.SMS

# ─── Email Setup ──────────────────────────────────────────────────
EMAIL_ADDRESS  = os.environ.get("EMAIL_ADDRESS", "raymondpolycarp383@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "inpwjrhlprurmnbh")

# ─── Database Model ───────────────────────────────────────────────
class School(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    email    = db.Column(db.String(100), unique=True, nullable=False)
    phone    = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    otp      = db.Column(db.String(6))
    verified = db.Column(db.Boolean, default=False)

with app.app_context():
    db.create_all()

# ─── Generate OTP ─────────────────────────────────────────────────
def generate_otp():
    return str(random.randint(100000, 999999))

# ─── Send Email OTP ───────────────────────────────────────────────
def send_email_otp(to_email, otp):
    try:
        msg = MIMEText(f"Your ShuleAudits OTP verification code is: {otp}\n\nDo not share this code with anyone.")
        msg["Subject"] = "ShuleAudits - OTP Verification Code"
        msg["From"]    = EMAIL_ADDRESS
        msg["To"]      = to_email
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Email error: {e}")

# ─── Send SMS OTP ─────────────────────────────────────────────────
def send_sms_otp(phone, otp):
    try:
        sms.send(
            message=f"Your ShuleAudits OTP is: {otp}. Do not share this code.",
            recipients=[phone]
        )
        print(f"✅ SMS sent to {phone}")
    except Exception as e:
        print(f"❌ SMS error: {e}")

# ─── HOME ──────────────────────────────────────────────────────────
@app.route("/")
def home():
    return redirect(url_for("login"))

# ─── REGISTER ─────────────────────────────────────────────────────
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name     = request.form["name"]
        email    = request.form["email"]
        phone    = request.form["phone"]
        password = request.form["password"]
        confirm  = request.form["confirm"]

        if password != confirm:
            return render_template("register.html", error="Passwords do not match.")

        existing = School.query.filter_by(email=email).first()
        if existing:
            return render_template("register.html", error="Email already registered.")

        hashed = generate_password_hash(password)
        otp    = generate_otp()

        school = School(name=name, email=email, phone=phone,
                        password=hashed, otp=otp)
        db.session.add(school)
        db.session.commit()

        send_email_otp(email, otp)
        send_sms_otp(phone, otp)

        session["pending_email"] = email
        session["debug_otp"]     = otp  # remove this after testing
        return redirect(url_for("verify"))

    return render_template("register.html")

# ─── VERIFY ───────────────────────────────────────────────────────
@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        entered_otp = request.form["otp"]
        email       = session.get("pending_email")
        school      = School.query.filter_by(email=email).first()

        if school and school.otp == entered_otp:
            school.verified = True
            db.session.commit()
            session.pop("debug_otp", None)
            session["school_id"] = school.id
            return redirect(url_for("dashboard"))
        else:
            return render_template("verify.html", error="Invalid OTP. Please try again.")

    return render_template("verify.html")

# ─── LOGIN ────────────────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"]
        password = request.form["password"]
        school   = School.query.filter_by(email=email).first()

        if school and check_password_hash(school.password, password):
            if not school.verified:
                return render_template("login.html", error="Please verify your account first.")
            session["school_id"] = school.id
            return redirect(url_for("dashboard"))

        return render_template("login.html", error="Invalid email or password.")

    return render_template("login.html")

# ─── DASHBOARD ────────────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if "school_id" not in session:
        return redirect(url_for("login"))
    school = School.query.get(session["school_id"])
    return render_template("dashboard.html", school=school)

# ─── LOGOUT ───────────────────────────────────────────────────────
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)