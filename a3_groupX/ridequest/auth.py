"""Registration, login and logout routes."""

from urllib.parse import urljoin, urlparse

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from . import db
from .forms import EmptyForm, LoginForm, RegisterForm
from .models import User


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def is_safe_redirect(target):
    """Allow only local redirect targets."""
    if not target:
        return False
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return (
        redirect_url.scheme in {"http", "https"}
        and host_url.netloc == redirect_url.netloc
    )


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        existing_user = db.session.scalar(
            db.select(User).where(User.email == email)
        )
        if existing_user:
            form.email.errors.append(
                "An account already exists for this email address."
            )
        else:
            user = User(
                first_name=form.first_name.data.strip(),
                surname=form.surname.data.strip(),
                email=email,
                contact_number=form.contact_number.data.strip(),
                street_address=form.street_address.data.strip(),
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome to RideQuest. Your account is ready.", "success")
            return redirect(url_for("main.index"))

    return render_template(
        "register.html", form=form, title="Create account"
    )


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = db.session.scalar(db.select(User).where(User.email == email))
        if user is None or not user.check_password(form.password.data):
            flash("The email address or password is incorrect.", "danger")
        else:
            login_user(user, remember=form.remember.data)
            flash(f"Welcome back, {user.first_name}.", "success")
            next_page = request.args.get("next")
            if is_safe_redirect(next_page):
                return redirect(next_page)
            return redirect(url_for("main.index"))

    return render_template("login.html", form=form, title="Sign in")


@auth_bp.post("/logout")
def logout():
    form = EmptyForm()
    if not form.validate_on_submit():
        flash("The logout request could not be verified.", "danger")
        return redirect(url_for("main.index"))
    logout_user()
    flash("You have signed out.", "info")
    return redirect(url_for("main.index"))
