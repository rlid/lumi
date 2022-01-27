import secrets
import string
from datetime import datetime

from app import db

_INVITE_CODE_CHARS = string.ascii_lowercase + string.digits


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
        if code is None or code == '':
            return None, f'The invite code "{code}" is invalid.'
        invite_code = InviteCode.query.filter_by(code=code).first()
        if invite_code is None:
            return None, f'The invite code "{code}" is invalid.'
        elif datetime.utcnow() > invite_code.expiry:
            return None, f'The invite code "{code}" has expired.'
        else:
            return invite_code, None
