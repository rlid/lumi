from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    email = EmailField("Email address", validators=[DataRequired()], render_kw={"placeholder": "name@example.com"})
    password = PasswordField("Password", validators=[DataRequired(), Length(8)],
                             render_kw={"placeholder": "Password"})
    remember_me = BooleanField("Remember me")
    submit = SubmitField("Log In", render_kw={"class": "w-100"})
