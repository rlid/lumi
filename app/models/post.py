from datetime import datetime

import bleach
from bleach.sanitizer import Cleaner
from bleach.html5lib_shim import Filter
from markdown import markdown

from app import db
from app.models import Node

STATUS_OPEN = 0


class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)

    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    is_request = db.Column(db.Boolean, nullable=False)
    reward = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=False)

    body = db.Column(db.Text)
    body_html = db.Column(db.Text)

    nodes = db.relationship('Node',
                            backref=db.backref('post'),
                            lazy='dynamic',
                            cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Post[{self.id}]>'

    @staticmethod
    def on_changed_body(target, value, oldvalue, initiator):
        allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
                        'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
                        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']

        class MooFilter(Filter):
            def __iter__(self):
                for token in Filter.__iter__(self):
                    if token['type'] in ['StartTag', 'EndTag'] and \
                            token['name'] in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        token['name'] = 'h6'
                    yield token

        cleaner = Cleaner(tags=allowed_tags, filters=[MooFilter], strip=True)

        target.body_html = bleach.linkify(cleaner.clean(markdown(value, output_format='html')))


db.event.listen(Post.body, 'set', Post.on_changed_body)
