import unittest

from app import create_app, db
from app.models import User, Post


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

    def test_buy_post_standard_mode(self):
        poster = User(email='poster', total_balance_cent=1000)
        referrer = User(email='contributor', total_balance_cent=1000)
        other_user = User(email='other_user', total_balance_cent=1000)
        db.session.add_all([poster, referrer, other_user])

        post = poster.create_post(post_type=Post.TYPE_BUY, price_cent=500, title='')
        root_node = post.nodes.all()[0]
        node = referrer.create_node(root_node)
        self.assertAlmostEqual(root_node.display_value(poster), 5)
        self.assertAlmostEqual(root_node.display_value(referrer), 5 - 0.1 * 5)
        self.assertAlmostEqual(root_node.display_value(other_user), 5 - 0.1 * 5)

        self.assertAlmostEqual(root_node.display_referrer_reward(poster), 0)
        self.assertAlmostEqual(root_node.display_referrer_reward(referrer), 0.5 * 0.2 * 5)
        self.assertAlmostEqual(root_node.display_referrer_reward(other_user), 0.5 * 0.2 * 5)

        self.assertAlmostEqual(node.display_value(poster), 5)
        self.assertAlmostEqual(node.display_value(referrer), 5 - 0.1 * 5)
        self.assertAlmostEqual(node.display_value(other_user), 5 - 0.1 * 5 - 0.5 * 0.2 * 5)

        self.assertAlmostEqual(node.display_referrer_reward(poster), 0)
        self.assertAlmostEqual(node.display_referrer_reward(referrer), 0.5 * 0.2 * 5)
        self.assertAlmostEqual(node.display_referrer_reward(other_user), 0.5 * 0.2 * 5)

    def test_sell_post_standard_mode(self):
        poster = User(email='poster', total_balance_cent=1000)
        referrer = User(email='contributor', total_balance_cent=1000)
        other_user = User(email='other_user', total_balance_cent=1000)
        db.session.add_all([poster, referrer, other_user])

        post = poster.create_post(post_type=Post.TYPE_SELL, price_cent=500, title='')
        root_node = post.nodes.all()[0]
        node = referrer.create_node(root_node)
        self.assertAlmostEqual(root_node.display_value(poster), 5)
        self.assertAlmostEqual(root_node.display_value(referrer), 5 + 0.1 * 5)
        self.assertAlmostEqual(root_node.display_value(other_user), 5 + 0.1 * 5)

        self.assertAlmostEqual(root_node.display_referrer_reward(poster), 0)
        self.assertAlmostEqual(root_node.display_referrer_reward(referrer), 0.5 * 0.2 * 5)
        self.assertAlmostEqual(root_node.display_referrer_reward(other_user), 0.5 * 0.2 * 5)

        self.assertAlmostEqual(node.display_value(poster), 5)
        self.assertAlmostEqual(node.display_value(referrer), 5 + 0.1 * 5)
        self.assertAlmostEqual(node.display_value(other_user), 5 + 0.1 * 5 + 0.5 * 0.2 * 5)

        self.assertAlmostEqual(node.display_referrer_reward(poster), 0)
        self.assertAlmostEqual(node.display_referrer_reward(referrer), 0.5 * 0.2 * 5)
        self.assertAlmostEqual(node.display_referrer_reward(other_user), 0.5 * 0.2 * 5)


    def test_buy_post_social_media_mode(self):
        poster = User(email='poster', total_balance_cent=1000)
        referrer = User(email='contributor', total_balance_cent=1000)
        other_user = User(email='other_user', total_balance_cent=1000)
        db.session.add_all([poster, referrer, other_user])

        post = poster.create_post(post_type=Post.TYPE_BUY, price_cent=500, title='', social_media_mode=True)
        root_node = post.nodes.all()[0]
        node = referrer.create_node(root_node)
        self.assertAlmostEqual(root_node.display_value(poster), 5)
        self.assertAlmostEqual(root_node.display_value(referrer), 5 - 0.1 * 5)
        self.assertAlmostEqual(root_node.display_value(other_user), 5 - 0.1 * 5)

        self.assertAlmostEqual(root_node.display_referrer_reward(poster), 0)
        self.assertAlmostEqual(root_node.display_referrer_reward(referrer), 0.5 * 0.4 * 5)
        self.assertAlmostEqual(root_node.display_referrer_reward(other_user), 0.5 * 0.4 * 5)

        self.assertAlmostEqual(node.display_value(poster), 5)
        self.assertAlmostEqual(node.display_value(referrer), 5 - 0.1 * 5)
        self.assertAlmostEqual(node.display_value(other_user), 5 - 0.1 * 5 - 0.5 * 0.4 * 5)

        self.assertAlmostEqual(node.display_referrer_reward(poster), 0)
        self.assertAlmostEqual(node.display_referrer_reward(referrer), 0.5 * 0.4 * 5)
        self.assertAlmostEqual(node.display_referrer_reward(other_user), 0.5 * 0.5 * 0.4 * 5)


    def test_sell_post_social_media_mode(self):
        poster = User(email='poster', total_balance_cent=1000)
        referrer = User(email='contributor', total_balance_cent=1000)
        other_user = User(email='other_user', total_balance_cent=1000)
        db.session.add_all([poster, referrer, other_user])

        post = poster.create_post(post_type=Post.TYPE_SELL, price_cent=500, title='', social_media_mode=True)
        root_node = post.nodes.all()[0]
        node = referrer.create_node(root_node)
        self.assertAlmostEqual(root_node.display_value(poster), 5)
        self.assertAlmostEqual(root_node.display_value(referrer), 5 + 0.1 * 5)
        self.assertAlmostEqual(root_node.display_value(other_user), 5 + 0.1 * 5)

        self.assertAlmostEqual(root_node.display_referrer_reward(poster), 0)
        self.assertAlmostEqual(root_node.display_referrer_reward(referrer), 0.5 * 0.4 * 5)
        self.assertAlmostEqual(root_node.display_referrer_reward(other_user), 0.5 * 0.4 * 5)

        self.assertAlmostEqual(node.display_value(poster), 5)
        self.assertAlmostEqual(node.display_value(referrer), 5 + 0.1 * 5)
        self.assertAlmostEqual(node.display_value(other_user), 5 + 0.1 * 5 + 0.5 * 0.4 * 5)

        self.assertAlmostEqual(node.display_referrer_reward(poster), 0)
        self.assertAlmostEqual(node.display_referrer_reward(referrer), 0.5 * 0.4 * 5)
        self.assertAlmostEqual(node.display_referrer_reward(other_user), 0.5 * 0.5 * 0.4 * 5)
