from flask import render_template
from flask_login import login_required

from app.main import main


@main.route('/')
def index():
    return render_template("landing.html")

@main.route('/how-it-works')
def how_it_works():
    return render_template("landing.html", title="How It Works")


@main.route('/alerts')
@login_required
def alerts():
    return render_template("landing.html", title="Alerts")


@main.route('/engagements')
@login_required
def engagements():
    return render_template("landing.html", title="Active Engagements")


@main.route('/saved')
@login_required
def saved():
    return render_template("landing.html", title="Saved")


@main.route('/guidelines')
def guidelines():
    return render_template("landing.html", title="Community Guidelines")


@main.route('/about')
def about():
    return render_template('about.html')
