import os

from sqlalchemy.engine.url import URL

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    APP_VER = "20220209_1100"
    APP_NAME = "LumiAsk"
    USE_SSL = False

    SECRET_KEY = os.environ.get("SECRET_KEY")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SITE_RID_NBYTES = 32
    SITE_RID_HASH_DIGEST_SIZE = 32

    GOOGLE_SERVER_METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')

    APPLE_SERVER_METADATA_URL = "https://appleid.apple.com/.well-known/openid-configuration"
    APPLE_CLIENT_ID = os.environ.get("APPLE_CLIENT_ID")
    APPLE_TEAM_ID = os.environ.get("APPLE_TEAM_ID")
    APPLE_KEY_ID = os.environ.get("APPLE_KEY_ID")
    # For Sign in with Apple, the client secret is dynamic - it is a JWT generated using a private key issued by Apple.
    # This variable stores the private key, and this convention is assumed by Authlib and auth_utils.ApplePrivateKeyJWT
    APPLE_CLIENT_SECRET = os.environ.get("APPLE_CLIENT_SECRET")
    if APPLE_CLIENT_SECRET is None:
        with open(os.environ.get("APPLE_KEY_FILE"), "r") as f:
            APPLE_CLIENT_SECRET = f.read()
    else:
        APPLE_CLIENT_SECRET = APPLE_CLIENT_SECRET.replace('|', '\n')

    @staticmethod
    def init_app(app):
        pass


class TestConfig(Config):
    APP_VER = "TEST-" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = "{server_type}+{driver}://{username}:{password}@{hostname}:{port}/{database}".format(
        server_type="postgresql",
        driver="pg8000",
        username=os.environ.get('DB_USERNAME') or "lumi",
        password=os.environ.get('DB_PASSWORD'),
        hostname=os.environ.get('DB_HOSTNAME') or "localhost",
        port=os.environ.get('DB_PORT') or "5432",
        database="testdb")


class DevConfig(Config):
    APP_VER = "DEV-" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = "{server_type}+{driver}://{username}:{password}@{hostname}:{port}/{database}".format(
        server_type="postgresql",
        driver="pg8000",
        username=os.environ.get('DB_USERNAME') or "lumi",
        password=os.environ.get('DB_PASSWORD'),
        hostname=os.environ.get('DB_HOSTNAME') or "localhost",
        port=os.environ.get('DB_PORT') or "5432",
        database=os.environ.get('DB_NAME') or "devdb")


class GAEConfig(Config):
    APP_VER = "GAE-" + Config.APP_VER
    USE_SSL = True
    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="postgresql+pg8000",
        username="lumi",
        password=os.environ.get('DB_PASSWORD'),
        database="devdb",
        query={"unix_sock": "{socket_path}/{instance_name}/.s.PGSQL.5432".format(
            socket_path="/cloudsql",
            instance_name="lumiask:europe-west2:devins")})


class AWSConfig(Config):
    APP_VER = "AWS-" + Config.APP_VER
    USE_SSL = True
    SQLALCHEMY_DATABASE_URI = "{server_type}+{driver}://{username}:{password}@{hostname}:{port}/{database}".format(
        server_type="postgresql",
        driver="pg8000",
        username=os.environ.get('RDS_USERNAME') or "lumi",
        password=os.environ.get('RDS_PASSWORD') or os.environ.get('DB_PASSWORD'),
        hostname=os.environ.get('RDS_HOSTNAME') or "lumi-4.cikyf0stsfwt.eu-west-2.rds.amazonaws.com",
        port=os.environ.get('RDS_PORT') or "5432",
        database=os.environ.get('RDS_DB_NAME') or "devdb")


config = {
    "DEV": DevConfig,
    "TEST": TestConfig,
    "GAE": GAEConfig,
    "AWS": AWSConfig,

    "DEFAULT": DevConfig
}
