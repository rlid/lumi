from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, IntegerField, RadioField, TextAreaField
from wtforms.validators import InputRequired, NumberRange, Length, DataRequired
from wtforms.validators import ValidationError

from app.models import Post

TITLE_MIN_LENGTH = 5


class TUIEditorField(TextAreaField):
    pass


class PostForm(FlaskForm):
    type = RadioField("Are you buying or selling?",
                      choices=[
                          (Post.TYPE_BUY, "Buying - I am asking a question / making a request"),
                          (Post.TYPE_SELL, "Selling - I am answering questions / offering my service"),
                      ],
                      validators=[InputRequired()]
                      )
    reward = IntegerField("Reward / Price (in USD - $)",
                          validators=[InputRequired(), NumberRange(1, 5)],
                          render_kw={"placeholder": "Price"})
    title = StringField("Title",
                        validators=[InputRequired(), Length(TITLE_MIN_LENGTH, 100)],
                        render_kw={"placeholder": "Title"})
    body = TextAreaField("Details (optional)", render_kw={"placeholder": "Details (optional)"})
    submit = SubmitField("Post", render_kw={"class": "w-100"})

    def validate_title(self, field):
        if len(field.data.strip()) < TITLE_MIN_LENGTH:
            raise ValidationError(f'Title cannot be less than {TITLE_MIN_LENGTH} characters')


class MarkdownPostForm(PostForm):
    body = TextAreaField("Details (optional)", render_kw={"style": "display:none;"})
    editor = TUIEditorField()
    submit = SubmitField("Post", render_kw={"class": "w-100"})


class MessageForm(FlaskForm):
    text = TextAreaField("Text", validators=[InputRequired()])
    submit = SubmitField("Send")


class ReportPostForm(FlaskForm):
    text = TextAreaField(
        "Text",
        validators=[InputRequired()],
        render_kw={"placeholder": "Spam / Phishing / Harassment / Other illegal activities"}
    )
    submit = SubmitField("Send")
