import os

from app import create_app, db, socketio
from app.models.user import User, Post, Node, Engagement, PostTag, Tag, Message

application = create_app(os.getenv('FLASK_CONFIG') or 'DEFAULT')


@application.shell_context_processor
def make_shell_context():
    return dict(
        db=db,
        User=User,
        Post=Post,
        Node=Node,
        Engagement=Engagement,
        PostTag=PostTag,
        Tag=Tag,
        Message=Message
    )


@application.cli.command()
def test():
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    socketio.run(application, host='192.168.0.95', port=8080, debug=True)
    # app.run(host="0.0.0.0", port=8080, debug=True)
