from flask import current_app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash

from . import db, login_manager


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<User[{self.id}] {self.email}>"

    @property
    def password(self):
        raise AttributeError("password is not a readable attribute")

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_token(self, action, cookie_key=None, expiration=600):
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        return s.dumps({action: self.id, "cookie_key": cookie_key}).decode("utf-8")

    @staticmethod
    def decode_token(token, action):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token.encode("utf-8"))
        except:
            return None, None
        return data.get(action), data.get("cookie_key")

    def verify_token(self, token, action, cookie_key=None):
        token_user_id, token_cookie_key = User.decode_token(token, action)
        return token_user_id == self.id and token_cookie_key == cookie_key


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
