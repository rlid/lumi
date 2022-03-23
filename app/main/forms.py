from flask_login import current_user
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, DecimalField, RadioField, TextAreaField, IntegerRangeField, EmailField, \
    BooleanField
from wtforms.validators import InputRequired, NumberRange, Length
from wtforms.validators import ValidationError

from app.models import Post

TITLE_MIN_LENGTH = 5


class PostForm(FlaskForm):
    # if editing existing post, do not validate price because user's current value limit might be lower than when he
    # made the post:
    edit_mode = False

    is_asking = RadioField("I want to...",
                           choices=[
                               ('True', "ask questions, or request a service"),
                               ('False', "answer questions, or offer my service"),
                           ],
                           validators=[InputRequired()],
                           default='True'
                           )
    price = DecimalField("Reward (USD - $)",
                         validators=[InputRequired(), NumberRange(min=1)],
                         render_kw={"placeholder": "Price"})
    title = StringField("Topic",
                        validators=[InputRequired(), Length(TITLE_MIN_LENGTH, 100)],
                        render_kw={"placeholder": "Title"})
    body = TextAreaField("Details (optional)", render_kw={"placeholder": "Details (optional)"})
    is_private = BooleanField("Private mode", default=False)

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
            if self.is_asking.data == 'True':
                if current_user.value_limit_cent < price_cent:
                    raise ValidationError(f'Your current limit is ${current_user.reward_limit:.2f}.')
            else:
                m_platform_fee = 0.1  # Default
                m_referral = 0.4 if self.is_private.data else 0.2  # Default
                value_cent = price_cent
                value_cent += round(m_platform_fee * price_cent)
                value_cent += round(m_referral * price_cent)
                if current_user.value_limit_cent < value_cent:
                    raise ValidationError(
                        'Your current limit on selling price is ' +
                        f'${0.01 * int(100 * current_user.reward_limit / (1 + m_platform_fee + m_referral)):.2f}.'
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
    request_invite = BooleanField("Request an invite code", default=False)
    submit = SubmitField("Send")

    def validate_email(self, field):
        if self.request_invite.data:
            if not field.data:
                raise ValidationError(f'Please leave an email address where we can send the invite code to.')


class ConfirmForm(FlaskForm):
    submit = SubmitField('Confirm')


class RatingForm(FlaskForm):
    tip_cent = IntegerRangeField('Tip')
    submit = SubmitField('Confirm')
