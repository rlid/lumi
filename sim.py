import random

from faker import Faker
from sqlalchemy import or_, and_

from app import create_app, db
from app.models import Transaction, User, Post, Node, Engagement

faker = Faker()
adjectives = ['friendly', 'wholesome', 'random', 'special', 'funny', 'approachable', 'adaptable', 'adventurous',
              'affectionate', 'ambitious', 'amiable', 'compassionate', 'considerate', 'courageous', 'courteous',
              'diligent', 'empathetic', 'exuberant', 'frank', 'generous', 'gregarious', 'impartial', 'intuitive',
              'inventive', 'passionate', 'persistent', 'philosophical', 'practical', 'rational', 'reliable',
              'resourceful', 'sensible', 'sincere', 'sympathetic', 'unassuming', 'witty', 'adaptable', 'adventurous',
              'diligent', 'humble', 'courageous', 'efficient', 'enchanting', 'generous', 'serious',
              'likeable', 'sincere', 'non-judgemental', 'trustworthy', 'resourceful', 'well-read', 'wise',
              'resilient', 'reliable', 'determined', 'strong', 'stupendous', 'exceptional', 'generous', 'kind',
              'witty', 'extraordinary', 'breathtaking', 'flawless', 'magnificent',
              'lively', 'versatile', 'amazing', 'fun-loving', 'well-travelled', 'outgoing', 'amicable', 'friendly',
              'perseverant', 'enthusiastic', 'affectionate', 'thoughtful', 'modest', 'hygienic', 'considerate',
              'courteous', 'optimistic', 'motivated', 'encouraging', 'eager', 'diplomatic', 'convivial',
              'active', 'assertive', 'affable', 'supportive', 'steadfast', 'shy', 'laid-back',
              'introverted', 'hopeful', 'focused', 'extroverted', 'cheerful', 'analytical',
              'good-looking', 'hard-working', 'easy-going', 'bright', 'warm-hearted', 'honest']


def sim_random():
    users = [User(email=faker.email(), total_balance_cent=100000, adjective=random.choice(adjectives)) for i in
             range(N_USERS)]
    db.session.add_all(users)
    # db.session.commit()

    tag_names = [word.capitalize() for word in faker.words(N_TAGS)]

    competence = {}
    credibility = {}
    for user in users:
        competence[user] = random.uniform(0.7, 0.9)
        credibility[user] = random.uniform(0.75, 0.95)

    actual_success = {}

    for day in range(N_DAYS):
        for user in users:
            if random.uniform(0, 1) < P_POST:
                post = user.create_post(is_asking=random.choice([True, False]),
                                        price_cent=100 * random.randint(1, 5),
                                        title=faker.text(100),
                                        body='\n'.join(faker.text(100) for i in range(random.randint(2, 5))))
                print(f'{user} created {post}')
                for i in range(random.randint(1, 5)):
                    tag = user.add_tag(post, random.choice(tag_names).capitalize())
                    print(f'{user} added {tag}')

        for user in users:
            for post in Post.query.filter(Post.is_archived.is_not(True)).all():
                if user != post.creator:
                    if random.uniform(0, 1) < P_NODE:
                        node = user.create_node(parent_node=random.choice(post.nodes.all()))
                        print(f'{user} created {node}')
                        if random.uniform(0, 1) < P_MESSAGE:
                            for i in range(random.randint(1, 1)):
                                m1 = [user.create_message(
                                    node, text=faker.text(100)
                                ) for i in range(random.randint(1, 2))]
                                print(f'{user} sent {m1}')
                                m2 = [post.creator.create_message(
                                    node, text=faker.text(100)
                                ) for i in range(random.randint(1, 2))]
                                print(f'{post.creator} replied {m1}')

        for user in users:
            for node in user.nodes.filter(Node.parent_id.is_not(None)).all():
                if not node.post.is_archived:
                    engagement = node.engagements.filter(Engagement.state < Engagement.STATE_COMPLETED).first()
                    if engagement is None:
                        if random.uniform(0, 1) < P_REQUEST_ENGAGE and user.value_limit_cent >= node.value_cent:
                            engagement = user.create_engagement(node)
                            if random.uniform(0, 1) < P_CANCEL_ENGAGE:
                                user.cancel_engagement(engagement)
                            else:
                                print(f'{user} created {engagement}')

        for user in users:
            for engagement in user.engagements_received.filter(Engagement.state == Engagement.STATE_REQUESTED).all():
                if not engagement.node.post.is_archived and \
                        random.uniform(0, 1) < P_ACCEPT_ENGAGE and \
                        user.value_limit_cent >= engagement.node.value_cent:
                    user.accept_engagement(engagement)
                    print(f'{user} accepted {engagement}')
                    for i in range(random.randint(1, 2)):
                        m1 = [user.create_message(
                            engagement.node, text=faker.text(100)
                        ) for i in range(random.randint(1, 2))]
                        print(f'{user} sent {m1}')
                        m2 = [engagement.sender.create_message(
                            engagement.node, text=faker.text(100)
                        ) for i in range(random.randint(1, 2))]
                        print(f'{post.creator} replied {m1}')

        for user in users:
            for engagement in user.engagements_as_answerer.filter(Engagement.state == Engagement.STATE_ENGAGED).all():
                if random.uniform(0, 1) < P_RATE_ENGAGE:
                    is_success = actual_success.get(engagement)
                    if is_success is None:
                        is_success = random.uniform(0, 1) < competence[user]
                        actual_success[engagement.answerer] = is_success
                        print(f'{engagement} success is {is_success}')
                    if not is_success and random.uniform(0, 1) > credibility[user]:
                        is_success = True
                    user.rate_engagement(engagement, is_success)
                    print(f'{user} rated {engagement} {is_success} as answerer')

            for engagement in user.engagements_as_asker.filter(Engagement.state == Engagement.STATE_ENGAGED).all():
                if random.uniform(0, 1) < P_RATE_ENGAGE:
                    is_success = actual_success.get(engagement)
                    if is_success is None:
                        is_success = random.uniform(0, 1) < competence[user]
                        actual_success[engagement.answerer] = is_success
                    if is_success and random.uniform(0, 1) > credibility[user]:
                        is_success = False
                    user.rate_engagement(engagement, is_success)
                    print(f'{user} rated {engagement} as {is_success} as asker')

        for user in users:
            for engagement in user.engagements_received.filter(Engagement.state == Engagement.STATE_COMPLETED):
                if random.uniform(0, 1) < P_ARCHIVE:
                    user.toggle_archive(engagement.node.post)

    db.session.commit()


