import unittest
from random import Random

from app import create_app, db
from app.models import User, Post, Node, Engagement, PlatformFee


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

    def test_referral(self):
        u1 = User(email='1', total_balance=10)
        u2 = User(email='2', total_balance=10)
        u3 = User(email='3', total_balance=10)
        u4 = User(email='4', total_balance=10)
        u5 = User(email='5', total_balance=10)
        db.session.add_all([u1, u2, u3, u4, u5])
        p = u1.create_post(type=Post.TYPE_BUY, reward=5, title='')
        n = u2.create_node(p.nodes.filter(Node.creator == u1).first())
        u2.create_message(n, 'u2')
        n = u3.create_node(n)
        u3.create_message(n, 'u3')
        n = u4.create_node(n)
        u4.create_message(n, 'u4')
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

    def test_leakage(self):
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
