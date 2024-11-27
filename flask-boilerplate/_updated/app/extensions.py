from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()

# Configure LoginManager
login_manager.login_view = 'pages.login'  # Adjust based on your Blueprint and route
login_manager.login_message_category = 'info'