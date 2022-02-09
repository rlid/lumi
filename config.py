import os

from sqlalchemy.engine.url import URL

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    APP_VER = "20220209_1100"
    APP_NAME = "LumiAsk"

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
    APPLE_CLIENT_SECRET = None
    with open(os.environ.get("APPLE_KEY_FILE"), "r") as f:
        APPLE_CLIENT_SECRET = f.read()

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
        username=os.environ.get('DB_USERNAME') or "postgres",
        password=os.environ.get('DB_PASSWORD'),
        hostname=os.environ.get('DB_HOSTNAME') or "localhost",
        port=os.environ.get('DB_PORT') or "9470",
        database=os.environ.get('DB_NAME') or "devdb")


class GAEConfig(Config):
    APP_VER = "GAE-" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="postgresql+pg8000",
        username="lumi",
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
