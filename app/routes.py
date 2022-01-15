from flask import render_template, redirect

from app import app


@app.route('/')
def index():
    return render_template("index.html")


@app.route('/login')
def login():
    return render_template("login.html")


@app.route('/how-it-works')
def guided_tour():
    return render_template("index.html", title="Guided Tour")


@app.route('/make-request')
def make_request():
    return render_template("index.html", title="Make a Request")


@app.route('/browse')
def browse():
    return render_template("index.html", title="Browse")


@app.route('/support')
def support():
    return redirect("https://discord.gg/xtXCScr9")


@app.route('/privacy-policy')
def privacy_policy():
    return render_template("index.html", title="Privacy Policy")


@app.route('/about-us')
def about_us():
    return redirect("https://www.linkedin.com/company/knowbleapp")


@app.route('/alerts')
def alerts():
    return render_template("index.html", title="Alerts")


@app.route('/conversations')
def conversations():
    return render_template("index.html", title="Conversations")


@app.route('/saved')
def saved():
    return render_template("index.html", title="Saved")


@app.route('/search')
def search():
    return render_template("index.html", title="Search")


@app.route('/account')
def account():
    return render_template("index.html", title="Account")


@app.route('/facebook')
def facebook():
    return redirect("https://fb.me/KnowbleApp")


@app.route('/twitter')
def twitter():
    return redirect("https://twitter.com/KnowbleApp")


@app.route('/linkedin')
def linkedin():
    return redirect("https://www.linkedin.com/company/knowbleapp")


@app.route('/discord')
def discord():
    return redirect("https://discord.gg/xtXCScr9")


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", title="Page Not Found"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html", title="Internal Server Error"), 500
