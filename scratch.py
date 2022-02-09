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
N_POSTS = N_USERS * 2 * N_DAYS
N_TAGS = 50
N_NODES = N_USERS * 4 * N_DAYS
N_ENGAGEMENTS = N_USERS * 1 * N_DAYS

users = [User(email=faker.email(), account_balance=100000) for i in range(N_USERS)]
db.session.add_all(users)
db.session.commit()

# choose a user at random and create a post
posts = [random.choice(users).post(is_request=random.choice([True, False]),
                                   reward=100 * random.randint(1, 5),
                                   title=faker.text(100),
                                   body='\n'.join(faker.text(100) for i in range(random.randint(2, 5)))) for i in
         range(N_POSTS)]

tag_names = [word.capitalize() for word in faker.words(N_TAGS)]

for i in range(N_NODES):
    # choose a post at random, choose a user who is not the post creator at random, and create a node
    post = random.choice(posts)
    answerer = random.choice(users)
    answerer.add_tag(post, random.choice(tag_names).capitalize())
    while answerer == post.creator:
        answerer = random.choice(users)
    answerer.create_node(post=post, parent=random.choice(post.nodes.all()))

print(len(Post.query.all()))
print(len(Node.query.all()))

competence = [random.uniform(0.7, 0.9) for i in range(User.query.count())]
credibility = [random.uniform(0.75, 0.95) for i in range(User.query.count())]
for i in range(N_ENGAGEMENTS):
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
