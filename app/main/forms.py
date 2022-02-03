from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, TextAreaField
from wtforms.validators import InputRequired


class PostForm(FlaskForm):
    title = StringField("Title", validators=[InputRequired()], render_kw={"placeholder": "Title"})
    text = TextAreaField("Text", render_kw={"placeholder": "Text", "style": "height: 20vh"})
    submit = SubmitField("Post", render_kw={"class": "w-100"})
