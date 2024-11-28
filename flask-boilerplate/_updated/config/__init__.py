import os

# Get absolute path to the project root directory
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Config:
    DEBUG = False
    SECRET_KEY = 'my precious'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(ROOT_DIR, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class DevelopmentConfig(Config):
    DEBUG = True
    # Database path specifically for development
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(ROOT_DIR, 'dev_database.db')

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class ProductionConfig(Config):
    # Production-specific settings
    pass

# Map config names to config classes
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Helper function to get configuration class"""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'default')
    return config.get(config_name, config['default'])