import os

from sqlalchemy.engine.url import URL

import utils.email

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    APP_VER = '20220320_1420'
    APP_NAME = 'LumiAsk'
    GOOGLE_SERVER_METADATA_URL = 'https://accounts.google.com/.well-known/openid-configuration'
    APPLE_SERVER_METADATA_URL = 'https://appleid.apple.com/.well-known/openid-configuration'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SITE_RID_NBYTES = 32
    SITE_RID_HASH_DIGEST_SIZE = 32

    EMAIL_SENDER = utils.email.send_email_aws if os.environ.get('EMAIL_SENDER') == 'AWS' else (
        utils.email.send_email_sg if os.environ.get('EMAIL_SENDER') == "SendGrid" else
        utils.email.send_email_dummy
    )

    GOOGLE_ANALYTICS_MEASUREMENT_ID = os.environ.get('GOOGLE_ANALYTICS_MEASUREMENT_ID', 'G-1NZF9TXT5X')
    GOOGLE_CLIENT_ID = os.environ.get(
        'GOOGLE_CLIENT_ID',
        '175206125409-9kun97nija8cvt0k8f71j8cb4vidb8n4.apps.googleusercontent.com'
    )
    APPLE_CLIENT_ID = os.environ.get('APPLE_CLIENT_ID', 'com.lumiask.client')
    APPLE_TEAM_ID = os.environ.get('APPLE_TEAM_ID', '3WT485YTP5')
    APPLE_KEY_ID = os.environ.get('APPLE_KEY_ID', 'V79GWHFDH4')

    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', '').lower() == 'true'

    SECRET_KEY = os.environ.get('SECRET_KEY', '')  # environment variable
    STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', '')  # environment variable
    STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')  # environment variable
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')  # environment variable
    APPLE_CLIENT_SECRET = os.environ.get('APPLE_CLIENT_SECRET', '').replace('|', '\n')  # environment variable
    # For Sign in with Apple, the client secret is dynamic - it is a JWT generated using a private key issued by Apple.
    # This variable stores the private key, and this convention is assumed by Authlib and auth_utils.ApplePrivateKeyJWT

    STRIPE_PRICE_5 = os.environ.get('STRIPE_PRICE_5', 'price_1KWgD0GoAMQGbjHHUBRINR2I')
    STRIPE_PRICE_10 = os.environ.get('STRIPE_PRICE_10', 'price_1KWkE2GoAMQGbjHHKOP6j5Be')
    STRIPE_PRICE_20 = os.environ.get('STRIPE_PRICE_20', 'price_1KWkEhGoAMQGbjHHdwIdNHvO')

    @staticmethod
    def init_app(app):
        pass


class TestConfig(Config):
    APP_VER = 'TEST-' + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = '{server_type}+{driver}://{username}:{password}@{hostname}:{port}/{database}'.format(
        server_type='postgresql',
        driver='pg8000',
        username=os.environ.get('DB_USERNAME', 'postgres'),
        password=os.environ.get('DB_PASSWORD'),
        hostname=os.environ.get('DB_HOSTNAME', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        database='testdb')


class DevConfig(Config):
    APP_VER = 'DEV-' + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = '{server_type}+{driver}://{username}:{password}@{hostname}:{port}/{database}'.format(
        server_type='postgresql',
        driver='pg8000',
        username=os.environ.get('DB_USERNAME', 'postgres'),
        password=os.environ.get('DB_PASSWORD'),
        hostname=os.environ.get('DB_HOSTNAME', 'localhost'),
        port=os.environ.get('DB_PORT', '5432'),
        database=os.environ.get('DB_NAME', 'devdb')
    )


class GAEConfig(Config):
    APP_VER = 'GAE-' + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername='postgresql+pg8000',
        username=os.environ.get('DB_USERNAME', 'postgres'),
        password=os.environ.get('DB_PASSWORD'),
        database=os.environ.get('DB_NAME', 'devdb'),
        query={'unix_sock': '{socket_path}/{instance_name}/.s.PGSQL.5432'.format(
            socket_path='/cloudsql',
            instance_name='lumiask:europe-west2:devins')
        }
    )


class AWSConfig(Config):
    APP_VER = 'AWS-' + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = '{server_type}+{driver}://{username}:{password}@{hostname}:{port}/{database}'.format(
        server_type='postgresql',
        driver='pg8000',
        username=os.environ.get('DB_USERNAME', 'postgres'),
        password=os.environ.get('DB_PASSWORD'),
        hostname=os.environ.get('DB_HOSTNAME', 'lumi.cikyf0stsfwt.eu-west-2.rds.amazonaws.com'),
        port=os.environ.get('DB_PORT', '5432'),
        database=os.environ.get('DB_NAME', 'devdb')
    )


config = {
    'DEV': DevConfig,
    'TEST': TestConfig,
    'GAE': GAEConfig,
    'AWS': AWSConfig,

    'DEFAULT': DevConfig
}
