from datetime import datetime

from app import db
from utils import security_utils

from sqlalchemy.dialects.postgresql import UUID
import uuid

_SINGLE_USE_TOKEN_NBYTES = 32


class SingleUseToken(db.Model):
    __tablename__ = 'single_use_tokens'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    expiry = db.Column(db.DateTime, nullable=False)

    def __init__(self, expiry_timedelta):
        self.expiry = datetime.utcnow() + expiry_timedelta

    @staticmethod
    def generate(timedelta_to_expiry):
        token = SingleUseToken(expiry_timedelta=timedelta_to_expiry)
        db.session.add(token)
        db.session.commit()
        print(f'Created {token}.')
        return token

    @staticmethod
    def validate(code):
        if code is None or code == '':
            return False
        token = SingleUseToken.query.filter_by(id=uuid.UUID(hex=code)).first()
        if token is None:
            return False
        elif datetime.utcnow() > token.expiry:
            return False
        else:
            db.session.delete(token)
            db.session.commit()
            print(f'Deleted {token}.')
            return True
