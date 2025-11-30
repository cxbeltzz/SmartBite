from urllib.parse import quote
import os
import secrets

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Database MODELO 
    POSTGRESQL_MODEL_HOST = os.environ.get('POSTGRES_MODEL_HOST', 'localhost')
    POSTGRESQL_MODEL_USER = os.environ.get('POSTGRES_MODEL_USER', 'postgres')
    POSTGRESQL_MODEL_PASSWORD = os.environ.get('POSTGRES_MODEL_PASSWORD', 'password')
    POSTGRESQL_MODEL_DB = os.environ.get('POSTGRES_MODEL_DB', 'v2')
    POSTGRESQL_MODEL_PORT = os.environ.get('POSTGRES_MODEL_PORT', '5432')
    
    # Database USUARIOS
    POSTGRESQL_USER_HOST = os.environ.get('POSTGRES_USER_HOST', 'localhost')
    POSTGRESQL_USER_USER = os.environ.get('POSTGRES_USER_USER', 'postgres')
    POSTGRESQL_USER_PASSWORD = os.environ.get('POSTGRES_USER_PASSWORD', 'postsoft%22')
    POSTGRESQL_USER_DB = os.environ.get('POSTGRES_USER_DB', 'users')
    POSTGRESQL_USER_PORT = os.environ.get('POSTGRES_USER_PORT', '5433')
    
    # Google OAuth
    GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    
    # Mail
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'False') == 'True'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', os.environ.get('MAIL_USERNAME'))


class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_model_database_url(config_class):
    user = config_class.POSTGRESQL_MODEL_USER
    password = quote(config_class.POSTGRESQL_MODEL_PASSWORD)
    host = config_class.POSTGRESQL_MODEL_HOST
    port = config_class.POSTGRESQL_MODEL_PORT
    db = config_class.POSTGRESQL_MODEL_DB
    
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def get_users_database_url(config_class):
    user = config_class.POSTGRESQL_USER_USER
    password = quote(config_class.POSTGRESQL_USER_PASSWORD)
    host = config_class.POSTGRESQL_USER_HOST
    port = config_class.POSTGRESQL_USER_PORT
    db = config_class.POSTGRESQL_USER_DB
    
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

# MODEL_DB_DSN = get_model_database_url(DevelopmentConfig)
dsn = get_users_database_url(DevelopmentConfig)