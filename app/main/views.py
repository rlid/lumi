from flask import render_template, redirect, flash, url_for
from flask_login import login_required, current_user

from app import db
from app.main import main
from app.main.forms import PostForm
from app.models.user import User, Quest


@main.route('/')
def index():
    return render_template("landing.html")


@main.route('/start')
def start():
    return render_template("landing.html", title="Guided Tour")


@main.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    form = PostForm()
    if form.validate_on_submit():
        current_user.create_quest(value=100, title=form.title.data, body=form.text.data)
        return redirect(url_for('main.browse'))
    return render_template("post.html", form=form)


@main.route('/browse')
def browse():
    quests = Quest.query.order_by(Quest.timestamp.desc()).all()
    return render_template("index.html", quests=quests)


@main.route('/support')
def support():
    return redirect("https://discord.gg/xtXCScr9")


@main.route('/privacy')
def privacy():
    return render_template("landing.html", title="Privacy Policy")


@main.route('/terms')
def terms():
    return render_template("landing.html", title="Terms Of Service")


@main.route('/about')
def about():
    return redirect("https://www.linkedin.com/company/knowbleapp")


@main.route('/user/<int:user_id>')
def user(user_id):
    u = User.query.filter_by(id=user_id).first_or_404()
    return render_template("user.html", user=u)


@main.route('/quest/<int:quest_id>')
def quest(quest_id):
    q = Quest.query.filter_by(id=quest_id).first_or_404()
    return render_template("quest.html", quest=q)


@main.route('/alerts')
@login_required
def alerts():
    return render_template("landing.html", title="Alerts")


@main.route('/conversations')
@login_required
def conversations():
    return render_template("landing.html", title="Conversations")


@main.route('/saved')
@login_required
def saved():
    return render_template("landing.html", title="Saved")


@main.route('/search')
def search():
    return render_template("landing.html", title="Search")


@main.route('/account')
@login_required
def account():
    flash(f"current_user is {current_user}", category="info")
    return render_template("landing.html", title="Account")


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
