import secrets
import string
from datetime import datetime, timedelta

from flask import current_app
from flask_login import UserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash

from utils import security_utils
from app import db, login_manager

_INVITE_CODE_CHARS = string.ascii_lowercase + string.digits

_REMEMBER_ME_ID_NBYTES = 32
_SINGLE_USE_TOKEN_NBYTES = 32
_ACCOUNT_TOKEN_EXPIRATION = 600


class SingleUseToken(db.Model):
    __tablename__ = 'single_use_tokens'
    id = db.Column(db.Integer, primary_key=True)
    # base64 encoding of _NBYTES bytes = ~1.3 * _NBYTES, rounded to 1.5 for safety
    code = db.Column(db.String(int(1.5 * _SINGLE_USE_TOKEN_NBYTES)), index=True, unique=True, nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)

    def __init__(self, expiry_timedelta):
        self.code = security_utils.random_urlsafe(nbytes=_SINGLE_USE_TOKEN_NBYTES)
        self.expiry = datetime.utcnow() + expiry_timedelta

    def __repr__(self):
        return f'<SingleUseToken[{self.id}]:code={self.code},expiry={self.expiry}>'

    @staticmethod
    def generate(expiry_timedelta):
        codes = [code for code, in db.session.query(SingleUseToken.code).all()]
        token = SingleUseToken(expiry_timedelta=expiry_timedelta)
        while token.code in codes:
            token = SingleUseToken(expiry_timedelta=expiry_timedelta)
        db.session.add(token)
        db.session.commit()
        print(f"Created {token}.")
        return token

    @staticmethod
    def validate(code):
        if code is None or code == "":
            return False
        token = SingleUseToken.query.filter_by(code=code).first()
        if token is None:
            return False
        elif datetime.utcnow() > token.expiry:
            return False
        else:
            db.session.delete(token)
            db.session.commit()
            print(f"Deleted {token}.")
            return True


class InviteCode(db.Model):
    __tablename__ = 'invite_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), index=True, unique=True, nullable=False)
    expiry = db.Column(db.DateTime, nullable=False)

    def __init__(self, length, expiry_timedelta):
        self.code = ''.join(secrets.choice(_INVITE_CODE_CHARS) for i in range(length))
        self.expiry = datetime.utcnow() + expiry_timedelta

    def __repr__(self):
        return f'<InviteCode[{self.id}]:code={self.code},expiry={self.expiry}>'

    @staticmethod
    def generate(length, expiry_timedelta):
        codes = [code for code, in db.session.query(InviteCode.code).all()]
        invite_code = InviteCode(length=length, expiry_timedelta=expiry_timedelta)
        while invite_code.code in codes:
            invite_code = InviteCode(length=length, expiry_timedelta=expiry_timedelta)
        db.session.add(invite_code)
        db.session.commit()
        return invite_code

    @staticmethod
    def validate(code):
        if code is None or code == "":
            return None, f'The invite code "{code}" is invalid.'
        invite_code = InviteCode.query.filter_by(code=code).first()
        if invite_code is None:
            return None, f'The invite code "{code}" is invalid.'
        elif datetime.utcnow() > invite_code.expiry:
            return None, f'The invite code "{code}" has expired.'
        else:
            return invite_code, None


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

    def generate_token(self, action, site_rid_hash=None, expiration=_ACCOUNT_TOKEN_EXPIRATION):
        s = Serializer(current_app.config["SECRET_KEY"], expiration)
        server_token = SingleUseToken.generate(expiry_timedelta=timedelta(seconds=_ACCOUNT_TOKEN_EXPIRATION))
        return s.dumps({action: self.id,
                        "server_token": server_token.code,
                        "site_rid_hash": site_rid_hash}).decode()

    @staticmethod
    def decode_token(token):
        s = Serializer(current_app.config["SECRET_KEY"])
        try:
            data = s.loads(token.encode())
        except:
            data = dict()
        return data

    @staticmethod
    def verify_token_data(user, data, action, site_rid_hash=None):
        id_match = user.id == data.get(action)
        server_token_is_valid = SingleUseToken.validate(data.get("server_token"))
        site_rid_match = site_rid_hash == data.get("site_rid_hash")

        return id_match and server_token_is_valid and site_rid_match

    def verify_token(self, token, action, site_rid_hash=None):
        return User.verify_token_data(user=self,
                                      data=User.decode_token(token),
                                      action=action,
                                      site_rid_hash=site_rid_hash)

    @staticmethod
    def verify_token_static(token, action, site_rid_hash=None):
        data = User.decode_token(token)
        user_id = data.get(action)
        if user_id is None:
            return False, None
        user = User.query.get(int(user_id))
        if user is None:
            return False, None
        return User.verify_token_data(user=user, data=data, action=action, site_rid_hash=site_rid_hash), user


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(remember_me_id=user_id).first()
