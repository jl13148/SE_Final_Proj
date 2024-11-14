import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, time, timedelta
from flask import url_for
from flask_login import login_user, AnonymousUserMixin
from werkzeug.exceptions import NotFound
from app import app
from models import User, Medication, MedicationLog, GlucoseRecord, BloodPressureRecord
import json
import HtmlTestRunner

class HealthAppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SERVER_NAME'] = 'localhost'
        app.config['PREFERRED_URL_SCHEME'] = 'http'

        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

        # Mock database session
        self.patcher_add = patch('app.db.session.add')
        self.patcher_commit = patch('app.db.session.commit')
        self.patcher_rollback = patch('app.db.session.rollback')
        self.patcher_delete = patch('app.db.session.delete')
        self.mock_add = self.patcher_add.start()
        self.mock_commit = self.patcher_commit.start()
        self.mock_rollback = self.patcher_rollback.start()
        self.mock_delete = self.patcher_delete.start()

        # Mock current user
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = 1
        self.mock_user.username = 'testuser'
        self.mock_user.email = 'test@example.com'
        self.mock_user.is_authenticated = True

        # Patch User.query.get and current_user
        self.patcher_user = patch('models.User.query.get', return_value=self.mock_user)
        self.mock_query_get = self.patcher_user.start()
        self.patcher_login = patch('flask_login.utils._get_user', return_value=self.mock_user)
        self.mock_login = self.patcher_login.start()

    def tearDown(self):
        self.patcher_add.stop()
        self.patcher_commit.stop()
        self.patcher_rollback.stop()
        self.patcher_user.stop()
        self.patcher_login.stop()
        self.app_context.pop()

    def login(self):
        """
        Simulate logging in a user by ensuring that the current_user is mocked.
        """
        with patch('flask_login.utils._get_user', return_value=self.mock_user):
            pass

    # Medication Management Tests
    def test_medications_redirect(self):
        """Test /medications redirect"""
        response = self.client.get('/medications')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/medication-schedule', response.location)

    def test_manage_medications_success(self):
        """Test successful medications management"""
        mock_medications = [
            MagicMock(id=1, name='Med1', dosage='10mg'),
            MagicMock(id=2, name='Med2', dosage='20mg')
        ]
        with patch('app.Medication.query') as mock_query:
            mock_query.filter_by.return_value.all.return_value = mock_medications
            response = self.client.get('/medications/manage')
            self.assertEqual(response.status_code, 200)
            mock_query.filter_by.assert_called_with(user_id=self.mock_user.id)

    def test_manage_medications_error(self):
        """Test error in medications management"""
        with patch('app.Medication.query') as mock_query, \
             patch('app.flash') as mock_flash:
            mock_query.filter_by.side_effect = Exception("Database error")
            response = self.client.get('/medications/manage')
            self.assertEqual(response.status_code, 302)
            self.assertIn('/', response.location)
            mock_flash.assert_called_once()

    def test_add_medication_get(self):
        """Test GET request to add medication"""
        response = self.client.get('/medications/add')
        self.assertEqual(response.status_code, 200)

    def test_add_medication_success(self):
            """Test successful medication addition"""
            with patch('app.MedicationForm') as MockForm, \
                patch('app.flash') as mock_flash:
                # Mock form with valid data
                mock_form = MagicMock()
                mock_form.validate_on_submit.return_value = True
                mock_form.name.data = "TestMed"
                mock_form.dosage.data = "10mg"
                mock_form.frequency.data = "daily"
                mock_form.time.data = time(8, 0)
                MockForm.return_value = mock_form

                with app.test_request_context():
                    response = self.client.post('/medications/add')
                    
                    # Verify success
                    self.assertEqual(response.status_code, 302)
                    self.mock_add.assert_called_once()
                    mock_flash.assert_called_with(
                        'Medication added successfully!', 
                        'success'
                    )

    def test_add_medication_database_error(self):
        """Test database error handling in medication addition"""
        with patch('app.MedicationForm') as MockForm, \
            patch('app.flash') as mock_flash:
            # Mock the form to return valid data
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.name.data = "Test Medicine"
            mock_form.dosage.data = "100mg"
            mock_form.frequency.data = "Daily"
            mock_form.time.data = time(9, 0)
            MockForm.return_value = mock_form

            # Force db.session.commit to raise an exception
            self.mock_commit.side_effect = Exception("Database error")
            
            with app.test_request_context():
                response = self.client.post('/medications/add')
                
                # Verify error handling
                self.assertEqual(response.status_code, 302)
                self.mock_rollback.assert_called_once()
                mock_flash.assert_called_with(
                    'Error adding medication: Database error', 
                    'danger'
                )
                # Reset the side effect for other tests
                self.mock_commit.side_effect = None

    def test_delete_medication_success(self):
        """Test successful medication deletion"""
        with patch('app.Medication.query') as mock_query, \
             patch('app.MedicationLog.query') as mock_log_query, \
             patch('app.flash') as mock_flash:
            # Setup mock medication
            mock_med = MagicMock()
            mock_med.user_id = self.mock_user.id
            mock_query.get_or_404.return_value = mock_med
            
            # Setup mock log query
            mock_log_query.filter_by.return_value.delete.return_value = None
            
            response = self.client.post('/medications/1/delete')
            
            # Verify deletion was successful
            self.assertEqual(response.status_code, 302)
            self.mock_delete.assert_called_once_with(mock_med)
            self.mock_commit.assert_called_once()
            mock_flash.assert_called_with('Medication deleted successfully.', 'success')

    def test_delete_medication_unauthorized(self):
        """Test unauthorized medication deletion"""
        with patch('app.Medication.query') as mock_query, \
             patch('app.flash') as mock_flash:
            # Setup mock medication with different user_id
            mock_med = MagicMock()
            mock_med.user_id = 999  # Different user
            mock_query.get_or_404.return_value = mock_med
            
            response = self.client.post('/medications/1/delete')
            
            # Verify unauthorized access was handled
            self.assertEqual(response.status_code, 302)
            self.mock_delete.assert_not_called()
            self.mock_commit.assert_not_called()
            mock_flash.assert_called_with('Unauthorized action.', 'danger')

    def test_delete_medication_database_error(self):
        """Test database error handling in medication deletion"""
        with patch('app.Medication.query') as mock_query, \
             patch('app.MedicationLog.query') as mock_log_query, \
             patch('app.flash') as mock_flash:
            # Setup mock medication
            mock_med = MagicMock()
            mock_med.user_id = self.mock_user.id
            mock_query.get_or_404.return_value = mock_med
            
            # Setup mock log query
            mock_log_query.filter_by.return_value.delete.return_value = None
            
            # Force database error
            self.mock_commit.side_effect = Exception("Database error")
            
            response = self.client.post('/medications/1/delete')
            
            # Verify error handling
            self.assertEqual(response.status_code, 302)
            self.mock_rollback.assert_called_once()
            mock_flash.assert_called_with('An error occurred while deleting the medication.', 'danger')
            
            # Reset the side effect for other tests
            self.mock_commit.side_effect = None

    def test_log_medication_success(self):
        """Test successful medication logging"""
        with patch('app.Medication.query') as mock_query:
            mock_med = MagicMock()
            mock_med.user_id = self.mock_user.id
            mock_query.get_or_404.return_value = mock_med
            
            with patch('app.MedicationLog.query') as mock_log_query:
                mock_log_query.filter.return_value.first.return_value = None
                
                response = self.client.post('/medications/log/1')
                
                self.assertEqual(response.status_code, 200)
                data = json.loads(response.data)
                self.assertEqual(data['message'], 'Medication logged successfully')
                self.mock_add.assert_called_once()
                self.mock_commit.assert_called_once()

    def test_log_medication_unauthorized(self):
        """Test unauthorized medication logging attempt"""
        with patch('app.Medication.query') as mock_query:
            mock_med = MagicMock()
            mock_med.user_id = 10  
            mock_query.get_or_404.return_value = mock_med
            
            response = self.client.post('/medications/log/1')
            
            self.assertEqual(response.status_code, 403)
            data = json.loads(response.data)
            self.assertEqual(data['error'], 'Unauthorized')
            self.mock_add.assert_not_called()
            self.mock_commit.assert_not_called()

    def test_log_medication_already_taken(self):
        """Test logging already taken medication"""
        with patch('app.Medication.query') as mock_query:
            mock_med = MagicMock()
            mock_med.user_id = self.mock_user.id
            mock_query.get_or_404.return_value = mock_med
            
            with patch('app.MedicationLog.query') as mock_log_query:
                mock_log_query.filter.return_value.first.return_value = MagicMock()
                
                response = self.client.post('/medications/log/1')
                
                self.assertEqual(response.status_code, 400)
                data = json.loads(response.data)
                self.assertEqual(data['message'], 'Medication already logged today')
                self.mock_add.assert_not_called()
                self.mock_commit.assert_not_called()

    def test_log_medication_database_error(self):
        """Test database error handling in medication logging"""
        with patch('app.Medication.query') as mock_query:
            mock_med = MagicMock()
            mock_med.user_id = self.mock_user.id
            mock_query.get_or_404.return_value = mock_med
            
            with patch('app.MedicationLog.query') as mock_log_query:
                mock_log_query.filter.return_value.first.return_value = None
                
                # Force database error
                self.mock_commit.side_effect = Exception("Database error")
                
                try:
                    response = self.client.post('/medications/log/1')
                    
                    self.assertEqual(response.status_code, 500)
                    data = json.loads(response.data)
                    self.assertEqual(data['error'], 'Database error')
                    self.mock_rollback.assert_called_once()
                finally:
                    # Reset the side effect
                    self.mock_commit.side_effect = None

    def test_medication_schedule_success(self):
        """Test medication schedule page"""
        response = self.client.get('/medication-schedule')
        self.assertEqual(response.status_code, 200)

    def test_medication_schedule_exception(self):
        """Test medication schedule page with exception"""
        with patch('app.render_template') as mock_render, \
            patch('app.flash') as mock_flash:
            # Force render_template to raise an exception
            mock_render.side_effect = Exception("Template error")
            
            response = self.client.get('/medication-schedule')
            
            # Verify redirect to home page
            self.assertEqual(response.status_code, 302)
            mock_flash.assert_called_with('Error loading schedule. Please try again.', 'danger')

    def test_get_daily_medications_success(self):
        """Test daily medications retrieval"""
        mock_med = MagicMock()
        mock_med.id = 1
        mock_med.name = "TestMed"
        mock_med.dosage = "10mg"
        mock_med.time = time(8, 0)
        mock_med.frequency = "daily"
        
        with patch('app.Medication.query') as mock_query:
            mock_query.filter_by.return_value.all.return_value = [mock_med]
            
            response = self.client.get('/medications/daily')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], "TestMed")

    def test_get_daily_medications_exception(self):
        """Test daily medications retrieval with database error"""
        with patch('app.Medication.query') as mock_query:
            # Force database error
            mock_query.filter_by.side_effect = Exception("Database error")
            
            response = self.client.get('/medications/daily')
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertEqual(data['error'], 'Database error')

    def test_check_reminders_success(self):
        """Test medication reminders"""
        current_time = datetime.now()
        test_time = (current_time + timedelta(minutes=10)).time()
        
        mock_med = MagicMock()
        mock_med.id = 1
        mock_med.name = "TestMed"
        mock_med.dosage = "10mg"
        mock_med.time = test_time
        
        with patch('app.Medication.query') as mock_query, \
            patch('app.MedicationLog.query') as mock_log_query:
            mock_query.filter_by.return_value.all.return_value = [mock_med]
            mock_log_query.filter.return_value.first.return_value = None
            
            response = self.client.get('/medications/check-reminders')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], 'TestMed')

    def test_check_reminders_exception(self):
        """Test medication reminders with database error"""
        with patch('app.Medication.query') as mock_query:
            # Force database error
            mock_query.filter_by.side_effect = Exception("Database error")
            
            response = self.client.get('/medications/check-reminders')
            
            self.assertEqual(response.status_code, 500)
            data = json.loads(response.data)
            self.assertEqual(data['error'], 'Database error')

    def test_check_reminders_empty(self):
        """Test medication reminders with no upcoming medications"""
        current_time = datetime.now()
        test_time = (current_time + timedelta(hours=2)).time()  # Time far in future
        
        mock_med = MagicMock()
        mock_med.id = 1
        mock_med.name = "TestMed"
        mock_med.dosage = "10mg"
        mock_med.time = test_time
        
        with patch('app.Medication.query') as mock_query, \
            patch('app.MedicationLog.query') as mock_log_query:
            mock_query.filter_by.return_value.all.return_value = [mock_med]
            mock_log_query.filter.return_value.first.return_value = None
            
            response = self.client.get('/medications/check-reminders')
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(len(data), 0)  # No medications should be returned


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

    # Check db for Logger
    def test_blood_pressure_records_success(self):
        """Test successful blood pressure records retrieval"""
        # Create mock records
        mock_record1 = MagicMock(spec=BloodPressureRecord)
        mock_record1.date = datetime.now().date()
        mock_record1.time = datetime.now().time()
        mock_record1.systolic = 120
        mock_record1.diastolic = 80

        with patch('app.BloodPressureRecord.query') as mock_query, \
            patch('app.render_template') as mock_render:
            # Setup query mock
            mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_record1]
            mock_render.return_value = 'rendered template'
            
            response = self.client.get('/blood_pressure_records')
            
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_with('pages/blood_pressure_records.html', records=[mock_record1])

    def test_glucose_records_success(self):
        """Test successful glucose records retrieval"""
        # Create mock records
        mock_record1 = MagicMock(spec=GlucoseRecord)
        mock_record1.date = datetime.now().date()
        mock_record1.time = datetime.now().time()
        mock_record1.level = 100

        with patch('app.GlucoseRecord.query') as mock_query, \
            patch('app.render_template') as mock_render:
            # Setup query mock
            mock_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_record1]
            mock_render.return_value = 'rendered template'
            
            response = self.client.get('/glucose_records')
            
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_with('pages/glucose_records.html', records=[mock_record1])

    def test_delete_glucose_record_success(self):
        """Test successful glucose record deletion"""
        with patch('app.GlucoseRecord.query') as mock_query, \
            patch('app.flash') as mock_flash:
            # Setup mock record
            mock_record = MagicMock(spec=GlucoseRecord)
            mock_record.user_id = self.mock_user.id
            mock_query.get_or_404.return_value = mock_record
            
            response = self.client.post('/glucose_records/delete/1')
            
            self.assertEqual(response.status_code, 302)
            self.mock_delete.assert_called_once_with(mock_record)
            self.mock_commit.assert_called_once()
            mock_flash.assert_called_with('Glucose record deleted.', 'success')

    def test_delete_glucose_record_unauthorized(self):
        """Test unauthorized glucose record deletion"""
        with patch('app.GlucoseRecord.query') as mock_query, \
            patch('app.flash') as mock_flash:
            # Setup mock record with different user_id
            mock_record = MagicMock(spec=GlucoseRecord)
            mock_record.user_id = 99  # Different from self.mock_user.id
            mock_query.get_or_404.return_value = mock_record
            
            response = self.client.post('/glucose_records/delete/1')
            
            self.assertEqual(response.status_code, 302)
            self.mock_delete.assert_not_called()
            self.mock_commit.assert_not_called()
            mock_flash.assert_called_with('Unauthorized access.', 'danger')

    def test_delete_glucose_record_not_found(self):
        """Test deletion of non-existent glucose record"""
        with patch('app.GlucoseRecord.query') as mock_query:
            mock_query.get_or_404.side_effect = NotFound()
            
            response = self.client.post('/glucose_records/delete/99')
            
            self.assertEqual(response.status_code, 404)
            self.mock_delete.assert_not_called()
            self.mock_commit.assert_not_called()

    def test_delete_blood_pressure_record_success(self):
        """Test successful blood pressure record deletion"""
        with patch('app.BloodPressureRecord.query') as mock_query, \
            patch('app.flash') as mock_flash:
            # Setup mock record
            mock_record = MagicMock(spec=BloodPressureRecord)
            mock_record.user_id = self.mock_user.id
            mock_query.get_or_404.return_value = mock_record
            
            response = self.client.post('/blood_pressure_records/delete/1')
            
            self.assertEqual(response.status_code, 302)
            self.mock_delete.assert_called_once_with(mock_record)
            self.mock_commit.assert_called_once()
            mock_flash.assert_called_with('Blood pressure record deleted.', 'success')

    def test_delete_blood_pressure_record_unauthorized(self):
        """Test unauthorized blood pressure record deletion"""
        with patch('app.BloodPressureRecord.query') as mock_query, \
            patch('app.flash') as mock_flash:
            # Setup mock record with different user_id
            mock_record = MagicMock(spec=BloodPressureRecord)
            mock_record.user_id = 99  # Different from self.mock_user.id
            mock_query.get_or_404.return_value = mock_record
            
            response = self.client.post('/blood_pressure_records/delete/1')
            
            self.assertEqual(response.status_code, 302)
            self.mock_delete.assert_not_called()
            self.mock_commit.assert_not_called()
            mock_flash.assert_called_with('Unauthorized access.', 'danger')

    def test_delete_blood_pressure_record_not_found(self):
        """Test deletion of non-existent blood pressure record"""
        with patch('app.BloodPressureRecord.query') as mock_query:
            mock_query.get_or_404.side_effect = NotFound()
            
            response = self.client.post('/blood_pressure_records/delete/99')
            
            self.assertEqual(response.status_code, 404)
            self.mock_delete.assert_not_called()
            self.mock_commit.assert_not_called()
if __name__ == '__main__':
    # Use a simpler test runner if HtmlTestRunner is causing issues
    try:
        unittest.main(testRunner=HtmlTestRunner.HTMLTestRunner(
            output='test_reports',
            combine_reports=True,
            report_title="Test Results",
            add_timestamp=True
        ))
    except AttributeError:
        # Fallback to standard test runner
        unittest.main(verbosity=2)