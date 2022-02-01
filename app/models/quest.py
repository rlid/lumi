from datetime import datetime

from app import db
from app.models.node import Node

STATUS_OPEN = 0


class Quest(db.Model):
    __tablename__ = 'quests'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Integer, default=STATUS_OPEN)

    value = db.Column(db.Integer, nullable=False)

    title = db.Column(db.String(100), nullable=False)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)

    nodes = db.relationship('Node',
                            foreign_keys=[Node.quest_id],
                            backref=db.backref('quest', lazy='joined'),
                            lazy='dynamic',
                            cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Quest[{self.id}]>'

    @staticmethod
    def make(creator, value, title, body=None, body_html=None):
        quest = Quest(creator=creator, value=value, title=title, body=body, body_html=body_html)
        node = Node(quest=quest, creator=creator)
        db.session.add_all([quest, node])
        db.session.commit()
        return quest
