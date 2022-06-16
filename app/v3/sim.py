import random

from faker import Faker

from app import db, create_app
from app.models import User
from app.v3.models import Product

faker = Faker()


def sim0():
    p1 = Product(name=faker.company())
    p2 = Product(name=faker.company())
    db.session.add_all([p1, p2])
    u1 = User(email='1')
    u2 = User(email='2')
    u3 = User(email='3')
    u4 = User(email='4')
    u5 = User(email='5')
    u6 = User(email='6')
    u7 = User(email='7')
    u8 = User(email='8')
    u9 = User(email='9')
    u10 = User(email='10')
    u11 = User(email='11')
    u12 = User(email='12')

    db.session.add_all([u1, u2, u3, u4, u5, u6, u7, u8,u9, u10, u11, u12])
    u1.rate_product(product=p1, score=2)
    u2.rate_product(product=p1, score=-2)
    u3.rate_product(product=p1, score=2)
    u4.rate_product(product=p1, score=-2)
    u5.rate_product(product=p1, score=2)
    u6.rate_product(product=p1, score=-2)
    u7.rate_product(product=p1, score=2)
    u8.rate_product(product=p1, score=-2)
    u9.rate_product(product=p1, score=2)
    u10.rate_product(product=p1, score=-2)
    u11.rate_product(product=p1, score=2)
    u12.rate_product(product=p1, score=-2)
    u1.rate_product(product=p2, score=2)
    u2.rate_product(product=p2, score=-2)
    # u3.rate_product(product=p2, score=-2)
    # u4.rate_product(product=p2, score=-2)
    # u5.rate_product(product=p2, score=-2)
    # u6.rate_product(product=p2, score=2)
    # u7.rate_product(product=p2, score=2)
    # u8.rate_product(product=p2, score=2)
    # u9.rate_product(product=p2, score=2)
    # u10.rate_product(product=p2, score=2)
    # u11.rate_product(product=p2, score=2)
    # u12.rate_product(product=p2, score=2)
    db.session.commit()


def sim1(n_product=100, n_user=100):
    products = [Product(name=str(i), state_positive=1) for i in range(n_product)]
    for product in products:
        db.session.add(product)

    users = [User(email=str(i), state_agree=random.uniform(0.2, 0.8)) for i in range(n_user)]

    for user in users:
        db.session.add(user)
        for product in products:
            score = 2 if random.uniform(0, 1) < user.state_agree else -2
            user.rate_product(product=product, score=score)
            print(f'User {user.email} rated Product {product.name} {score}.')

    db.session.commit()


app = create_app("DEV")
app_context = app.app_context()
app_context.push()
db.drop_all()
db.create_all()
sim1()
for p in Product.query.all():
    print(f'Product {p.name}: state={p.state_positive}, estimate={p.rating}')

for u in User.query.all():
    print(f'User {u.email}: state={u.state_agree}, estimate={u.p_agree}')
