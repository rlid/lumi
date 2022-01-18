from flask import render_template

from .forms import LoginForm
from . import auth


@auth.route("/login")
def login():
    form = LoginForm()
    return render_template("auth/login.html", form=form)
