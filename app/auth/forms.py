from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, BooleanField, SubmitField, StringField
from wtforms.validators import InputRequired, EqualTo, ValidationError, Length

from app.models import User, InviteCode


class LogInForm(FlaskForm):
    email = EmailField("Email address", validators=[InputRequired()], render_kw={"placeholder": "name@example.com"})
    password = PasswordField("Password",
                             validators=[
                                 InputRequired(),
                                 Length(min=8, message='Password must be at least 8 characters long.')
                             ],
                             render_kw={"placeholder": "Password"})
    remember_me = BooleanField("Remember me", default=False)
    submit = SubmitField("Log In", render_kw={"class": "w-100"})


class SignUpForm(FlaskForm):
    invite_code = StringField("Invite code", validators=[InputRequired()], render_kw={"placeholder": "Invite Code"})
    email = EmailField("Email address", validators=[InputRequired()], render_kw={"placeholder": "name@example.com"})
    password = PasswordField("Password",
                             validators=[
                                 InputRequired(),
                                 EqualTo("confirm_password", message="Passwords must match."),
                                 Length(min=8, message='Password must be at least 8 characters long.')
                             ],
                             render_kw={"placeholder": "Password"})
    confirm_password = PasswordField("Confirm password",
                                     validators=[
                                         InputRequired(),
                                         Length(min=8, message='Password must be at least 8 characters long.')
                                     ],
                                     render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField("Sign Up", render_kw={"class": "w-100"})

    def validate_email(self, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("The email address is already registered.")

    def validate_invite_code(self, field):
        invite_code, error_message = InviteCode.validate(field.data)
        if invite_code is None:
            raise ValidationError(error_message)


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password',
                                 validators=[
                                     InputRequired(),
                                     Length(min=8, message='Password must be at least 8 characters long.')
                                 ],
                                 render_kw={"placeholder": "Old Password"})
    password = PasswordField('New password',
                             validators=[
                                 InputRequired(),
                                 EqualTo("confirm_password", message="Passwords must match."),
                                 Length(min=8, message='Password must be at least 8 characters long.')
                             ],
                             render_kw={"placeholder": "New Password"})
    confirm_password = PasswordField('Confirm new password',
                                     validators=[
                                         InputRequired(),
                                         Length(min=8, message='Password must be at least 8 characters long.')
                                     ],
                                     render_kw={"placeholder": "Confirm New Password"})
    submit = SubmitField('Update Password', render_kw={"class": "w-100"})


class PasswordResetRequestForm(FlaskForm):
    email = EmailField("Email address", validators=[InputRequired()], render_kw={"placeholder": "name@example.com"})
    submit = SubmitField('Reset Password', render_kw={"class": "w-100"})


class PasswordResetForm(FlaskForm):
    password = PasswordField('New password',
                             validators=[
                                 InputRequired(),
                                 EqualTo("confirm_password", message="Passwords must match."),
                                 Length(min=8, message='Password must be at least 8 characters long.')
                             ],
                             render_kw={"placeholder": "New Password"})
    confirm_password = PasswordField('Confirm new password',
                                     validators=[
                                         InputRequired(),
                                         Length(min=8, message='Password must be at least 8 characters long.')
                                     ],
                                     render_kw={"placeholder": "Confirm New Password"})
    submit = SubmitField('Reset Password', render_kw={"class": "w-100"})
