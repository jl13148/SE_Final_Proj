import unittest
from unittest.mock import patch, MagicMock, ANY, call 
from datetime import datetime, time, timedelta
from click.testing import CliRunner
from flask.cli import ScriptInfo
from flask import url_for
from flask_login import login_user, AnonymousUserMixin
from werkzeug.exceptions import NotFound
from django.db import IntegrityError
from app import app, ExportPDFForm, ExportCSVForm, reset_db, init_db
from models import db, User, Medication, GlucoseRecord, BloodPressureRecord, MedicationLog, UserType, AccessLevel, CompanionAccess
import json
import HtmlTestRunner

class HealthAppTestCase(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SERVER_NAME'] = 'localhost'
        app.config['PREFERRED_URL_SCHEME'] = 'http'

        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

        # Create all database tables
        db.create_all()

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

        # Mock the utility_processor with proper context
        self.mock_context = {'pending_connections_count': 0}
        self.patcher_utility = patch('app.utility_processor', return_value=self.mock_context)
        self.mock_utility = self.patcher_utility.start()

        # Patch User.query.get and current_user
        self.patcher_user = patch('models.User.query.get', return_value=self.mock_user)
        self.mock_query_get = self.patcher_user.start()
        self.patcher_login = patch('flask_login.utils._get_user', return_value=self.mock_user)
        self.mock_login = self.patcher_login.start()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.patcher_add.stop()
        self.patcher_commit.stop()
        self.patcher_rollback.stop()
        self.patcher_delete.stop()
        self.patcher_user.stop()
        self.patcher_login.stop()
        self.patcher_utility.stop()
        self.app_context.pop()

    def login(self):
        """
        Simulate logging in a user by ensuring that the current_user is mocked.
        """
        with patch('flask_login.utils._get_user', return_value=self.mock_user):
            pass

#----------------------------------------------------------------------------#
# Login and Register Tests
#----------------------------------------------------------------------------#
    def test_login_success_patient(self):
        """Test successful login for patient users"""
        with patch('app.LoginForm') as MockForm, \
            patch('app.current_user', is_authenticated=False):
            
            # Create mock user
            mock_user = MagicMock(spec=User)
            mock_user.user_type = 'PATIENT'
            mock_user.check_password.return_value = True
            mock_user.patients = []
            
            # Setup form mock with proper data
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.email.data = 'test@test.com'
            mock_form.password.data = 'password'
            mock_form.user_type.data = 'PATIENT'
            mock_form.remember.data = True
            MockForm.return_value = mock_form

            # Setup user query mock
            with patch('app.User.query') as mock_query:
                mock_query.filter_by.return_value.first.return_value = mock_user

                # Setup login_user mock
                with patch('app.login_user') as mock_login:
                    response = self.client.post('/login', data={
                        'email': 'test@test.com',
                        'password': 'password',
                        'user_type': 'PATIENT',
                        'remember': True
                    })

                    mock_login.assert_called_once_with(mock_user, remember=True)
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(response.location, '/')

    def test_login_success_companion_no_patients(self):
        """Test successful login for companion without linked patients"""
        with patch('app.LoginForm') as MockForm, \
            patch('app.current_user', is_authenticated=False):
            
            # Create mock user
            mock_user = MagicMock(spec=User)
            mock_user.user_type = 'companion'
            mock_user.check_password.return_value = True
            mock_user.patients = []  # No linked patients
            
            # Setup form mock
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.email.data = 'companion@test.com'
            mock_form.password.data = 'password'
            mock_form.user_type.data = 'companion'
            mock_form.remember.data = True
            MockForm.return_value = mock_form
            
            with patch('app.User.query') as mock_query, \
                patch('app.login_user') as mock_login:
                mock_query.filter_by.return_value.first.return_value = mock_user
                
                response = self.client.post('/login', data={
                    'email': 'companion@test.com',
                    'password': 'password',
                    'user_type': 'companion',
                    'remember': True
                })
                
                mock_login.assert_called_once_with(mock_user, remember=True)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/companion/setup')

    def test_login_success_companion_with_patients(self):
        """Test successful login for companion with linked patients"""
        with patch('app.LoginForm') as MockForm, \
            patch('app.current_user', is_authenticated=False):
            
            # Create mock user
            mock_user = MagicMock(spec=User)
            mock_user.user_type = 'companion'
            mock_user.check_password.return_value = True
            mock_user.patients = [MagicMock()]  # Has linked patients
            
            # Setup form mock
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.email.data = 'companion@test.com'
            mock_form.password.data = 'password'
            mock_form.user_type.data = 'companion'
            mock_form.remember.data = True
            MockForm.return_value = mock_form
            
            with patch('app.User.query') as mock_query, \
                patch('app.login_user') as mock_login:
                mock_query.filter_by.return_value.first.return_value = mock_user
                
                response = self.client.post('/login', data={
                    'email': 'companion@test.com',
                    'password': 'password',
                    'user_type': 'companion',
                    'remember': True
                })
                
                mock_login.assert_called_once_with(mock_user, remember=True)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/')

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials"""
        with patch('app.LoginForm') as MockForm, \
            patch('app.current_user', is_authenticated=False):
            
            # Setup form mock
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.email.data = 'test@test.com'
            mock_form.password.data = 'wrongpassword'
            mock_form.user_type.data = 'PATIENT'
            MockForm.return_value = mock_form
            
            with patch('app.User.query') as mock_query, \
                patch('app.render_template') as mock_render:
                # User not found
                mock_query.filter_by.return_value.first.return_value = None
                mock_render.return_value = ''
                
                response = self.client.post('/login', data={
                    'email': 'test@test.com',
                    'password': 'wrongpassword',
                    'user_type': 'PATIENT'
                })
                
                self.assertEqual(response.status_code, 200)

    def test_register_success_patient(self):
        """Test successful registration for patient user"""
        with patch('app.RegisterForm') as MockForm, \
            patch('app.current_user', is_authenticated=False):
            
            # Setup form mock with validation passing
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.username.data = 'testuser'
            mock_form.email.data = 'test@test.com'
            mock_form.password.data = 'password'
            mock_form.user_type.data = 'PATIENT'
            MockForm.return_value = mock_form
            
            with patch('app.User') as MockUser:
                # Setup mock user
                mock_user = MagicMock()
                mock_user.set_password = MagicMock()
                MockUser.return_value = mock_user
                
                response = self.client.post('/register', data={
                    'username': 'testuser',
                    'email': 'test@test.com',
                    'password': 'password',
                    'confirm_password': 'password',
                    'user_type': 'PATIENT'
                })
                
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/login')
                self.mock_add.assert_called_once_with(mock_user)
                self.mock_commit.assert_called_once()

    def test_register_success_companion(self):
        """Test successful registration for companion user"""
        with patch('app.RegisterForm') as MockForm, \
            patch('app.current_user', is_authenticated=False):
            
            # Setup form mock with validation passing
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.username.data = 'companion'
            mock_form.email.data = 'companion@test.com'
            mock_form.password.data = 'password'
            mock_form.user_type.data = 'COMPANION'
            MockForm.return_value = mock_form
            
            with patch('app.User') as MockUser, \
                patch('app.login_user') as mock_login:
                # Setup mock user
                mock_user = MagicMock()
                mock_user.set_password = MagicMock()
                MockUser.return_value = mock_user
                
                response = self.client.post('/register', data={
                    'username': 'companion',
                    'email': 'companion@test.com',
                    'password': 'password',
                    'confirm_password': 'password',
                    'user_type': 'COMPANION'
                })
                
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.location, '/companion/setup')
                mock_login.assert_called_once_with(mock_user)
                self.mock_add.assert_called_once_with(mock_user)
                self.mock_commit.assert_called_once()

    def test_register_database_error(self):
        """Test registration with database error"""
        with patch('app.RegisterForm') as MockForm, \
            patch('app.current_user', is_authenticated=False), \
            patch('app.render_template') as mock_render:
            
            # Setup form mock
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.username.data = 'testuser'
            mock_form.email.data = 'test@test.com'
            mock_form.password.data = 'password'
            mock_form.user_type.data = 'PATIENT'
            MockForm.return_value = mock_form
            
            with patch('app.User') as MockUser:
                mock_user = MagicMock()
                MockUser.return_value = mock_user
                mock_render.return_value = ''
                
                # Force database error
                self.mock_commit.side_effect = Exception("Database error")
                
                response = self.client.post('/register', data={
                    'username': 'testuser',
                    'email': 'test@test.com',
                    'password': 'password',
                    'confirm_password': 'password',
                    'user_type': 'PATIENT'
                })
                
                self.assertEqual(response.status_code, 200)
                self.mock_rollback.assert_called_once()

    def test_register_form_validation_error(self):
        """Test registration with form validation error"""
        with patch('app.RegisterForm') as MockForm, \
            patch('app.current_user', is_authenticated=False), \
            patch('app.render_template') as mock_render:
            
            # Setup form mock with validation failing
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = False
            MockForm.return_value = mock_form
            mock_render.return_value = ''
            
            response = self.client.post('/register', data={})
            
            self.assertEqual(response.status_code, 200)
            self.mock_add.assert_not_called()
            self.mock_commit.assert_not_called()

#----------------------------------------------------------------------------#
# Database Tests
#----------------------------------------------------------------------------#
    def test_reset_db_success(self):
        """Test successful database reset"""
        runner = CliRunner()
        
        with patch('app.db.drop_all') as mock_drop, \
            patch('app.db.create_all') as mock_create:
            
            # Create an app context for the command
            obj = ScriptInfo(create_app=lambda info: app)
            
            # Run the command
            result = runner.invoke(reset_db, obj=obj)
            
            # Verify command execution
            self.assertEqual(result.exit_code, 0)
            mock_drop.assert_called_once()
            mock_create.assert_called_once()
            self.assertIn('Database has been reset!', result.output)

    def test_init_db_empty_database(self):
        """Test database initialization when no tables exist"""
        with patch('app.db.engine.connect') as mock_connect, \
            patch('app.db.inspect') as mock_inspect, \
            patch('app.db.create_all') as mock_create_all, \
            patch('builtins.print') as mock_print:
            
            # Mock inspector to return empty table list
            mock_inspector = MagicMock()
            mock_inspector.get_table_names.return_value = []
            mock_inspect.return_value = mock_inspector
            
            result = init_db()
            
            # Verify all expected operations occurred
            self.assertTrue(result)
            mock_connect.assert_called_once()
            mock_create_all.assert_called_once()
            
            # Verify print messages
            mock_print.assert_has_calls([
                call("No tables found. Creating database schema..."),
                call("Database schema created successfully!")
            ])

    def test_init_db_existing_tables(self):
        """Test database initialization when tables already exist"""
        with patch('app.db.engine.connect') as mock_connect, \
            patch('app.db.inspect') as mock_inspect, \
            patch('builtins.print') as mock_print:
            
            # Mock inspector to return all expected tables
            expected_tables = [
                'users',
                'medications',
                'glucose_records',
                'blood_pressure_records',
                'medication_logs',
                'companion_access'
            ]
            mock_inspector = MagicMock()
            mock_inspector.get_table_names.return_value = expected_tables
            mock_inspect.return_value = mock_inspector
            
            result = init_db()
            
            # Verify operations
            self.assertTrue(result)
            mock_connect.assert_called_once()
            mock_print.assert_called_once_with(f"Found existing tables: {expected_tables}")

    def test_init_db_missing_tables(self):
        """Test database initialization when some tables are missing"""
        with patch('app.db.engine.connect') as mock_connect, \
            patch('app.db.inspect') as mock_inspect, \
            patch('builtins.print') as mock_print:
            
            # Mock inspector to return partial table list
            existing_tables = ['users', 'medications']
            mock_inspector = MagicMock()
            mock_inspector.get_table_names.return_value = existing_tables
            mock_inspect.return_value = mock_inspector
            
            # Mock table creation
            mock_table = MagicMock()
            expected_missing_tables = [
                'glucose_records',
                'blood_pressure_records',
                'medication_logs',
                'companion_access'
            ]
            
            # Mock the models' __table__ attribute
            for model in [GlucoseRecord, BloodPressureRecord, MedicationLog, CompanionAccess]:
                setattr(model, '__table__', mock_table)
            
            result = init_db()
            
            # Verify operations
            self.assertTrue(result)
            mock_connect.assert_called_once()
            
            # Verify print messages for missing tables
            expected_calls = [call(f"Found existing tables: {existing_tables}")] + \
                            [call(f"Creating missing table: {table}") for table in expected_missing_tables]
            mock_print.assert_has_calls(expected_calls, any_order=True)
            
            # Verify table creation calls
            self.assertEqual(mock_table.create.call_count, len(expected_missing_tables))

    def test_init_db_connection_error(self):
        """Test database initialization when connection fails"""
        with patch('app.db.engine.connect') as mock_connect, \
            patch('builtins.print') as mock_print:
            
            # Force connection error
            mock_connect.side_effect = Exception("Connection failed")
            
            result = init_db()
            
            # Verify operations
            self.assertFalse(result)
            mock_connect.assert_called_once()
            mock_print.assert_called_once_with("Database initialization error: Connection failed")

    def test_init_db_inspection_error(self):
        """Test database initialization when inspection fails"""
        with patch('app.db.engine.connect') as mock_connect, \
            patch('app.db.inspect') as mock_inspect, \
            patch('builtins.print') as mock_print:
            
            # Force inspection error
            mock_inspect.side_effect = Exception("Inspection failed")
            
            result = init_db()
            
            # Verify operations
            self.assertFalse(result)
            mock_connect.assert_called_once()
            mock_print.assert_called_once_with("Database initialization error: Inspection failed")
            
#----------------------------------------------------------------------------#
# Medication Management Tests
#----------------------------------------------------------------------------#
    def test_medications_redirect(self):
        """Test /medications redirect"""
        response = self.client.get('/medications')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/medications/manage', response.location)

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
            mock_flash.assert_called_with('Error loading schedule. Please try again. Template error', 'danger')

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

    @patch('app.Medication')
    def test_edit_medication_get_success(self, mock_medication_class):
        """Test successful GET request to edit medication"""
        self.login()
        
        # Setup mock medication
        mock_medication = MagicMock()
        mock_medication.user_id = self.mock_user.id
        mock_medication.name = "TestMed"
        mock_medication.dosage = "10mg"
        mock_medication.frequency = "daily"
        mock_medication.time = time(8, 0)
        
        mock_medication_class.query.get_or_404.return_value = mock_medication
        
        response = self.client.get('/medications/1/edit')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'TestMed', response.data)  # Verify form is populated
        mock_medication_class.query.get_or_404.assert_called_with(1)

    @patch('app.Medication')
    def test_edit_medication_get_unauthorized(self, mock_medication_class):
        """Test GET request to edit medication with unauthorized access"""
        self.login()
        
        # Setup mock medication with different user_id
        mock_medication = MagicMock()
        mock_medication.user_id = 1022  # Different from self.mock_user.id
        mock_medication_class.query.get_or_404.return_value = mock_medication
        
        response = self.client.get('/medications/1/edit', follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Unauthorized access.', response.data)
        mock_medication_class.query.get_or_404.assert_called_with(1)

    @patch('app.Medication')
    def test_edit_medication_get_not_found(self, mock_medication_class):
        """Test GET request to edit non-existent medication"""
        self.login()
        
        mock_medication_class.query.get_or_404.side_effect = NotFound()
        
        response = self.client.get('/medications/1022/edit')
        
        self.assertEqual(response.status_code, 404)

    @patch('app.Medication')
    @patch('app.MedicationForm')
    def test_edit_medication_post_success(self, mock_form_class, mock_medication_class):
        """Test successful POST request to edit medication"""
        self.login()
        
        # Setup mock medication
        mock_medication = MagicMock()
        mock_medication.user_id = self.mock_user.id
        mock_medication_class.query.get_or_404.return_value = mock_medication
        
        # Setup mock form with valid data
        mock_form = MagicMock()
        mock_form.validate_on_submit.return_value = True
        mock_form.name.data = "Updated Med"
        mock_form.dosage.data = "20mg"
        mock_form.frequency.data = "twice daily"
        mock_form.time.data = time(9, 0)
        mock_form_class.return_value = mock_form
        
        response = self.client.post('/medications/1/edit', 
                                data={
                                    'name': 'Updated Med',
                                    'dosage': '20mg',
                                    'frequency': 'twice daily',
                                    'time': '09:00'
                                },
                                follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Medication updated successfully!', response.data)
        
        # Verify medication was updated
        self.assertEqual(mock_medication.name, "Updated Med")
        self.assertEqual(mock_medication.dosage, "20mg")
        self.assertEqual(mock_medication.frequency, "twice daily")
        self.assertEqual(mock_medication.time, time(9, 0))
        
        self.mock_commit.assert_called_once()

    @patch('app.Medication')
    @patch('app.MedicationForm')
    def test_edit_medication_post_unauthorized(self, mock_form_class, mock_medication_class):
        """Test POST request to edit medication with unauthorized access"""
        self.login()
        
        # Setup mock medication with different user_id
        mock_medication = MagicMock()
        mock_medication.user_id = 1022  # Different from self.mock_user.id
        mock_medication_class.query.get_or_404.return_value = mock_medication
        
        response = self.client.post('/medications/1/edit',
                                data={
                                    'name': 'Updated Med',
                                    'dosage': '20mg',
                                    'frequency': 'twice daily',
                                    'time': '09:00'
                                },
                                follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Unauthorized access.', response.data)
        self.mock_commit.assert_not_called()

    @patch('app.Medication')
    @patch('app.MedicationForm')
    def test_edit_medication_post_validation_error(self, mock_form_class, mock_medication_class):
        """Test POST request with invalid form data"""
        self.login()
        
        # Setup mock medication
        mock_medication = MagicMock()
        mock_medication.user_id = self.mock_user.id
        mock_medication_class.query.get_or_404.return_value = mock_medication
        
        # Setup mock form that fails validation
        mock_form = MagicMock()
        mock_form.validate_on_submit.return_value = False
        mock_form_class.return_value = mock_form
        
        response = self.client.post('/medications/1/edit',
                                data={},  # Empty data to trigger validation error
                                follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.mock_commit.assert_not_called()

    @patch('app.Medication')
    @patch('app.MedicationForm')
    def test_edit_medication_post_database_error(self, mock_form_class, mock_medication_class):
        """Test POST request with database error"""
        self.login()
        
        # Setup mock medication
        mock_medication = MagicMock()
        mock_medication.user_id = self.mock_user.id
        mock_medication_class.query.get_or_404.return_value = mock_medication
        
        # Setup mock form with valid data
        mock_form = MagicMock()
        mock_form.validate_on_submit.return_value = True
        mock_form.name.data = "Updated Med"
        mock_form.dosage.data = "20mg"
        mock_form.frequency.data = "twice daily"
        mock_form.time.data = time(9, 0)
        mock_form_class.return_value = mock_form
        
        # Force database error
        self.mock_commit.side_effect = Exception("Database error")
        
        response = self.client.post('/medications/1/edit',
                                data={
                                    'name': 'Updated Med',
                                    'dosage': '20mg',
                                    'frequency': 'twice daily',
                                    'time': '09:00'
                                },
                                follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error updating medication: Database error', response.data)
        self.mock_rollback.assert_called_once()

#----------------------------------------------------------------------------#
# Health Logger Tests
#----------------------------------------------------------------------------#
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

    # BVA for logging glucose value
    @patch('app.GlucoseRecord')
    def test_glucose_post_boundary_values(self, mock_glucose_record):
        """
        Test glucose level input using Boundary Value Analysis
        Valid range: 70-180 mg/dL
        Test values: 69 (invalid), 70 (min), 71 (min+1), 179 (max-1), 180 (max), 181 (invalid)
        """
        self.login()
        
        # Mock is_duplicate_record to return False
        with patch('app.is_duplicate_record', return_value=False):
            test_cases = [
                # (glucose_level, expected_message, should_create_record)
                (69, b'Glucose level must be between 70 and 180 mg/dL.', False),  # Below minimum
                (70, b'Glucose data logged successfully!', True),  # Minimum boundary
                (71, b'Glucose data logged successfully!', True),  # Just above minimum
                (179, b'Glucose data logged successfully!', True), # Just below maximum
                (180, b'Glucose data logged successfully!', True), # Maximum boundary
                (181, b'Glucose level must be between 70 and 180 mg/dL.', False)  # Above maximum
            ]

            base_data = {
                'date': '2024-11-13',
                'time': '17:00'
            }

            for glucose_level, expected_message, should_create_record in test_cases:
                with self.subTest(glucose_level=glucose_level):
                    mock_glucose_record.reset_mock()
                    self.mock_add.reset_mock()
                    self.mock_commit.reset_mock()

                    test_data = base_data.copy()
                    test_data['glucose_level'] = str(glucose_level)

                    response = self.client.post('/glucose', 
                                            data=test_data, 
                                            follow_redirects=True)

                    self.assertEqual(response.status_code, 200)
                    self.assertIn(expected_message, response.data)
                    
                    if should_create_record:
                        mock_glucose_record.assert_called_with(
                            glucose_level=glucose_level,
                            date='2024-11-13',
                            time='17:00',
                            user_id=self.mock_user.id
                        )
                        self.mock_add.assert_called_once()
                        self.mock_commit.assert_called_once()
                    else:
                        mock_glucose_record.assert_not_called()
                        self.mock_add.assert_not_called()
                        self.mock_commit.assert_not_called()

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
    
    # strong equivalance partitions for logging blood pressure
    @patch('app.BloodPressureRecord')
    def test_blood_pressure_post_strong_equivalence_partitions(self, mock_blood_pressure_record):
        """
        Test blood pressure logging using Strong Equivalence Partitioning
        
        Partitions:
        Systolic (S):
        - S1: Invalid low: < 90 mm Hg
        - S2: Valid: 90-180 mm Hg
        - S3: Invalid high: > 180 mm Hg
        
        Diastolic (D):
        - D1: Invalid low: < 60 mm Hg
        - D2: Valid: 60-120 mm Hg
        - D3: Invalid high: > 120 mm Hg
        
        Test cases (strong equivalence testing - all combinations):
        1. (S1,D1): (80,50) - Both invalid low
        2. (S1,D2): (80,80) - Invalid low systolic, Valid diastolic
        3. (S1,D3): (80,130) - Invalid low systolic, Invalid high diastolic
        4. (S2,D1): (120,50) - Valid systolic, Invalid low diastolic
        5. (S2,D2): (120,80) - Both valid
        6. (S2,D3): (120,130) - Valid systolic, Invalid high diastolic
        7. (S3,D1): (190,50) - Invalid high systolic, Invalid low diastolic
        8. (S3,D2): (190,80) - Invalid high systolic, Valid diastolic
        9. (S3,D3): (190,130) - Both invalid high
        """
        self.login()
        
        # Mock is_duplicate_record to return False
        with patch('app.is_duplicate_record', return_value=False):
            test_cases = [
                # (systolic, diastolic, expected_message, should_create_record)
                (80, 50, b'Systolic value must be between 90 and 180 mm Hg.', False),    # Case 1
                (80, 80, b'Systolic value must be between 90 and 180 mm Hg.', False),    # Case 2
                (80, 130, b'Systolic value must be between 90 and 180 mm Hg.', False),   # Case 3
                (120, 50, b'Diastolic value must be between 60 and 120 mm Hg.', False),  # Case 4
                (120, 80, b'Blood pressure data logged successfully!', True),            # Case 5
                (120, 130, b'Diastolic value must be between 60 and 120 mm Hg.', False), # Case 6
                (190, 50, b'Systolic value must be between 90 and 180 mm Hg.', False),   # Case 7
                (190, 80, b'Systolic value must be between 90 and 180 mm Hg.', False),   # Case 8
                (190, 130, b'Systolic value must be between 90 and 180 mm Hg.', False)   # Case 9
            ]

            base_data = {
                'date': '2024-11-13',
                'time': '17:00'
            }

            for systolic, diastolic, expected_message, should_create_record in test_cases:
                with self.subTest(systolic=systolic, diastolic=diastolic):
                    mock_blood_pressure_record.reset_mock()
                    self.mock_add.reset_mock()
                    self.mock_commit.reset_mock()

                    test_data = base_data.copy()
                    test_data['systolic'] = str(systolic)
                    test_data['diastolic'] = str(diastolic)

                    response = self.client.post('/blood_pressure', 
                                            data=test_data, 
                                            follow_redirects=True)

                    self.assertEqual(response.status_code, 200)
                    self.assertIn(expected_message, response.data)

                    if should_create_record:
                        mock_blood_pressure_record.assert_called_with(
                            systolic=systolic,
                            diastolic=diastolic,
                            date='2024-11-13',
                            time='17:00',
                            user_id=self.mock_user.id
                        )
                        self.mock_add.assert_called_once()
                        self.mock_commit.assert_called_once()
                    else:
                        mock_blood_pressure_record.assert_not_called()
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
    # Test cases for edit_glucose_record
    @patch('app.GlucoseRecord')
    def test_edit_glucose_record_get_success(self, mock_glucose_record_class):
        """Test successful GET request to edit glucose record"""
        self.login()
        
        # Setup mock record
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_record.glucose_level = 100
        mock_record.date = "2024-01-01"
        mock_record.time = "10:00"
        
        mock_glucose_record_class.query.get_or_404.return_value = mock_record
        
        response = self.client.get('/glucose/edit/1')
        
        self.assertEqual(response.status_code, 200)
        mock_glucose_record_class.query.get_or_404.assert_called_with(1)

    @patch('app.GlucoseRecord')
    def test_edit_glucose_record_get_unauthorized(self, mock_glucose_record_class):
        """Test GET request with unauthorized access"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = 999  # Different from self.mock_user.id
        mock_glucose_record_class.query.get_or_404.return_value = mock_record
        
        response = self.client.get('/glucose/edit/1', follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You do not have permission to edit this record.', response.data)

    @patch('app.GlucoseRecord')
    def test_edit_glucose_record_post_non_integer(self, mock_glucose_record_class):
        """Test POST request with non-integer glucose level"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_glucose_record_class.query.get_or_404.return_value = mock_record
        
        response = self.client.post('/glucose/edit/1', data={
            'glucose_level': 'abc',
            'date': '2024-01-01',
            'time': '10:00'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Glucose level must be an integer.', response.data)

    @patch('app.GlucoseRecord')
    def test_edit_glucose_record_post_invalid_range(self, mock_glucose_record_class):
        """Test POST request with glucose level outside valid range"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_glucose_record_class.query.get_or_404.return_value = mock_record
        
        response = self.client.post('/glucose/edit/1', data={
            'glucose_level': '200',  # Above MAX_GLUCOSE
            'date': '2024-01-01',
            'time': '10:00'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Glucose level must be between 70 and 180 mg/dL.', response.data)

    @patch('app.GlucoseRecord')
    def test_edit_glucose_record_post_duplicate_time(self, mock_glucose_record_class):
        """Test POST request with duplicate date/time"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_record.date = "2024-01-01"
        mock_record.time = "09:00"
        mock_glucose_record_class.query.get_or_404.return_value = mock_record
        
        with patch('app.is_duplicate_record', return_value=True):
            response = self.client.post('/glucose/edit/1', data={
                'glucose_level': '100',
                'date': '2024-01-01',
                'time': '10:00'  # Different time
            })
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'A glucose record for this date and time already exists.', response.data)

    @patch('app.GlucoseRecord')
    def test_edit_glucose_record_post_success(self, mock_glucose_record_class):
        """Test successful POST request"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_record.date = "2024-01-01"
        mock_record.time = "10:00"
        mock_glucose_record_class.query.get_or_404.return_value = mock_record
        
        with patch('app.is_duplicate_record', return_value=False):
            response = self.client.post('/glucose/edit/1', data={
                'glucose_level': '100',
                'date': '2024-01-01',
                'time': '10:00'
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Glucose record updated successfully!', response.data)
            self.mock_commit.assert_called_once()

    @patch('app.GlucoseRecord')
    def test_edit_glucose_record_post_generic_error(self, mock_glucose_record_class):
        """Test POST request with generic database error"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_glucose_record_class.query.get_or_404.return_value = mock_record
        
        with patch('app.is_duplicate_record', return_value=False):
            self.mock_commit.side_effect = Exception("Database error")
            
            response = self.client.post('/glucose/edit/1', data={
                'glucose_level': '100',
                'date': '2024-01-01',
                'time': '10:00'
            })
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Error updating glucose record: Database error', response.data)
            self.mock_rollback.assert_called_once()

    # Test cases for edit_blood_pressure_record
    @patch('app.BloodPressureRecord')
    def test_edit_blood_pressure_record_get_success(self, mock_bp_record_class):
        """Test successful GET request to edit blood pressure record"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_record.systolic = 120
        mock_record.diastolic = 80
        mock_record.date = "2024-01-01"
        mock_record.time = "10:00"
        
        mock_bp_record_class.query.get_or_404.return_value = mock_record
        
        response = self.client.get('/blood_pressure/edit/1')
        
        self.assertEqual(response.status_code, 200)
        mock_bp_record_class.query.get_or_404.assert_called_with(1)

    @patch('app.BloodPressureRecord')
    def test_edit_blood_pressure_record_post_non_integer(self, mock_bp_record_class):
        """Test POST request with non-integer blood pressure values"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_bp_record_class.query.get_or_404.return_value = mock_record
        
        response = self.client.post('/blood_pressure/edit/1', data={
            'systolic': 'abc',
            'diastolic': 'xyz',
            'date': '2024-01-01',
            'time': '10:00'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Systolic and Diastolic values must be integers.', response.data)

    @patch('app.BloodPressureRecord')
    def test_edit_blood_pressure_record_post_invalid_systolic(self, mock_bp_record_class):
        """Test POST request with invalid systolic value"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_bp_record_class.query.get_or_404.return_value = mock_record
        
        response = self.client.post('/blood_pressure/edit/1', data={
            'systolic': '200',  # Above MAX_SYSTOLIC
            'diastolic': '80',
            'date': '2024-01-01',
            'time': '10:00'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Systolic value must be between 90 and 180 mm Hg.', response.data)

    @patch('app.BloodPressureRecord')
    def test_edit_blood_pressure_record_post_invalid_diastolic(self, mock_bp_record_class):
        """Test POST request with invalid diastolic value"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_bp_record_class.query.get_or_404.return_value = mock_record
        
        response = self.client.post('/blood_pressure/edit/1', data={
            'systolic': '120',
            'diastolic': '130',  # Above MAX_DIASTOLIC
            'date': '2024-01-01',
            'time': '10:00'
        })
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Diastolic value must be between 60 and 120 mm Hg.', response.data)

    @patch('app.BloodPressureRecord')
    def test_edit_blood_pressure_record_post_duplicate_time(self, mock_bp_record_class):
        """Test POST request with duplicate date/time"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_record.date = "2024-01-01"
        mock_record.time = "09:00"
        mock_bp_record_class.query.get_or_404.return_value = mock_record
        
        with patch('app.is_duplicate_record', return_value=True):
            response = self.client.post('/blood_pressure/edit/1', data={
                'systolic': '120',
                'diastolic': '80',
                'date': '2024-01-01',
                'time': '10:00'  # Different time
            })
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'A blood pressure record for this date and time already exists.', response.data)

    @patch('app.BloodPressureRecord')
    def test_edit_blood_pressure_record_post_success(self, mock_bp_record_class):
        """Test successful POST request"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_record.date = "2024-01-01"
        mock_record.time = "10:00"
        mock_bp_record_class.query.get_or_404.return_value = mock_record
        
        with patch('app.is_duplicate_record', return_value=False):
            response = self.client.post('/blood_pressure/edit/1', data={
                'systolic': '120',
                'diastolic': '80',
                'date': '2024-01-01',
                'time': '10:00'
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Blood pressure record updated successfully!', response.data)
            self.mock_commit.assert_called_once()

    @patch('app.BloodPressureRecord')
    def test_edit_blood_pressure_record_post_generic_error(self, mock_bp_record_class):
        """Test POST request with generic database error"""
        self.login()
        
        mock_record = MagicMock()
        mock_record.user_id = self.mock_user.id
        mock_bp_record_class.query.get_or_404.return_value = mock_record
        
        with patch('app.is_duplicate_record', return_value=False):
            self.mock_commit.side_effect = Exception("Database error")
            
            response = self.client.post('/blood_pressure/edit/1', data={
                'systolic': '120',
                'diastolic': '80',
                'date': '2024-01-01',
                'time': '10:00'
            })
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'Error updating blood pressure record: Database error', response.data)
            self.mock_rollback.assert_called_once()

#----------------------------------------------------------------------------#
# Health Reporter Tests
#----------------------------------------------------------------------------#
    def test_health_reports_get(self):
        """Test GET request to health reports page"""
        response = self.client.get('/health-reports')
        self.assertEqual(response.status_code, 200)

    def test_export_csv_success(self):
        """Test successful CSV export with mock data"""
        # Mock glucose records
        mock_glucose = MagicMock()
        mock_glucose.date = '2024-01-01'
        mock_glucose.time = '10:00'
        mock_glucose.glucose_level = 120

        # Mock blood pressure records
        mock_bp = MagicMock()
        mock_bp.date = '2024-01-01'
        mock_bp.time = '10:30'
        mock_bp.systolic = 120
        mock_bp.diastolic = 80

        # Patch the database queries
        with patch('models.GlucoseRecord.query') as mock_glucose_query, \
            patch('models.BloodPressureRecord.query') as mock_bp_query:
            
            # Configure mock queries
            mock_glucose_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_glucose]
            mock_bp_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_bp]

            # Make request to export CSV
            response = self.client.post('/export/csv')

            # Assert response
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'text/csv')
            self.assertIn('health_report_', response.headers['Content-Disposition'])
            
            # Verify CSV content
            csv_data = response.data.decode('utf-8')
            self.assertIn('Glucose Levels', csv_data)
            self.assertIn('Blood Pressure Levels', csv_data)
            self.assertIn('120', csv_data)  # glucose level
            self.assertIn('80', csv_data)   # diastolic

    def test_export_csv_no_records(self):
        """Test CSV export when no health records exist"""
        # Patch the database queries to return empty lists
        with patch('models.GlucoseRecord.query') as mock_glucose_query, \
            patch('models.BloodPressureRecord.query') as mock_bp_query:
            
            mock_glucose_query.filter_by.return_value.order_by.return_value.all.return_value = []
            mock_bp_query.filter_by.return_value.order_by.return_value.all.return_value = []

            response = self.client.post('/export/csv')

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'text/csv')
            
            csv_data = response.data.decode('utf-8')
            self.assertIn('No glucose records found.', csv_data)
            self.assertIn('No blood pressure records found.', csv_data)

    def test_export_csv_error(self):
        """Test CSV export when an error occurs"""
        # Patch the database query to raise an exception
        with patch('models.GlucoseRecord.query') as mock_query:
            mock_query.filter_by.side_effect = Exception('Database error')

            response = self.client.post('/export/csv')

            self.assertEqual(response.status_code, 302)  # Redirect on error
            self.assertIn('/health-reports', response.location)

    def test_export_pdf_success(self):
        """Test successful PDF export with mock data"""
        # Mock glucose records
        mock_glucose = MagicMock()
        mock_glucose.date = '2024-01-01'
        mock_glucose.time = '10:00'
        mock_glucose.glucose_level = 120

        # Mock blood pressure records
        mock_bp = MagicMock()
        mock_bp.date = '2024-01-01'
        mock_bp.time = '10:30'
        mock_bp.systolic = 120
        mock_bp.diastolic = 80

        # Patch the database queries
        with patch('models.GlucoseRecord.query') as mock_glucose_query, \
            patch('models.BloodPressureRecord.query') as mock_bp_query:
            
            mock_glucose_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_glucose]
            mock_bp_query.filter_by.return_value.order_by.return_value.all.return_value = [mock_bp]

            response = self.client.post('/export/pdf')

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'application/pdf')
            self.assertIn('health_report.pdf', response.headers['Content-Disposition'])

    def test_export_pdf_no_records(self):
        """Test PDF export when no health records exist"""
        # Patch the database queries to return empty lists
        with patch('models.GlucoseRecord.query') as mock_glucose_query, \
            patch('models.BloodPressureRecord.query') as mock_bp_query:
            
            mock_glucose_query.filter_by.return_value.order_by.return_value.all.return_value = []
            mock_bp_query.filter_by.return_value.order_by.return_value.all.return_value = []

            response = self.client.post('/export/pdf')

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.mimetype, 'application/pdf')

    def test_export_pdf_error(self):
        """Test PDF export when an error occurs"""
        # Patch the database query to raise an exception
        with patch('models.GlucoseRecord.query') as mock_query:
            mock_query.filter_by.side_effect = Exception('Database error')

            response = self.client.post('/export/pdf')

            self.assertEqual(response.status_code, 302)  # Redirect on error
            self.assertIn('/health-reports', response.location)

    def test_health_reports_get(self):
        """Test GET request to health reports page"""
        response = self.client.get('/health-reports')
        self.assertEqual(response.status_code, 200)

    def test_health_reports_pdf_form_submission(self):
        """Test PDF form submission on the health reports page"""
        with patch('app.ExportPDFForm') as MockPDFForm:
            # Configure the mock form
            mock_form = MockPDFForm.return_value
            mock_form.validate_on_submit.return_value = True
            mock_form.submit.data = True
            
            with self.client as client:
                response = client.post('/health-reports', data={
                    'submit': True
                })
                
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.location.endswith('/export/pdf'))

    def test_health_reports_invalid_form_submission(self):
        """Test invalid form submission on the health reports page"""
        with patch('app.ExportPDFForm') as MockPDFForm, \
            patch('app.ExportCSVForm') as MockCSVForm:
            # Configure the mock forms to fail validation
            MockPDFForm.return_value.validate_on_submit.return_value = False
            MockCSVForm.return_value.validate_on_submit.return_value = False
            
            with self.client as client:
                response = client.post('/health-reports', data={})
                self.assertEqual(response.status_code, 200)

#----------------------------------------------------------------------------#
# Companion Management Tests
#----------------------------------------------------------------------------#
    def test_companion_setup_get(self):
        """Test GET request to companion setup page"""
        self.mock_user.user_type = 'COMPANION'
        
        with patch('app.render_template') as mock_render:
            mock_render.return_value = 'companion setup page'
            response = self.client.get('/companion/setup')
            
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_with('pages/companion_setup.html', form=ANY)

    def test_companion_setup_non_companion_redirect(self):
        """Test companion setup access by non-companion user"""
        self.mock_user.user_type = 'PATIENT'
        
        response = self.client.get('/companion/setup')
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.location, '/')

    def test_companion_setup_post_success(self):
        """Test successful companion-patient linking"""
        self.mock_user.user_type = 'COMPANION'
        
        mock_patient = MagicMock(spec=User)
        mock_patient.id = 2
        mock_patient.email = 'patient@test.com'
        mock_patient.user_type = 'PATIENT'
        
        with patch('app.User.query') as mock_user_query, \
            patch('app.CompanionAccess.query') as mock_access_query:
            # Setup mock queries
            mock_user_query.filter_by.return_value.first.return_value = mock_patient
            mock_access_query.filter_by.return_value.first.return_value = None
            
            response = self.client.post('/companion/setup', data={
                'patient_email': 'patient@test.com'
            })
            
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')
            self.mock_add.assert_called_once()
            self.mock_commit.assert_called_once()

    def test_companion_patients_list(self):
        """Test companion's patient list view"""
        self.mock_user.user_type = 'COMPANION'
        
        mock_approved = MagicMock()
        mock_approved.patient = MagicMock(username='Test Patient', email='patient@test.com')
        mock_approved.medication_access = 'VIEW'
        mock_approved.glucose_access = 'EDIT'
        mock_approved.blood_pressure_access = 'VIEW'
        
        with patch('app.CompanionAccess.query') as mock_query, \
            patch('app.render_template') as mock_render, \
            patch('app.CompanionLinkForm') as MockForm:
            # Setup form mock
            mock_form = MagicMock()
            MockForm.return_value = mock_form
            
            # Setup query mocks
            mock_query.filter.return_value.all.return_value = [mock_approved]
            mock_query.filter_by.return_value.all.return_value = []
            mock_render.return_value = 'patients list page'
            
            response = self.client.get('/companion/patients')
            
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_with('pages/companion_patients.html', 
                                        form=mock_form,
                                        connections=[mock_approved],
                                        pending_connections=[])

    def test_view_patient_data_success(self):
        """Test viewing patient data by authorized companion"""
        self.mock_user.user_type = 'COMPANION'
        
        mock_access = MagicMock()
        mock_access.glucose_access = 'VIEW'
        mock_access.blood_pressure_access = 'VIEW'
        mock_access.medication_access = 'VIEW'
        mock_patient = MagicMock(spec=User)
        
        with patch('app.CompanionAccess.query') as mock_access_query, \
            patch('app.User.query') as mock_user_query, \
            patch('app.render_template') as mock_render:
            mock_access_query.filter_by.return_value.first_or_404.return_value = mock_access
            mock_user_query.get_or_404.return_value = mock_patient
            mock_render.return_value = 'patient data page'
            
            response = self.client.get('/companion/patient/2')
            
            self.assertEqual(response.status_code, 200)
            mock_render.assert_called_with('pages/patient_data.html',
                                        patient=mock_patient,
                                        access=mock_access,
                                        glucose_data=ANY,
                                        blood_pressure_data=ANY,
                                        medication_data=ANY)

    def test_manage_connections_patient_only(self):
        """Test that only patients can access connection management"""
        self.mock_user.user_type = 'COMPANION'
        
        with patch('app.flash') as mock_flash:
            response = self.client.get('/connections')
            
            self.assertEqual(response.status_code, 302)
            mock_flash.assert_called_with('Only patients can manage connections.', 'danger')
            self.assertEqual(response.location, '/')

    def test_approve_connection_success(self):
        """Test successful connection approval by patient"""
        self.mock_user.user_type = 'PATIENT'
        
        mock_connection = MagicMock()
        mock_connection.patient_id = self.mock_user.id
        mock_connection.companion = MagicMock(username='test_companion')
        
        with patch('app.CompanionAccess.query') as mock_query, \
            patch('app.flash') as mock_flash:
            mock_query.get_or_404.return_value = mock_connection
            
            response = self.client.post('/connections/1/approve')
            
            self.assertEqual(response.status_code, 302)
            mock_flash.assert_called_with(
                f'Connection approved. Please set access levels for {mock_connection.companion.username}.', 
                'success'
            )
            self.mock_commit.assert_called_once()

    def test_reject_connection_success(self):
        """Test successful connection rejection by patient"""
        self.mock_user.user_type = 'PATIENT'
        
        mock_connection = MagicMock()
        mock_connection.patient_id = self.mock_user.id
        
        with patch('app.CompanionAccess.query') as mock_query, \
            patch('app.flash') as mock_flash:
            mock_query.get_or_404.return_value = mock_connection
            
            response = self.client.post('/connections/1/reject')
            
            self.assertEqual(response.status_code, 302)
            mock_flash.assert_called_with('Connection rejected.', 'success')
            self.mock_delete.assert_called_once_with(mock_connection)
            self.mock_commit.assert_called_once()

    def test_update_access_levels_success(self):
        """Test successful update of companion access levels"""
        self.mock_user.user_type = 'PATIENT'
        
        mock_connection = MagicMock()
        mock_connection.patient_id = self.mock_user.id
        
        with patch('app.CompanionAccess.query') as mock_query, \
            patch('app.flash') as mock_flash:
            mock_query.get_or_404.return_value = mock_connection
            
            response = self.client.post('/connections/1/access', data={
                'medication_access': 'VIEW',
                'glucose_access': 'EDIT',
                'blood_pressure_access': 'VIEW',
                'export_access': 'true'
            })
            
            self.assertEqual(response.status_code, 302)
            mock_flash.assert_called_with('Access levels updated successfully!', 'success')
            self.assertEqual(mock_connection.medication_access, 'VIEW')
            self.assertEqual(mock_connection.glucose_access, 'EDIT')
            self.assertEqual(mock_connection.blood_pressure_access, 'VIEW')
            self.mock_commit.assert_called_once()


    def test_companion_setup_post_duplicate_link(self):
        """Test attempting to create duplicate companion-patient link"""
        self.mock_user.user_type = 'COMPANION'
        
        with patch('app.User.query') as mock_user_query, \
            patch('app.CompanionAccess.query') as mock_access_query, \
            patch('app.CompanionLinkForm') as MockForm:
            # Setup mock form
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.patient_email.data = 'patient@test.com'
            MockForm.return_value = mock_form
            
            # Mock existing link
            mock_access_query.filter_by.return_value.first.return_value = MagicMock()
            
            response = self.client.post('/companion/setup', data={
                'patient_email': 'patient@test.com'
            }, follow_redirects=True)
            
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'You are already linked with this patient', response.data)
            self.mock_add.assert_not_called()
            self.mock_commit.assert_not_called()

    def test_view_patient_data_unauthorized(self):
        """Test viewing patient data without proper access"""
        self.mock_user.user_type = 'COMPANION'
        
        with patch('app.CompanionAccess.query') as mock_query:
            mock_query.filter_by.return_value.first_or_404.side_effect = NotFound()
            
            response = self.client.get('/companion/patient/2')
            
            self.assertEqual(response.status_code, 404)

    def test_remove_connection_success(self):
        """Test successful connection removal by patient"""
        self.mock_user.user_type = 'PATIENT'
        
        # Create mock connection
        mock_connection = MagicMock()
        mock_connection.patient_id = self.mock_user.id
        
        with patch('app.CompanionAccess.query') as mock_query, \
            patch('app.flash') as mock_flash, \
            patch('app.session', dict()) as mock_session, \
            patch('app.utility_processor', return_value={'pending_connections_count': 0}):
            # Setup mock query to return our mock connection
            mock_query.get_or_404.return_value = mock_connection
            
            response = self.client.post('/connections/1/remove')
            
            # Verify response
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/connections')
            
            # Verify database operations
            self.mock_delete.assert_called_once_with(mock_connection)
            self.mock_commit.assert_called_once()
            
            # Verify flash message
            mock_flash.assert_called_with('Connection removed successfully.', 'success')

    def test_remove_connection_unauthorized_user_type(self):
        """Test connection removal attempt by non-patient user"""
        self.mock_user.user_type = 'COMPANION'
        
        with patch('app.flash') as mock_flash, \
            patch('app.utility_processor', return_value={'pending_connections_count': 0}):
            response = self.client.post('/connections/1/remove')
            
            # Verify response
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')
            
            # Verify error message
            mock_flash.assert_called_with('Unauthorized access.', 'danger')
            
            # Verify no database operations occurred
            self.mock_delete.assert_not_called()
            self.mock_commit.assert_not_called()

    def test_remove_connection_unauthorized_patient(self):
        """Test connection removal attempt by wrong patient"""
        self.mock_user.user_type = 'PATIENT'
        
        # Create mock connection with different patient_id
        mock_connection = MagicMock()
        mock_connection.patient_id = self.mock_user.id + 1
        
        with patch('app.CompanionAccess.query') as mock_query, \
            patch('app.flash') as mock_flash, \
            patch('app.utility_processor', return_value={'pending_connections_count': 0}):
            mock_query.get_or_404.return_value = mock_connection
            
            response = self.client.post('/connections/1/remove')
            
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/connections')
            
            mock_flash.assert_called_with('Unauthorized access.', 'danger')
            self.mock_delete.assert_not_called()
            self.mock_commit.assert_not_called()

    def test_remove_connection_not_found(self):
        """Test removal of non-existent connection"""
        self.mock_user.user_type = 'PATIENT'
        
        with patch('app.CompanionAccess.query') as mock_query, \
            patch('app.render_template', return_value='') as mock_render, \
            patch('app.utility_processor', return_value={'pending_connections_count': 0}):
            # Setup mock query to raise 404
            mock_query.get_or_404.side_effect = NotFound()
            
            # Mock the template rendering for 404
            mock_render.return_value = ''
            
            response = self.client.post('/connections/1/remove')
            
            self.assertEqual(response.status_code, 404)
            self.mock_delete.assert_not_called()
            self.mock_commit.assert_not_called()

    def test_remove_connection_database_error(self):
        """Test connection removal with database error"""
        self.mock_user.user_type = 'PATIENT'
        
        mock_connection = MagicMock()
        mock_connection.patient_id = self.mock_user.id
        
        with patch('app.CompanionAccess.query') as mock_query, \
            patch('app.flash') as mock_flash, \
            patch('app.session', dict()) as mock_session, \
            patch('app.utility_processor', return_value={'pending_connections_count': 0}):
            mock_query.get_or_404.return_value = mock_connection
            
            # Force database error
            self.mock_commit.side_effect = Exception("Database error")
            
            response = self.client.post('/connections/1/remove')
            
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/connections')
            
            self.mock_rollback.assert_called_once()
            mock_flash.assert_called_with('Error removing connection.', 'danger')
            
            # Reset the side effect
            self.mock_commit.side_effect = None

    def test_companion_patients_unauthorized_user(self):
        """Test accessing companion patients page as non-companion user"""
        self.mock_user.user_type = 'PATIENT'
        
        with patch('app.flash') as mock_flash:
            response = self.client.get('/companion/patients')
            
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/')
            mock_flash.assert_called_once_with('Access denied.', 'danger')

    def test_companion_patients_get_success(self):
        """Test successful GET request to companion patients page"""
        self.mock_user.user_type = 'COMPANION'
        self.mock_user.id = 1
        
        # Create mock approved and pending connections
        mock_approved = [MagicMock(spec=CompanionAccess)]
        mock_approved[0].medication_access = 'VIEW'
        mock_approved[0].glucose_access = 'VIEW'
        mock_approved[0].blood_pressure_access = 'NONE'
        
        mock_pending = MagicMock(spec=CompanionAccess)
        mock_pending.medication_access = 'NONE'
        mock_pending.glucose_access = 'NONE'
        mock_pending.blood_pressure_access = 'NONE'
        
        with patch('app.CompanionAccess.query') as mock_query, \
            patch('app.render_template') as mock_render, \
            patch('app.CompanionLinkForm') as MockForm:
            # Setup form mock
            mock_form = MagicMock()
            MockForm.return_value = mock_form
            
            # Setup query chains for approved connections
            filter_chain = MagicMock()
            filter_chain.all.return_value = mock_approved
            mock_query.filter.return_value = filter_chain
            
            # Setup pending connections query
            mock_query.filter_by.return_value.all.return_value = [mock_pending]
            
            # Mock render_template
            mock_render.return_value = ''
            
            response = self.client.get('/companion/patients')
            
            # Verify response
            self.assertEqual(response.status_code, 200)
            
            # Get the actual call args
            call_args = mock_render.call_args
            args, kwargs = call_args
            
            # Verify template name
            self.assertEqual(args[0], 'pages/companion_patients.html')
            
            # Verify kwargs exist
            self.assertIn('form', kwargs)
            self.assertIn('connections', kwargs)
            self.assertIn('pending_connections', kwargs)
            
            # Verify kwargs types
            self.assertIsInstance(kwargs['pending_connections'], list)
            self.assertEqual(len(kwargs['pending_connections']), 1)

    def test_companion_patients_link_new_patient_success(self):
        """Test successful patient linking"""
        self.mock_user.user_type = 'COMPANION'
        self.mock_user.id = 1
        
        # Create mock patient
        mock_patient = MagicMock(spec=User)
        mock_patient.id = 2
        mock_patient.email = 'patient@test.com'
        mock_patient.user_type = 'PATIENT'
        
        with patch('app.CompanionLinkForm') as MockForm, \
            patch('app.User.query') as mock_user_query, \
            patch('app.CompanionAccess.query') as mock_access_query, \
            patch('app.flash') as mock_flash:
            # Setup form mock with validation
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.patient_email.data = 'patient@test.com'
            MockForm.return_value = mock_form
            
            # Setup query mocks
            mock_user_query.filter_by.return_value.first.return_value = mock_patient
            mock_access_query.filter_by.return_value.first.return_value = None
            
            response = self.client.post('/companion/patients', data={
                'patient_email': 'patient@test.com'
            })
            
            # Verify the CompanionAccess object creation
            expected_link = CompanionAccess(
                patient_id=mock_patient.id,
                companion_id=self.mock_user.id,
                medication_access='NONE',
                glucose_access='NONE',
                blood_pressure_access='NONE',
                export_access=False
            )
            
            args, _ = self.mock_add.call_args
            actual_link = args[0]
            
            self.assertEqual(actual_link.patient_id, expected_link.patient_id)
            self.assertEqual(actual_link.companion_id, expected_link.companion_id)
            self.assertEqual(actual_link.medication_access, expected_link.medication_access)
            self.assertEqual(actual_link.glucose_access, expected_link.glucose_access)
            self.assertEqual(actual_link.blood_pressure_access, expected_link.blood_pressure_access)
            self.assertEqual(actual_link.export_access, expected_link.export_access)
            
            self.mock_commit.assert_called_once()
            mock_flash.assert_called_with('Successfully linked with patient. Waiting for access approval.', 'success')
            self.assertEqual(response.status_code, 200)

    def test_companion_patients_link_nonexistent_patient(self):
        """Test linking with non-existent patient"""
        self.mock_user.user_type = 'COMPANION'
        
        with patch('app.CompanionLinkForm') as MockForm, \
            patch('app.User.query') as mock_query, \
            patch('app.flash') as mock_flash:
            # Setup form mock
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.patient_email.data = 'nonexistent@test.com'
            MockForm.return_value = mock_form
            
            # Patient not found
            mock_query.filter_by.return_value.first.return_value = None
            
            response = self.client.post('/companion/patients', data={
                'patient_email': 'nonexistent@test.com'
            })
            
            self.assertEqual(response.status_code, 200)
            mock_flash.assert_called_with('No patient account found with that email.', 'danger')
            self.mock_add.assert_not_called()
            self.mock_commit.assert_not_called()

    def test_companion_patients_link_existing_connection(self):
        """Test linking with already connected patient"""
        self.mock_user.user_type = 'COMPANION'
        self.mock_user.id = 1
        
        mock_patient = MagicMock(spec=User)
        mock_patient.id = 2
        mock_patient.email = 'patient@test.com'
        mock_patient.user_type = 'PATIENT'
        
        with patch('app.CompanionLinkForm') as MockForm, \
            patch('app.User.query') as mock_user_query, \
            patch('app.CompanionAccess.query') as mock_access_query, \
            patch('app.flash') as mock_flash:
            # Setup form mock
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.patient_email.data = 'patient@test.com'
            MockForm.return_value = mock_form
            
            # Setup query mocks
            mock_user_query.filter_by.return_value.first.return_value = mock_patient
            mock_access_query.filter_by.return_value.first.return_value = MagicMock()  # Existing link
            
            response = self.client.post('/companion/patients', data={
                'patient_email': 'patient@test.com'
            })
            
            self.assertEqual(response.status_code, 200)
            mock_flash.assert_called_with('You are already linked with this patient.', 'warning')
            self.mock_add.assert_not_called()
            self.mock_commit.assert_not_called()

    def test_companion_patients_link_database_error(self):
        """Test database error during patient linking"""
        self.mock_user.user_type = 'COMPANION'
        self.mock_user.id = 1
        
        mock_patient = MagicMock(spec=User)
        mock_patient.id = 2
        mock_patient.email = 'patient@test.com'
        mock_patient.user_type = 'PATIENT'
        
        with patch('app.CompanionLinkForm') as MockForm, \
            patch('app.User.query') as mock_user_query, \
            patch('app.CompanionAccess.query') as mock_access_query, \
            patch('app.flash') as mock_flash:
            # Setup form mock
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.patient_email.data = 'patient@test.com'
            MockForm.return_value = mock_form
            
            # Setup query mocks
            mock_user_query.filter_by.return_value.first.return_value = mock_patient
            mock_access_query.filter_by.return_value.first.return_value = None
            
            # Force database error
            self.mock_commit.side_effect = Exception("Database error")
            
            response = self.client.post('/companion/patients', data={
                'patient_email': 'patient@test.com'
            })
            
            self.assertEqual(response.status_code, 200)
            self.mock_rollback.assert_called_once()
            mock_flash.assert_called_with('An error occurred while linking with patient.', 'danger')
            
            # Reset the side effect
            self.mock_commit.side_effect = None

    def test_companion_patients_link_form_validation_error(self):
        """Test form validation error during patient linking"""
        self.mock_user.user_type = 'COMPANION'
        
        with patch('app.CompanionLinkForm') as MockForm:
            # Setup form mock with validation error
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = False
            MockForm.return_value = mock_form
            
            response = self.client.post('/companion/patients', data={})
            
            self.assertEqual(response.status_code, 200)
            self.mock_add.assert_not_called()
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