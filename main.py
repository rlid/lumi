import os

from app import create_app, db
from app.models.user import User, Post, Node, PostTag

app = create_app(os.getenv("FLASK_CONFIG") or "DEFAULT")


@app.shell_context_processor
def make_shell_context():
    return dict(db=db, User=User, Post=Post, Node=Node, PostTag=PostTag)


@app.cli.command()
def test():
    import unittest
    tests = unittest.TestLoader().discover("tests")
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080, debug=True)
    # app.run(host="0.0.0.0", port=8080, debug=True, ssl_context="adhoc")
