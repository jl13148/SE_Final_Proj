from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy import Column, Integer, String
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from enum import Enum
from sqlalchemy import String, Integer, Enum as SQLAlchemyEnum 

db = SQLAlchemy()

# engine = create_engine('sqlite:///database.db', echo=True)
# db_session = scoped_session(sessionmaker(autocommit=False,
#                                          autoflush=False,
#                                          bind=engine))
# Base = declarative_base()
# Base.query = db_session.query_property()

# Set your classes here.

'''
class User(Base):
    __tablename__ = 'Users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True)
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(30))

    def __init__(self, name=None, password=None):
        self.name = name
        self.password = password
'''

class UserType(Enum):
    PATIENT = "PATIENT"
    COMPANION = "COMPANION"

class AccessLevel(Enum):
    NONE = "NONE"
    VIEW = "VIEW"
    EDIT = "EDIT"

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(120), unique=True)
    email = db.Column(db.String(120), unique=True)
    password_hash = db.Column(db.String(255))
    user_type = db.Column(db.String(20), nullable=False)
    medications = db.relationship('Medication', backref='user', lazy=True)
    glucose_records = db.relationship('GlucoseRecord', backref='user', lazy='dynamic')
    blood_pressure_records = db.relationship('BloodPressureRecord', backref='user', lazy='dynamic')

    # Relationships
    companions = db.relationship('CompanionAccess', foreign_keys='CompanionAccess.patient_id', backref='patient')
    patients = db.relationship('CompanionAccess', foreign_keys='CompanionAccess.companion_id', backref='companion')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def user_type_enum(self):
        return UserType(self.user_type)

    @user_type_enum.setter
    def user_type_enum(self, value):
        if isinstance(value, UserType):
            self.user_type = value.value
        else:
            self.user_type = str(value).upper()


class CompanionAccess(db.Model):
    __tablename__ = 'companion_access'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    companion_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    medication_access = db.Column(db.String(20), nullable=False, default='NONE')
    glucose_access = db.Column(db.String(20), nullable=False, default='NONE')
    blood_pressure_access = db.Column(db.String(20), nullable=False, default='NONE')
    export_access = db.Column(db.Boolean, default=False)
    
    __table_args__ = (
        db.UniqueConstraint('patient_id', 'companion_id', name='unique_patient_companion'),
    )

    @property
    def medication_access_enum(self):
        return AccessLevel(self.medication_access)

    @medication_access_enum.setter
    def medication_access_enum(self, value):
        if isinstance(value, AccessLevel):
            self.medication_access = value.value
        else:
            self.medication_access = str(value).upper()

    @property
    def glucose_access_enum(self):
        return AccessLevel(self.glucose_access)

    @glucose_access_enum.setter
    def glucose_access_enum(self, value):
        if isinstance(value, AccessLevel):
            self.glucose_access = value.value
        else:
            self.glucose_access = str(value).upper()

    @property
    def blood_pressure_access_enum(self):
        return AccessLevel(self.blood_pressure_access)

    @blood_pressure_access_enum.setter
    def blood_pressure_access_enum(self, value):
        if isinstance(value, AccessLevel):
            self.blood_pressure_access = value.value
        else:
            self.blood_pressure_access = str(value).upper()


class Medication(db.Model):
    __tablename__ = 'medications'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(120), nullable=False)
    frequency = db.Column(db.String(120), nullable=False)  # Keep this for backward compatibility
    time = db.Column(db.Time, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    logs = db.relationship('MedicationLog', backref='medication', lazy=True)

class MedicationLog(db.Model):
    __tablename__ = 'medication_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    medication_id = db.Column(db.Integer, db.ForeignKey('medications.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    taken_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Remove the duplicate relationship definitions
    user = db.relationship('User', backref='medication_logs', lazy=True)

    
class GlucoseRecord(db.Model):
    __tablename__ = 'glucose_records'
    
    id = db.Column(db.Integer, primary_key=True)
    glucose_level = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(5), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f'<GlucoseRecord {self.glucose_level}>'

class BloodPressureRecord(db.Model):
    __tablename__ = 'blood_pressure_records'
    
    id = db.Column(db.Integer, primary_key=True)
    systolic = db.Column(db.Integer, nullable=False)
    diastolic = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(5), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f'<BloodPressureRecord {self.systolic}/{self.diastolic}>'
# # Create tables.
# Base.metadata.create_all(bind=engine)
