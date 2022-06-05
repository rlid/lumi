import uuid
from datetime import datetime

import bleach
from bleach.html5lib_shim import Filter
from bleach.sanitizer import Cleaner
from markdown import Markdown
from sqlalchemy import event
from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models import PostTag, Node
from utils.markdown_ext import DelExtension


class Post(db.Model):
    __tablename__ = 'posts'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    last_updated = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    completed = db.Column(db.Boolean, default=False, nullable=False)

    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)

    is_asking = db.Column(db.Boolean, nullable=False)
    price_cent = db.Column(db.Integer, nullable=False)
    platform_fee_cent = db.Column(db.Integer, nullable=False)

    is_private = db.Column(db.Boolean, default=False, nullable=False)
    referral_budget_cent = db.Column(db.Integer)

    is_archived = db.Column(db.Boolean, default=False, nullable=False)
    is_reported = db.Column(db.Boolean, default=False, nullable=False)
    report_reason = db.Column(db.Text, default='')

    topic = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(256), nullable=False)
    body = db.Column(db.Text)
    body_html = db.Column(db.Text)

    ab_test_tag = db.Column(db.String(64))

    comments = db.relationship('Comment',
                               backref=db.backref('post'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

    root_node = db.relationship('Node',
                                backref=db.backref('post_if_root'),
                                foreign_keys=[Node.post_id_if_root],
                                lazy='immediate',
                                uselist=False)

    nodes = db.relationship('Node',
                            backref=db.backref('post'),
                            foreign_keys=[Node.post_id],
                            lazy='dynamic',
                            cascade='all, delete-orphan')

    post_tags = db.relationship("PostTag",
                                foreign_keys=[PostTag.post_id],
                                backref=db.backref("post", lazy="joined"),
                                lazy="dynamic",
                                cascade="all, delete-orphan")

    def ping(self, utcnow):
        self.last_updated = utcnow
        db.session.add(self)

    def __repr__(self):
        return f'<p{self.id}>creator={self.creator}</p{self.id}>'

    @property
    def root_node(self):
        return self.nodes.filter_by(parent=None).first()


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
