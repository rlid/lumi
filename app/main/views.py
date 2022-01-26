from flask import render_template, redirect, flash
from flask_login import login_required, current_user

from app import db
from app.main import main


@main.route('/')
def index():
    return render_template("index.html")


@main.route('/start')
def start():
    return render_template("index.html", title="Guided Tour")


@main.route('/create')
@login_required
def create():
    return render_template("index.html", title="Make a Request")


@main.route('/browse')
def browse():
    return render_template("index.html", title="Browse")


@main.route('/support')
def support():
    return redirect("https://discord.gg/xtXCScr9")


@main.route('/privacy')
def privacy():
    return render_template("index.html", title="Privacy Policy")


@main.route('/terms')
def terms():
    return render_template("index.html", title="Terms Of Service")


@main.route('/about')
def about():
    return redirect("https://www.linkedin.com/company/knowbleapp")


@main.route('/alerts')
@login_required
def alerts():
    return render_template("index.html", title="Alerts")


@main.route('/conversations')
@login_required
def conversations():
    return render_template("index.html", title="Conversations")


@main.route('/saved')
@login_required
def saved():
    return render_template("index.html", title="Saved")


@main.route('/search')
def search():
    return render_template("index.html", title="Search")


@main.route('/account')
@login_required
def account():
    flash(f"current_user is {current_user}", category="info")
    return render_template("index.html", title="Account")


@main.route('/facebook')
def facebook():
    return redirect("https://fb.me/KnowbleApp")


@main.route('/twitter')
def twitter():
    return redirect("https://twitter.com/KnowbleApp")


@main.route('/linkedin')
def linkedin():
    return redirect("https://www.linkedin.com/company/knowbleapp")


@main.route('/discord')
def discord():
    return redirect("https://discord.gg/JUD7SMh5tA")


@main.route("/initdb")
def initdb():
    db.session.remove()
    db.drop_all()
    db.create_all()
    return {"success": True}, 200
