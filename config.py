import os


class Config:
    APP_VER = "20220117_1254"
    APP_NAME = "OnmiAsk"
    SECRET_KEY = os.environ.get("SECRET_KEY") or "zorVef-buwpof-9rowta"

    @staticmethod
    def init_app(app):
        pass


class DevConfig(Config):
    APP_VER = "DEV-" + Config.APP_VER
    DEBUG = True


class TestConfig(Config):
    APP_VER = "TEST-" + Config.APP_VER
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