def sim_reset():
    from random import Random
    random = Random(1)

    db.drop_all()
    db.create_all()
    u1 = User(email='1', total_balance_cent=10000)
    u2 = User(email='2', total_balance_cent=10000)
    u3 = User(email='3', total_balance_cent=10000)
    u4 = User(email='4', total_balance_cent=10000)
    u5 = User(email='5', total_balance_cent=10000)
    users = [u1, u2, u3, u4, u5]
    db.session.add_all(users)
    p1b = u1.create_post(is_asking=True, price_cent=100, title='')
    p1s = u1.create_post(is_asking=False, price_cent=500, title='')
    p2b = u2.create_post(is_asking=True, price_cent=200, title='')
    p2s = u2.create_post(is_asking=False, price_cent=400, title='')
    p3b = u3.create_post(is_asking=True, price_cent=300, title='')
    p3s = u3.create_post(is_asking=False, price_cent=300, title='')
    p4b = u4.create_post(is_asking=True, price_cent=400, title='')
    p4s = u4.create_post(is_asking=False, price_cent=200, title='')
    p5b = u5.create_post(is_asking=True, price_cent=500, title='')
    p5s = u5.create_post(is_asking=False, price_cent=100, title='')
    posts = [p1b, p1s, p2b, p2s, p3b, p3s, p4b, p4s, p5b, p5s]

    for day in range(10):
        for user in users:
            post = random.choice(posts)
            if user != post.creator:
                parent_node = random.choice(post.nodes.all())
                if user.value_limit_cent >= parent_node.value_cent and post.creator.value_limit_cent >= parent_node.value_cent:
                    node = user.create_node(parent_node)
                    engagement = user.create_engagement(node)
                    post.creator.accept_engagement(engagement)
                    user.rate_engagement(engagement, True if random.uniform(0, 1) < 0.9 else False)
                    post.creator.rate_engagement(engagement, True if random.uniform(0, 1) < 0.9 else False)

    db.session.commit()


def sim_existing():
    u1 = User.query.get('6590d9ea-6208-4365-b3cb-5decea456b52')
    u2 = User.query.get('660d1e1e-6d1e-42a4-b2db-96287dcfb8f2')
    p = u1.create_post(is_asking=False, price_cent=610, title=faker.text(100))
    n = u2.create_node(p.nodes.filter(Node.creator == u1).first())
    e = u2.create_engagement(n)
    u1.accept_engagement(e)
    u1.rate_engagement(e, True)
    u2.rate_engagement(e, True)

    db.session.commit()


