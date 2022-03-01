from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, DecimalField, RadioField, TextAreaField
from wtforms.validators import InputRequired, NumberRange, Length
from wtforms.validators import ValidationError

from app.models import Post

TITLE_MIN_LENGTH = 5


class TUIEditorField(TextAreaField):
    pass


class PostForm(FlaskForm):
    platform_fee = 0.1  # Default
    referral_budget = 0.2  # Default for public mode

    type = RadioField("Are you buying or selling?",
                      choices=[
                          (Post.TYPE_BUY, "Buying - I am asking a question / making a request"),
                          (Post.TYPE_SELL, "Selling - I am answering questions / offering my service"),
                      ],
                      validators=[InputRequired()]
                      )
    price = DecimalField("Price (USD - $)",
                         validators=[InputRequired(), NumberRange(min=1)],
                         render_kw={"placeholder": "Price"})
    title = StringField("Title",
                        validators=[InputRequired(), Length(TITLE_MIN_LENGTH, 100)],
                        render_kw={"placeholder": "Title"})
    body = TextAreaField("Details (optional)", render_kw={"placeholder": "Details (optional)"})
    submit = SubmitField("Post", render_kw={"class": "w-100"})

    def validate_title(self, field):
        if len(field.data.strip()) < TITLE_MIN_LENGTH:
            raise ValidationError(f'Title cannot be less than {TITLE_MIN_LENGTH} characters')

    def validate_price(self, field):
        # value limit checks
        # if current_user.value_limit_cent < 100 * field.data:
        #     raise ValidationError(f'Your current price limit is {current_user.reward_limit:.2f}.')
        price_cent = round(100 * field.data)
        if self.type.data == Post.TYPE_BUY:
            if current_user.value_limit_cent < round(100 * price_cent):
                raise ValidationError(f'Your current limit on buying price is {current_user.reward_limit:.2f}.')
        if self.type.data == Post.TYPE_SELL:
            value_cent = price_cent
            value_cent += round(self.platform_fee * price_cent)
            value_cent += round(self.referral_budget * price_cent)
            print(value_cent)
            if current_user.value_limit_cent < value_cent:
                raise ValidationError(
                    'Your current limit on selling price is ' +
                    f'{0.01 * int(100 * current_user.reward_limit / (1 + self.platform_fee + self.referral_budget)):.2f}.'
                )


class PostFormPrivate(PostForm):
    referral_budget = 0.4  # Default for private mode


class MarkdownPostForm(PostForm):
    body = TextAreaField("Details (optional)", render_kw={"style": "display:none;"})
    editor = TUIEditorField()
    submit = SubmitField("Post", render_kw={"class": "w-100"})


class MarkdownPostFormPrivate(MarkdownPostForm):
    referral_budget = 0.4  # Default for private mode


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
