import math
from datetime import datetime, timedelta

from authlib.jose.errors import BadSignatureError
from flask import current_app
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager
from app.models.quest import Quest
from app.models.node import Node
from app.models.single_use_token import SingleUseToken
from app.models.errors import InvalidActionError, RewardDistributionError
from utils import security_utils, authlib_ext

_REMEMBER_ME_ID_NBYTES = 32
_TOKEN_SECONDS_TO_EXPIRY = 600
_REP_DECAY = 0.0


def _distribute_reward(node, amount):
    nodes = node.nodes_before_inc().all()
    referral_nodes = nodes[1:(len(nodes) - 1)]

    if len(nodes) == 1:
        raise RewardDistributionError('Cannot distribute reward from the asker node')

    # if the answerer node is directly connected to the asker node or if the answerer does not share:
    if len(referral_nodes) == 0 or node.reward_share == 0:
        # reward for answerer
        node.creator.account_balance += amount
        db.session.add(node.creator)
    else:  # there is at least 1 referer and reward share is not 0:
        remaining_amount = amount
        answerer_reward = int((1.0 - node.reward_share) * remaining_amount)
        node.creator.account_balance += answerer_reward
        db.session.add(node.creator)

        remaining_amount -= answerer_reward
        i = len(referral_nodes)
        while i > 0:
            i = i - 1
            referer_reward = int(0.5 * remaining_amount)
            referral_nodes[i].creator.account_balance += referer_reward
            db.session.add(referral_nodes[i].creator)
            remaining_amount -= referer_reward
        #  the initial referer gets all remaining amount
        referral_nodes[i].creator.account_balance += remaining_amount


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)

    account_balance = db.Column(db.Integer, nullable=False, default=0)
    committed_amount = db.Column(db.Integer, nullable=False, default=0)

    sum_value = db.Column(db.Float, default=0.0)
    sum_abs_value = db.Column(db.Float, default=0.0)
    sum_one = db.Column(db.Float, default=0.0)
    sum_abs_one = db.Column(db.Float, default=0.0)

    email = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    email_verified = db.Column(db.Boolean, default=False)
    signup_method = db.Column(db.String(16), default='email')

    # length of str(unsigned 64-bit integer) = 20
    # length of separator = 1
    # base64 encoding of n bytes = ~1.3 * n, rounded to 1.5 for safety
    remember_me_id = db.Column(db.String(21 + int(1.5 * _REMEMBER_ME_ID_NBYTES)))

    quest_created = db.relationship('Quest',
                                    foreign_keys=[Quest.creator_id],
                                    backref=db.backref('creator', lazy='subquery'),
                                    lazy='dynamic',
                                    cascade='all, delete-orphan')

    nodes_created = db.relationship('Node',
                                    foreign_keys=[Node.creator_id],
                                    backref=db.backref('creator', lazy='joined'),
                                    lazy='dynamic',
                                    cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User[{self.id}]:email={self.email}>'

    def __str__(self):
        return f'User(email={self.email}, signup_method={self.signup_method}, email_verified={self.email_verified}, ' \
               f'account_balance={self.account_balance}, committed_amount={self.committed_amount}, ' \
               f'sum_value={self.sum_value}, sum_abs_value={self.sum_abs_value}, ' \
               f'sum_one={self.sum_one}, sum_abs_one={self.sum_abs_one})'

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def reset_remember_id(self):
        self.remember_me_id = f'{self.id}/{security_utils.random_urlsafe(nbytes=_REMEMBER_ME_ID_NBYTES)}'
        db.session.add(self)
        db.session.commit()

    def get_id(self):
        '''For Flask-Login remember-me security, see https://flask-login.readthedocs.io/en/latest/#alternative-tokens'''
        if self.remember_me_id is None:
            self.reset_remember_id()
        return self.remember_me_id

    def generate_token(self, action, site_rid_hash=None, seconds_to_exp=_TOKEN_SECONDS_TO_EXPIRY):
        server_token = SingleUseToken.generate(timedelta_to_expiry=timedelta(seconds=seconds_to_exp))
        return authlib_ext.jws_compact_serialize_timed(
            payload={action: self.id,
                     'server_token': server_token.code,
                     'site_rid_hash': site_rid_hash},
            key=current_app.config['SECRET_KEY'],
            seconds_to_exp=seconds_to_exp
        )

    @staticmethod
    def _decode_token(token):
        try:
            payload = authlib_ext.jws_compact_deserialize_timed(token, current_app.config['SECRET_KEY'])
        except BadSignatureError:
            payload = dict()
        return payload

    @staticmethod
    def _verify_token_data(user, data, action, site_rid_hash=None):
        id_match = user.id == data.get(action)
        server_token_is_valid = SingleUseToken.validate(data.get('server_token'))
        site_rid_match = site_rid_hash == data.get('site_rid_hash')

        return id_match and server_token_is_valid and site_rid_match

    def verify_token(self, token, action, site_rid_hash=None):
        data = User._decode_token(token)
        if not data:
            return False

        return User._verify_token_data(user=self,
                                       data=data,
                                       action=action,
                                       site_rid_hash=site_rid_hash)

    @staticmethod
    def verify_token_static(token, action, site_rid_hash=None):
        data = User._decode_token(token)
        if not data:
            return False, None

        user_id = data.get(action)
        if user_id is None:
            return False, None

        user = User.query.get(int(user_id))
        if user is None:
            return False, None
        return User._verify_token_data(user=user,
                                       data=data,
                                       action=action,
                                       site_rid_hash=site_rid_hash), user

    def create_quest(self, value, title, body=None):
        return Quest.make(creator=self, value=value, title=title, body=body)

    def create_node(self, quest, parent=None):
        node = quest.nodes.filter_by(creator=self).first()
        if node is None:
            if parent is None:
                # if no parent node, add the node to the root node (created by the quest creator) directly
                # TODO: make it more efficient to get the root node
                parent = quest.nodes.filter_by(creator=quest.creator).first()
            node = Node.make(creator=self, quest=quest, parent=parent)
        return node

    # TODO: think whether this is the best place to ask to share reward, alternative place would be when the answerer
    # rates the engagement
    def request_engagement(self, node, reward_share):
        if self == node.quest.creator:
            raise InvalidActionError('Cannot request engagement because the user cannot be the asker')
        if self != node.creator:
            raise InvalidActionError('Cannot request engagement because the user is not the answerer')
        node.state = Node.STATE_ENGAGEMENT_REQUESTED
        node.reward_share = reward_share
        db.session.add(node)
        db.session.commit()

    def accept_engagement(self, node):
        if node.state != Node.STATE_ENGAGEMENT_REQUESTED:
            raise InvalidActionError('Cannot accept engagement because engagement has not been requested')
        if self != node.quest.creator:
            raise InvalidActionError('Cannot accept engagement because the user is not the asker')
        if self.account_balance - self.committed_amount < node.quest.value:
            raise InvalidActionError('Cannot accept engagement due to insufficient funds')
        self.committed_amount = self.committed_amount + node.quest.value
        db.session.add(self)
        node.state = Node.STATE_ENGAGED
        db.session.add(node)
        db.session.commit()

    @property
    def reputation(self):
        return min(self.sum_value / self.sum_abs_value, self.sum_one / self.sum_abs_one)

    @property
    def competence(self):
        return 0.5 * (self.sum_one + self.sum_abs_one) / self.sum_abs_one

    def reputation_if_dispute_lost(self, x):
        m = math.exp(-math.fabs(x) * _REP_DECAY)
        s = -x + m * self.sum_value
        s_abs = math.fabs(x) + m * self.sum_abs_value

        m1 = math.exp(-_REP_DECAY)
        s1 = -1 + m1 * self.sum_one
        s1_abs = 1 + m1 * self.sum_abs_one

        return min(s / s_abs, s1 / s1_abs)

    def update_reputation(self, x, success, dispute_lost):
        '''
        The visible reputation is only affected if the interaction is a success or if the user lose a dispute.
        This is to protect the side with a higher reputation - his visible reputation is not affected but the
        internal components of his reputation are weakened due to decay, and he will be in a weaker position in
        the next dispute unless he starts to build a good track record
        '''
        #  decay the weights of past observations in ALL cases:
        m = math.exp(-math.fabs(x) * _REP_DECAY)
        self.sum_value *= m
        self.sum_abs_value *= m

        m1 = math.exp(-_REP_DECAY)
        self.sum_one *= m1
        self.sum_abs_one *= m1

        # add most recent observation only if it is a success or dispute lost
        if success or dispute_lost:
            self.sum_value += x if success else -x
            self.sum_abs_value += math.fabs(x)
            self.sum_one += 1 if success else -1
            self.sum_abs_one += 1

    def rate_engagement(self, node, success):
        if node.state != Node.STATE_ENGAGED:
            raise InvalidActionError('Cannot rate engagement because the node is not engaged')
        asker = node.quest.creator
        answerer = node.creator
        if self == asker:
            node.rating_by_asker = 1 if success else -1
            db.session.add(node)
        elif self == answerer:
            node.rating_by_answerer = 1 if success else -1
            db.session.add(node)
        else:
            raise InvalidActionError('Cannot rate engagement because the user is not the asker or answerer')

        if node.rating_by_asker == 0 or node.rating_by_answerer == 0:
            db.session.commit()
            return

        quest_value = node.quest.value
        if node.rating_by_asker == node.rating_by_answerer == 1:
            asker.committed_amount -= quest_value
            asker.account_balance -= quest_value
            _distribute_reward(node=node, amount=quest_value)

            asker.update_reputation(quest_value, success=True, dispute_lost=False)
            answerer.update_reputation(quest_value, success=True, dispute_lost=False)

        if node.rating_by_asker == -1 and node.rating_by_answerer == 1:
            asker.committed_amount -= quest_value

            asker_rep_if_dispute = asker.reputation_if_dispute_lost(quest_value)
            answerer_rep_if_dispute = answerer.reputation_if_dispute_lost(quest_value)

            if asker_rep_if_dispute < answerer_rep_if_dispute:  # asker lost:
                asker.update_reputation(quest_value, success=False, dispute_lost=True)
                answerer.update_reputation(quest_value, success=False, dispute_lost=False)
            elif asker_rep_if_dispute > answerer_rep_if_dispute:  # answerer lost:
                asker.update_reputation(quest_value, success=False, dispute_lost=False)
                answerer.update_reputation(quest_value, success=False, dispute_lost=True)
            else:  # it is a draw, no punishment
                # TODO: consider reducing the reputation of both to prevent users intentionally decaying bad history
                # currently this is deemed unnecessary as it should be very rare to have exactly the same reputation
                asker.update_reputation(quest_value, success=False, dispute_lost=False)
                answerer.update_reputation(quest_value, success=False, dispute_lost=False)

        if node.rating_by_asker == -1 and node.rating_by_answerer == -1:
            asker.committed_amount -= quest_value

        node.state = Node.STATE_ENGAGEMENT_COMPLETED
        db.session.add(node)
        db.session.add(asker)
        db.session.add(answerer)
        db.session.commit()


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(remember_me_id=user_id).first()