def sim_all(n_days=50,
            n_users=20,
            n_tags=50,
            a_competence=0.8, d_competence=0.1,
            a_credibility=0.85, d_credibility=0.1,
            p_post=0.25,
            p_private=0.5,
            p_share=0.75,
            p_message=0.5,
            p_request=0.75,
            p_cancel_given_request=0.1,
            p_accept_given_request=0.8,
            p_rate_given_accept=0.8,
            p_archive_given_complete=0.5,
            initial_balance_cent=10000):
    users = [User(email=faker.email(), total_balance_cent=initial_balance_cent, adjective=random.choice(adjectives)) for
             i in
             range(n_users)]
    db.session.add_all(users)
    db.session.commit()

    users = User.query.all()
    sum_initial_balance = sum([u.total_balance for u in users])

    tag_names = [word.capitalize() for word in faker.words(n_tags)]

    competence = {}
    credibility = {}
    for user in users:
        competence[user] = random.uniform(a_competence - d_competence, a_competence + d_competence)
        credibility[user] = random.uniform(a_credibility - d_credibility, a_credibility + d_credibility)

    actual_success = {}
    for day in range(n_days):
        for user in users:
            if random.uniform(0, 1) < p_post:
                value_cent = random.randint(100, user.value_limit_cent)
                if random.uniform(0, 1) < p_private:
                    post = user.create_post(is_asking=random.choice([True, False]),
                                            price_cent=value_cent,
                                            title=faker.text(100),
                                            body='\n'.join(faker.text(100) for i in range(random.randint(2, 5))),
                                            is_private=True,
                                            referral_budget_cent=round(0.4 * value_cent))
                else:
                    post = user.create_post(is_asking=random.choice([True, False]),
                                            price_cent=value_cent,
                                            title=faker.text(100),
                                            body='\n'.join(faker.text(100) for i in range(random.randint(2, 5))))
                print('Post created')
                for i in range(random.randint(1, 5)):
                    user.add_tag(post, random.choice(tag_names).capitalize())
                    print('Tag added')

            if random.uniform(0, 1) < p_share:
                nodes = Node.query.join(
                    Post, Post.id == Node.post_id
                ).filter(
                    Post.creator != user,  # not required in practice because the OP can share his own post
                    Post.is_archived.is_not(True)
                ).all()
                if len(nodes) > 0:
                    parent_node = random.choice(nodes)
                    if parent_node.post.is_private:
                        user.create_node(
                            parent_node=parent_node,
                            referrer_reward_cent=random.randint(
                                round(0.25 * parent_node.remaining_referral_budget_cent),
                                round(0.75 * parent_node.remaining_referral_budget_cent)))
                    else:
                        user.create_node(parent_node)
                    print('Post shared')

            if random.uniform(0, 1) < p_message:
                nodes = user.nodes.join(
                    Post, Post.id == Node.post_id
                ).filter(
                    Node.parent_id.is_not(None),
                    Post.is_archived.is_not(True)
                ).all()
                if len(nodes) > 0:
                    node = random.choice(nodes)
                    if random.uniform(0, 1) < 0.5:
                        [user.create_message(node, text=faker.text(100)) for i in range(random.randint(1, 2))]
                        [node.post.creator.create_message(node, text=faker.text(100)) for i in
                         range(random.randint(1, 2))]
                        print('Messages exchanged')

            if random.uniform(0, 1) < p_request:
                nodes = user.nodes.join(
                    Post, Post.id == Node.post_id
                ).filter(
                    Node.parent_id.is_not(None),
                    Post.is_archived.is_not(True),
                    Node.value_cent <= user.value_limit_cent
                ).all()
                if len(nodes) > 0:
                    node = random.choice(nodes)
                    if node.current_engagement is None:
                        if not node.post.is_asking and user.balance_available_cent < node.value_cent:
                            top_up_cent = 1000 * int(1 + (node.value_cent - user.balance_available_cent) / 1000)
                            Transaction.add(
                                transaction_type=Transaction.TYPE_TOP_UP,
                                amount_cent=top_up_cent,
                                user=user)
                            print(f'Account topped up by {0.01 * top_up_cent:g}')
                        engagement = user.create_engagement(node)
                        print('Engagement requested')
                        if random.uniform(0, 1) < p_cancel_given_request:
                            user.cancel_engagement(engagement)
                            print('Engagement cancelled')

            engagement_requests = user.engagements_received.join(
                Node, Node.id == Engagement.node_id,
            ).join(
                Post, Post.id == Node.post_id
            ).filter(
                Engagement.state == Engagement.STATE_REQUESTED,
                Post.is_archived.is_not(True),
                Node.value_cent <= user.value_limit_cent
            ).all()
            for engagement_request in engagement_requests:
                node = engagement_request.node
                post = node.post
                if random.uniform(0, 1) < p_accept_given_request:
                    if post.is_asking and user.balance_available_cent < node.value_cent:
                        top_up_cent = 1000 * int(1 + (node.value_cent - user.balance_available_cent) / 1000)
                        Transaction.add(
                            transaction_type=Transaction.TYPE_TOP_UP,
                            amount_cent=top_up_cent,
                            user=user)
                        print(f'Account topped up by {0.01 * top_up_cent:g}')
                    user.accept_engagement(engagement_request)
                    print('Engagement accepted')
                    [user.create_message(node, text=faker.text(100)) for i in range(random.randint(1, 2))]
                    [node.creator.create_message(node, text=faker.text(100)) for i in range(random.randint(1, 2))]
                    print('Messages exchanged')

            engagements = Engagement.query.filter(
                Engagement.state == Engagement.STATE_ENGAGED,
                or_(
                    and_(Engagement.asker == user, Engagement.rating_by_asker == 0),
                    and_(Engagement.answerer == user, Engagement.rating_by_answerer == 0)
                )
            ).all()
            for engagement in engagements:
                if random.uniform(0, 1) < p_rate_given_accept:
                    is_success = actual_success.get(engagement)
                    if is_success is None:
                        is_success = random.uniform(0, 1) < competence[user]
                        actual_success[engagement] = is_success
                    if is_success and user == engagement.asker and random.uniform(0, 1) > credibility[user]:
                        is_success = False
                    if (not is_success) and user == engagement.answerer and random.uniform(0, 1) > credibility[user]:
                        is_success = True
                    if user == engagement.asker:
                        user.rate_engagement(
                            engagement,
                            is_success,
                            tip_cent=min(
                                user.balance_available_cent,
                                random.randint(
                                    0,
                                    round(engagement.node.answerer_reward_cent * (1 if is_success else 0.4)))
                            )
                        )
                    else:
                        user.rate_engagement(engagement, is_success)
                    print('Engagement rated')

            posts = Post.query.join(
                Node, Node.post_id == Post.id
            ).join(
                Engagement, Engagement.node_id == Node.id
            ).filter(
                Post.creator == user,
                Post.is_archived.is_not(True),
                Engagement.state == Engagement.STATE_COMPLETED
            ).group_by(
                Post
            ).all()
            for post in posts:
                if random.uniform(0, 1) < p_archive_given_complete:
                    user.toggle_archive(post)
    db.session.commit()
    return sum_initial_balance


