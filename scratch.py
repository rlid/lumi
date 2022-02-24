import random

from faker import Faker

from app import create_app, db
from app.models.user import User, Post, Node, Engagement

faker = Faker()
N_DAYS = 10
N_USERS = 10
P_POST = 0.5
P_NODE = 0.5
P_MESSAGE = 1.0
P_REQUEST_ENGAGE = 0.2
P_CANCEL_ENGAGE = 0.1
P_ACCEPT_ENGAGE = 0.5
P_RATE_ENGAGE = 0.5
P_ARCHIVE = 0.75
N_TAGS = 50

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
    db.drop_all()
    db.create_all()
    users = [User(email=faker.email(), total_balance=100, adjective=random.choice(adjectives)) for i in
             range(N_USERS)]
    db.session.add_all(users)
    db.session.commit()

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
                post = user.create_post(type=random.choice([Post.TYPE_BUY, Post.TYPE_SELL]),
                                        reward=random.randint(1, 5),
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
                        if random.uniform(0, 1) < P_REQUEST_ENGAGE and user.reward_limit_cent >= node.post.reward_cent:
                            engagement = user.create_engagement(node)
                            if random.uniform(0, 1) < P_CANCEL_ENGAGE:
                                user.cancel_engagement(engagement)
                            else:
                                print(f'{user} created {engagement}')

        for user in users:
            for engagement in user.engagements_received.filter(Engagement.state == Engagement.STATE_REQUESTED).all():
                if not engagement.node.post.is_archived and \
                        random.uniform(0, 1) < P_ACCEPT_ENGAGE and \
                        user.reward_limit_cent >= engagement.node.post.reward_cent:
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
    u1 = User(email='1', total_balance=100)
    u2 = User(email='2', total_balance=100)
    u3 = User(email='3', total_balance=100)
    u4 = User(email='4', total_balance=100)
    u5 = User(email='5', total_balance=100)
    users = [u1, u2, u3, u4, u5]
    db.session.add_all(users)
    p1b = u1.create_post(type=Post.TYPE_BUY, reward=1, title='')
    p1s = u1.create_post(type=Post.TYPE_SELL, reward=5, title='')
    p2b = u2.create_post(type=Post.TYPE_BUY, reward=2, title='')
    p2s = u2.create_post(type=Post.TYPE_SELL, reward=4, title='')
    p3b = u3.create_post(type=Post.TYPE_BUY, reward=3, title='')
    p3s = u3.create_post(type=Post.TYPE_SELL, reward=3, title='')
    p4b = u4.create_post(type=Post.TYPE_BUY, reward=4, title='')
    p4s = u4.create_post(type=Post.TYPE_SELL, reward=2, title='')
    p5b = u5.create_post(type=Post.TYPE_BUY, reward=5, title='')
    p5s = u5.create_post(type=Post.TYPE_SELL, reward=1, title='')
    posts = [p1b, p1s, p2b, p2s, p3b, p3s, p4b, p4s, p5b, p5s]

    for day in range(10):
        for user in users:
            post = random.choice(posts)
            if user != post.creator:
                if user.reward_limit_cent >= post.reward_cent and post.creator.reward_limit_cent >= post.reward_cent:
                    node = user.create_node(random.choice(post.nodes.all()))
                    engagement = user.create_engagement(node)
                    post.creator.accept_engagement(engagement)
                    user.rate_engagement(engagement, True if random.uniform(0, 1) < 0.9 else False)
                    post.creator.rate_engagement(engagement, True if random.uniform(0, 1) < 0.9 else False)

    db.session.commit()


def sim_existing():
    u1 = User.query.get('6590d9ea-6208-4365-b3cb-5decea456b52')
    u2 = User.query.get('660d1e1e-6d1e-42a4-b2db-96287dcfb8f2')
    p = u1.create_post(type=Post.TYPE_SELL, reward=610, title=faker.text(100))
    n = u2.create_node(p.nodes.filter(Node.creator == u1).first())
    e = u2.create_engagement(n)
    u1.accept_engagement(e)
    u1.rate_engagement(e, True)
    u2.rate_engagement(e, True)

    db.session.commit()


app = create_app("DEV")
app_context = app.app_context()
app_context.push()
# db.drop_all()
# db.create_all()

sim_random()
# sim_reset()
# sim_existing()

users = User.query.all()

print(f'Number of posts = {len(Post.query.all())}')
print(f'Number of nodes (including root) = {len(Node.query.all())}')

print(Engagement.query.filter(
    Engagement.state == Engagement.STATE_COMPLETED,
    Engagement.rating_by_asker == 1,
    Engagement.rating_by_answerer == 1
).count())
print(Engagement.query.filter(Engagement.state == Engagement.STATE_COMPLETED).count())

print(sum([u.total_balance for u in users]))
engagements = Engagement.query.filter(
    Engagement.state == Engagement.STATE_COMPLETED,
    Engagement.rating_by_asker == 1,
    Engagement.rating_by_answerer == 1).all()
print(0.1 * sum([e.node.post.reward for e in engagements]))

# db.session.commit()
# db.session.remove()
# db.drop_all()
app_context.pop()
