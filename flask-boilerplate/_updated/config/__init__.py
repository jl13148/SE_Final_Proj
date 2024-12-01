import os

# Get absolute path to the project root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Config:
    DEBUG = False
    SECRET_KEY = 'my precious'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(ROOT_DIR, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    STATIC_FOLDER = 'static'
    STATIC_URL_PATH = '/static'
    TEMPLATE_FOLDER = 'templates'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    DEBUG = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(ROOT_DIR, 'dev_database.db')

class ProductionConfig(Config):
    pass

# Dictionary mapping config names to config classes
CONFIG = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Helper function to get configuration class"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    return CONFIG.get(config_name, CONFIG['default'])