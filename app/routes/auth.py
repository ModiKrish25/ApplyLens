from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from ..extensions import db, login_manager
from ..models import User
from ..utils.validators import (validate_email, validate_password_pair,
                                failed_password_rules, password_strength,
                                STRENGTH_LABELS, PASSWORD_RULES)

auth_bp = Blueprint("auth", __name__)

# naive in-memory rate limiting — fine for a local, single-process app
FAILED_LOGINS = {}          # email -> list of timestamps
MAX_ATTEMPTS = 5
LOCKOUT_MINUTES = 10


def _too_many_attempts(email):
    now = datetime.now(timezone.utc).timestamp()
    hits = [t for t in FAILED_LOGINS.get(email, []) if now - t < LOCKOUT_MINUTES * 60]
    FAILED_LOGINS[email] = hits
    return len(hits) >= MAX_ATTEMPTS


def _record_failure(email):
    FAILED_LOGINS.setdefault(email, []).append(datetime.now(timezone.utc).timestamp())


def _clear_failures(email):
    FAILED_LOGINS.pop(email, None)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = {}
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        name = request.form.get("name", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        form = {"email": email, "name": name}

        ok, err = validate_email(email)
        if not ok:
            flash(err, "error")
        elif len(name) < 2:
            flash("Please enter your name (at least 2 characters).", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists. Try logging in.", "error")
        else:
            ok, err = validate_password_pair(password, confirm, email)
            if not ok:
                flash(err, "error")
            else:
                user = User(email=email, name=name or email.split("@")[0])
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                login_user(user)
                flash("Welcome! Your account is ready.", "success")
                return redirect(url_for("dashboard.index"))

    failed = failed_password_rules(request.form.get("password", ""))
    return render_template("auth.html", mode="signup", form=form, failed=failed,
                           strength=password_strength(request.form.get("password", "")),
                           strength_labels=STRENGTH_LABELS, pw_rules=PASSWORD_RULES)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    form = {}
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        form = {"email": email}

        ok, err = validate_email(email)
        if not ok:
            flash(err, "error")
        elif _too_many_attempts(email):
            flash(f"Too many failed attempts. Try again in {LOCKOUT_MINUTES} minutes.", "error")
        else:
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                _clear_failures(email)
                login_user(user)
                next_page = request.args.get("next")
                return redirect(next_page or url_for("dashboard.index"))
            _record_failure(email)
            left = MAX_ATTEMPTS - len(FAILED_LOGINS.get(email, []))
            flash("Invalid email or password." +
                  (f" {left} attempt{'s' if left != 1 else ''} left." if left <= 2 else ""),
                  "error")

    return render_template("auth.html", mode="login", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))
