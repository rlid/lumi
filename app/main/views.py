from flask import render_template, redirect

from . import main


@main.route('/')
def index():
    return render_template("index.html")


@main.route('/login')
def login():
    return render_template("login.html")


@main.route('/how-it-works')
def guided_tour():
    return render_template("index.html", title="Guided Tour")


@main.route('/make-request')
def make_request():
    return render_template("index.html", title="Make a Request")


@main.route('/browse')
def browse():
    return render_template("index.html", title="Browse")


@main.route('/support')
def support():
    return redirect("https://discord.gg/xtXCScr9")


@main.route('/privacy-policy')
def privacy_policy():
    return render_template("index.html", title="Privacy Policy")


@main.route('/about-us')
def about_us():
    return redirect("https://www.linkedin.com/company/knowbleapp")


@main.route('/alerts')
def alerts():
    return render_template("index.html", title="Alerts")


@main.route('/conversations')
def conversations():
    return render_template("index.html", title="Conversations")


@main.route('/saved')
def saved():
    return render_template("index.html", title="Saved")


@main.route('/search')
def search():
    return render_template("index.html", title="Search")


@main.route('/account')
def account():
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
    return redirect("https://discord.gg/xtXCScr9")
