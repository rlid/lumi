from datetime import datetime

from app import db
from utils import security_utils

_SINGLE_USE_TOKEN_NBYTES = 32


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
