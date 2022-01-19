from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, EqualTo, ValidationError

from app.models import User


class LogInForm(FlaskForm):
    email = EmailField("Email address", validators=[DataRequired()], render_kw={"placeholder": "name@example.com"})
    password = PasswordField("Password(*)", validators=[],
                             render_kw={"placeholder": "Password"})
    remember_me = BooleanField("Remember me", default=True)
    submit = SubmitField("Log In", render_kw={"class": "w-100"})


class SignUpForm(FlaskForm):
    email = EmailField("Email address", validators=[DataRequired()], render_kw={"placeholder": "name@example.com"})
    password = PasswordField("Password(*)",
                             validators=[EqualTo("confirm_password", message="Passwords must match.")],
                             render_kw={"placeholder": "Password"})
    confirm_password = PasswordField("Confirm password(*)", validators=[],
                                     render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField("Register", render_kw={"class": "w-100"})

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("The email address is already registered.")

    def validate_password(self, field):
        n = len(field.data)
        if 0 < n < 8:
            raise ValidationError("Password must be at least 8 characters long.")
