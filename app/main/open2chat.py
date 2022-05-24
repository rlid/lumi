from flask import render_template
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, SubmitField, BooleanField
from wtforms.validators import InputRequired, Length
from app.main import main
from app.models import User


class GenerateLinkForm(FlaskForm):
    email = EmailField("Email address", validators=[InputRequired()], render_kw={"placeholder": "name@example.com"})
    # We will send you the generated link, and notify you when there is a chat request. Your email address is not shared with anyone.
    username = StringField(
        "Open2.Chat/",
        validators=[InputRequired(), Length(min=4)]
    )
    # Optional - leave it blank and we will generate a short link for you to share
    topic = StringField("Topics", validators=[InputRequired()], render_kw={"placeholder": "Topics"})
    # Optional - list a couple of topics you are knowledgeable about, we will use this info to help other users to
    # connect with you
    submit = SubmitField("Generate")


class SearchForm(FlaskForm):
    topic = StringField("Enter a topic you want to chat about",
                        validators=[InputRequired()],
                        render_kw={"placeholder": "Topic"})
    is_public = BooleanField("Visible to all", default=False)
    # Make your search visible to all so others can help you connect with the right person
    email = EmailField("Email address", validators=[InputRequired()], render_kw={"placeholder": "name@example.com"})
    # Please leave an email address so we can contact you when we can connect you with the right person
    submit = SubmitField("Create", render_kw={"class": "w-100"})


class AskForm(FlaskForm):
    text = StringField("Message", validators=[InputRequired()], render_kw={"placeholder": "Message"})
    email = EmailField("Email address", validators=[InputRequired()], render_kw={"placeholder": "name@example.com"})
    # Please leave an email address so we can let you know when the other user replied
    submit = SubmitField("Send", render_kw={"class": "w-100"})


class AnswerForm(FlaskForm):
    text = StringField("Message", validators=[InputRequired()], render_kw={"placeholder": "Message"})
    claim_reward = BooleanField("Claim reward", default=True)
    # Check this box if you do not want to claim the reward for whatever reason
    submit = SubmitField("Send", render_kw={"class": "w-100"})


@main.route('/generate')
def generate():
    form_gen_link = GenerateLinkForm()
    form_gen_link.username.data = User.generate_short_code()
    return render_template('open2chat/landing.html', form_gen_link=form_gen_link)
