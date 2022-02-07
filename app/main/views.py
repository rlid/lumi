import re

from bs4 import BeautifulSoup
from flask import render_template, redirect, flash, url_for, Markup
from flask_login import login_required, current_user

from app import db
from app.main import main
from app.main.forms import PostForm, MarkdownPostForm
from app.models.user import User, Post


@main.app_context_processor
def truncate_html_processor():
    def truncate_html(value, length=255):
        n = value.find(' ', length)
        if n == -1:
            partial_html = value
        else:
            partial_html = value[:n] + '...'
        soup = BeautifulSoup(partial_html, "html.parser")
        return soup.prettify()

    return dict(truncate_html=truncate_html)


@main.app_context_processor
def html_text_processor():
    def html_text(value):
        return BeautifulSoup(value, "html.parser").text

    return dict(html_text=html_text)


@main.route('/')
def index():
    return render_template("landing.html")


@main.route('/start')
def start():
    return render_template("landing.html", title="Guided Tour")


@main.route('/post', methods=['GET', 'POST'])
@login_required
def new_post():
    form = MarkdownPostForm() if current_user.use_markdown else PostForm()
    if form.validate_on_submit():
        body = form.body.data.replace('<br>', '')
        body = body.replace('\r\n', '\n')
        body = body.rstrip()
        body = re.sub(r'(?<!\\)#[A-Za-z0-9]+', lambda x: '\\' + x.group(0), body)
        body = ('m' if current_user.use_markdown else 's') + body
        tag_names = [name[2:] for name in re.findall(r'\\#[A-Za-z0-9]+', body)]
        # usernames = [name[1:] for name in re.findall(r'@[A-Za-z0-9]+', body)]
        current_user.post(is_request=(form.is_request.data == '1'), reward=100 * int(form.reward.data),
                          title=form.title.data, body=body, tag_names=tag_names)
        return redirect(url_for('main.browse'))
    if current_user.use_markdown:
        flash('Don\'t like Markdown? Switch to ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>simple editor</a>'), category='info')
    else:
        flash('Need more formatting options? Try the ' +
              Markup(f'<a href={url_for("main.toggle_editor")}>Markdown editor</a>'), category='info')
    return render_template("new_post.html", form=form, use_markdown=current_user.use_markdown)


@main.route('/toggle-editor', methods=['GET', 'POST'])
@login_required
def toggle_editor():
    current_user.use_markdown = not current_user.use_markdown
    db.session.add(current_user)
    db.session.commit()
    return redirect(url_for('main.new_post'))


@main.route('/browse')
def browse():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    return render_template("index.html", posts=posts)


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


@main.route('/post/<int:post_id>')
def view_post(post_id):
    p = Post.query.filter_by(id=post_id).first_or_404()
    return render_template("view_post.html", post=p)


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
