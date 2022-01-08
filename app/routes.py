from flask import render_template

from app import app


@app.route('/')
def hello():
    user = {'username': 'World'}
    return render_template("index.html", title="Home", user=user)
