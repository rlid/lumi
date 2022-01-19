import time
import unittest

from app import create_app, db
from app.models import User


class UserModelTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_password_setter(self):
        u = User(password="cat")
        self.assertTrue(u.password_hash is not None)

    def test_no_password_getter(self):
        u = User(password="cat")
        with self.assertRaises(AttributeError):
            u.password

    def test_password_verification(self):
        u = User(password="cat")
        self.assertTrue(u.verify_password("cat"))
        self.assertFalse(u.verify_password("dog"))

    def test_password_salts_are_random(self):
        u1 = User(password="cat")
        u2 = User(password="cat")
        self.assertFalse(u1.password_hash == u2.password_hash)

    def test_valid_tokens(self):
        u = User()
        db.session.add(u)
        db.session.commit()
        token1 = u.generate_token(action="dummy")
        self.assertTrue(u.verify_token(token1, action="dummy"))
        token2 = u.generate_token(action="dummy", expiration=60)
        self.assertTrue(u.verify_token(token2, action="dummy"))

    def test_invalid_tokens(self):
        u1 = User()
        u2 = User()
        db.session.add_all([u1, u2])
        db.session.commit()

        token1 = u1.generate_token(action="dummy", expiration=1)
        time.sleep(2)
        self.assertFalse(u1.verify_token(token1, action="dummy"))

        token2 = u2.generate_token(action="dummy")
        self.assertFalse(u1.verify_token(token2, action="dummy"))
