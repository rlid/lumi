from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from app import db


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    is_public = db.Column(db.Boolean, default=False, nullable=False)

    text = db.Column(db.Text, nullable=False)

    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