P_POST = 0.5
P_NODE = 0.5
P_MESSAGE = 1.0
P_REQUEST_ENGAGE = 0.5
P_CANCEL_ENGAGE = 0.1
P_ACCEPT_ENGAGE = 0.75
P_RATE_ENGAGE = 0.25
P_ARCHIVE = 0.5
N_TAGS = 50

N_DAYS = 50
N_USERS = 20
N_BAL = 1000
P_PRIVATE = 0.5

app = create_app("DEV")
app_context = app.app_context()
app_context.push()

db.drop_all()
db.create_all()

sum_initial_platform_fee = sum(
    [fee.amount for fee in Transaction.query.filter_by(type=Transaction.TYPE_PLATFORM_FEE).all()])
sum_initial_top_up = sum(
    [top_up.amount for top_up in Transaction.query.filter_by(type=Transaction.TYPE_TOP_UP).all()])
sum_initial_balance = sim_all(n_days=N_DAYS, n_users=N_USERS, initial_balance_cent=N_BAL,
                              p_private=P_PRIVATE)
# sim_random()
# sim_reset()
# sim_existing()

print(f'Number of posts = {len(Post.query.all())}')
print(f'Number of nodes (including root) = {len(Node.query.all())}')

print('Number of successful engagements = ' + str(Engagement.query.filter(
    Engagement.state == Engagement.STATE_COMPLETED,
    Engagement.rating_by_asker == 1,
    Engagement.rating_by_answerer == 1
).count()))
print('Number of completed engagements = ' + str(Engagement.query.filter(
    Engagement.state == Engagement.STATE_COMPLETED
).count()))

users = User.query.all()
sum_final_balance = sum([u.total_balance for u in users])
sum_final_platform_fee = sum(
    [fee.amount for fee in Transaction.query.filter_by(type=Transaction.TYPE_PLATFORM_FEE).all()])
sum_final_top_up = sum(
    [top_up.amount for top_up in Transaction.query.filter_by(type=Transaction.TYPE_TOP_UP).all()])

print(f'Change in platform fee = {sum_final_platform_fee - sum_initial_platform_fee:g}')
print(f'Change in balance = {sum_final_balance - sum_initial_balance:g}')
print(f'Sum top up = {sum_final_top_up - sum_initial_top_up:g}')

# db.session.remove()
# db.drop_all()
app_context.pop()
