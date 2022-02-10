from datetime import datetime

from sqlalchemy import event, select, case, and_

from app import db


# Contribution Node
class Node(db.Model):
    '''
    https://docs.sqlalchemy.org/en/14/_modules/examples/nested_sets/nested_sets.html
    https://docs.sqlalchemy.org/en/14/orm/self_referential.html#self-referential
    '''
    __tablename__ = 'nodes'
    __mapper_args__ = {
        'batch': False  # allows extension to fire for each instance before going to the next.
    }

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    left = db.Column(db.Integer, nullable=False)
    right = db.Column(db.Integer, nullable=False)

    children = db.relationship('Node',
                               backref=db.backref('parent',
                                                  remote_side=[id],
                                                  lazy='joined'),
                               lazy='select',
                               cascade='all, delete-orphan')

    messages = db.relationship('Message',
                               backref=db.backref('node'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

    engagements = db.relationship('Engagement',
                                  backref=db.backref('node'),
                                  lazy='dynamic',
                                  cascade='all, delete-orphan')

    def nodes_before_inc(self):
        return self.post.nodes.filter(Node.left <= self.left, self.left <= Node.right).order_by(Node.left)

    def nodes_after__inc(self):
        return self.post.nodes.filter(Node.left.between(self.left, self.right)).order_by(Node.left)

    def __repr__(self):
        return f'<n{self.id}{" ROOT" if self.parent is None else ""}>creator={self.creator},post={self.post}</n{self.id}>'


@event.listens_for(Node, 'before_insert')
def before_insert(mapper, connection, node):
    if not node.parent:
        node.left = 1
        node.right = 2
    else:
        nodes_table = mapper.mapped_table
        # need to re-query the database as the state of the parent object might be stale
        right_most_sibling = connection.scalar(
            select([nodes_table.c.right]).where(
                and_(nodes_table.c.id == node.parent_id,
                     nodes_table.c.post_id == node.post_id)))

        connection.execute(
            nodes_table.update(
                and_(nodes_table.c.right >= right_most_sibling,
                     nodes_table.c.post_id == node.post_id)).values(
                left=case(
                    [(nodes_table.c.left > right_most_sibling, nodes_table.c.left + 2)],
                    else_=nodes_table.c.left),
                right=case(
                    [(nodes_table.c.right >= right_most_sibling, nodes_table.c.right + 2)],
                    else_=nodes_table.c.right)
            )
        )
        node.left = right_most_sibling
        node.right = right_most_sibling + 1
