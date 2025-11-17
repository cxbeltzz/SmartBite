from urllib.parse import quote


class Config:
    SECRET_KEY = "AS%#doa^ds!wuaSM?*+s"


class DevelopmentConfig(Config):
    DEBUG = True
    POSTGRESQL_HOST = "localhost:5433"
    POSTGRESQL_USER = "postgres"
    # Esta la uso en mi entorno, toca cambiarla para que funcione en el contenedor
    POSTGRESQL_PASSWORD = quote("postsoft%22")
    POSTGRESQL_DB = "users"


config = {"development": DevelopmentConfig}

URL = DevelopmentConfig()

dsn = f"postgresql://{URL.POSTGRESQL_USER}:{URL.POSTGRESQL_PASSWORD}@{URL.POSTGRESQL_HOST}/{URL.POSTGRESQL_DB}"
