import os
from sqlalchemy.engine.url import URL

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    APP_VER = "20220120_1430"
    APP_NAME = "LumiAsk"

    SECRET_KEY = os.environ.get("SECRET_KEY")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    APPLE_OAUTH_URL = "https://appleid.apple.com/.well-known/openid-configuration"

    GOOGLE_OAUTH_URL = "https://accounts.google.com/.well-known/openid-configuration"
    GOOGLE_OAUTH_ID = os.environ.get("GOOGLE_OAUTH_ID")
    GOOGLE_OAUTH_SECRET = os.environ.get("GOOGLE_OAUTH_SECRET")

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
