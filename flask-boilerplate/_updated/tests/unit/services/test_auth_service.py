# tests/unit/services/test_auth_service.py
from unittest.mock import patch, MagicMock
from tests.base import BaseTestCase
from app.services.auth_service import AuthService
from app.models import User
from app.extensions import db
from models import UserType
import uuid

class TestAuthService(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.auth_service = AuthService(db)
        # Create unique email for each test
        unique_id = str(uuid.uuid4())[:8]
        self.test_email = f'test_{unique_id}@test.com'
        self.test_user = self.create_test_user(self.test_email)
        
    def test_authenticate_user_success_patient(self):
        """Test successful patient authentication"""
        success, user, redirect_url, error = self.auth_service.authenticate_user(
            email=self.test_email,
            password='password123',
            user_type='PATIENT'
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, self.test_email)
        self.assertIsNone(redirect_url)  # Patient doesn't need redirect
        self.assertIsNone(error)
        
    def test_authenticate_user_invalid_password(self):
        """Test authentication with invalid password"""
        success, user, redirect_url, error = self.auth_service.authenticate_user(
            email=self.test_email,
            password='wrongpassword',
            user_type='PATIENT'
        )
        
        self.assertFalse(success)
        self.assertIsNone(user)
        self.assertIsNone(redirect_url)
        self.assertEqual(error, 'Invalid password.')

    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        success, user, redirect_url, error = self.auth_service.authenticate_user(
            email='nonexistent@test.com',
            password='password123',
            user_type='PATIENT'
        )
        
        self.assertFalse(success)
        self.assertIsNone(user)
        self.assertIsNone(redirect_url)
        self.assertEqual(error, 'User not found.')

    def test_authenticate_user_database_error(self):
        """Test authentication with database error"""
        with patch('app.models.User.query') as mock_query:
            mock_query.filter_by.side_effect = Exception("Database error")
            
            success, user, redirect_url, error = self.auth_service.authenticate_user(
                email=self.test_email,
                password='password123',
                user_type='PATIENT'
            )
            
            self.assertFalse(success)
            self.assertIsNone(user)
            self.assertIsNone(redirect_url)
            self.assertTrue(error.startswith('Authentication error:'))

    def test_authenticate_companion_with_setup_needed(self):
        """Test companion authentication requiring setup"""
        # Create companion without patients
        unique_id = str(uuid.uuid4())[:8]
        companion_email = f'companion_{unique_id}@test.com'
        companion = User(
            username=f'companion_{unique_id}',
            email=companion_email,
            user_type=UserType.COMPANION  # Use the enum here
        )
        companion.set_password('password123')
        db.session.add(companion)
        db.session.commit()

        # Authenticate the user
        success, user, redirect_url, error = self.auth_service.authenticate_user(
            email=companion_email,
            password='password123',
            user_type=UserType.COMPANION  # Use the enum here
        )
        
        # Assertions
        self.assertTrue(success, "Authentication should succeed")
        self.assertIsNotNone(user, "User should not be None")
        self.assertEqual(redirect_url, 'companion.companion_setup', "Redirect URL should be 'companion.companion_setup'")
        self.assertIsNone(error, "Error should be None")

        # Additional Assertions (Optional)
        self.assertEqual(user.email, companion_email, "Authenticated user email should match")
        self.assertEqual(user.user_type, UserType.COMPANION, "User type should be 'COMPANION'")
        self.assertFalse(user.patients.count(), "User should have no patients")
    def test_register_user_success_patient(self):
        """Test successful patient registration"""
        unique_id = str(uuid.uuid4())[:8]
        email = f'new_patient_{unique_id}@test.com'
        
        success, user, redirect_url, error = self.auth_service.register_user(
            username=f'patient_{unique_id}',
            email=email,
            password='password123',
            user_type='PATIENT'
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertEqual(redirect_url, 'auth.login')
        self.assertIsNone(error)

    def test_register_user_success_companion(self):
        """Test successful companion registration"""
        unique_id = str(uuid.uuid4())[:8]
        email = f'new_companion_{unique_id}@test.com'
        
        success, user, redirect_url, error = self.auth_service.register_user(
            username=f'companion_{unique_id}',
            email=email,
            password='password123',
            user_type='COMPANION'
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertEqual(redirect_url, 'companion.companion_setup')
        self.assertIsNone(error)

    def test_register_user_existing_email(self):
        """Test registration with existing email"""
        success, user, redirect_url, error = self.auth_service.register_user(
            username='new_username',
            email=self.test_email,  # Use existing email
            password='password123',
            user_type='PATIENT'
        )
        
        self.assertFalse(success)
        self.assertIsNone(user)
        self.assertIsNone(redirect_url)
        self.assertEqual(error, 'Email already registered.')

    def test_register_user_existing_username(self):
        """Test registration with existing username"""
        success, user, redirect_url, error = self.auth_service.register_user(
            username=self.test_user.username,  # Use existing username
            email=f'different_{uuid.uuid4()}@test.com',
            password='password123',
            user_type='PATIENT'
        )
        
        self.assertFalse(success)
        self.assertIsNone(user)
        self.assertIsNone(redirect_url)
        self.assertEqual(error, 'Username already taken.')

    def test_register_user_database_error(self):
        """Test registration with database error"""
        with patch('app.models.User.query') as mock_query:
            mock_query.filter_by.side_effect = Exception("Database error")
            
            success, user, redirect_url, error = self.auth_service.register_user(
                username='new_user',
                email='new@test.com',
                password='password123',
                user_type='PATIENT'
            )
            
            self.assertFalse(success)
            self.assertIsNone(user)
            self.assertIsNone(redirect_url)
            self.assertTrue(error.startswith('Registration error:'))

    def test_initiate_password_reset_success(self):
        """Test successful password reset initiation"""
        success, error = self.auth_service.initiate_password_reset(self.test_email)
        self.assertTrue(success)
        self.assertIsNone(error)

    def test_initiate_password_reset_user_not_found(self):
        """Test password reset for non-existent user"""
        success, error = self.auth_service.initiate_password_reset('nonexistent@test.com')
        self.assertFalse(success)
        self.assertEqual(error, 'No account found with this email.')

    def test_initiate_password_reset_error(self):
        """Test password reset with database error"""
        with patch('app.models.User.query') as mock_query:
            mock_query.filter_by.side_effect = Exception("Database error")
            success, error = self.auth_service.initiate_password_reset(self.test_email)
            self.assertFalse(success)
            self.assertTrue(error.startswith('Password reset error:'))