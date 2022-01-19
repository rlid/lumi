from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required

from app import db
from app.auth import auth
from app.models import User
from app.auth.forms import LogInForm, SignUpForm


@auth.route("/login", methods=["GET", "POST"])
def login():
    form = LogInForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None:
            if user.password_hash and user.verify_password(form.password.data):
                login_user(user, form.remember_me.data)
                next_url = request.args.get("next")
                if next_url is None or not next_url.startwith("/"):
                    next_url = url_for("main.index")
                return redirect(next_url)
            elif not form.password.data:
                flash("Passwordless login", "info")
                return redirect(url_for("main.index"))
        flash("Invalid username or password", "danger")
    return render_template("auth/login.html", form=form)


@auth.route("/logout", methods=["GET", "POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.index"))


@auth.route("/signup", methods=["GET", "POST"])
def signup():
    form = SignUpForm()
    if form.validate_on_submit():
        if form.password.data:
            user = User(email=form.email.data, password=form.password.data)
        else:
            user = User(email=form.email.data)
        db.session.add(user)
        db.session.commit()
        flash("You can now log in.")
        return redirect(url_for("auth.login"))
    return render_template("auth/signup.html", form=form)
