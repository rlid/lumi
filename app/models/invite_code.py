import secrets
import string
import uuid
from datetime import datetime

from app import db
from app.models import Node

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
        return invite_code

    @staticmethod
    def validate(code):
        if code is None or code == '':
            return False, None, f'The invite code "{code}" is invalid.'
        invite_code = InviteCode.query.filter_by(code=code).first()
        if invite_code is None:
            try:
                node_id = uuid.UUID(code)
            except ValueError as e:
                return False, None, f'The invite code "{code}" is invalid.'
            node = Node.query.get(node_id)
            if node:
                return True, None, None
            else:
                return False, None, f'The invite code "{code}" is invalid.'
        elif datetime.utcnow() > invite_code.expiry:
            return False, None, f'The invite code "{code}" has expired.'
        else:
            return True, invite_code, None

    @staticmethod
    def delete(code):
        invite_code = InviteCode.query.filter_by(code=code).first()
        if invite_code is not None:
            db.session.delete(invite_code)
