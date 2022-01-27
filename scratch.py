from app import create_app, db
from app.models.user import User, Quest, Node

app = create_app("TEST")
app_context = app.app_context()
app_context.push()
db.create_all()

u1 = User(email='a')
u2 = User(email='b')
u3 = User(email='c')
u4 = User(email='d')
u5 = User(email='e')
u6 = User(email='f')
db.session.add_all([u1, u2, u3, u4, u5, u6])

q = u1.create_quest('title')

n1 = u1.create_node(q)
n2 = u2.create_node(q)
n3 = u3.create_node(q, parent=n2)
n4 = u4.create_node(q, parent=n2)
n5 = u5.create_node(q, parent=n4)
n6 = u6.create_node(q, parent=n5)

for n in Node.query.all():
    print(n.nodes_before_inc().all())


db.session.remove()
db.drop_all()
app_context.pop()
