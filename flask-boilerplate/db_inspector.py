# db_inspector.py

from sqlalchemy import inspect
import sqlite3
from models import db, User, Medication, GlucoseRecord, BloodPressureRecord, MedicationLog, CompanionAccess
from flask import Flask
import sys

def create_test_app():
    """Create a test Flask application context"""
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def get_model_columns(model):
    """Get column information from SQLAlchemy model"""
    return {column.name: str(column.type) 
            for column in model.__table__.columns}

def get_db_columns(table_name):
    """Get column information from SQLite database"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row[1]: row[2].upper() for row in cursor.fetchall()}
    conn.close()
    return columns

def get_db_tables():
    """Get list of tables in the database"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tables

def inspect_database():
    """Inspect and compare database schema with models"""
    app = create_test_app()
    
    with app.app_context():
        inspector = inspect(db.engine)
        
        print("\n=== Database Schema Analysis ===\n")
        
        # Get actual database tables
        db_tables = get_db_tables()
        print("Tables in database:", db_tables)
        
        # Dictionary of all models
        models = {
            'users': User,
            'medications': Medication,
            'glucose_records': GlucoseRecord,
            'blood_pressure_records': BloodPressureRecord,
            'medication_logs': MedicationLog,
            'companion_access': CompanionAccess
        }
        
        print("\nComparing model definitions with database schema:")
        print("------------------------------------------------")
        
        for table_name, model in models.items():
            print(f"\nTable: {table_name}")
            
            if table_name not in db_tables:
                print(f"WARNING: Table {table_name} exists in models but not in database!")
                continue
            
            model_columns = get_model_columns(model)
            db_columns = get_db_columns(table_name)
            
            # Compare columns
            print("\nColumns comparison:")
            all_columns = set(model_columns.keys()) | set(db_columns.keys())
            
            for column in all_columns:
                if column in model_columns and column in db_columns:
                    if model_columns[column].upper() != db_columns[column]:
                        print(f"  ⚠️  {column}: Type mismatch")
                        print(f"     Model: {model_columns[column]}")
                        print(f"     DB:    {db_columns[column]}")
                elif column in model_columns:
                    print(f"  ➕ {column}: In model but not in database")
                else:
                    print(f"  ➖ {column}: In database but not in model")
            
            # Check foreign keys
            fks = inspector.get_foreign_keys(table_name)
            if fks:
                print("\nForeign Keys:")
                for fk in fks:
                    print(f"  {fk['constrained_columns']} -> {fk['referred_table']}.{fk['referred_columns']}")

if __name__ == '__main__':
    inspect_database()