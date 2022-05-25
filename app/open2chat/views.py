from flask import render_template, session
from flask_login import current_user

from app.models import User
from app.open2chat.forms import GenerateLinkForm, SearchForm

from app.open2chat import open2chat

@open2chat.route('/generate')
def generate():
    form = GenerateLinkForm()
    form.username.data = User.generate_short_code()
    return render_template('open2chat/generate_link.html', form=form)


@open2chat.route('/', methods=['GET', 'POST'])
def search():
    form = SearchForm()
    if form.validate_on_submit():
        if current_user.is_authenticated:
            post = current_user.create_post(is_asking=True, price_cent=500, title=form.topic.data)
        else:
            session['topic'] = form.topic.data
        return redirect(url_for('main.view_node', node_id=post.root_node.id))

    return render_template("open2chat/landing.html", form=form)