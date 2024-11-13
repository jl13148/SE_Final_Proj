import unittest
from unittest.mock import patch, MagicMock
from app import app
from models import User, GlucoseRecord, BloodPressureRecord
from flask import url_for
from flask_login import login_user
from datetime import datetime
from flask_login import AnonymousUserMixin
import HtmlTestRunner

class FlaskAppTestCase(unittest.TestCase):
    def setUp(self):
        # Configure the app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        
        # Push the application context
        self.app_context = app.app_context()
        self.app_context.push()
        
        self.client = app.test_client()

        # Patch the database session
        self.patcher_add = patch('app.db.session.add')
        self.patcher_commit = patch('app.db.session.commit')
        self.mock_add = self.patcher_add.start()
        self.mock_commit = self.patcher_commit.start()

        # Create a mock user and patch the User.query.get method
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = 1
        self.mock_user.username = 'testuser'
        self.mock_user.email = 'test@example.com'
        
        # Patch User.query.get to return the mock_user
        self.patcher_user = patch('models.User.query.get', return_value=self.mock_user)
        self.mock_query_get = self.patcher_user.start()

        # Patch the current_user in flask_login
        self.patcher_login = patch('flask_login.utils._get_user', return_value=self.mock_user)
        self.mock_login = self.patcher_login.start()

    def tearDown(self):
        # Stop all patches
        self.patcher_add.stop()
        self.patcher_commit.stop()
        self.patcher_user.stop()
        self.patcher_login.stop()
        
        # Pop the application context
        self.app_context.pop()

    def login(self):
        """
        Simulate logging in a user by ensuring that the current_user is mocked.
        """
        with patch('flask_login.utils._get_user', return_value=self.mock_user):
            pass  # The actual login logic is mocked

    # Tests for /glucose route
    @patch('app.GlucoseRecord')
    def test_glucose_get_requires_login(self, mock_glucose_record):
        """
        Test accessing the /glucose route without being logged in.
        Expect a redirect to the login page.
        """
        # Use AnonymousUserMixin instead of None to avoid AttributeError
        with patch('flask_login.utils._get_user', return_value=AnonymousUserMixin()):
            response = self.client.get('/glucose')
            self.assertEqual(response.status_code, 302)  # Redirect to login
            self.assertIn('/login', response.headers['Location'])  # Ensure redirection to login

    @patch('app.GlucoseRecord')
    def test_glucose_get_logged_in(self, mock_glucose_record):
        """
        Test accessing the /glucose route while logged in.
        Expect a 200 OK response and appropriate template rendering.
        """
        self.login()
        response = self.client.get('/glucose')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Glucose Logger', response.data)  # Adjust based on your template

    @patch('app.GlucoseRecord')
    def test_glucose_post_valid_data(self, mock_glucose_record):
        """
        Test posting valid glucose data.
        Expect a success message and that the record is added to the database.
        """
        self.login()
        response = self.client.post('/glucose', data={
            'glucose_level': '100',
            'date': '2024-11-13',
            'time': '17:00'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Glucose data logged successfully!', response.data)

        # Assert that GlucoseRecord was instantiated with correct parameters
        mock_glucose_record.assert_called_with(
            glucose_level=100,
            date='2024-11-13',
            time='17:00',
            user_id=self.mock_user.id
        )
        # Assert that add and commit were called
        self.mock_add.assert_called_once_with(mock_glucose_record.return_value)
        self.mock_commit.assert_called_once()

    @patch('app.GlucoseRecord')
    def test_glucose_post_invalid_glucose_level(self, mock_glucose_record):
        """
        Test posting an invalid (negative) glucose level.
        Expect an error message and that the record is not added.
        """
        self.login()
        response = self.client.post('/glucose', data={
            'glucose_level': '-50',
            'date': '2024-11-13',
            'time': '17:00'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Glucose level must be between 70 and 180 mg/dL.', response.data)

        # Assert that GlucoseRecord was not instantiated
        mock_glucose_record.assert_not_called()
        # Assert that add and commit were not called
        self.mock_add.assert_not_called()
        self.mock_commit.assert_not_called()

    @patch('app.GlucoseRecord')
    def test_glucose_post_non_integer_glucose_level(self, mock_glucose_record):
        """
        Test posting a non-integer glucose level.
        Expect an error message and that the record is not added.
        """
        self.login()
        response = self.client.post('/glucose', data={
            'glucose_level': 'abc',
            'date': '2024-11-13',
            'time': '17:00'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Glucose level must be an integer.', response.data)

        # Assert that GlucoseRecord was not instantiated
        mock_glucose_record.assert_not_called()
        # Assert that add and commit were not called
        self.mock_add.assert_not_called()
        self.mock_commit.assert_not_called()

    # Tests for /blood_pressure route
    @patch('app.BloodPressureRecord')
    def test_blood_pressure_get_requires_login(self, mock_blood_pressure_record):
        """
        Test accessing the /blood_pressure route without being logged in.
        Expect a redirect to the login page.
        """
        # Simulate not being logged in
        with patch('flask_login.utils._get_user', return_value=AnonymousUserMixin()):
            response = self.client.get('/blood_pressure')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.headers['Location'])

    @patch('app.BloodPressureRecord')
    def test_blood_pressure_get_logged_in(self, mock_blood_pressure_record):
        """
        Test accessing the /blood_pressure route while logged in.
        Expect a 200 OK response and appropriate template rendering.
        """
        self.login()
        response = self.client.get('/blood_pressure')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Blood Pressure Logger', response.data)  # Adjust based on your template

    @patch('app.BloodPressureRecord')
    def test_blood_pressure_post_valid_data(self, mock_blood_pressure_record):
        """
        Test posting valid blood pressure data.
        Expect a success message and that the record is added to the database.
        """
        self.login()
        response = self.client.post('/blood_pressure', data={
            'systolic': '120',
            'diastolic': '80',
            'date': '2024-11-13',
            'time': '17:00'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Blood pressure data logged successfully!', response.data)

        # Assert that BloodPressureRecord was instantiated with correct parameters
        mock_blood_pressure_record.assert_called_with(
            systolic=120,
            diastolic=80,
            date='2024-11-13',
            time='17:00',
            user_id=self.mock_user.id
        )
        # Assert that add and commit were called
        self.mock_add.assert_called_once_with(mock_blood_pressure_record.return_value)
        self.mock_commit.assert_called_once()

    @patch('app.BloodPressureRecord')
    def test_blood_pressure_post_invalid_systolic(self, mock_blood_pressure_record):
        """
        Test posting an invalid (below minimum) systolic value.
        Expect an error message and that the record is not added.
        """
        self.login()
        response = self.client.post('/blood_pressure', data={
            'systolic': '80',  # Below minimum
            'diastolic': '80',
            'date': '2024-11-13',
            'time': '17:00'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Systolic value must be between 90 and 180 mm Hg.', response.data)

        # Assert that BloodPressureRecord was not instantiated
        mock_blood_pressure_record.assert_not_called()
        # Assert that add and commit were not called
        self.mock_add.assert_not_called()
        self.mock_commit.assert_not_called()

    @patch('app.BloodPressureRecord')
    def test_blood_pressure_post_invalid_diastolic(self, mock_blood_pressure_record):
        """
        Test posting an invalid (above maximum) diastolic value.
        Expect an error message and that the record is not added.
        """
        self.login()
        response = self.client.post('/blood_pressure', data={
            'systolic': '120',
            'diastolic': '130',  # Above maximum
            'date': '2024-11-13',
            'time': '17:00'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Diastolic value must be between 60 and 120 mm Hg.', response.data)

        # Assert that BloodPressureRecord was not instantiated
        mock_blood_pressure_record.assert_not_called()
        # Assert that add and commit were not called
        self.mock_add.assert_not_called()
        self.mock_commit.assert_not_called()

    @patch('app.BloodPressureRecord')
    def test_blood_pressure_post_non_integer_values(self, mock_blood_pressure_record):
        """
        Test posting non-integer systolic and diastolic values.
        Expect an error message and that the record is not added.
        """
        self.login()
        response = self.client.post('/blood_pressure', data={
            'systolic': 'abc',
            'diastolic': 'xyz',
            'date': '2024-11-13',
            'time': '17:00'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Systolic and Diastolic values must be integers.', response.data)

        # Assert that BloodPressureRecord was not instantiated
        mock_blood_pressure_record.assert_not_called()
        # Assert that add and commit were not called
        self.mock_add.assert_not_called()
        self.mock_commit.assert_not_called()

    @patch('app.BloodPressureRecord')
    def test_blood_pressure_post_missing_fields(self, mock_blood_pressure_record):
        """
        Test posting with missing fields.
        Expect an error message and that the record is not added.
        """
        self.login()
        response = self.client.post('/blood_pressure', data={
            'systolic': '',
            'diastolic': '',
            'date': '',
            'time': ''
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Systolic and Diastolic values must be integers.', response.data)

        # Assert that BloodPressureRecord was not instantiated
        mock_blood_pressure_record.assert_not_called()
        # Assert that add and commit were not called
        self.mock_add.assert_not_called()
        self.mock_commit.assert_not_called()

if __name__ == '__main__':
    unittest.main(testRunner=HtmlTestRunner.HTMLTestRunner(output='test-reports'))