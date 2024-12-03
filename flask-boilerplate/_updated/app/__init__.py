from flask import Flask, current_app
from flask_login import current_user
from .extensions import db, migrate, login_manager
from .models import User, CompanionAccess

# Import blueprints
from .controllers.auth import auth as auth_blueprint
from .controllers.health import health as health_blueprint
from .controllers.medication import medication as medication_blueprint
from .controllers.pages import pages as pages_blueprint
from .controllers.report import report as report_blueprint
from .controllers.connection import connection as connection_blueprint
from .controllers.companion import companion as companion_blueprint

# Import services
from .services.auth_service import AuthService
from .services.health_service import HealthService
from .services.medication_service import MedicationService
# from .services.report_service import ReportService
from .services.connection_service import ConnectionService
from .services.companion_service import CompanionService

from config import get_config

def create_app(config_name=None):
    app = Flask(__name__)

    # Get configuration
    config_class = get_config(config_name)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)

    # Set up login manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    # Initialize services
    # Store services in app context for access in routes
    with app.app_context():
        app.auth_service = AuthService(db)
        app.health_service = HealthService(db)
        app.medication_service = MedicationService(db)
        # app.report_service = ReportService(db)
        app.connection_service = ConnectionService(db)
        app.companion_service = CompanionService(db)

    # Register blueprints
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(health_blueprint)
    app.register_blueprint(medication_blueprint)
    app.register_blueprint(pages_blueprint)
    app.register_blueprint(report_blueprint)
    app.register_blueprint(connection_blueprint)
    app.register_blueprint(companion_blueprint)

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
    
    @app.context_processor
    def inject_notification_count():
        """
        Injects 'notifications_count' into the template context for companion users.
        """
        notifications_count = 0
        if current_user.is_authenticated and current_user.user_type == "COMPANION":
            success, notifications = current_app.companion_service.get_notifications(current_user.id)
            notifications_count = len(notifications) if success else 0
        return {'notifications_count': notifications_count}

    # Configure Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    return app