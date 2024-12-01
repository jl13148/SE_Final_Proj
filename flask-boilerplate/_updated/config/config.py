import os
from datetime import timedelta

# Get the folder where this script runs
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Basic Flask config
    DEBUG = True
    SECRET_KEY = 'my precious'
    
    # Database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'database.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # # Mail settings
    # MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    # MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    # MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
    # MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    # MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Static files
    STATIC_FOLDER = 'static'
    STATIC_URL_PATH = '/static'
    TEMPLATE_FOLDER = 'templates'

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    DEBUG = False