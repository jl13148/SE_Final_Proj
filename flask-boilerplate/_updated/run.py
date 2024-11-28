from app import create_app
from app.extensions import db


app = create_app('config.development')

def reset_db():
    """Reset the database."""
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        print('Database has been reset!')

if __name__ == '__main__':
    reset_db()
    app.run(debug=True)
