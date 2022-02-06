from flask_wtf import FlaskForm
from flask_pagedown.fields import PageDownField
from wtforms import SubmitField, StringField, DecimalField, RadioField, TextAreaField
from wtforms.validators import InputRequired, NumberRange


class TUIEditorField(TextAreaField):
    pass


class PostForm(FlaskForm):
    is_request = RadioField("Are you buying or selling?",
                            choices=[
                                (1, "Buying - I am making a request"),
                                (0, "Selling - I am offering my service"),
                            ],
                            validators=[InputRequired()]
                            )
    title = StringField("Title",
                        validators=[InputRequired()],
                        render_kw={"placeholder": "Title"})
    reward = DecimalField("Price (in USD $)",
                          validators=[InputRequired(), NumberRange(1, 5)],
                          render_kw={"placeholder": "Price"})
    body = TextAreaField("Details (optional)", render_kw={"style": "display:none;"})
    editor = TUIEditorField()
    # tags = StringField("Tags",
    #                    validators=[InputRequired()],
    #                    render_kw={"placeholder": "Tags"})
    submit = SubmitField("Post", render_kw={"class": "w-100"})
