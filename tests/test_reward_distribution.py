import math
import unittest
from random import Random

from app import create_app, db
from app.models import User, Post, Node, PlatformFee
from app.models.user import REP_DECAY, REP_I_DECAY


class BasicsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("TEST")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_public_buy(self):
        u1 = User(email='1', total_balance_cent=1000)
        u2 = User(email='2', total_balance_cent=1000)
        u3 = User(email='3', total_balance_cent=1000)
        u4 = User(email='4', total_balance_cent=1000)
        u5 = User(email='5', total_balance_cent=1000)
        db.session.add_all([u1, u2, u3, u4, u5])
        p = u1.create_post(post_type=Post.TYPE_BUY, price_cent=500, title='')
        n = u2.create_node(p.nodes.filter(Node.creator == u1).first())
        n = u3.create_node(n)
        n = u4.create_node(n)
        n = u5.create_node(n)
        e = u5.create_engagement(n)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u5.rate_engagement(e, True)
        self.assertEqual(u1.total_balance_cent, 500)
        self.assertEqual(u2.total_balance_cent, 1012)
        self.assertEqual(u3.total_balance_cent, 1025)
        self.assertEqual(u4.total_balance_cent, 1050)
        self.assertEqual(u5.total_balance_cent, 1363)

    def test_public_sell(self):
        u1 = User(email='1', total_balance_cent=1000)
        u2 = User(email='2', total_balance_cent=1000)
        u3 = User(email='3', total_balance_cent=1000)
        u4 = User(email='4', total_balance_cent=1000)
        u5 = User(email='5', total_balance_cent=1000)
        db.session.add_all([u1, u2, u3, u4, u5])
        p = u1.create_post(post_type=Post.TYPE_SELL, price_cent=200, title='')
        n = u2.create_node(p.nodes.filter(Node.creator == u1).first())
        n = u3.create_node(n)
        n = u4.create_node(n)
        n = u5.create_node(n)
        e = u5.create_engagement(n)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u5.rate_engagement(e, True)
        self.assertEqual(u1.total_balance_cent, 1200)
        self.assertEqual(u2.total_balance_cent, 1005)
        self.assertEqual(u3.total_balance_cent, 1010)
        self.assertEqual(u4.total_balance_cent, 1020)
        self.assertEqual(u5.total_balance_cent, 745)

    def test_private_buy(self):
        u1 = User(email='1', total_balance_cent=1000)
        u2 = User(email='2', total_balance_cent=1000)
        u3 = User(email='3', total_balance_cent=1000)
        u4 = User(email='4', total_balance_cent=1000)
        u5 = User(email='5', total_balance_cent=1000)
        db.session.add_all([u1, u2, u3, u4, u5])
        p = u1.create_post(
            post_type=Post.TYPE_BUY,
            price_cent=500,
            title='',
            is_private=True)
        n = u2.create_node(p.nodes.filter(Node.creator == u1).first())
        n = u3.create_node(n)
        n = u4.create_node(n)
        n = u5.create_node(n)
        e = u5.create_engagement(n)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u5.rate_engagement(e, True)
        self.assertEqual(u1.total_balance_cent, 500)
        self.assertEqual(u2.total_balance_cent, 1100)
        self.assertEqual(u3.total_balance_cent, 1050)
        self.assertEqual(u4.total_balance_cent, 1025)
        self.assertEqual(u5.total_balance_cent, 1275)

    def test_private_sell(self):
        u1 = User(email='1', total_balance_cent=1000)
        u2 = User(email='2', total_balance_cent=1000)
        u3 = User(email='3', total_balance_cent=1000)
        u4 = User(email='4', total_balance_cent=1000)
        u5 = User(email='5', total_balance_cent=1000)
        db.session.add_all([u1, u2, u3, u4, u5])
        p = u1.create_post(
            post_type=Post.TYPE_SELL,
            price_cent=300,
            title='',
            is_private=True,
            referral_budget_cent=200)
        n = u2.create_node(p.nodes.filter(Node.creator == u1).first(), referrer_reward_cent=40)
        n = u3.create_node(n, referrer_reward_cent=50)
        n = u4.create_node(n, referrer_reward_cent=20)
        n = u5.create_node(n, referrer_reward_cent=90)
        e = u5.create_engagement(n)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u5.rate_engagement(e, True)
        self.assertEqual(u1.total_balance_cent, 1300)
        self.assertEqual(u2.total_balance_cent, 1040)
        self.assertEqual(u3.total_balance_cent, 1050)
        self.assertEqual(u4.total_balance_cent, 1020)
        self.assertEqual(u5.total_balance_cent, 560)

    def test_reputation_public(self):
        u1 = User(email='1', total_balance_cent=10000)
        u2 = User(email='2', total_balance_cent=10000)
        u3 = User(email='3', total_balance_cent=10000)
        u4 = User(email='4', total_balance_cent=10000)
        u5 = User(email='5', total_balance_cent=10000)
        db.session.add_all([u1, u2, u3, u4, u5])

        p1 = u1.create_post(post_type=Post.TYPE_BUY, price_cent=400, title='')
        n12 = u2.create_node(p1.nodes.filter(Node.creator == u1).first())
        e = u2.create_engagement(n12)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u2.rate_engagement(e, True)
        self.assertAlmostEqual(u1.sum_x, 400)
        self.assertAlmostEqual(u2.sum_x, 400)
        self.assertAlmostEqual(u1.reputation, 1.0)
        self.assertAlmostEqual(u2.reputation, 1.0)
        self.assertEqual(u1.value_limit_cent, 700)
        self.assertEqual(u2.value_limit_cent, 700)

        n13 = u3.create_node(n12)
        e = u3.create_engagement(n13)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u3.rate_engagement(e, False)
        self.assertAlmostEqual(u1.sum_x, 400)
        self.assertAlmostEqual(u3.sum_x, 0)
        self.assertAlmostEqual(u1.reputation, 1.0)
        self.assertAlmostEqual(u3.reputation, 1.0)
        self.assertEqual(u1.value_limit_cent, 700)
        self.assertEqual(u3.value_limit_cent, 500)

        n14 = u4.create_node(n13)
        e = u4.create_engagement(n14)
        u1.accept_engagement(e)
        u1.rate_engagement(e, False)
        u4.rate_engagement(e, True)
        self.assertAlmostEqual(u1.sum_x, math.exp(-400 * REP_DECAY) * 400)
        self.assertAlmostEqual(u4.sum_x, -400)
        self.assertAlmostEqual(u1.reputation, 1.0)
        self.assertAlmostEqual(u4.reputation, -1.0)
        self.assertEqual(u1.value_limit_cent, 700)
        self.assertEqual(u4.value_limit_cent, 200)

        p2 = u2.create_post(post_type=Post.TYPE_BUY, price_cent=300, title='')
        n23 = u3.create_node(p2.nodes.filter(Node.creator == u2).first())
        e = u3.create_engagement(n23)
        u2.accept_engagement(e)
        u2.rate_engagement(e, False)
        u3.rate_engagement(e, True)
        self.assertAlmostEqual(u2.sum_x, math.exp(-300 * REP_DECAY) * 400)
        self.assertAlmostEqual(u3.sum_x, -300)
        self.assertAlmostEqual(u2.reputation, 1.0)
        self.assertAlmostEqual(u3.reputation, -1.0)
        self.assertEqual(u2.value_limit_cent, 700)
        self.assertEqual(u3.value_limit_cent, 150)

    def test_reputation_public_tie(self):
        u1 = User(email='1', total_balance_cent=10000)
        u2 = User(email='2', total_balance_cent=10000)
        u3 = User(email='3', total_balance_cent=10000)
        db.session.add_all([u1, u2, u3])

        p1 = u1.create_post(post_type=Post.TYPE_SELL, price_cent=400, title='')
        n12 = u2.create_node(p1.nodes.filter(Node.creator == u1).first())
        e = u2.create_engagement(n12)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u2.rate_engagement(e, True)
        e = u2.create_engagement(n12)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u2.rate_engagement(e, True)
        e = u2.create_engagement(n12)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u2.rate_engagement(e, True)
        n13 = u3.create_node(p1.nodes.filter(Node.creator == u1).first())
        e = u3.create_engagement(n13)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u3.rate_engagement(e, True)
        e = u3.create_engagement(n13)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u3.rate_engagement(e, True)
        e = u3.create_engagement(n13)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u3.rate_engagement(e, True)

        p2 = u2.create_post(post_type=Post.TYPE_BUY, price_cent=500, title='')
        n23 = u3.create_node(p2.nodes.filter(Node.creator == u2).first())
        e = u3.create_engagement(n23)
        u2.accept_engagement(e)
        u2.rate_engagement(e, False)
        u3.rate_engagement(e, True)
        a = -500 + math.exp(-500 * REP_DECAY) * 440 + math.exp(-940 * REP_DECAY) * 440 + math.exp(
            -1380 * REP_DECAY) * 440
        b = 500 + math.exp(-500 * REP_DECAY) * 440 + math.exp(-940 * REP_DECAY) * 440 + math.exp(
            -1380 * REP_DECAY) * 440
        self.assertAlmostEqual(u2.sum_x, a)
        self.assertAlmostEqual(u3.sum_x, a)
        self.assertAlmostEqual(u2.reputation, a / b)
        self.assertAlmostEqual(u3.reputation, a / b)
        self.assertEqual(u2.value_limit_cent, 500)
        self.assertEqual(u2.value_limit_cent, 500)

    def test_reputation_private(self):
        u1 = User(email='1', total_balance_cent=10000)
        u2 = User(email='2', total_balance_cent=10000)
        u3 = User(email='3', total_balance_cent=10000)
        u4 = User(email='4', total_balance_cent=10000)
        u5 = User(email='5', total_balance_cent=10000)
        db.session.add_all([u1, u2, u3, u4, u5])

        p1 = u1.create_post(
            post_type=Post.TYPE_SELL,
            price_cent=300,
            title='',
            is_private=True)
        n2 = u2.create_node(p1.nodes.filter(Node.creator == u1).first())
        n3 = u3.create_node(n2)
        n4 = u4.create_node(n3)
        n5 = u5.create_node(n4)

        e3 = u3.create_engagement(n3)
        e4 = u4.create_engagement(n4)
        e5 = u5.create_engagement(n5)

        u1.accept_engagement(e3)
        u1.accept_engagement(e4)
        u1.accept_engagement(e5)

        u1.rate_engagement(e3, True)
        u3.rate_engagement(e3, False)
        self.assertAlmostEqual(u1.sum_x, -(300 + 60 + 30))
        self.assertAlmostEqual(u3.sum_x, -(300 + 60 + 30))
        self.assertAlmostEqual(u1.reputation, -1.0)
        self.assertAlmostEqual(u3.reputation, -1.0)
        self.assertEqual(u1.value_limit_cent, round(0.5 * (300 + 60 + 30)))
        self.assertEqual(u3.value_limit_cent, round(0.5 * (300 + 60 + 30)))

        u1.rate_engagement(e4, False)
        u4.rate_engagement(e4, True)
        self.assertAlmostEqual(u1.sum_x, -(300 + 60 + 30))
        self.assertAlmostEqual(u4.sum_x, 0)
        self.assertAlmostEqual(u1.reputation, -1)
        self.assertAlmostEqual(u4.reputation, 1.0)
        self.assertEqual(u1.value_limit_cent, 195)
        self.assertEqual(u4.value_limit_cent, 500)

        u1.rate_engagement(e5, True)
        u5.rate_engagement(e5, True)
        a = (300 + 60 + 30 + 30 + 15) - math.exp(-435 * REP_DECAY) * 390
        self.assertAlmostEqual(u1.sum_x, a)
        self.assertAlmostEqual(u5.sum_x, 435)
        a = 1 - math.exp(-1 * REP_I_DECAY) * 1
        b = 1 + math.exp(-1 * REP_I_DECAY) * 1
        self.assertAlmostEqual(u1.reputation, a / b)
        self.assertAlmostEqual(u5.reputation, 1.0)
        self.assertEqual(u1.value_limit_cent, 195 + round(435 * 0.1))
        self.assertEqual(u5.value_limit_cent, 500 + round(435 * 0.5))

    def test_leakage(self):
        u1 = User(email='1', total_balance_cent=10000)
        u2 = User(email='2', total_balance_cent=10000)
        u3 = User(email='3', total_balance_cent=10000)
        u4 = User(email='4', total_balance_cent=10000)
        u5 = User(email='5', total_balance_cent=10000)
        users = [u1, u2, u3, u4, u5]
        db.session.add_all(users)
        p1b = u1.create_post(post_type=Post.TYPE_BUY, price_cent=100, title='')
        p1s = u1.create_post(post_type=Post.TYPE_SELL, price_cent=500, title='')
        p2b = u2.create_post(post_type=Post.TYPE_BUY, price_cent=200, title='')
        p2s = u2.create_post(post_type=Post.TYPE_SELL, price_cent=400, title='')
        p3b = u3.create_post(post_type=Post.TYPE_BUY, price_cent=300, title='')
        p3s = u3.create_post(post_type=Post.TYPE_SELL, price_cent=300, title='')
        p4b = u4.create_post(post_type=Post.TYPE_BUY, price_cent=400, title='')
        p4s = u4.create_post(post_type=Post.TYPE_SELL, price_cent=200, title='')
        p5b = u5.create_post(post_type=Post.TYPE_BUY, price_cent=500, title='')
        p5s = u5.create_post(post_type=Post.TYPE_SELL, price_cent=100, title='')
        posts = [p1b, p1s, p2b, p2s, p3b, p3s, p4b, p4s, p5b, p5s]

        random = Random(1)
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

        initial_balance = 5 * 100.0
        final_balance = sum([u.total_balance for u in users])
        platform_fees = sum([fee.amount for fee in PlatformFee.query.all()])
        self.assertAlmostEqual(initial_balance - final_balance, platform_fees)
