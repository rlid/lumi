from datetime import datetime

from app import db


class PostTag(db.Model):
    __tablename__ = "post_tags"

    post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), primary_key=True)
    tag_name = db.Column(db.String(64), db.ForeignKey("tags.name"), primary_key=True)

    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=True)

    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)


class Tag(db.Model):
    __tablename__ = "tags"

    name = db.Column(db.String(64), primary_key=True)

    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=True)

    creator_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    post_tags = db.relationship("PostTag",
                                foreign_keys=[PostTag.tag_name],
                                backref=db.backref("tag", lazy="joined"),
                                lazy="dynamic",
                                cascade="all, delete-orphan")
