import secrets
from flask import current_app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash

from . import db, login_manager

_TOKEN_SERVER_KEY_NBYTES = 32
_TOKEN_EXPIRATION = 600


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)

    valid_server_key = db.Column(db.String(2 * _TOKEN_SERVER_KEY_NBYTES))

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

    def generate_token(self, action, client_key=None, expiration=_TOKEN_EXPIRATION):
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        server_key = secrets.token_urlsafe(nbytes=_TOKEN_SERVER_KEY_NBYTES)
        self.valid_server_key = server_key
        db.session.add(self)
        db.session.commit()
        return s.dumps({action: self.id,
                        "server_key": server_key,
                        "client_key": client_key}).decode("utf-8")

    @staticmethod
    def decode_token(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token.encode("utf-8"))
        except:
            return dict()
        return data

    def verify_token_data(self, data, action, client_key=None):
        token_user_id = data.get(action)
        token_server_key = data.get("server_key")
        token_client_key = data.get("client_key")

        # print(f"token_server_key={token_server_key}, self.valid_server_key={self.valid_server_key}")
        # print(f"token_client_key={token_client_key}, client_key={client_key}")

        verified = False
        if self.valid_server_key is not None and self.valid_server_key == token_server_key:
            verified = token_user_id == self.id \
                       and token_server_key == self.valid_server_key \
                       and token_client_key == client_key
            self.valid_server_key = None
            db.session.add(self)
            db.session.commit()
        return verified

    def verify_token(self, token, action, client_key=None):
        return self.verify_token_data(User.decode_token(token), action, client_key=client_key)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
