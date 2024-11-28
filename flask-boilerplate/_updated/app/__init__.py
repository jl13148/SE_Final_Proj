from app.controllers import report
from flask import Flask
from flask_login import current_user
from .extensions import db, migrate, login_manager
from .models import User
from .controllers.auth import auth as auth_blueprint
from .controllers.health import health as health_blueprint
from .controllers.medication import medication as medication_blueprint
from .controllers.pages import pages as pages_blueprint
from .controllers.report import report as report_blueprint
from .controllers.connection import connection as connection_blueprint
from .models import CompanionAccess
from config import get_config


def create_app(config_name=None):
    app = Flask(__name__)
    
    # Get configuration class
    config = get_config(config_name)
    app.config.from_object(config)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    
    # Set up login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(health_blueprint)
    app.register_blueprint(medication_blueprint)
    app.register_blueprint(pages_blueprint)
    app.register_blueprint(report_blueprint)
    app.register_blueprint(connection_blueprint)

    @app.context_processor
    def utility_processor():
        def get_pending_connections_count():
            if not current_user.is_authenticated or current_user.user_type != "PATIENT":
                return 0
            return CompanionAccess.query.filter_by(
                patient_id=current_user.id,
                medication_access="NONE",
                glucose_access="NONE",
                blood_pressure_access="NONE"
            ).count()
        return dict(pending_connections_count=get_pending_connections_count())
    
    # Configure Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    return app