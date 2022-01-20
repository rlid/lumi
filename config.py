import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    APP_VER = "20220120_1430"
    APP_NAME = "LumiAsk"

    SECRET_KEY = os.environ.get("SECRET_KEY") or "zorVef-buwpof-9rowta"

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    @staticmethod
    def init_app(app):
        pass


class DevConfig(Config):
    APP_VER = "DEV-" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URI") or \
        "sqlite:///" + os.path.join(basedir, "db-dev.sqlite")
    DEBUG = True


class TestConfig(Config):
    APP_VER = "TEST-" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URI") or "sqlite://"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URI") or \
        "sqlite:///" + os.path.join(basedir, "db-prod.sqlite")
    TESTING = True


class ProdConfig(Config):
    APP_VER = "PROD" + Config.APP_VER
    PRODUCTION = True


config = {
    "development": DevConfig,
    "testing": TestConfig,
    "production": ProdConfig,

    "default": DevConfig
}
