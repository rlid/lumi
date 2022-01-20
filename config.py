import os
from sqlalchemy.engine.url import URL

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
                              "{server_type}+{driver}://{username}:{password}@{hostname}:{port}/{database}".format(
                                  server_type="postgresql",
                                  driver="pg8000",
                                  username="postgres",
                                  password=os.environ.get('DB_PASSWORD'),
                                  hostname="localhost",
                                  port="3306",
                                  database="devdb")


class GoogleCloudConfig(Config):
    APP_VER = "GCLOUD-" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URI") or \
                              URL.create(
                                  drivername="postgresql+pg8000",
                                  username="postgres",
                                  password=os.environ.get('DB_PASSWORD'),
                                  database="devdb",
                                  query={"unix_sock": "{socket_path}/{instance_name}/.s.PGSQL.5432".format(
                                      socket_path="/cloudsql",
                                      instance_name="lumiask:europe-west2:devins")})


class TestConfig(Config):
    APP_VER = "TEST-" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URI") or "sqlite://"


class ProdConfig(Config):
    APP_VER = "PROD" + Config.APP_VER
    SQLALCHEMY_DATABASE_URI = os.environ.get("DEV_DATABASE_URI") or \
                              "sqlite:///" + os.path.join(basedir, "db-prod.sqlite")


config = {
    "DEV": DevConfig,
    "TEST": TestConfig,
    "PROD": ProdConfig,
    "GCLOUD": GoogleCloudConfig,

    "DEFAULT": DevConfig
}
