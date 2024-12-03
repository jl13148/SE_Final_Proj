# tests/base.py
import unittest
from datetime import time
from app import create_app
from app.extensions import db
from app.models import User, Medication
from typing import Optional

class BaseTestCase(unittest.TestCase):
    """Base test case with common setup and teardown"""
    
    def setUp(self):
        """Set up test environment"""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()  # Push application context
        
        # Get test client
        self.client = self.app.test_client()
        
        # Create tables
        db.create_all()
        
        # Create test user
        self.test_user = self.create_test_user('test@test.com')
        
        # Create test medication
        self.test_medication = self.create_test_medication('Test Med', time(9, 0)) 
    
    def tearDown(self):
        """Clean up after tests"""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()  # Pop application context

    def create_test_user(self, email: str, user_type: str = 'PATIENT') -> User:
        """Helper method to create a test user."""
        user = User(
            username=email.split('@')[0],
            email=email,
            user_type=user_type
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user
    
    def create_test_medication(self, name: str, med_time: time, user_id: Optional[int] = None) -> Medication:
        """Helper method to create a test medication."""
        if not user_id:
            user_id = self.test_user.id
        medication = Medication(
            name=name,
            dosage="100mg",
            frequency="once_daily",
            time=med_time,
            user_id=user_id
        )
        db.session.add(medication)
        db.session.commit()
        return medication