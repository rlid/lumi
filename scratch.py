from app import create_app, db
from app.models.user import User, Quest, Node

app = create_app("TEST")
app_context = app.app_context()
app_context.push()
db.create_all()

u1 = User(email='1', account_balance=100)
u2 = User(email='2')
u3 = User(email='3')
u4 = User(email='4')
u5 = User(email='5')
u6 = User(email='6')
db.session.add_all([u1, u2, u3, u4, u5, u6])

q = u1.create_quest(value=100, title='title')

n1 = u1.create_node(q)
n2 = u2.create_node(q)
n3 = u3.create_node(q, parent=n2)
n4 = u4.create_node(q, parent=n2)
n5 = u5.create_node(q, parent=n4)
n6 = u6.create_node(q, parent=n5)

for n in Node.query.all():
    print(n.nodes_before_inc().all())


u6.request_engagement(n6, 0.2)
u1.accept_engagement(n6)
u1.rate_engagement(n6, success=True)
u6.rate_engagement(n6, success=True)

print(u1)
print(u2)
print(u3)
print(u4)
print(u5)
print(u6)

db.session.remove()
db.drop_all()
app_context.pop()
