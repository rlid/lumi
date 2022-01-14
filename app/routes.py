from flask import render_template

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
    return render_template("index.html", title="Support")


@app.route('/privacy-policy')
def privacy_policy():
    return render_template("index.html", title="Privacy Policy")


@app.route('/about-us')
def about_us():
    return render_template("index.html", title="About Us")


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", title="Page Not Found"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html", title="Internal Server Error"), 500
