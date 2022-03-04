import uuid
from datetime import datetime

from sqlalchemy import event, select, case, and_, asc, desc
from sqlalchemy.dialects.postgresql import UUID

from app import db
from app.models import Message, Post, Notification


# Contribution Node


class Node(db.Model):
    """
    https://docs.sqlalchemy.org/en/14/_modules/examples/nested_sets/nested_sets.html
    https://docs.sqlalchemy.org/en/14/orm/self_referential.html#self-referential
    """
    __tablename__ = 'nodes'
    __mapper_args__ = {
        'batch': False  # allows extension to fire for each instance before going to the next.
    }

    STATE_CHAT = 2 ** 10
    STATE_REQUESTED = 2 * STATE_CHAT
    STATE_ENGAGED = 2 * STATE_REQUESTED

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    last_updated = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)

    state = db.Column(db.Integer, default=STATE_CHAT, nullable=False)

    creator_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.id'), nullable=False)
    post_id = db.Column(UUID(as_uuid=True), db.ForeignKey('posts.id'), nullable=False)

    # sum of all referrer rewards if an engagement is successful on this node
    # sum_referrer_reward_cent = db.Column(db.Integer, nullable=False)
    value_cent = db.Column(db.Integer, nullable=False)
    answerer_reward_cent = db.Column(db.Integer, nullable=False)
    # the reward to the node creator as a referrer if the node is in a successful referral chain
    referrer_reward_cent = db.Column(db.Integer)

    parent_id = db.Column(UUID(as_uuid=True), db.ForeignKey('nodes.id'))
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

    notifications = db.relationship("Notification",
                                    backref=db.backref('node'),
                                    foreign_keys=[Notification.node_id],
                                    lazy="dynamic",
                                    cascade="all, delete-orphan")

    def display_value(self, user):
        post = self.post
        if user == post.creator:
            return 0.01 * post.price_cent

        if user == self.creator:
            if post.type == Post.TYPE_BUY:
                return 0.01 * self.answerer_reward_cent
            else:
                return 0.01 * self.value_cent

        answerer_reward_cent, sum_referrer_reward_cent, value_cent = self.rewards_for_next_node_cent()
        if post.type == Post.TYPE_BUY:
            return 0.01 * answerer_reward_cent
        else:
            return 0.01 * value_cent

    def display_referrer_reward(self, user):
        post = self.post
        if user == post.creator:
            return 0

        if post.is_private:
            if user == self.creator:
                return 0.01 * self.referrer_reward_cent
            else:
                # TODO: make this (up to) 100% of remaining in power user mode
                return 0.01 * self.remaining_referral_budget_cent
        else:
            return 0.01 * round(0.5 * post.referral_budget_cent)

    def _sum_referrer_reward_inc_cent(self):
        """Sum of all referrer rewards assuming the successful engagement is on the next node"""
        post = self.post
        if post.is_private:
            return self.sum_referrer_reward_cent + self.referrer_reward_cent
        else:
            sum_referrer_reward_cent = 0
            total_referrer_reward_cent_cap = post.referral_budget_cent
            for node in self.nodes_before_inc()[1:]:
                referrer_reward_cent = round(
                    0.5 * (total_referrer_reward_cent_cap - sum_referrer_reward_cent)  # Default is 50% of remaining
                )
                sum_referrer_reward_cent += referrer_reward_cent
            return sum_referrer_reward_cent

    def rewards_for_next_node_cent(self):
        post = self.post
        value_cent = self.value_cent
        answerer_reward_cent = self.answerer_reward_cent
        sum_referrer_reward_cent = self._sum_referrer_reward_inc_cent()
        if post.type == Post.TYPE_BUY:
            if post.is_private:
                answerer_reward_cent -= self.referrer_reward_cent
            else:
                answerer_reward_cent = post.price_cent - post.platform_fee_cent - sum_referrer_reward_cent
        else:
            if post.is_private:
                value_cent += self.referrer_reward_cent
            else:
                value_cent = answerer_reward_cent + post.platform_fee_cent + sum_referrer_reward_cent
        return answerer_reward_cent, sum_referrer_reward_cent, value_cent

    @property
    def value(self):
        return 0.01 * self.value_cent

    @property
    def sum_referrer_reward_cent(self):
        """Sum of all referrer rewards if an engagement is successful on this node"""
        return self.value_cent - self.answerer_reward_cent - self.post.platform_fee_cent

    @property
    def remaining_referral_budget_cent(self):
        """The remaining referral budget AFTER the referral reward for this node is claimed"""
        return self.post.referral_budget_cent - self.sum_referrer_reward_cent - self.referrer_reward_cent

    def ping(self, utcnow):
        self.last_updated = utcnow
        db.session.add(self)
        self.post.ping(utcnow)

    def nodes_before_inc(self):
        return self.post.nodes.filter(Node.left <= self.left, self.left <= Node.right).order_by(Node.left)

    def nodes_after__inc(self):
        return self.post.nodes.filter(Node.left.between(self.left, self.right)).order_by(Node.left)

    def __repr__(self):
        return f'<n{self.id}{" ROOT" if self.parent is None else ""}>' + \
               f'creator={self.creator},post={self.post}</n{self.id}>'

    def messages_ordered(self, order_desc=True):
        return self.messages.order_by((desc if order_desc else asc)(Message.timestamp)).all()


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
