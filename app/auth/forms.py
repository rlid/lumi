from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, BooleanField, SubmitField, Label
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    email = EmailField("Email address", validators=[DataRequired()], render_kw={"placeholder": "name@example.com"})
    password = PasswordField("Password(*)", validators=[],
                             render_kw={"placeholder": "Password"})
    remember_me = BooleanField("Remember me", default=True)
    submit = SubmitField("Log In", render_kw={"class": "w-100"})
