from flask import Flask
from .extensions import db, migrate, login_manager
from .models import User  # Ensure User model is imported
from .controllers.pages import blueprint

def create_app(config_class='config.Config'):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    
    # Register Blueprints
    app.register_blueprint(blueprint)
    
    # Configure Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app