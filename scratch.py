import random
from faker import Faker

from sqlalchemy import and_
from app import create_app, db
from app.models.user import User, Post, Node, Engagement

app = create_app("DEV")
app_context = app.app_context()
app_context.push()

db.drop_all()
db.create_all()

faker = Faker()
N_DAYS = 10
N_USERS = 10
P_POST = 0.5
P_NODE = 0.5
P_MESSAGE = 1.0
P_REQUEST_ENGAGE = 0.2
P_ACCEPT_ENGAGE = 0.5
P_RATE_ENGAGE = 0.5
N_TAGS = 50

users = [User(email=faker.email(), account_balance=100000) for i in range(N_USERS)]
db.session.add_all(users)
db.session.commit()

tag_names = [word.capitalize() for word in faker.words(N_TAGS)]

competence = {}
credibility = {}
for user in users:
    competence[user] = random.uniform(0.4, 0.6)
    credibility[user] = random.uniform(0.4, 0.6)

actual_success = {}

for day in range(N_DAYS):
    for user in users:
        if random.uniform(0, 1) < P_POST:
            post = user.create_post(is_request=random.choice([True, False]),
                                    reward=100 * random.randint(1, 5),
                                    title=faker.text(100),
                                    body='\n'.join(faker.text(100) for i in range(random.randint(2, 5))))
            print(f'{user} created {post}')
            for i in range(random.randint(1, 5)):
                tag = user.add_tag(post, random.choice(tag_names).capitalize())
                print(f'{user} added {tag}')

    for user in users:
        for post in Post.query.all():
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
        for node in user.nodes.filter(Node.parent != None).all():
            engagement = node.engagements.filter(Engagement.state != Engagement.STATE_COMPLETED).first()
            if engagement is None:
                if random.uniform(0, 1) < P_REQUEST_ENGAGE:
                    engagement = user.create_engagement(node)
                    print(f'{user} created {engagement}')

    for user in users:
        for engagement in user.engagements_received.filter(Engagement.state == Engagement.STATE_REQUESTED).all():
            if random.uniform(0, 1) < P_ACCEPT_ENGAGE:
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

print(len(Post.query.all()))
print(len(Node.query.all()))

print(Engagement.query.filter(and_(Engagement.state == Engagement.STATE_COMPLETED,
                                   Engagement.rating_by_asker == 1)).count())

print(Engagement.query.filter(Engagement.state == Engagement.STATE_COMPLETED).count())

# db.session.remove()
# db.drop_all()
app_context.pop()
