from datetime import datetime
from sqlalchemy import event

import bleach
from bleach.html5lib_shim import Filter
from bleach.sanitizer import Cleaner
from markdown import Markdown

from app import db
from app.models import PostTag
from utils.markdown_ext import DelExtension


class Post(db.Model):
    __tablename__ = 'posts'

    TYPE_BUY = 'buy'
    TYPE_SELL = 'sell'
    TYPE_ANNOUNCEMENT = 'announcement'
    TYPE_WARNING = 'warning'
    TYPE_INFO = 'info'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)

    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    type = db.Column(db.String(16), nullable=False)
    reward = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=False)
    is_open = db.Column(db.Boolean, default=True, nullable=False)

    body = db.Column(db.Text)
    body_html = db.Column(db.Text)

    comments = db.relationship('Comment',
                               backref=db.backref('post'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

    nodes = db.relationship('Node',
                            backref=db.backref('post'),
                            lazy='dynamic',
                            cascade='all, delete-orphan')

    post_tags = db.relationship("PostTag",
                                foreign_keys=[PostTag.post_id],
                                backref=db.backref("post", lazy="joined"),
                                lazy="dynamic",
                                cascade="all, delete-orphan")

    def __repr__(self):
        return f'<p{self.id}>creator={self.creator},type={self.type}</p{self.id}>'


@event.listens_for(Post.body, 'set')
def on_changed_body(target, value, oldvalue, initiator):
    allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'br', 'code', 'del',
                    'em', 'hr', 'i', 'img', 'li', 'ol', 'pre', 'strong', 'ul',
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p']

    allowed_attributes = {
        "a": ["href", "title"],
        "abbr": ["title"],
        "acronym": ["title"],
        "img": ["alt", "src"]
    }

    class HxFilter(Filter):
        def __iter__(self):
            for token in Filter.__iter__(self):
                if token['type'] in ['StartTag', 'EndTag'] and \
                        token['name'] in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                    token['name'] = 'h6'
                yield token

    use_markdown = value[0] == 'm'
    value = value[1:]

    cleaner = Cleaner(tags=allowed_tags, attributes=allowed_attributes, filters=[HxFilter], strip=True)
    if use_markdown:
        markdown = Markdown(extensions=[DelExtension()])
        html = markdown.convert(value)
    else:
        html = value.replace('\n', '<br>').replace('\\#', '#')
    target.body_html = bleach.linkify(cleaner.clean(html))
