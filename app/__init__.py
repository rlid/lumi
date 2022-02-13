from authlib.integrations.flask_client import OAuth
from flask import Flask
from flask_bootstrap import Bootstrap5
from flask_login import LoginManager, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_moment import Moment
from flask_mobility import Mobility
from flask_socketio import SocketIO
from flask_sock import Sock

from config import config
from utils.authlib_ext import ApplePrivateKeyJWT


db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
bootstrap = Bootstrap5()
oauth = OAuth()
moment = Moment()
mobility = Mobility()
socketio = SocketIO()
sock = Sock()


def create_app(config_name):
    app = Flask(__name__)
    app_config = config[config_name]
    app.config.from_object(app_config)
    app_config.init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    bootstrap.init_app(app)
    oauth.init_app(app)
    moment.init_app(app)
    mobility.init_app(app)
    socketio.init_app(app)

    oauth.register(
        name='google',
        client_kwargs={'scope': 'openid email profile'}
    )

    oauth.register(
        name='apple',
        # response_mode must be form_post when name or email scope is requested, as required by Apple:
        authorize_params={'response_mode': 'form_post'},
        token_endpoint_auth_method=ApplePrivateKeyJWT(apple_key_id=app_config.APPLE_KEY_ID,
                                                      apple_team_id=app_config.APPLE_TEAM_ID),
        client_kwargs={'scope': 'openid email name'}
    )

    from .main import main as main_blueprint
    app.register_blueprint(main_blueprint)

    from .auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')

    sock.init_app(app)
    return app
