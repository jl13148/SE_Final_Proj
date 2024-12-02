# tests/integration/test_health_routes.py
from unittest.mock import patch, MagicMock, ANY
from flask import url_for
from flask_login import AnonymousUserMixin
from tests.base import BaseTestCase

class TestHealthRoutes(BaseTestCase):
    def test_health_logger_get(self):
        """Test GET request to health logger page"""
        self.login()
        response = self.client.get('/health-logger')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Health Logger', response.data)

    # Glucose Routes Tests
    def test_glucose_logger_get_requires_login(self):
        """Test accessing glucose logger without login"""
        with patch('flask_login.utils._get_user', return_value=AnonymousUserMixin()):
            response = self.client.get('/glucose/logger')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.headers['Location'])

    def test_glucose_logger_get_success(self):
        """Test GET request to glucose logger page"""
        self.login()
        response = self.client.get('/glucose/logger')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Glucose Logger', response.data)

    def test_glucose_logger_post_invalid_input(self):
        """Test POST request with invalid glucose input"""
        self.login()
        response = self.client.post('/glucose/logger', data={
            'glucose_level': 'abc',  # Invalid: non-numeric
            'glucose_type': 'FASTING',
            'date': '2024-01-01',
            'time': '10:00'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid input', response.data)

    def test_glucose_logger_post_missing_data(self):
        """Test POST request with missing required data"""
        self.login()
        response = self.client.post('/glucose/logger', data={
            'glucose_type': 'FASTING',
            # Missing glucose_level, date, time
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid input', response.data)

    def test_glucose_records_get(self):
        """Test viewing glucose records"""
        self.login()
        with patch('app.health_service.get_glucose_records') as mock_get_records:
            mock_get_records.return_value = (True, [], None)
            response = self.client.get('/glucose/records')
            self.assertEqual(response.status_code, 200)

    def test_glucose_records_delete_unauthorized(self):
        """Test unauthorized deletion of glucose record"""
        self.login()
        with patch('app.GlucoseRecord.query') as mock_query:
            mock_record = MagicMock()
            mock_record.user_id = self.test_user.id + 1  # Different user
            mock_query.get_or_404.return_value = mock_record
            
            response = self.client.post('/glucose/records/delete/1')
            self.assertEqual(response.status_code, 302)
            self.assertIn(b'Unauthorized', response.data)

    # Blood Pressure Routes Tests
    def test_blood_pressure_logger_get_requires_login(self):
        """Test accessing blood pressure logger without login"""
        with patch('flask_login.utils._get_user', return_value=AnonymousUserMixin()):
            response = self.client.get('/blood_pressure/logger')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/login', response.headers['Location'])

    def test_blood_pressure_logger_get_success(self):
        """Test GET request to blood pressure logger page"""
        self.login()
        response = self.client.get('/blood_pressure/logger')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Blood Pressure Logger', response.data)

    def test_blood_pressure_logger_post_invalid_input(self):
        """Test POST request with invalid blood pressure input"""
        self.login()
        response = self.client.post('/blood_pressure/logger', data={
            'systolic': 'abc',  # Invalid: non-numeric
            'diastolic': '80',
            'date': '2024-01-01',
            'time': '10:00'
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid input', response.data)

    def test_blood_pressure_records_get(self):
        """Test viewing blood pressure records"""
        self.login()
        with patch('app.health_service.get_blood_pressure_records') as mock_get_records:
            mock_get_records.return_value = (True, [], None)
            response = self.client.get('/blood_pressure/records')
            self.assertEqual(response.status_code, 200)

    def test_blood_pressure_records_delete_unauthorized(self):
        """Test unauthorized deletion of blood pressure record"""
        self.login()
        with patch('app.BloodPressureRecord.query') as mock_query:
            mock_record = MagicMock()
            mock_record.user_id = self.test_user.id + 1  # Different user
            mock_query.get_or_404.return_value = mock_record
            
            response = self.client.post('/blood_pressure/records/delete/1')
            self.assertEqual(response.status_code, 302)
            self.assertIn(b'Unauthorized', response.data)

    # Edit Record Routes Tests
    def test_edit_glucose_record_get_success(self):
        """Test GET request to edit glucose record"""
        self.login()
        with patch('app.GlucoseRecord.query') as mock_query:
            mock_record = MagicMock()
            mock_record.user_id = self.test_user.id
            mock_query.get_or_404.return_value = mock_record
            
            response = self.client.get('/glucose/edit/1')
            self.assertEqual(response.status_code, 200)

    def test_edit_blood_pressure_record_get_success(self):
        """Test GET request to edit blood pressure record"""
        self.login()
        with patch('app.BloodPressureRecord.query') as mock_query:
            mock_record = MagicMock()
            mock_record.user_id = self.test_user.id
            mock_query.get_or_404.return_value = mock_record
            
            response = self.client.get('/blood_pressure/edit/1')
            self.assertEqual(response.status_code, 200)