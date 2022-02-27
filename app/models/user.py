import math
import re
import uuid
from datetime import datetime, timedelta

from authlib.jose.errors import BadSignatureError
from flask import current_app
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager
from app.models import SingleUseToken, Node, Post, Engagement, PostTag, Tag, Message, PlatformFee
from app.models.errors import InvalidActionError, RewardDistributionError, InsufficientFundsError
from app.models.payment import PaymentIntent
from utils import security_utils, authlib_ext

_REMEMBER_ME_ID_NBYTES = 8
_TOKEN_SECONDS_TO_EXPIRY = 600
REP_I_DECAY = 0.1
REP_DECAY = REP_I_DECAY / 1000


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    last_seen = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)

    adjective = db.Column(db.String(20))

    total_balance_cent = db.Column(db.Integer, default=0, nullable=False)
    reserved_balance_cent = db.Column(db.Integer, default=0, nullable=False)
    reward_limit_cent = db.Column(db.Integer, default=500, nullable=False)

    sum_x = db.Column(db.Float, default=0.0, nullable=False)
    sum_abs_x = db.Column(db.Float, default=0.0, nullable=False)
    sum_i = db.Column(db.Float, default=0.0, nullable=False)
    sum_abs_i = db.Column(db.Float, default=0.0, nullable=False)

    email = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    signup_method = db.Column(db.String(16), default='email', nullable=False)

    use_markdown = db.Column(db.Boolean, default=False, nullable=False)

    # 16-byte UUID is 32-char hex string
    # length of separator = 1
    # base64 encoding of n bytes = ~1.3 * n, rounded to 1.5 for safety
    remember_me_id = db.Column(db.String(32 + 1 + int(1.5 * _REMEMBER_ME_ID_NBYTES)))

    posts = db.relationship('Post',
                            backref=db.backref('creator'),
                            lazy='dynamic',
                            cascade='all, delete-orphan')

    comments = db.relationship('Comment',
                               backref=db.backref('creator'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

    tags_created = db.relationship('Tag',
                                   backref=db.backref('creator'),
                                   lazy='dynamic',
                                   cascade='all, delete-orphan')

    post_tags_created = db.relationship('PostTag',
                                        backref=db.backref('creator'),
                                        lazy='dynamic',
                                        cascade='all, delete-orphan')

    nodes = db.relationship('Node',
                            backref=db.backref('creator'),
                            lazy='dynamic',
                            cascade='all, delete-orphan')

    messages = db.relationship('Message',
                               backref=db.backref('creator'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')

    engagements_as_asker = db.relationship('Engagement',
                                           backref=db.backref('asker'),
                                           foreign_keys=[Engagement.asker_id],
                                           lazy='dynamic',
                                           cascade='all, delete-orphan')

    engagements_as_answerer = db.relationship('Engagement',
                                              backref=db.backref('answerer'),
                                              foreign_keys=[Engagement.answerer_id],
                                              lazy='dynamic',
                                              cascade='all, delete-orphan')

    engagements_sent = db.relationship('Engagement',
                                       backref=db.backref('sender'),
                                       foreign_keys=[Engagement.sender_id],
                                       lazy='dynamic',
                                       cascade='all, delete-orphan')

    engagements_received = db.relationship('Engagement',
                                           backref=db.backref('receiver'),
                                           foreign_keys=[Engagement.receiver_id],
                                           lazy='dynamic',
                                           cascade='all, delete-orphan')

    payment_intents = db.relationship("PaymentIntent",
                                      backref=db.backref('creator'),
                                      foreign_keys=[PaymentIntent.creator_id],
                                      lazy="dynamic",
                                      cascade="all, delete-orphan")

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def reset_remember_id(self):
        self.remember_me_id = f'{self.id.hex}/{security_utils.random_urlsafe(nbytes=_REMEMBER_ME_ID_NBYTES)}'
        db.session.add(self)
        db.session.commit()

    def get_id(self):
        """For Flask-Login remember-me security, see https://flask-login.readthedocs.io/en/latest/#alternative-tokens"""
        if self.remember_me_id is None:
            self.reset_remember_id()
        return self.remember_me_id

    def generate_token(self, action, site_rid_hash=None, seconds_to_exp=_TOKEN_SECONDS_TO_EXPIRY):
        server_token = SingleUseToken.generate(timedelta_to_expiry=timedelta(seconds=seconds_to_exp))
        return authlib_ext.jws_compact_serialize_timed(
            payload={action: self.id.hex,
                     'server_token': server_token.id.hex,
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
        id_match = user.id.hex == data.get(action)
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

        user = User.query.get(user_id)
        if user is None:
            return False, None
        return User._verify_token_data(user=user,
                                       data=data,
                                       action=action,
                                       site_rid_hash=site_rid_hash), user

    @property
    def balance_available_cent(self):
        return self.total_balance_cent - self.reserved_balance_cent

    @property
    def total_balance(self):
        return 0.01 * self.total_balance_cent

    @property
    def reserved_balance(self):
        return 0.01 * self.reserved_balance_cent

    @property
    def reward_limit(self):
        return 0.01 * self.reward_limit_cent

    @property
    def reputation(self):
        if self.sum_abs_x == 0 or self.sum_abs_i == 0:
            return 1.0
        else:
            return min(self.sum_x / self.sum_abs_x, self.sum_i / self.sum_abs_i)

    @property
    def competence(self):
        return 0.5 * (self.sum_i + self.sum_abs_i) / self.sum_abs_i

    def percentile_rank(self, window_in_days=7):
        min_engagements = 3
        min_users = 5
        if self.sum_abs_i < min_engagements:
            return None
        users = User.query.filter(
            User.last_seen >= datetime.utcnow() - timedelta(days=window_in_days),
            User.sum_abs_i >= min_engagements
        ).all()
        if len(users) < min_users:
            return None
        self_score = self.reputation
        return sum([1 for user in users if user.reputation <= self_score]) / len(users)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def _add_tag(self, post, name):
        tag = Tag.query.get(name.lower())
        if tag is None:
            tag = Tag(id=name.lower(), name=name, creator=self)
            db.session.add(tag)
        post_tag = post.post_tags.filter_by(tag=tag).first()
        if post_tag is None:
            post_tag = PostTag(post=post, tag=tag, creator=self)
            db.session.add(post_tag)
            post.ping(datetime.utcnow())
            return post_tag

    def add_tag(self, post, name):
        if name.lower() not in ('buying', 'selling'):
            post_tag = self._add_tag(post, name)
            if post_tag:
                db.session.commit()
                return post_tag

    def create_post(self, type, reward_cent, title, body='', social_media_mode=False, referral_budget_cent=None):
        title = title.strip()
        body = body.replace('<br>', '')  # remove <br> added by Toast UI
        body = body.replace('\r\n', '\n')  # standardise new lines as '\n'
        body = body.strip()
        # add '\' to hashtag so the '#' is preserved by the Markdown processor:
        body = re.sub(r'(?<!\\)#\w+', lambda x: '\\' + x.group(0), body)
        # usernames = [name[1:] for name in re.findall(r'@\w+', body)]
        tag_names = [name[2:] for name in re.findall(r'\\#\w+', body)]

        if referral_budget_cent is None:
            referral_budget_cent = round(0.4 * reward_cent)  # Default is 40% of the OP reward
        post = Post(creator=self,
                    type=type,
                    reward_cent=reward_cent,
                    social_media_mode=social_media_mode,
                    referral_budget_cent=referral_budget_cent,
                    title=title,
                    body=('m' if self.use_markdown else 's') + body)
        db.session.add(post)

        self._add_tag(post, 'Buying' if type == Post.TYPE_BUY else 'Selling')
        [self._add_tag(post, name) for name in tag_names if name.lower() not in ('buying', 'selling')]

        if social_media_mode:
            node = Node(post=post, creator=self, total_reward_cent=post.reward_cent, referral_reward_cent=0)
        else:
            node = Node(post=post, creator=self, total_reward_cent=post.reward_cent)
        db.session.add(node)
        db.session.commit()

        return post

    def edit_post(self, post, title, body, social_media_mode=None, referral_budget_cent=None):
        title = title.strip()
        body = body.replace('<br>', '')  # remove <br> added by Toast UI
        body = body.replace('\r\n', '\n')  # standardise new lines as '\n'
        body = body.strip()
        # add '\' to hashtag so the '#' is preserved by the Markdown processor:
        body = re.sub(r'(?<!\\)#\w+', lambda x: '\\' + x.group(0), body)
        # usernames = [name[1:] for name in re.findall(r'@\w+', body)]
        tag_names = [name[2:] for name in re.findall(r'\\#\w+', body)]

        post.title = title
        post.body = ('m' if self.use_markdown else 's') + body
        if social_media_mode is not None:
            post.social_media_mode = social_media_mode
        if referral_budget_cent is not None:
            post.referral_budget_cent = referral_budget_cent
        post.ping(datetime.utcnow())
        db.session.add(post)

        # reset all post tags
        [db.session.delete(post_tag) for post_tag in post.post_tags]
        self._add_tag(post, 'Buying' if post.type == Post.TYPE_BUY else 'Selling')
        [self._add_tag(post, name) for name in tag_names if name.lower() not in ('buying', 'selling')]

        db.session.commit()

    def toggle_archive(self, post):
        if self != post.creator:
            raise InvalidActionError(
                'Cannot change the archive status of the post because the user is not the post creator.')
        if post.is_reported:
            raise InvalidActionError('Cannot change the archive status of the post because the post is reported.')
        post.is_archived = not post.is_archived
        post.ping(datetime.utcnow())
        db.session.add(post)
        db.session.commit()

    def report(self, post, reason):
        post.is_reported = True
        post.report_reason = f'{self}: {reason}\n' + post.report_reason
        post.is_archived = True
        post.ping(datetime.utcnow())
        db.session.add(post)
        db.session.commit()

    def create_node(self, parent_node, referral_reward_cent=None):
        post = parent_node.post
        if post.is_archived:
            raise InvalidActionError('Cannot create node because the post is archived')
        if self == post.creator:
            raise InvalidActionError('Cannot create node because the user is the post creator')
        node = None
        if self == parent_node.creator:  # try some heuristics to reduce the cost of querying the database
            node = parent_node
        if node is None:
            # check if a node exists already as 2 nodes with the same creator is not allowed
            # TODO: consider if it makes sense to make it more strict by raising an error if a node is found
            node = post.nodes.filter_by(creator=self).first()

        if node is None:
            node = self._create_node(parent=parent_node, referral_reward_cent=referral_reward_cent)
            db.session.add(node)
            post.ping(datetime.utcnow())
            db.session.commit()
        return node

    def _create_node(self, parent, referral_reward_cent=None):
        post = parent.post
        total_reward_cent = parent.total_reward_cent
        if post.social_media_mode:
            if referral_reward_cent is None:
                # Default is 50% of the remaining referral budget:
                referral_reward_cent = round(0.5 * parent.remaining_referral_budget_cent)
            else:
                if referral_reward_cent > parent.remaining_referral_budget_cent:
                    raise InvalidActionError(
                        'Cannot create node because referral reward exceeds the remaining referral budget')
            if post.type == Post.TYPE_SELL:
                total_reward_cent += parent.referral_reward_cent

        node = Node(creator=self,
                    post=parent.post,
                    parent=parent,
                    total_reward_cent=total_reward_cent,
                    referral_reward_cent=referral_reward_cent)
        return node

    def create_message(self, node, text):
        if self != node.creator and self != node.post.creator:
            raise InvalidActionError(
                'Cannot create node message because the user is not the post creator or the node creator'
            )
        engagement = node.engagements.filter(Engagement.state == Engagement.STATE_ENGAGED).first()
        if engagement is None and node.post.is_archived:
            raise InvalidActionError('Cannot create message because the post is archived')
        message = Message(creator=self, node=node, engagement=engagement, text=text)
        db.session.add(message)
        if engagement is not None:
            engagement.ping(datetime.utcnow())
        else:
            node.ping(datetime.utcnow())
        db.session.commit()
        return message

    def create_payment_intent(self, stripe_session_id, stripe_payment_intent_id):
        payment_intent = PaymentIntent(
            creator=self,
            stripe_session_id=stripe_session_id,
            stripe_payment_intent_id=stripe_payment_intent_id
        )
        db.session.add(payment_intent)
        db.session.commit()
        return payment_intent

    # TODO: think whether this is the best place to ask to share reward, alternative place would be when the answerer
    # rates the engagement
    def create_engagement(self, node):
        post = node.post
        if post.is_archived:
            raise InvalidActionError('Cannot create engagement because the post is archived')
        if self != node.creator:
            raise InvalidActionError('Cannot create engagement because the user is not the node creator')
        if self == post.creator:
            raise InvalidActionError('Cannot create engagement because the user cannot be the post creator')
        if node.state != Node.STATE_CHAT:
            raise InvalidActionError('Cannot create engagement because an uncompleted engagement already exists')
        if self.reward_limit_cent < node.total_reward_cent:
            raise InvalidActionError(
                'Cannot create engagement because the post reward exceeds the reward limit of the user')
        if post.type == Post.TYPE_SELL and self.balance_available_cent < node.total_reward_cent:
            raise InsufficientFundsError('Cannot create engagement as buyer due to insufficient funds')

        if post.type == Post.TYPE_BUY:
            engagement = Engagement(node=node, sender=self, receiver=post.creator,
                                    asker=post.creator, answerer=self)
        else:
            engagement = Engagement(node=node, sender=self, receiver=post.creator,
                                    asker=self, answerer=post.creator)
            self.reserved_balance_cent += node.total_reward_cent
            db.session.add(self)
        db.session.add(engagement)

        message = Message(creator=self, node=node, type=Message.TYPE_REQUEST, text=f'Engagement requested')
        db.session.add(message)

        node.state = Node.STATE_REQUESTED
        node.ping(datetime.utcnow())
        db.session.commit()

        return engagement

    def cancel_engagement(self, engagement):
        node = engagement.node
        post = node.post
        if post.is_archived:
            raise InvalidActionError('Cannot cancel engagement because the post is archived')
        if self != node.creator:
            raise InvalidActionError('Cannot cancel engagement because the user is not the node creator')
        if engagement.state != Engagement.STATE_REQUESTED:
            raise InvalidActionError('Cannot cancel engagement because the engagement is not requested')

        engagement.state = Engagement.STATE_CANCELLED
        engagement.ping(datetime.utcnow())
        db.session.add(engagement)

        if post.type == Post.TYPE_SELL:
            self.reserved_balance_cent -= node.total_reward_cent
            db.session.add(self)

        message = Message(creator=self,
                          node=node,
                          engagement=engagement,
                          type=Message.TYPE_CANCEL,
                          text=f'Engagement cancelled')
        db.session.add(message)

        node.state = Node.STATE_CHAT
        node.ping(datetime.utcnow())

        db.session.commit()

    def accept_engagement(self, engagement):
        node = engagement.node
        post = node.post
        if post.is_archived:
            raise InvalidActionError('Cannot accept engagement because the post is archived')
        if engagement.state != Engagement.STATE_REQUESTED:
            raise InvalidActionError('Cannot accept engagement because it is not in requested state')
        if self != post.creator:
            raise InvalidActionError('Cannot accept engagement because the user is not the post creator')
        if self.reward_limit_cent < node.total_reward_cent:
            raise InvalidActionError(
                'Cannot accept engagement because the post reward exceeds the reward limit of the user')
        if post.type == Post.TYPE_BUY and self.balance_available_cent < node.total_reward_cent:
            raise InsufficientFundsError('Cannot accept engagement as buyer due to insufficient funds')

        if post.type == Post.TYPE_BUY:
            self.reserved_balance_cent += node.total_reward_cent
            db.session.add(self)

        engagement.state = Engagement.STATE_ENGAGED
        engagement.ping(datetime.utcnow())
        db.session.add(engagement)
        message = Message(creator=self,
                          node=node,
                          engagement=engagement,
                          type=Message.TYPE_ACCEPT,
                          text=f'Engagement accepted')
        db.session.add(message)

        node.state = Node.STATE_ENGAGED
        node.ping(datetime.utcnow())

        db.session.commit()

    def rate_engagement(self, engagement, is_success):
        node = engagement.node
        asker = engagement.asker
        answerer = engagement.answerer

        # if node.total_reward_cent > self.reward_limit_cent:
        #     raise InvalidActionError(
        #         'Cannot rate engagement as successful because the post reward exceeds the reward limit of the user')

        if engagement.state != Engagement.STATE_ENGAGED:
            raise InvalidActionError('Cannot rate engagement because it is not in engaged state')

        if self != asker and self != answerer:
            raise InvalidActionError('Cannot rate engagement because the user is not the asker or the answerer')

        if self == asker:
            engagement.rating_by_asker = 1 if is_success else -1
        elif self == answerer:
            engagement.rating_by_answerer = 1 if is_success else -1

        engagement.ping(datetime.utcnow())
        db.session.add(engagement)

        message = Message(creator=self,
                          node=node,
                          engagement=engagement,
                          type=Message.TYPE_RATE,
                          text=f'Engagement rated {"+" if is_success else "-"}')
        db.session.add(message)

        if engagement.rating_by_asker != 0 and engagement.rating_by_answerer != 0:
            self._finalise_engagement(engagement)
        db.session.commit()

    def _finalise_engagement(self, engagement):
        if engagement.rating_by_asker == engagement.rating_by_answerer == 1:
            self._handle_success(engagement)
        elif engagement.rating_by_asker == -1 and engagement.rating_by_answerer == 1:
            self._handle_dispute(engagement)
        elif engagement.rating_by_asker == 1 and engagement.rating_by_answerer == -1:
            self._handle_success(engagement, fraction=0.5)  # Default fraction is 50% in this scenario
        else:
            node = engagement.node
            asker = engagement.asker
            asker.reserved_balance_cent -= node.total_reward_cent
            db.session.add(asker)
            message = Message(creator=self,
                              node=node,
                              type=Message.TYPE_COMPLETE,
                              text=f'Engagement unsuccessful - no reward will be distributed')
            db.session.add(message)

        engagement.state = Engagement.STATE_COMPLETED
        engagement.node.state = Node.STATE_CHAT

    def _handle_success(self, engagement, fraction=1.0):
        node = engagement.node
        asker = engagement.asker
        answerer = engagement.answerer

        total_reward_cent = _distribute_reward_cent(node=node, fraction=fraction)

        asker.update_reputation(total_reward_cent, success=True, dispute_lost=False)
        answerer.update_reputation(total_reward_cent, success=True, dispute_lost=False)

        db.session.add(asker)
        db.session.add(answerer)

        message = Message(creator=self,
                          node=node,
                          type=Message.TYPE_COMPLETE,
                          text=f'Engagement successful - reward has been distributed')
        db.session.add(message)

    def _handle_dispute(self, engagement):
        node = engagement.node
        asker = engagement.asker
        answerer = engagement.answerer

        total_reward_cent = node.total_reward_cent
        asker.reserved_balance_cent -= total_reward_cent

        rx_asker, ri_asker = asker.reputation_if_dispute_lost(total_reward_cent)
        rx_answerer, ri_answerer = answerer.reputation_if_dispute_lost(total_reward_cent)

        # 3-D lexical ordering by (min(rx, ri), rx, ri)
        if min(rx_asker, ri_asker) < min(rx_answerer, ri_answerer) or \
                (
                        min(rx_asker, ri_asker) == min(rx_answerer, ri_answerer) and \
                        rx_asker < rx_answerer
                ) or \
                (
                        min(rx_asker, ri_asker) == min(rx_answerer, ri_answerer) and \
                        rx_asker == rx_answerer and \
                        ri_asker < ri_answerer
                ):
            # asker lost:
            asker.update_reputation(total_reward_cent, success=False, dispute_lost=True)
            answerer.update_reputation(total_reward_cent, success=False, dispute_lost=False)
        elif min(rx_asker, ri_asker) > min(rx_answerer, ri_answerer) or \
                (
                        min(rx_asker, ri_asker) == min(rx_answerer, ri_answerer) and \
                        rx_asker > rx_answerer
                ) or \
                (
                        min(rx_asker, ri_asker) == min(rx_answerer, ri_answerer) and \
                        rx_asker == rx_answerer and \
                        ri_asker > ri_answerer
                ):  # answerer lost:
            asker.update_reputation(total_reward_cent, success=False, dispute_lost=False)
            answerer.update_reputation(total_reward_cent, success=False, dispute_lost=True)
        else:  # it is a draw, punishment both
            # TODO: consider reducing the reputation of both to prevent users intentionally decaying bad history
            # currently this is deemed unnecessary as it should be very rare to have exactly the same reputation
            asker.update_reputation(total_reward_cent, success=False, dispute_lost=True)
            answerer.update_reputation(total_reward_cent, success=False, dispute_lost=True)

        db.session.add(asker)
        db.session.add(answerer)

        message = Message(creator=self,
                          node=node,
                          type=Message.TYPE_COMPLETE,
                          text=f'Engagement outcome disputed - no reward will be distributed')
        db.session.add(message)

    def reputation_if_dispute_lost(self, total_reward_cent):
        m_x = math.exp(-abs(total_reward_cent) * REP_DECAY)
        sum_x = -total_reward_cent + m_x * self.sum_x
        sum_abs_x = abs(total_reward_cent) + m_x * self.sum_abs_x

        m_i = math.exp(-REP_I_DECAY)
        sum_i = -1 + m_i * self.sum_i
        sum_abs_i = 1 + m_i * self.sum_abs_i

        return sum_x / sum_abs_x, sum_i / sum_abs_i

    def update_reward_limit(self, total_reward_cent, success, dispute_lost):
        if success:
            r = self.reputation
            if r > 0.8:
                self.reward_limit_cent = min(1000, self.reward_limit_cent + round(0.5 * total_reward_cent))
            elif r > 0.6:
                self.reward_limit_cent = min(1000, self.reward_limit_cent + round(0.4 * total_reward_cent))
            elif r > 0.4:
                self.reward_limit_cent = min(1000, self.reward_limit_cent + round(0.3 * total_reward_cent))
            elif r > 0.2:
                self.reward_limit_cent = min(1000, self.reward_limit_cent + round(0.2 * total_reward_cent))
            elif r > 0:
                self.reward_limit_cent = min(1000, self.reward_limit_cent + round(0.1 * total_reward_cent))
            else:
                self.reward_limit_cent = min(1000, self.reward_limit_cent + round(0.05 * total_reward_cent))

        if dispute_lost:
            r = self.reputation
            if r > 0.5:
                self.reward_limit_cent = max(100, round(0.75 * self.reward_limit_cent))
            elif r > 0:
                self.reward_limit_cent = max(100, round(0.5 * self.reward_limit_cent))
            elif r > -0.5:
                self.reward_limit_cent = max(
                    100,
                    round(min(0.5 * self.reward_limit_cent, 0.75 * total_reward_cent))
                )
            else:
                self.reward_limit_cent = max(100, round(0.5 * total_reward_cent))

    def update_reputation(self, total_reward_cent, success, dispute_lost):
        """
        The visible reputation is only affected if the interaction is a success or if the user lose a dispute.
        This is to protect the side with a higher reputation - his visible reputation is not affected but the
        internal components of his reputation are weakened due to decay, and he will be in a weaker position in
        the next dispute unless he starts to build a good track record
        """
        #  decay the weights of past observations in ALL cases:
        m_x = math.exp(-abs(total_reward_cent) * REP_DECAY)
        self.sum_x *= m_x
        self.sum_abs_x *= m_x

        m_i = math.exp(-REP_I_DECAY)
        self.sum_i *= m_i
        self.sum_abs_i *= m_i

        # add most recent observation only if it is a success or dispute lost
        if success or dispute_lost:
            self.sum_x += total_reward_cent if success else -total_reward_cent
            self.sum_abs_x += abs(total_reward_cent)
            self.sum_i += 1 if success else -1
            self.sum_abs_i += 1

        self.update_reward_limit(total_reward_cent, success, dispute_lost)


def _distribute_reward_cent(node, fraction):
    post = node.post
    if post.type == Post.TYPE_BUY:
        buyer = post.creator
        seller = node.creator
    else:
        buyer = node.creator
        seller = post.creator

    # fully release what has been reserved for this engagement but only deduct the fraction from the actual balance:
    total_reward_cent = node.total_reward_cent
    buyer.reserved_balance_cent -= total_reward_cent
    total_reward_cent = round(fraction * total_reward_cent)
    buyer.total_balance_cent -= total_reward_cent
    db.session.add(buyer)

    platform_fee_cent = round(0.1 * fraction * post.reward_cent)  # Default platform fee = 10% of OP reward
    platform_fee = PlatformFee(amount_cent=platform_fee_cent)
    db.session.add(platform_fee)

    total_referrer_reward_cent = 0
    if post.social_media_mode:
        nodes = node.nodes_before_inc().all()
        referrer_nodes = nodes[1:(len(nodes) - 1)]
        for node in referrer_nodes:
            referrer = node.creator
            referrer_reward_cent = round(fraction * node.referral_reward_cent)
            referrer.total_balance_cent += referrer_reward_cent
            db.session.add(referrer)
            total_referrer_reward_cent += referrer_reward_cent
    else:
        nodes = node.nodes_before_inc().all()  # all nodes including buyers and sellers
        referrer_nodes = nodes[1:(len(nodes) - 1)]  # referrers only
        if len(nodes) == 1:  # there is only OP's node - should never reach here
            raise RewardDistributionError('Cannot distribute reward from the root node')
        # Default total referral cap = 20% of OP reward:
        total_referrer_reward_cent_cap = round(0.2 * fraction * post.reward_cent)
        referrer_nodes.reverse()
        for referrer_node in referrer_nodes:
            referrer = referrer_node.creator
            # Default strategy is to distribute 50% of remaining at each node in the chain:
            referrer_reward_cent = round(
                0.5 * (total_referrer_reward_cent_cap - total_referrer_reward_cent)
            )
            referrer.total_balance_cent += referrer_reward_cent
            db.session.add(referrer)
            total_referrer_reward_cent += referrer_reward_cent

    # the seller gets everything left
    seller.total_balance_cent += total_reward_cent - platform_fee_cent - total_referrer_reward_cent
    db.session.add(seller)

    return total_reward_cent


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(remember_me_id=user_id).first()
