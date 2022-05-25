import stripe
from authlib.integrations.flask_client import OAuth
from flask import Flask
from flask_login import LoginManager
from flask_mobility import Mobility
from flask_moment import Moment
from flask_socketio import SocketIO
from flask_sqlalchemy import SQLAlchemy
from flask_talisman import Talisman
from flask_qrcode import QRcode
from flask_minify import Minify

from config import config
from utils.authlib_ext import ApplePrivateKeyJWT
from utils.uuid_converter import UUIDConverter

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'
oauth = OAuth()
moment = Moment()
mobility = Mobility()
socketio = SocketIO()
qrcode = QRcode()
talisman = Talisman()
minify = Minify()

csp = {
    'default-src': [
        '\'unsafe-inline\' \'self\' data:',
        'wss://lumiask.com',
        '*.jsdelivr.net',
        '*.cloudflare.com',
        '*.unpkg.com',
        '*.toast.com',
        '*.googletagmanager.com',
        '*.google-analytics.com',
        '*.hotjar.com',
        '*.small.chat',
        'wss://*.hotjar.com'
    ]
}


def create_app(config_name='DEV'):
    app = Flask(__name__)
    app_config = config[config_name]
    app.config.from_object(app_config)
    app_config.init_app(app)

    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)
    moment.init_app(app)
    mobility.init_app(app)
    socketio.init_app(app)
    qrcode.init_app(app)
    minify.init_app(app)
    talisman.init_app(
        app,
        force_https=app_config.FORCE_HTTPS,
        content_security_policy=csp,
        content_security_policy_report_only=True,
        content_security_policy_report_uri='/csp-report',
        session_cookie_samesite='None'  # need this to be None for Sign in with Apple to work. See
        # https://www.bscotch.net/post/sign-in-with-apple-implementation-hurdles
    )

    app.url_map.converters['uuid'] = UUIDConverter

    stripe.api_key = app.config['STRIPE_SECRET_KEY']

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

    from .open2chat import open2chat as open2chat_blueprint
    app.register_blueprint(open2chat_blueprint, url_prefix='/open2chat')

    return app
