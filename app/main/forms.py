from flask_wtf import FlaskForm
from flask_pagedown.fields import PageDownField
from wtforms import SubmitField, StringField, DecimalField, Field, TextAreaField
from wtforms.validators import InputRequired, NumberRange


class TUIEditorField(TextAreaField):
    pass


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
    text = TextAreaField("Details (optional)", render_kw={"style": "display:none;"})
    editor = TUIEditorField()
    submit = SubmitField("Post", render_kw={"class": "w-100"})
