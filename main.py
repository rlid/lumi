import logging
import os

from app import create_app, db, socketio
from app.models import PlatformFee, User, Post, Node, Engagement, PostTag, Tag, Message, Feedback

app = create_app(os.getenv('FLASK_CONFIG') or 'DEFAULT')
app.logger.setLevel(logging.INFO)

@app.shell_context_processor
def make_shell_context():
    return dict(
        db=db,
        User=User,
        Post=Post,
        Node=Node,
        Engagement=Engagement,
        PostTag=PostTag,
        Tag=Tag,
        Message=Message,
        PlatformFee=PlatformFee,
        Feedback=Feedback
    )


@app.cli.command()
def test():
    import unittest
    tests = unittest.TestLoader().discover('tests')
    unittest.TextTestRunner(verbosity=2).run(tests)


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=80, debug=True)
    # app.run(host="0.0.0.0", port=8080, debug=True)
