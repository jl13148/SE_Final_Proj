# tests/unit/services/test_auth_service.py
from unittest.mock import patch, MagicMock
from tests.base import BaseTestCase
from app.services.auth_service import AuthService
from app.models import User

class TestAuthService(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.auth_service = AuthService(self.db)

    def test_authenticate_user_success(self):
        """Test successful user authentication"""
        success, user, redirect_url, error = self.auth_service.authenticate_user(
            email='test@test.com',
            password='password123',
            user_type='PATIENT'
        )
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertIsNone(error)

    def test_authenticate_user_invalid_password(self):
        """Test authentication with wrong password"""
        success, user, redirect_url, error = self.auth_service.authenticate_user(
            email='test@test.com',
            password='wrongpassword',
            user_type='PATIENT'
        )
        self.assertFalse(success)
        self.assertIsNone(user)
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
        self.assertEqual(error, 'User not found.')

    def test_register_user_success(self):
        """Test successful user registration"""
        success, user, redirect_url, error = self.auth_service.register_user(
            username='newuser',
            email='newuser@test.com',
            password='password123',
            user_type='PATIENT'
        )
        self.assertTrue(success)
        self.assertIsNotNone(user)
        self.assertIsNone(error)
        self.assertEqual(user.email, 'newuser@test.com')

    def test_register_user_duplicate_email(self):
        """Test registration with existing email"""
        success, user, redirect_url, error = self.auth_service.register_user(
            username='testuser2',
            email='test@test.com',  # Already exists from BaseTestCase
            password='password123',
            user_type='PATIENT'
        )
        self.assertFalse(success)
        self.assertIsNone(user)
        self.assertEqual(error, 'Email already registered.')

