import unittest
from datetime import time
from app import create_app
from app.extensions import db
from app.models import User, Medication

class BaseTestCase(unittest.TestCase):
    """Base test case with common setup and teardown"""
    
    def setUp(self):
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Get test client
        self.client = self.app.test_client()
        
        # Create tables
        db.create_all()
        
        # Create test user
        self.test_user = self.create_test_user('test@test.com')
        
        # Create test medication
        self.test_medication = self.create_test_medication('Test Med')

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def create_test_user(self, email):
        """Helper method to create test user"""
        user = User(
            username=email.split('@')[0],
            email=email,
            user_type='PATIENT'
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user

    def create_test_medication(self, name, test_time=None):
        """Helper method to create test medication"""
        if test_time is None:
            test_time = time(8, 0)  # Default time
            
        medication = Medication(
            name=name,
            dosage='100mg',
            frequency='daily',
            time=test_time,  # Use test_time here
            user_id=self.test_user.id
        )
        db.session.add(medication)
        db.session.commit()
        return medication

    def login(self, email='test@test.com', password='password123'):
        """Helper method to login"""
        return self.client.post('/login', data={
            'email': email,
            'password': password,
            'user_type': 'PATIENT'
        }, follow_redirects=True)