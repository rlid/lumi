import uuid
from datetime import datetime

from sqlalchemy.dialects.postgresql import UUID

from app import db


class Rating(db.Model):
    __tablename__ = 'ratings'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=True)
    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))

    product_id = db.Column(UUID(as_uuid=True), db.ForeignKey('products.id'))
    score = db.Column(db.Integer, nullable=False)
    s_agree = db.Column(db.Float, default=1.0)
    s_disagree = db.Column(db.Float, default=0.0)
    review = db.Column(db.Text)


class ProductLabel(db.Model):
    __tablename__ = 'product_labels'

    product_id = db.Column(UUID(as_uuid=True), db.ForeignKey('products.id'), primary_key=True)
    label_id = db.Column(db.String(64), db.ForeignKey('labels.id'), primary_key=True)

    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=True)
    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=True)


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    name = db.Column(db.String, nullable=True)
    product_labels = db.relationship('ProductLabel',
                                     foreign_keys=[ProductLabel.product_id],
                                     backref=db.backref('product', lazy='joined'),
                                     lazy='dynamic',
                                     cascade='all, delete-orphan')
    ratings = db.relationship('Rating',
                              foreign_keys=[Rating.product_id],
                              backref=db.backref('product', lazy='joined'),
                              lazy='dynamic',
                              cascade='all, delete-orphan')
    state_positive = db.Column(db.Float)

    @property
    def rating(self):
        ratings = self.ratings.all()
        xs = [(rating.score > 0, rating.creator.p_agree) for rating in ratings]
        return sum([x * w for (x, w) in xs]) / sum([w for (x, w) in xs])


class Label(db.Model):
    __tablename__ = 'labels'

    id = db.Column(db.String(64), primary_key=True)

    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=True)

    name = db.Column(db.String(64), nullable=False)
    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'))
    product_labels = db.relationship('ProductLabel',
                                     foreign_keys=[ProductLabel.label_id],
                                     backref=db.backref('label', lazy='joined'),
                                     lazy='dynamic',
                                     cascade='all, delete-orphan')
