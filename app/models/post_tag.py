from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID
from app import db


class PostTag(db.Model):
    __tablename__ = "post_tags"

    post_id = db.Column(UUID(as_uuid=True), db.ForeignKey("posts.id"), primary_key=True)
    tag_id = db.Column(db.String(64), db.ForeignKey("tags.id"), primary_key=True)

    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=True)

    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=True)


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.String(64), primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=True)

    name = db.Column(db.String(64), nullable=False)

    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"))

    post_tags = db.relationship("PostTag",
                                foreign_keys=[PostTag.tag_id],
                                backref=db.backref("tag", lazy="joined"),
                                lazy="dynamic",
                                cascade="all, delete-orphan")
