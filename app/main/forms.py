from flask_wtf import FlaskForm
from flask_pagedown.fields import PageDownField
from wtforms import SubmitField, StringField, DecimalField, Label
from wtforms.validators import InputRequired, NumberRange


class PostForm(FlaskForm):
    title = StringField("Title",
                        validators=[InputRequired()],
                        render_kw={
                            "placeholder": "Title",
                            'data-bs-toggle': 'tooltip'
                        })
    criteria = StringField("I want to hear from...",
                           validators=[InputRequired()],
                           render_kw={"placeholder": "criteria"})
    price = DecimalField("As reward I offer (in USD $)...",
                         validators=[InputRequired(), NumberRange(1, 5)],
                         render_kw={"placeholder": "Price"})
    # text = TextAreaField("Text", render_kw={"placeholder": "Text", "style": "height: 20vh"})
    text = PageDownField("Text", render_kw={"placeholder": "Details (optional)", "style": "height: 20vh"})
    submit = SubmitField("Post", render_kw={"class": "w-100"})
