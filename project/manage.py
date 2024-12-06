import click
import os
from flask.cli import FlaskGroup
from app import create_app
from app.extensions import db

def get_app():
    return create_app('development')

cli = FlaskGroup(create_app=get_app)

def ensure_db_directory_exists(app):
    """Ensure the directory for the database file exists"""
    db_path = os.path.dirname(app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', ''))
    if not os.path.exists(db_path):
        os.makedirs(db_path)

@cli.command("init-db")
def init_db():
    """Initialize the database."""
    app = get_app()
    with app.app_context():
        ensure_db_directory_exists(app)
        db.create_all()
        click.echo('Initialized the database.')
        # Print the database location for verification
        click.echo(f"Database created at: {app.config['SQLALCHEMY_DATABASE_URI']}")

@cli.command("reset-db")
def reset_db():
    """Reset the database."""
    if click.confirm('Are you sure you want to reset the database? This will delete all data!', abort=True):
        app = get_app()
        with app.app_context():
            ensure_db_directory_exists(app)
            db.drop_all()
            db.create_all()
            click.echo('Reset the database.')
            # Print the database location for verification
            click.echo(f"Database reset at: {app.config['SQLALCHEMY_DATABASE_URI']}")

if __name__ == '__main__':
    cli()