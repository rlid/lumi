import math
import unittest
from random import Random

from app import create_app, db
from app.models import User, Post, Node, PlatformFee
from app.models.user import REP_DECAY


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

    def test_standard_mode_buy(self):
        u1 = User(email='1', total_balance_cent=1000)
        u2 = User(email='2', total_balance_cent=1000)
        u3 = User(email='3', total_balance_cent=1000)
        u4 = User(email='4', total_balance_cent=1000)
        u5 = User(email='5', total_balance_cent=1000)
        db.session.add_all([u1, u2, u3, u4, u5])
        p = u1.create_post(type=Post.TYPE_BUY, reward_cent=500, title='')
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

    def test_standard_mode_sell(self):
        u1 = User(email='1', total_balance_cent=1000)
        u2 = User(email='2', total_balance_cent=1000)
        u3 = User(email='3', total_balance_cent=1000)
        u4 = User(email='4', total_balance_cent=1000)
        u5 = User(email='5', total_balance_cent=1000)
        db.session.add_all([u1, u2, u3, u4, u5])
        p = u1.create_post(type=Post.TYPE_SELL, reward_cent=500, title='')
        n = u2.create_node(p.nodes.filter(Node.creator == u1).first())
        n = u3.create_node(n)
        n = u4.create_node(n)
        n = u5.create_node(n)
        e = u5.create_engagement(n)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u5.rate_engagement(e, True)
        self.assertEqual(u1.total_balance_cent, 1363)
        self.assertEqual(u2.total_balance_cent, 1012)
        self.assertEqual(u3.total_balance_cent, 1025)
        self.assertEqual(u4.total_balance_cent, 1050)
        self.assertEqual(u5.total_balance_cent, 500)

    def test_social_media_mode_buy(self):
        u1 = User(email='1', total_balance_cent=1000)
        u2 = User(email='2', total_balance_cent=1000)
        u3 = User(email='3', total_balance_cent=1000)
        u4 = User(email='4', total_balance_cent=1000)
        u5 = User(email='5', total_balance_cent=1000)
        db.session.add_all([u1, u2, u3, u4, u5])
        p = u1.create_post(
            type=Post.TYPE_BUY,
            reward_cent=500,
            title='',
            social_media_mode=True)
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

    def test_social_media_mode_sell(self):
        u1 = User(email='1', total_balance_cent=1000)
        u2 = User(email='2', total_balance_cent=1000)
        u3 = User(email='3', total_balance_cent=1000)
        u4 = User(email='4', total_balance_cent=1000)
        u5 = User(email='5', total_balance_cent=1000)
        db.session.add_all([u1, u2, u3, u4, u5])
        p = u1.create_post(
            type=Post.TYPE_SELL,
            reward_cent=300,
            title='',
            social_media_mode=True,
            referral_budget_cent=200)
        n = u2.create_node(p.nodes.filter(Node.creator == u1).first(), 40)
        n = u3.create_node(n, referral_reward_cent=50)
        n = u4.create_node(n, referral_reward_cent=20)
        n = u5.create_node(n, referral_reward_cent=90)
        e = u5.create_engagement(n)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u5.rate_engagement(e, True)
        self.assertEqual(u1.total_balance_cent, 1270)
        self.assertEqual(u2.total_balance_cent, 1040)
        self.assertEqual(u3.total_balance_cent, 1050)
        self.assertEqual(u4.total_balance_cent, 1020)
        self.assertEqual(u5.total_balance_cent, 590)

    def test_reputation_standard_mode(self):
        u1 = User(email='1', total_balance_cent=10000)
        u2 = User(email='2', total_balance_cent=10000)
        u3 = User(email='3', total_balance_cent=10000)
        u4 = User(email='4', total_balance_cent=10000)
        u5 = User(email='5', total_balance_cent=10000)
        db.session.add_all([u1, u2, u3, u4, u5])

        p1 = u1.create_post(type=Post.TYPE_BUY, reward_cent=400, title='')
        n12 = u2.create_node(p1.nodes.filter(Node.creator == u1).first())
        e = u2.create_engagement(n12)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u2.rate_engagement(e, True)
        self.assertAlmostEqual(u1.sum_x, 400)
        self.assertAlmostEqual(u2.sum_x, 400)
        self.assertAlmostEqual(u1.reputation, 1.0)
        self.assertAlmostEqual(u2.reputation, 1.0)
        self.assertEqual(u1.reward_limit_cent, 700)
        self.assertEqual(u2.reward_limit_cent, 700)

        n13 = u3.create_node(n12)
        e = u3.create_engagement(n13)
        u1.accept_engagement(e)
        u1.rate_engagement(e, True)
        u3.rate_engagement(e, False)
        self.assertAlmostEqual(u1.sum_x, 200 + math.exp(-200 * REP_DECAY) * 400)
        self.assertAlmostEqual(u3.sum_x, 200)
        self.assertAlmostEqual(u1.reputation, 1.0)
        self.assertAlmostEqual(u3.reputation, 1.0)
        self.assertEqual(u1.reward_limit_cent, 800)
        self.assertEqual(u3.reward_limit_cent, 600)

        n14 = u4.create_node(n13)
        e = u4.create_engagement(n14)
        u1.accept_engagement(e)
        u1.rate_engagement(e, False)
        u4.rate_engagement(e, True)
        self.assertAlmostEqual(u1.sum_x, math.exp(-400 * REP_DECAY) * 200 + math.exp(-600 * REP_DECAY) * 400)
        self.assertAlmostEqual(u4.sum_x, -400)
        self.assertAlmostEqual(u1.reputation, 1.0)
        self.assertAlmostEqual(u4.reputation, -1.0)
        self.assertEqual(u1.reward_limit_cent, 800)
        self.assertEqual(u4.reward_limit_cent, 200)

        p2 = u2.create_post(type=Post.TYPE_BUY, reward_cent=300, title='')
        n23 = u3.create_node(p2.nodes.filter(Node.creator == u2).first())
        e = u3.create_engagement(n23)
        u2.accept_engagement(e)
        u2.rate_engagement(e, False)
        u3.rate_engagement(e, True)
        a = -300 + math.exp(-300 * REP_DECAY) * 200
        b = 300 + math.exp(-300 * REP_DECAY) * 200
        self.assertAlmostEqual(u2.sum_x, math.exp(-300 * REP_DECAY) * 400)
        self.assertAlmostEqual(u3.sum_x, -300 + math.exp(-300 * REP_DECAY) * 200)
        self.assertAlmostEqual(u2.reputation, 1.0)
        self.assertAlmostEqual(u3.reputation, a / b)
        self.assertEqual(u2.reward_limit_cent, 700)
        self.assertEqual(u3.reward_limit_cent, 225)

    def test_reputation_standard_mode_tie(self):
        u1 = User(email='1', total_balance_cent=10000)
        u2 = User(email='2', total_balance_cent=10000)
        u3 = User(email='3', total_balance_cent=10000)
        db.session.add_all([u1, u2, u3])

        p1 = u1.create_post(type=Post.TYPE_SELL, reward_cent=400, title='')
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

        p2 = u2.create_post(type=Post.TYPE_BUY, reward_cent=500, title='')
        n23 = u3.create_node(p2.nodes.filter(Node.creator == u2).first())
        e = u3.create_engagement(n23)
        u2.accept_engagement(e)
        u2.rate_engagement(e, False)
        u3.rate_engagement(e, True)
        a = -500 + math.exp(-500 * REP_DECAY) * 400 + math.exp(-900 * REP_DECAY) * 400 + math.exp(
            -1300 * REP_DECAY) * 400
        b = 500 + math.exp(-500 * REP_DECAY) * 400 + math.exp(-900 * REP_DECAY) * 400 + math.exp(
            -1300 * REP_DECAY) * 400
        self.assertAlmostEqual(u2.sum_x, a)
        self.assertAlmostEqual(u3.sum_x, a)
        self.assertAlmostEqual(u2.reputation, a / b)
        self.assertAlmostEqual(u3.reputation, a / b)
        self.assertEqual(u2.reward_limit_cent, 500)
        self.assertEqual(u2.reward_limit_cent, 500)

    def test_reputation_social_media_mode(self):
        u1 = User(email='1', total_balance_cent=10000)
        u2 = User(email='2', total_balance_cent=10000)
        u3 = User(email='3', total_balance_cent=10000)
        u4 = User(email='4', total_balance_cent=10000)
        u5 = User(email='5', total_balance_cent=10000)
        db.session.add_all([u1, u2, u3, u4, u5])

        p1 = u1.create_post(
            type=Post.TYPE_SELL,
            reward_cent=300,
            title='',
            social_media_mode=True)
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
        self.assertAlmostEqual(u1.sum_x, -360)
        self.assertAlmostEqual(u3.sum_x, -360)
        self.assertAlmostEqual(u1.reputation, -1.0)
        self.assertAlmostEqual(u3.reputation, -1.0)
        self.assertEqual(u1.reward_limit_cent, 180)
        self.assertEqual(u3.reward_limit_cent, 180)

        u1.rate_engagement(e4, False)
        u4.rate_engagement(e4, True)
        a = 195 - math.exp(-195 * REP_DECAY) * 360
        b = 195 + math.exp(-195 * REP_DECAY) * 360
        self.assertAlmostEqual(u1.sum_x, a)
        self.assertAlmostEqual(u4.sum_x, 195)
        self.assertAlmostEqual(u1.reputation, a / b)
        self.assertAlmostEqual(u4.reputation, 1.0)
        self.assertEqual(u1.reward_limit_cent, 190)
        self.assertEqual(u4.reward_limit_cent, 598)

        u1.rate_engagement(e5, True)
        u5.rate_engagement(e5, True)
        a = 405 + math.exp(-405 * REP_DECAY) * 195 - math.exp(-600 * REP_DECAY) * 360
        b = 405 + math.exp(-405 * REP_DECAY) * 195 + math.exp(-600 * REP_DECAY) * 360
        self.assertAlmostEqual(u1.sum_x, 405 + math.exp(-405 * REP_DECAY) * 195 - math.exp(-600 * REP_DECAY) * 360)
        self.assertAlmostEqual(u5.sum_x, 405)
        self.assertAlmostEqual(u1.reputation, a / b)
        self.assertAlmostEqual(u5.reputation, 1.0)
        self.assertEqual(u1.reward_limit_cent, 271)
        self.assertEqual(u5.reward_limit_cent, 702)

    def test_leakage(self):
        u1 = User(email='1', total_balance_cent=10000)
        u2 = User(email='2', total_balance_cent=10000)
        u3 = User(email='3', total_balance_cent=10000)
        u4 = User(email='4', total_balance_cent=10000)
        u5 = User(email='5', total_balance_cent=10000)
        users = [u1, u2, u3, u4, u5]
        db.session.add_all(users)
        p1b = u1.create_post(type=Post.TYPE_BUY, reward_cent=100, title='')
        p1s = u1.create_post(type=Post.TYPE_SELL, reward_cent=500, title='')
        p2b = u2.create_post(type=Post.TYPE_BUY, reward_cent=200, title='')
        p2s = u2.create_post(type=Post.TYPE_SELL, reward_cent=400, title='')
        p3b = u3.create_post(type=Post.TYPE_BUY, reward_cent=300, title='')
        p3s = u3.create_post(type=Post.TYPE_SELL, reward_cent=300, title='')
        p4b = u4.create_post(type=Post.TYPE_BUY, reward_cent=400, title='')
        p4s = u4.create_post(type=Post.TYPE_SELL, reward_cent=200, title='')
        p5b = u5.create_post(type=Post.TYPE_BUY, reward_cent=500, title='')
        p5s = u5.create_post(type=Post.TYPE_SELL, reward_cent=100, title='')
        posts = [p1b, p1s, p2b, p2s, p3b, p3s, p4b, p4s, p5b, p5s]

        random = Random(1)
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

        initial_balance = 5 * 100.0
        final_balance = sum([u.total_balance for u in users])
        platform_fees = sum([fee.amount for fee in PlatformFee.query.all()])
        self.assertAlmostEqual(initial_balance - final_balance, platform_fees)


if __name__ == '__main__':
    unittest.main()
