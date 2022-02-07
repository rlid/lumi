import re

from bs4 import BeautifulSoup
from flask import render_template, redirect, flash, url_for, Markup, request
from flask_login import login_required, current_user
from sqlalchemy import func, desc, distinct

from app import db
from app.main import main
from app.main.forms import PostForm, MarkdownPostForm
from app.models.user import User, Post, PostTag, Tag


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
        title = form.title.data.strip()
        body = form.body.data.replace('<br>', '')
        body = body.replace('\r\n', '\n')
        body = body.strip()
        body = re.sub(r'(?<!\\)#\w+', lambda x: '\\' + x.group(0), body)
        tag_names = [name[2:] for name in re.findall(r'\\#\w+', body)]
        # usernames = [name[1:] for name in re.findall(r'@\w+', body)]
        current_user.post(is_request=(form.is_request.data == '1'), reward=100 * int(form.reward.data),
                          title=title, body=body, tag_names=tag_names)
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


def unique_lower(str_seq):
    seen = set()
    return [x.lower() for x in str_seq if not (x.lower() in seen or seen.add(x.lower()))]


@main.route('/browse')
def browse():
    print(request.args.get("tags", ""))
    tag_ids = unique_lower(re.findall(r'\w+', request.args.get("tags", "")))

    if tag_ids:
        post_query = Post.query.join(
            PostTag, PostTag.post_id == Post.id
        ).filter(
            PostTag.tag_id.in_(tag_ids)
        ).group_by(
            Post
        ).having(
            func.count(distinct(PostTag.tag_id)) == len(tag_ids)
        )
    else:
        post_query = Post.query

    post_query_sq = post_query.subquery()
    tag_freq_query = db.session.query(
        Tag,
        func.count(PostTag.post_id).label('freq')
    ).join(
        PostTag,
        PostTag.tag_id == Tag.id
    ).join(
        post_query_sq,
        post_query_sq.c.id == PostTag.post_id
    ).group_by(
        Tag
    ).order_by(
        desc('freq')
    )

    posts = post_query.order_by(Post.timestamp.desc()).all()
    tag_freqs = tag_freq_query.all()
    return render_template("index.html", posts=posts, tag_freqs=tag_freqs)


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
