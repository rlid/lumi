import os
from sqlalchemy.engine.url import URL

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    APP_VER = "20220120_1430"
    APP_NAME = "LumiAsk"

    SECRET_KEY = os.environ.get("SECRET_KEY")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    OAUTH_RANDOM_NBYTES = 32
    OAUTH_NONCE_HASH_DIGEST_SIZE = 32

    OAUTH_APPLE_URL = "https://appleid.apple.com/.well-known/openid-configuration"
    OAUTH_APPLE_CLIENT_ID = os.environ.get("OAUTH_APPLE_CLIENT_ID")
    OAUTH_APPLE_TEAM_ID = os.environ.get("OAUTH_APPLE_TEAM_ID")
    OAUTH_APPLE_KEY_ID = os.environ.get("OAUTH_APPLE_KEY_ID")

    OAUTH_APPLE_PRIVATE_KEY = None
    with open(os.environ.get("OAUTH_APPLE_KEY_FILE"), "r") as f:
        OAUTH_APPLE_PRIVATE_KEY = f.read()

    OAUTH_GOOGLE_URL = "https://accounts.google.com/.well-known/openid-configuration"
    OAUTH_GOOGLE_CLIENT_ID = os.environ.get("OAUTH_GOOGLE_CLIENT_ID")
    OAUTH_GOOGLE_CLIENT_SECRET = os.environ.get("OAUTH_GOOGLE_CLIENT_SECRET")

    CLIENT_NONCE_NBYTES = 32
    CLIENT_NONCE_HASH_DIGEST_SIZE = 32

    GOOGLE_SERVER_METADATA_URL = "https://accounts.google.com/.well-known/openid-configuration"
    GOOGLE_CLIENT_ID = os.getenv('OAUTH_GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('OAUTH_GOOGLE_CLIENT_SECRET')

    APPLE_SERVER_METADATA_URL = "https://appleid.apple.com/.well-known/openid-configuration"
    APPLE_CLIENT_ID = os.environ.get("OAUTH_APPLE_CLIENT_ID")
    # APPLE_CLIENT_SECRET = None
    # with open(os.environ.get("OAUTH_APPLE_KEY_FILE"), "rb") as f:
    #     APPLE_CLIENT_SECRET = f.read()

    @staticmethod
    def init_app(app):
        pass


class TestConfig(Config):
    APP_VER = "TEST-" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = "sqlite://"


class DevConfig(Config):
    APP_VER = "DEV-" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = "{server_type}+{driver}://{username}:{password}@{hostname}:{port}/{database}".format(
        server_type="postgresql",
        driver="pg8000",
        username="postgres",
        password=os.environ.get('DB_PASSWORD'),
        hostname="localhost",
        port="9470",
        database="devdb")


class GAEConfig(Config):
    APP_VER = "GAE-" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="postgresql+pg8000",
        username="postgres",
        password=os.environ.get('DB_PASSWORD'),
        database="devdb",
        query={"unix_sock": "{socket_path}/{instance_name}/.s.PGSQL.5432".format(
            socket_path="/cloudsql",
            instance_name="lumiask:europe-west2:devins")})


config = {
    "DEV": DevConfig,
    "TEST": TestConfig,
    "GAE": GAEConfig,

    "DEFAULT": DevConfig
}
