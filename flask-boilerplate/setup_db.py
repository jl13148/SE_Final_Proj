# setup_db.py

from flask import Flask
from models import db, User, UserType
from app import app
from flask_migrate import Migrate, init, migrate, upgrade

def setup_database():
    """Set up a fresh database with migrations"""
    with app.app_context():
        # Initialize database
        db.create_all()
        
        # Initialize migrations
        migrate = Migrate(app, db)
        
        try:
            # Initialize migrations directory
            init()
            
            # Create initial migration
            migrate()
            
            # Apply migration
            upgrade()
            
            print("Database and migrations initialized successfully!")
            
            # Optionally create a test user
            test_user = User(
                username="test_user",
                email="test@example.com",
                user_type="PATIENT"
            )
            test_user.set_password("password123")
            
            db.session.add(test_user)
            db.session.commit()
            
            print("Test user created successfully!")
            
        except Exception as e:
            print(f"Error during setup: {e}")
            db.session.rollback()

if __name__ == "__main__":
    setup_database()