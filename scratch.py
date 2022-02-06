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

N_USERS = 10

faker = Faker()

users = [User(email=faker.email(), account_balance=100000) for i in range(N_USERS)]
db.session.add_all(users)
db.session.commit()

# choose a user at random and create a post
posts = [random.choice(users).post(is_request=random.choice([True, False]),
                                   reward=random.randint(50, 500),
                                   title=faker.text(100),
                                   body=faker.text(500)) for i in
         range(20)]

for i in range(100):
    # choose a post at random, choose a user who is not the post creator at random, and create a node
    post = random.choice(posts)
    answerer = random.choice(users)
    while answerer == post.creator:
        answerer = random.choice(users)
    answerer.create_node(post=post, parent=random.choice(post.nodes.all()))

print(len(Post.query.all()))
print(len(Node.query.all()))

competence = [random.uniform(0.7, 0.9) for i in range(N_USERS)]
credibility = [random.uniform(0.75, 0.95) for i in range(N_USERS)]
for i in range(50):
    # choose a node which is not an asker node at random, and make engagement
    node = random.choice(Node.query.filter(Node.parent != None).all())
    asker = node.post.creator
    answerer = node.creator
    engagement = answerer.request_engagement(node)
    asker.accept_engagement(engagement)
    actual_success = random.uniform(0, 1) < competence[int(answerer.id) - 1]
    answerer_claim = actual_success
    if not actual_success and random.uniform(0, 1) > credibility[int(answerer.id) - 1]:
        answerer_claim = True
    asker_claim = actual_success
    if actual_success and random.uniform(0, 1) > credibility[int(asker.id) - 1]:
        asker_claim = False
    answerer.rate_engagement(engagement, success=answerer_claim)
    asker.rate_engagement(engagement, success=asker_claim)

print(answerer.engagements_as_answerer.filter(and_(Engagement.state == Engagement.STATE_COMPLETED,
                                                   Engagement.rating_by_asker == 1)).count())

print(answerer.engagements_as_answerer.filter(Engagement.state == Engagement.STATE_COMPLETED).count())

# db.session.remove()
# db.drop_all()
app_context.pop()
