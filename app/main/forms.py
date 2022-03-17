from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, DecimalField, RadioField, TextAreaField, IntegerRangeField, EmailField
from wtforms.validators import InputRequired, NumberRange, Length
from wtforms.validators import ValidationError

from app.models import Post

TITLE_MIN_LENGTH = 5


class PostForm(FlaskForm):
    platform_fee = 0.1  # Default
    referral_budget = 0.2  # Default for public mode
    # if editing existing post, do not validate price because user's current value limit might be lower than when he
    # made the post:
    edit_mode = False

    type = RadioField("Choose a type:",
                      choices=[
                          (Post.TYPE_BUY, "I have a question to ask or a task to perform"),
                          (Post.TYPE_SELL, "(New) I want to answer questions or offering my service"),
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
        if not self.edit_mode:
            # do not validate price in edit mode because user's current value limit might be lower than when he made the
            # post
            price_cent = round(100 * field.data)
            if self.type.data == Post.TYPE_BUY:
                if current_user.value_limit_cent < price_cent:
                    raise ValidationError(f'Your current limit on buying price is ${current_user.reward_limit:.2f}.')
            if self.type.data == Post.TYPE_SELL:
                value_cent = price_cent
                value_cent += round(self.platform_fee * price_cent)
                value_cent += round(self.referral_budget * price_cent)
                if current_user.value_limit_cent < value_cent:
                    raise ValidationError(
                        'Your current limit on selling price is ' +
                        f'{0.01 * int(100 * current_user.reward_limit / (1 + self.platform_fee + self.referral_budget)):.2f}.'
                    )


class ShareForm(FlaskForm):
    percentage = IntegerRangeField('Percentage')
    submit = SubmitField('Adjust')


class MessageForm(FlaskForm):
    text = TextAreaField("Text", id='textareaMessage', validators=[InputRequired()])
    submit = SubmitField("Send")


class ReportForm(FlaskForm):
    text = TextAreaField("Text", id='textareaReport', validators=[InputRequired()])
    submit = SubmitField("Send")


class FeedbackForm(FlaskForm):
    text = TextAreaField('Text', id='textareaFeedback', validators=[InputRequired()])
    email = EmailField('Email (Optional)', render_kw={"placeholder": "name@example.com"})
    submit = SubmitField("Send")


class ConfirmForm(FlaskForm):
    submit = SubmitField('Confirm')


class RatingForm(FlaskForm):
    tip_cent = IntegerRangeField('Tip')
    submit = SubmitField('Confirm')
