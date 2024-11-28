import os
from importlib import import_module

# Import the Config class from your root config.py
try:
    from config import Config
except ImportError:
    # Fallback configuration if config.py is not found
    class Config:
        SECRET_KEY = 'default-secret-key'
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), '../database.db')
        SQLALCHEMY_TRACK_MODIFICATIONS = False

# Make the Config class and get_config function available when importing from config
__all__ = ['Config']