import math
import re
import secrets
import statistics
import string
import uuid
from datetime import datetime, timedelta

from authlib.jose.errors import BadSignatureError
from flask import current_app
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import UUID
from werkzeug.security import generate_password_hash, check_password_hash

from app import db, login_manager
from app.models import SingleUseToken, Node, Post, Engagement, PostTag, Tag, Message, Notification, \
    Feedback, Transaction
from app.models.errors import InvalidActionError, RewardDistributionError, InsufficientFundsError
from app.models.payment import PaymentIntent
from app.v3.models import Rating
from utils import security_utils, authlib_ext

_SHORT_CODE_LENGTH = 4
_REMEMBER_ME_ID_NBYTES = 8
_TOKEN_SECONDS_TO_EXPIRY = 600

REP_I_DECAY = 0.1
AGREE_DECAY = 0.6
# normalise to $10 (1000c), i.e. counter metric and value metric would be equivalent if every engagement is $10
REP_DECAY = REP_I_DECAY / 1000


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    DEFAULT_VALUE_LIMIT = 10  # $10

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    last_seen = db.Column(db.DateTime, index=True, default=datetime.utcnow, nullable=False)
    is_online = db.Column(db.Boolean, default=False, nullable=False)

    adjective = db.Column(db.String(20))

    total_balance_cent = db.Column(db.Integer, default=0, nullable=False)
    reserved_balance_cent = db.Column(db.Integer, default=0, nullable=False)
    value_limit_cent = db.Column(db.Integer, default=100 * DEFAULT_VALUE_LIMIT, nullable=False)

    sum_x = db.Column(db.Float, default=0.0, nullable=False)
    sum_abs_x = db.Column(db.Float, default=0.0, nullable=False)
    sum_i = db.Column(db.Float, default=0.0, nullable=False)
    sum_abs_i = db.Column(db.Float, default=0.0, nullable=False)

    short_code = db.Column(db.String(16), index=True, unique=True)
    email = db.Column(db.String(64), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    signup_method = db.Column(db.String(16), default='email', nullable=False)

    # 16-byte UUID is 32-char hex string
    # length of separator = 1
    # base64 encoding of n bytes = ~1.3 * n, rounded to 1.5 for safety
    remember_me_id = db.Column(db.String(32 + 1 + int(1.5 * _REMEMBER_ME_ID_NBYTES)))

    state_agree = db.Column(db.Float)
    p_agree = db.Column(db.Float, default=0.5)

    ratings = db.relationship('Rating',
                              backref=db.backref('creator'),
                              lazy='dynamic',
                              cascade='all, delete-orphan')

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

    notifications = db.relationship("Notification",
                                    backref=db.backref('target_user'),
                                    foreign_keys=[Notification.target_user_id],
                                    lazy="dynamic",
                                    cascade="all, delete-orphan")

    transactions = db.relationship("Transaction",
                                   backref=db.backref('user'),
                                   foreign_keys=[Transaction.user_id],
                                   lazy="dynamic",
                                   cascade="all, delete-orphan")

    def p_agree_if_lost(self, lost_rating, m_i):
        ps = [rating.s_agree /
              (rating.s_agree + rating.s_disagree + (1 / m_i if rating == lost_rating else 0))
              for rating in self.ratings]
        r_min = min(ps)
        r_median = statistics.median(ps)
        return math.sqrt(r_min * r_median)

    def rate_product(self, product, score, review=None):
        rating = product.ratings.filter_by(creator=self).first()
        if rating is None:
            m_i = math.exp(-AGREE_DECAY * self.p_agree)
            for other_rating in product.ratings:
                # p_agree_before_update = None
                update_other_user = False
                if (other_rating.score == 2 and score > 0) or (other_rating.score == -2 and score < 0):
                    # ratings agree -> increment the other user's agreeability
                    other_rating.s_agree = 1 + m_i * other_rating.s_agree
                    other_rating.s_disagree *= m_i
                    update_other_user = True
                    db.session.add(other_rating)
                if (other_rating.score == 2 and score < 0) or (other_rating.score == -2 and score > 0):
                    # other_rating disagrees -> compare agreeability and update agreeability accordingly
                    other_user = other_rating.creator
                    if other_user.p_agree_if_lost(lost_rating=other_rating, m_i=m_i) <= self.p_agree:
                        # other_user loses -> increment the other user's disagreeability
                        other_rating.s_agree *= m_i
                        other_rating.s_disagree = 1 + m_i * other_rating.s_disagree
                        update_other_user = True
                    else:
                        # other_user wins -> keep their agreeability, decay its strength
                        other_rating.s_agree *= m_i
                        other_rating.s_disagree *= m_i
                    db.session.add(other_rating)

                # time to update user agreeability
                if update_other_user:  # TODO: maybe take the current rating agreeability as user agreeability if it's the same as the last updated rating for the user, otherwise take min(rating agreeability, user agreeability) in which case user agreeability is from another rating
                    other_user = other_rating.creator
                    ps = [rating.s_agree / (rating.s_agree + rating.s_disagree) for rating in other_user.ratings]
                    r_min = min(ps)
                    r_median = statistics.median(ps)
                    other_user.p_agree = math.sqrt(r_min * r_median)
                    db.session.add(other_user)

            rating = Rating(creator=self, product=product, score=score, review=review)
            db.session.add(rating)
        else:
            current_app.logger.warning(f'{product} is already rated by {self}.')

    @staticmethod
    def generate_short_code():
        short_codes = [short_code for short_code, in db.session.query(User.short_code).all()]
        short_code = None
        while short_code is None or short_code in short_codes:
            short_code = ''.join(
                secrets.choice(
                    string.ascii_letters if i % 2 == 0 else string.digits
                ) for i in range(_SHORT_CODE_LENGTH)
            )
        return short_code

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
        db.session.flush()
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
    def num_unread_notifications(self):
        return self.notifications.filter(Notification.is_read.is_not(True)).count()

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
    def value_limit(self):
        return 0.01 * self.value_limit_cent

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
        if name.lower() not in ('asking', 'answering'):
            post_tag = self._add_tag(post, name)
            if post_tag:
                db.session.commit()
                return post_tag

    def create_post(self, is_asking, price_cent, title, topic=0, body='', is_private=False, referral_budget_cent=None,
                    use_markdown=False):
        title = title.strip()
        body = body.replace('<br>', '')  # remove <br> added by Toast UI
        body = body.replace('\r\n', '\n')  # standardise new lines as '\n'
        body = body.strip()
        # add '\' to hashtag so the '#' is preserved by the Markdown processor:
        body = re.sub(r'(?<!\\)#\w+', lambda x: '\\' + x.group(0), body)
        # usernames = [name[1:] for name in re.findall(r'@\w+', body)]
        tag_names = [name[2:] for name in re.findall(r'\\#\w+', body)]

        if referral_budget_cent is None:
            if is_private:
                referral_budget_cent = round(0.4 * price_cent)  # Default is 40% of the post value in private mode
            else:
                referral_budget_cent = round(0.2 * price_cent)  # Default is 20% of the post value in public mode

        platform_fee_cent = round(0.1 * price_cent)  # Default is 10% of the post value
        if is_asking:
            value_cent = price_cent
        else:
            value_cent = price_cent + platform_fee_cent

        post = Post(creator=self,
                    is_asking=is_asking,
                    price_cent=price_cent,
                    platform_fee_cent=platform_fee_cent,
                    is_private=is_private,
                    referral_budget_cent=referral_budget_cent,
                    topic=topic,
                    title=title,
                    body=('m' if use_markdown else 's') + body)
        db.session.add(post)

        self._add_tag(post, 'Asking' if is_asking else 'Answering')
        [self._add_tag(post, name) for name in tag_names if name.lower() not in ('asking', 'answering')]

        if is_private:
            node = Node(
                post=post,
                creator=self,
                value_cent=value_cent,
                answerer_reward_cent=value_cent - platform_fee_cent,
                referrer_reward_cent=0
            )
        else:
            node = Node(
                post=post,
                creator=self,
                value_cent=value_cent,
                answerer_reward_cent=value_cent - platform_fee_cent
            )
        db.session.add(node)
        db.session.commit()

        send_email = current_app.config["EMAIL_SENDER"]
        send_email(
            sender='system@knowble.com',
            recipient='request@knowble.com',
            subject='Request received',
            body_text=f'User: {self.email}\n'
                      f'Topic: {post.topic}\n'
                      f'Details: {post.title}\n'
                      f'Price: ${0.01 * post.price_cent}'
        )

        return post

    def edit_post(self, post, title, body, use_markdown=False):
        title = title.strip()
        body = body.replace('<br>', '')  # remove <br> added by Toast UI
        body = body.replace('\r\n', '\n')  # standardise new lines as '\n'
        body = body.strip()
        # add '\' to hashtag so the '#' is preserved by the Markdown processor:
        body = re.sub(r'(?<!\\)#\w+', lambda x: '\\' + x.group(0), body)
        # usernames = [name[1:] for name in re.findall(r'@\w+', body)]
        tag_names = [name[2:] for name in re.findall(r'\\#\w+', body)]

        post.title = title
        post.body = ('m' if use_markdown else 's') + body

        post.ping(datetime.utcnow())
        db.session.add(post)

        # reset all post tags
        [db.session.delete(post_tag) for post_tag in post.post_tags]
        self._add_tag(post, 'Asking' if post.is_asking else 'Answering')
        [self._add_tag(post, name) for name in tag_names if name.lower() not in ('asking', 'answering')]

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
        # port might have been reported by multiple users, so add this report instead of overwriting it:
        post.report_reason = f'{self}: {reason}\n' + post.report_reason
        post.is_archived = True
        post.ping(datetime.utcnow())
        db.session.add(post)

        fb = Feedback(
            type='report',
            text=f'Post {post.id} is reported by User {self.id} for Reason "{reason}".',
            email=self.email)
        db.session.add(fb)

        db.session.commit()

    def create_node(self, parent_node, referrer_reward_cent=None):
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
            node = self._create_node(parent_node=parent_node, referrer_reward_cent=referrer_reward_cent)
            db.session.add(node)
            db.session.flush()  # flush to get the id of the node just created

            message = Message(creator=self, node=node, type=Message.TYPE_SHARE, text=f'Start a conversation')
            db.session.add(message)

            post.ping(datetime.utcnow())

            Notification.push(
                target_user=node.post.creator,
                node=node,
                message='A user shared your post.',
                email=True  # TODO: default to false if there are too many emails
            )
            db.session.commit()
        return node

    def _create_node(self, parent_node, referrer_reward_cent=None):
        post = parent_node.post
        answerer_reward_cent, sum_referrer_reward_cent, value_cent, max_referrer_reward_cent = parent_node.rewards_for_next_node_cent()

        if post.is_private:
            if referrer_reward_cent is None:
                # Default for each referrer is 50% of the remaining referral budget:
                referrer_reward_cent = round(0.5 * parent_node.remaining_referral_budget_cent)
            else:
                if referrer_reward_cent > parent_node.remaining_referral_budget_cent:
                    raise InvalidActionError(
                        'Cannot create node because referral reward exceeds the remaining referral budget')

        node = Node(creator=self,
                    post=parent_node.post,
                    parent=parent_node,
                    value_cent=value_cent,
                    answerer_reward_cent=answerer_reward_cent,
                    referrer_reward_cent=referrer_reward_cent)
        return node

    def create_message(self, node, text):
        post = node.post
        engagement = node.current_engagement
        if self != node.creator and self != post.creator:
            raise InvalidActionError(
                'Cannot create message because the user is not the post creator or the node creator'
            )
        if node.parent is None:
            raise InvalidActionError('Cannot create message on root node')

        if post.is_archived and (engagement is None or engagement.state != Engagement.STATE_ENGAGED):
            raise InvalidActionError('Cannot create message because the post is archived')
        if engagement and engagement.state == Engagement.STATE_ENGAGED:
            message = Message(creator=self, node=node, engagement=engagement, text=text)
        else:
            message = Message(creator=self, node=node, text=text)
        db.session.add(message)

        self.ping()
        db.session.add(self)

        if engagement is not None:
            engagement.ping(datetime.utcnow())
        else:
            node.ping(datetime.utcnow())

        Notification.push(
            target_user=node.creator if self != node.creator else post.creator,
            node=node,
            message='A user sent you a message.',
            email=True  # TODO: change condition if there are too many emails
            # email=node.current_engagement and node.current_engagement.state == Engagement.STATE_ENGAGED
        )
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
        if node.current_engagement is not None:
            raise InvalidActionError('Cannot create engagement because an uncompleted engagement already exists')
        # value limit checks
        # if self.value_limit_cent < post.price_cent:
        # value limit check is applied to the original post value as the referral reward could be set arbitrarily
        if self.value_limit_cent < node.value_cent:
            raise InvalidActionError(
                'Cannot create engagement because the post reward exceeds the reward limit of the user')
        if not post.is_asking and self.balance_available_cent < node.value_cent:
            raise InsufficientFundsError('Cannot create engagement as asker due to insufficient funds')

        if post.is_asking:
            engagement = Engagement(node=node, sender=self, receiver=post.creator,
                                    asker=post.creator, answerer=self)
        else:
            engagement = Engagement(node=node, sender=self, receiver=post.creator,
                                    asker=self, answerer=post.creator)
            self.reserved_balance_cent += node.value_cent
            db.session.add(self)
        db.session.add(engagement)

        message = Message(creator=self, node=node, type=Message.TYPE_REQUEST, text=f'Engagement requested')
        db.session.add(message)

        node.current_engagement = engagement
        node.ping(datetime.utcnow())

        Notification.push(
            target_user=post.creator,
            node=node,
            message='A user sent you an engagement request.',
            email=True
        )
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

        if not post.is_asking:
            self.reserved_balance_cent -= node.value_cent
            db.session.add(self)

        message = Message(creator=self,
                          node=node,
                          engagement=engagement,
                          type=Message.TYPE_CANCEL,
                          text=f'Engagement cancelled')
        db.session.add(message)

        node.current_engagement = None
        node.ping(datetime.utcnow())

        Notification.push(
            target_user=post.creator,
            node=node,
            message='A user cancelled an engagement request.')
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
        # value limit checks
        # if self.value_limit_cent < post.price_cent:
        # value limit check is applied to the original post value as the referral reward could be set arbitrarily
        if self.value_limit_cent < node.value_cent:
            raise InvalidActionError(
                'Cannot accept engagement because the post reward exceeds the reward limit of the user')
        if post.is_asking and self.balance_available_cent < node.value_cent:
            raise InsufficientFundsError('Cannot accept engagement as asker due to insufficient funds')

        if post.is_asking:
            self.reserved_balance_cent += node.value_cent
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

        node.ping(datetime.utcnow())

        Notification.push(
            target_user=node.creator,
            node=node,
            message='A user accepted your engagement request.',
            email=True
        )
        db.session.commit()

    def rate_engagement(self, engagement, is_success, tip_cent=0):
        node = engagement.node
        asker = engagement.asker
        answerer = engagement.answerer

        # value limit check is applied to the original post value as the referral reward could be set arbitrarily
        # if self.value_limit_cent < post.price_cent:
        # if self.value_limit_cent < node.value_cent:
        #     raise InvalidActionError(
        #         'Cannot rate engagement as successful because the post reward exceeds the reward limit of the user')

        if engagement.state != Engagement.STATE_ENGAGED:
            raise InvalidActionError('Cannot rate engagement because it is not in engaged state')

        if self != asker and self != answerer:
            raise InvalidActionError('Cannot rate engagement because the user is not the asker or the answerer')

        if (self == asker and engagement.rating_by_asker != 0) or \
                (self == answerer and engagement.rating_by_answerer != 0):
            raise InvalidActionError('Cannot rate engagement because the user has already rated')

        if self == answerer and tip_cent != 0:
            raise InvalidActionError(
                'Cannot rate engagement because the user is the answerer and a non-zero tip is set')

        if self == asker:
            if tip_cent > self.balance_available_cent:
                raise InvalidActionError('Cannot rate engagement because the tip value exceeds the balance available')
            if tip_cent > round(node.answerer_reward_cent * (1 if is_success else 0.4)):
                raise InvalidActionError('Cannot rate engagement because the tip value exceeds the maximum allowed')

        if self == asker:
            engagement.rating_by_asker = 1 if is_success else -1
            engagement.tip_cent = tip_cent
            self.reserved_balance_cent += tip_cent
            db.session.add(self)
        elif self == answerer:
            engagement.rating_by_answerer = 1 if is_success else -1

        engagement.ping(datetime.utcnow())
        db.session.add(engagement)

        tip_text = ''
        if self == asker and tip_cent > 0:
            tip_text = f' with a tip of ${0.01 * tip_cent:.2f}'
        message = Message(creator=self,
                          node=node,
                          engagement=engagement,
                          type=Message.TYPE_RATE,
                          text=f'Engagement rated {"+" if is_success else "-"}' + tip_text)
        db.session.add(message)

        if engagement.rating_by_asker != 0 and engagement.rating_by_answerer != 0:
            _finalise_engagement(engagement)

        Notification.push(
            target_user=asker if self != asker else answerer,
            node=node,
            message='A user rated an engagement with you.',
            email=True
        )
        db.session.commit()

    def reputation_if_dispute_lost(self, value_cent):
        m_x = math.exp(-abs(value_cent) * REP_DECAY)
        sum_x = -value_cent + m_x * self.sum_x
        sum_abs_x = abs(value_cent) + m_x * self.sum_abs_x

        m_i = math.exp(-REP_I_DECAY)
        sum_i = -1 + m_i * self.sum_i
        sum_abs_i = 1 + m_i * self.sum_abs_i

        return sum_x / sum_abs_x, sum_i / sum_abs_i

    def update_value_limit(self, value_cent, success, dispute_lost):
        if success:
            r = self.reputation
            if r > 0.8:
                self.value_limit_cent = min(1000, self.value_limit_cent + round(0.5 * value_cent))
            elif r > 0.6:
                self.value_limit_cent = min(1000, self.value_limit_cent + round(0.4 * value_cent))
            elif r > 0.4:
                self.value_limit_cent = min(1000, self.value_limit_cent + round(0.3 * value_cent))
            elif r > 0.2:
                self.value_limit_cent = min(1000, self.value_limit_cent + round(0.2 * value_cent))
            elif r > 0:
                self.value_limit_cent = min(1000, self.value_limit_cent + round(0.1 * value_cent))
            else:
                self.value_limit_cent = min(1000, self.value_limit_cent + round(0.05 * value_cent))

        if dispute_lost:
            r = self.reputation
            if r > 0.5:
                self.value_limit_cent = max(100, round(0.75 * self.value_limit_cent))
            elif r > 0:
                self.value_limit_cent = max(100, round(0.5 * self.value_limit_cent))
            elif r > -0.5:
                self.value_limit_cent = max(
                    100,
                    round(min(0.5 * self.value_limit_cent, 0.75 * value_cent))
                )
            else:
                self.value_limit_cent = max(100, round(0.5 * value_cent))

    def update_reputation(self, value_cent, success, dispute_lost):
        """
        The visible reputation is only affected if the interaction is a success or if the user lose a dispute.
        This is to protect the side with a higher reputation - his visible reputation is not affected but the
        internal components of his reputation are weakened due to decay, and he will be in a weaker position in
        the next dispute unless he starts to build a good track record
        """
        #  decay the weights of past observations in ALL cases:
        m_x = math.exp(-abs(value_cent) * REP_DECAY)
        self.sum_x *= m_x
        self.sum_abs_x *= m_x

        m_i = math.exp(-REP_I_DECAY)
        self.sum_i *= m_i
        self.sum_abs_i *= m_i

        # add most recent observation only if it is a success or dispute lost
        if success or dispute_lost:
            self.sum_x += value_cent if success else -value_cent
            self.sum_abs_x += abs(value_cent)
            self.sum_i += 1 if success else -1
            self.sum_abs_i += 1

        self.update_value_limit(value_cent, success, dispute_lost)


def _handle_success(engagement, fraction=1.0):
    node = engagement.node
    asker = engagement.asker
    answerer = engagement.answerer

    value_cent = _distribute_reward_cent(engagement=engagement, fraction=fraction)

    asker.update_reputation(value_cent, success=True, dispute_lost=False)
    answerer.update_reputation(value_cent, success=True, dispute_lost=False)

    # any tip to be paid by the asker to the answer
    _pay_tip(engagement)

    db.session.add(asker)
    db.session.add(answerer)

    message = Message(creator=node.creator,
                      node=node,
                      type=Message.TYPE_COMPLETE,
                      text=f'Engagement successful - reward has been distributed')
    db.session.add(message)


def _finalise_engagement(engagement):
    if engagement.rating_by_asker == engagement.rating_by_answerer == 1:
        _handle_success(engagement)
    elif engagement.rating_by_asker == -1 and engagement.rating_by_answerer == 1:
        _handle_dispute(engagement)
    # elif engagement.rating_by_asker == 1 and engagement.rating_by_answerer == -1:
    #     self._handle_success(engagement, fraction=0.5)  # Default fraction is 50% in this scenario
    else:
        _handle_non_success(engagement)

    engagement.state = Engagement.STATE_COMPLETED
    engagement.node.current_engagement = None


def _handle_non_success(engagement):
    node = engagement.node
    asker = engagement.asker
    answerer = engagement.answerer

    asker.reserved_balance_cent -= node.value_cent

    # any tip to be paid by the asker to the answer
    _pay_tip(engagement)

    db.session.add(asker)
    db.session.add(answerer)

    message = Message(creator=node.creator,
                      node=node,
                      type=Message.TYPE_COMPLETE,
                      text=f'Engagement unsuccessful - no reward will be distributed')
    db.session.add(message)


def _handle_dispute(engagement):
    node = engagement.node
    asker = engagement.asker
    answerer = engagement.answerer

    value_cent = node.value_cent
    asker.reserved_balance_cent -= value_cent

    rx_asker, ri_asker = asker.reputation_if_dispute_lost(value_cent)
    rx_answerer, ri_answerer = answerer.reputation_if_dispute_lost(value_cent)

    # 3-D lexical ordering by (min(rx, ri), rx, ri)
    if min(rx_asker, ri_asker) < min(rx_answerer, ri_answerer) or \
            (
                    min(rx_asker, ri_asker) == min(rx_answerer, ri_answerer) and
                    rx_asker < rx_answerer
            ) or \
            (
                    min(rx_asker, ri_asker) == min(rx_answerer, ri_answerer) and
                    rx_asker == rx_answerer and
                    ri_asker < ri_answerer
            ):
        # asker lost:
        engagement.dispute_status = Engagement.DISPUTE_STATUS_ASKER_LOST
        asker.update_reputation(value_cent, success=False, dispute_lost=True)
        answerer.update_reputation(value_cent, success=False, dispute_lost=False)
    elif min(rx_asker, ri_asker) > min(rx_answerer, ri_answerer) or \
            (
                    min(rx_asker, ri_asker) == min(rx_answerer, ri_answerer) and
                    rx_asker > rx_answerer
            ) or \
            (
                    min(rx_asker, ri_asker) == min(rx_answerer, ri_answerer) and
                    rx_asker == rx_answerer and
                    ri_asker > ri_answerer
            ):  # answerer lost:
        engagement.dispute_status = Engagement.DISPUTE_STATUS_ANSWERER_LOST
        asker.update_reputation(value_cent, success=False, dispute_lost=False)
        answerer.update_reputation(value_cent, success=False, dispute_lost=True)
    else:  # it is a draw, punishment both
        # TODO: consider punishing no one or a different logic
        # currently this is deemed unnecessary as it should be very rare to have exactly the same reputation
        engagement.dispute_status = Engagement.DISPUTE_STATUS_BOTH_LOST
        asker.update_reputation(value_cent, success=False, dispute_lost=True)
        answerer.update_reputation(value_cent, success=False, dispute_lost=True)

    db.session.add(asker)
    db.session.add(answerer)

    message = Message(creator=node.creator,
                      node=node,
                      type=Message.TYPE_COMPLETE,
                      text=f'Engagement outcome disputed - no reward will be distributed')
    db.session.add(message)


def _pay_tip(engagement):
    tip_cent = engagement.tip_cent
    asker = engagement.asker
    answerer = engagement.answerer
    if tip_cent > 0:
        asker.reserved_balance_cent -= tip_cent

        Transaction.add(
            transaction_type=Transaction.TYPE_ASKER_TIP_PAYMENT,
            amount_cent=-tip_cent,
            user=asker,
            engagement=engagement
        )

        Transaction.add(
            transaction_type=Transaction.TYPE_ANSWERER_TIP,
            amount_cent=tip_cent,
            user=answerer,
            engagement=engagement
        )

        Notification.push(
            target_user=asker,
            node=engagement.node,
            message=f'You paid ${0.01 * tip_cent:.2f} tip.',
            email=True
        )

        Notification.push(
            target_user=answerer,
            node=engagement.node,
            message=f'You earned ${0.01 * tip_cent:.2f} tip.',
            email=True
        )


def _distribute_reward_cent(engagement, fraction):
    node = engagement.node
    post = node.post
    if post.is_asking:
        buyer = post.creator
        seller = node.creator
    else:
        buyer = node.creator
        seller = post.creator

    # fully release what has been reserved for this engagement but only deduct the fraction from the actual balance:
    value_cent = node.value_cent
    buyer.reserved_balance_cent -= value_cent
    value_cent = round(fraction * value_cent)

    Transaction.add(
        transaction_type=Transaction.TYPE_ASKER_REWARD_PAYMENT,
        amount_cent=-value_cent,
        user=buyer,
        engagement=engagement
    )

    Notification.push(
        target_user=buyer,
        node=node,
        message=f'You paid ${0.01 * value_cent:.2f} as asker.',
        email=True
    )

    platform_fee_cent = round(fraction * post.platform_fee_cent)
    Transaction.add(
        transaction_type=Transaction.TYPE_PLATFORM_FEE,
        amount_cent=platform_fee_cent,
        engagement=engagement
    )

    sum_referrer_reward_cent = 0
    nodes = node.nodes_before_inc().all()  # all nodes including buyers and sellers
    referrer_nodes = nodes[1:(len(nodes) - 1)]  # referrers only
    if post.is_private:
        for node in referrer_nodes:
            referrer = node.creator
            referrer_reward_cent = round(fraction * node.referrer_reward_cent)
            Transaction.add(
                transaction_type=Transaction.TYPE_REFERRER_REWARD,
                amount_cent=referrer_reward_cent,
                user=referrer,
                engagement=engagement
            )
            sum_referrer_reward_cent += referrer_reward_cent

            Notification.push(
                target_user=referrer,
                node=node,
                message=f'You earned ${0.01 * referrer_reward_cent:.2f} as referrer.',
                email=True
            )
    else:
        if len(nodes) == 1:  # there is only OP's node - should never reach here
            raise RewardDistributionError('Cannot distribute reward from the root node')
        # Default total referral cap = 20% of OP reward:
        total_referrer_reward_cent_cap = round(0.2 * fraction * post.price_cent)
        referrer_nodes.reverse()
        for referrer_node in referrer_nodes:
            referrer = referrer_node.creator
            # Default strategy is to distribute 50% of remaining at each node in the chain:
            referrer_reward_cent = round(
                0.5 * (total_referrer_reward_cent_cap - sum_referrer_reward_cent)
            )
            Transaction.add(
                transaction_type=Transaction.TYPE_REFERRER_REWARD,
                amount_cent=referrer_reward_cent,
                user=referrer,
                engagement=engagement
            )
            sum_referrer_reward_cent += referrer_reward_cent

            Notification.push(
                target_user=referrer,
                node=node,
                message=f'You earned ${0.01 * referrer_reward_cent:.2f} as referrer.',
                email=True
            )

    # the seller gets everything left
    answerer_reward_cent = value_cent - platform_fee_cent - sum_referrer_reward_cent
    Transaction.add(
        transaction_type=Transaction.TYPE_ANSWERER_REWARD,
        amount_cent=answerer_reward_cent,
        user=seller,
        engagement=engagement
    )
    db.session.add(seller)

    Notification.push(
        target_user=seller,
        node=node,
        message=f'You earned ${0.01 * answerer_reward_cent:.2f} as answerer.',
        email=True
    )

    return value_cent


@login_manager.user_loader
def load_user(user_id):
    return User.query.filter_by(remember_me_id=user_id).first()
