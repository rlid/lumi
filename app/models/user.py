from datetime import timedelta

from authlib.jose.errors import BadSignatureError
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager
from app.models.single_use_token import SingleUseToken
from utils import security_utils, authlib_ext

_REMEMBER_ME_ID_NBYTES = 32
_TOKEN_SECONDS_TO_EXPIRY = 600


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    email_verified = db.Column(db.Boolean, default=False)
    signup_method = db.Column(db.String(16), default="email")

    # length of str(unsigned 64-bit integer) = 20
    # length of separator = 1
    # base64 encoding of n bytes = ~1.3 * n, rounded to 1.5 for safety
    remember_me_id = db.Column(db.String(21 + int(1.5 * _REMEMBER_ME_ID_NBYTES)))

    def __repr__(self):
        return f"<User[{self.id}]:email={self.email}>"

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

    def generate_token(self, action, site_rid_hash=None, seconds_to_exp=_TOKEN_SECONDS_TO_EXPIRY):
        server_token = SingleUseToken.generate(timedelta_to_expiry=timedelta(seconds=seconds_to_exp))
        return authlib_ext.jws_compact_serialize_timed(
            payload={action: self.id,
                     "server_token": server_token.code,
                     "site_rid_hash": site_rid_hash},
            key=current_app.config["SECRET_KEY"],
            seconds_to_exp=seconds_to_exp
        )

    @staticmethod
    def _decode_token(token):
        try:
            payload = authlib_ext.jws_compact_deserialize_timed(token, current_app.config["SECRET_KEY"])
        except BadSignatureError:
            payload = dict()
        return payload

    @staticmethod
    def _verify_token_data(user, data, action, site_rid_hash=None):
        id_match = user.id == data.get(action)
        server_token_is_valid = SingleUseToken.validate(data.get("server_token"))
        site_rid_match = site_rid_hash == data.get("site_rid_hash")

        return id_match and server_token_is_valid and site_rid_match

    def verify_token(self, token, action, site_rid_hash=None):
        data = User._decode_token(token)
        if not data:
            return False

        return User._verify_token_data(user=self,
                                       data=data,
                                       action=action,
                                       site_rid_hash=site_rid_hash)

    @staticmethod
    def verify_token_static(token, action, site_rid_hash=None):
        data = User._decode_token(token)
        if not data:
            return False, None

        user_id = data.get(action)
        if user_id is None:
            return False, None

        user = User.query.get(int(user_id))
        if user is None:
            return False, None
        return User._verify_token_data(user=user,
                                       data=data,
                                       action=action,
                                       site_rid_hash=site_rid_hash), user


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(remember_me_id=user_id).first()
