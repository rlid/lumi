from datetime import datetime

from sqlalchemy import event, select, case, and_

from app import db

STATUS_OPEN = 0


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

    STATE_CLOSED = 0
    STATE_OPEN = 1
    STATE_ENGAGEMENT_REQUESTED = 2
    STATE_ENGAGED = 3
    STATE_ENGAGEMENT_COMPLETED = 4

    DEFAULT_REWARD_SHARE = 0.1

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    state = db.Column(db.Integer, default=STATE_OPEN)
    rating_by_asker = db.Column(db.Integer, default=0)
    rating_by_answerer = db.Column(db.Integer, default=0)
    reward_share = db.Column(db.Float, default=DEFAULT_REWARD_SHARE)

    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    quest_id = db.Column(db.Integer, db.ForeignKey('quests.id'), nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey('nodes.id'))
    left = db.Column(db.Integer, nullable=False)
    right = db.Column(db.Integer, nullable=False)

    children = db.relationship('Node',
                               backref=db.backref('parent',
                                                  remote_side=[id],
                                                  lazy='joined'),
                               lazy='select',
                               cascade='all, delete-orphan')

    def nodes_before_inc(self):
        return self.quest.nodes.filter(Node.left <= self.left, self.left <= Node.right).order_by(Node.left)

    def nodes_after__inc(self):
        return self.quest.nodes.filter(Node.left.between(self.left, self.right)).order_by(Node.left)

    def __repr__(self):
        return f'<Node[{self.id}]:{self.quest_id}/{self.left}-{self.right}>'

    @staticmethod
    def make(creator, quest, parent=None):
        node = Node(creator=creator, quest=quest, parent=parent)
        db.session.add(node)
        db.session.commit()
        return node


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
                     nodes_table.c.quest_id == node.quest_id)))

        connection.execute(
            nodes_table.update(
                and_(nodes_table.c.right >= right_most_sibling,
                     nodes_table.c.quest_id == node.quest_id)).values(
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
