from flask import current_app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash

from utils import security_utils
from app import db, login_manager

_REMEMBER_ME_ID_NBYTES = 32
_TOKEN_SERVER_NONCE_NBYTES = 32
_TOKEN_EXPIRATION = 600


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    confirmed = db.Column(db.Boolean, default=False)

    # length of str(unsigned 64-bit integer) = 20
    # length of separator = 1
    # base64 encoding of _NBYTES bytes = ~1.3 * _NBYTES, rounded to 1.5 for safety
    server_nonce = db.Column(db.String(int(1.5 * _TOKEN_SERVER_NONCE_NBYTES)))
    remember_me_id = db.Column(db.String(21 + int(1.5 * _REMEMBER_ME_ID_NBYTES)))

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

    def reset_remember_id(self):
        self.remember_me_id = f"{self.id}/{security_utils.random_urlsafe(nbytes=_REMEMBER_ME_ID_NBYTES)}"
        db.session.add(self)
        db.session.commit()

    def get_id(self):
        """For Flask-Login remember-me security, see https://flask-login.readthedocs.io/en/latest/#alternative-tokens"""
        if self.remember_me_id is None:
            self.reset_remember_id()
        return self.remember_me_id

    def generate_token(self, action, client_nonce_hash=None, expiration=_TOKEN_EXPIRATION):
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        server_nonce = security_utils.random_urlsafe(nbytes=_TOKEN_SERVER_NONCE_NBYTES)
        self.server_nonce = server_nonce
        db.session.add(self)
        db.session.commit()
        print(f"server_nonce is set to [{server_nonce}].")
        return s.dumps({action: self.id,
                        "server_nonce": server_nonce,
                        "client_nonce_hash": client_nonce_hash}).decode("utf-8")

    @staticmethod
    def decode_token(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token.encode("utf-8"))
        except:
            data = dict()
        return data

    def verify_token_data(self, data, action, client_nonce_hash=None):
        token_user_id = data.get(action)
        token_server_nonce = data.get("server_nonce")
        token_client_nonce_hash = data.get("client_nonce_hash")

        verified = token_user_id == self.id \
                   and token_server_nonce == self.server_nonce \
                   and token_client_nonce_hash == client_nonce_hash
        if self.server_nonce == token_server_nonce and self.server_nonce is not None:
            self.server_nonce = None
            db.session.add(self)
            db.session.commit()
            print(f"server_nonce [{token_server_nonce}] is deleted.")
        return verified

    def verify_token(self, token, action, client_nonce_hash=None):
        return self.verify_token_data(data=User.decode_token(token), action=action, client_nonce_hash=client_nonce_hash)


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(remember_me_id=user_id).first()
