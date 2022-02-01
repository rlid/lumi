import random
from sqlalchemy import and_
from app import create_app, db
from app.models.user import User, Quest, Node

app = create_app("TEST")
app_context = app.app_context()
app_context.push()
db.create_all()

N_USERS = 10

users = [User(email=str(i), account_balance=10000) for i in range(N_USERS)]
db.session.add_all(users)
db.session.commit()

# choose a user at random and create a quest
quests = [random.choice(users).create_quest(value=random.randint(50, 500), title='title') for i in range(100)]

for i in range(200):
    # choose a quest at random, choose a user who is not the quest creator at random, and create a node
    quest = random.choice(quests)
    answerer = random.choice(users)
    while answerer == quest.creator:
        answerer = random.choice(users)
    answerer.create_node(quest=quest, parent=random.choice(quest.nodes.all()))

print(len(Quest.query.all()))
print(len(Node.query.all()))

competence = [random.uniform(0.91, 0.92) for i in range(N_USERS)]
credibility = [random.uniform(0.91, 0.92) for i in range(N_USERS)]
for i in range(100):
    # choose a node which is not an asker node at random, and make engagement
    node = random.choice(Node.query.filter(Node.parent != None).all())
    while node.state != Node.STATE_OPEN:
        node = random.choice(Node.query.filter(Node.parent != None).all())
    answerer = node.creator
    answerer.request_engagement(node, reward_share=.2)
    node.quest.creator.accept_engagement(node)
    actual_success = random.uniform(0, 1) < competence[int(answerer.id)-1]
    answerer_claim = actual_success
    if not actual_success and random.uniform(0, 1) > credibility[int(answerer.id)-1]:
        answerer_claim = True
    asker_claim = actual_success
    if actual_success and random.uniform(0, 1) > credibility[int(node.quest.creator_id)-1]:
        asker_claim = False
    answerer.rate_engagement(node, success=answerer_claim)
    node.quest.creator.rate_engagement(node, success=asker_claim)

print(answerer.nodes_created.filter(and_(Node.parent != None,
                                         Node.state == Node.STATE_ENGAGEMENT_COMPLETED,
                                         Node.rating_by_asker == 1)).count())

print(answerer.nodes_created.filter(and_(Node.parent != None,
                                         Node.state == Node.STATE_ENGAGEMENT_COMPLETED)).count())

db.session.remove()
db.drop_all()
app_context.pop()
