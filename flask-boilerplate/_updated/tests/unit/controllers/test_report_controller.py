import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
from flask_login import LoginManager, UserMixin
from app.view.report import report
from app.services.report_service import ReportService
from io import BytesIO
import os

# Define a simple User model for testing purposes
class TestUser(UserMixin):
    def __init__(self, id, email, user_type):
        self.id = id
        self.email = email
        self.user_type = user_type
        # self.is_authenticated = True

class TestReportController(unittest.TestCase):

    def setUp(self):
        # Create a Flask app instance for testing
        project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))

        # Path to the templates directory
        templates_dir = os.path.join(project_dir, 'templates')

        # Create a Flask app instance for testing with the correct template folder
        self.app = Flask(__name__, template_folder=templates_dir)
        self.app.config['TESTING'] = True
        self.app.config['SECRET_KEY'] = 'testsecretkey'

        # Initialize Flask-Login
        self.login_manager = LoginManager()
        self.login_manager.init_app(self.app)

        @self.login_manager.user_loader
        def load_user(user_id):
            return self.test_user

        # Register the report blueprint
        self.app.register_blueprint(report)

        # Create a test client
        self.client = self.app.test_client()

        # Create a test user (default to PATIENT)
        self.test_user = TestUser(id=1, email='test@example.com', user_type='PATIENT')  # Change user_type as needed

        # Context for the app
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def login(self):
        with self.client.session_transaction() as sess:
            sess['_user_id'] = str(self.test_user.id)
            sess['_fresh'] = True

    def logout(self):
        with self.client.session_transaction() as sess:
            sess.pop('_user_id', None)
            sess.pop('_fresh', None)

    @patch('app.controllers.report.ReportService')
    def test_health_reports_page_authenticated_get(self, mock_report_service):
        """Test accessing the health reports page with GET as an authenticated user"""
        self.login()
        response = self.client.get('/health-reports')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Health Reports', response.data)  # Adjust based on the actual template content

    @patch('app.controllers.report.ReportService')
    def test_health_reports_page_authenticated_post(self, mock_report_service):
        """Test accessing the health reports page with POST as an authenticated user"""
        self.login()
        response = self.client.post('/health-reports')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Health Reports', response.data)  # Adjust based on the actual template content

    def test_health_reports_page_unauthenticated_get(self):
        """Test accessing the health reports page with GET as an unauthenticated user"""
        response = self.client.get('/health-reports', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)  # Assuming the login page contains 'Login'

    def test_health_reports_page_unauthenticated_post(self):
        """Test accessing the health reports page with POST as an unauthenticated user"""
        response = self.client.post('/health-reports', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)  # Assuming the login page contains 'Login'

    @patch('app.controllers.report.send_file')
    @patch('app.controllers.report.ReportService')
    def test_export_csv_success_patient(self, mock_report_service_class, mock_send_file):
        """Test successful CSV export for PATIENT user"""
        self.login()

        # Mock ReportService instance and its generate_csv_report method
        mock_report_service = MagicMock()
        mock_report_service.generate_csv_report.return_value = BytesIO(b'id,name\n1,Test User')
        mock_report_service_class.return_value = mock_report_service

        # Mock send_file to return a response
        mock_send_file.return_value = ('CSV content', 200)

        # Perform POST request to export CSV
        response = self.client.post('/export/csv')

        # Assertions
        mock_report_service.generate_csv_report.assert_called_once_with()
        mock_send_file.assert_called_once_with(
            mock_report_service.generate_csv_report.return_value,
            as_attachment=True,
            download_name=unittest.mock.ANY,  # Filename includes current date; use ANY to ignore
            mimetype='text/csv'
        )
        self.assertEqual(response.status_code, 200)
        # Optionally, verify the response data if send_file is mocked to return specific content

    @patch('app.controllers.report.send_file')
    @patch('app.controllers.report.ReportService')
    def test_export_csv_success_companion(self, mock_report_service_class, mock_send_file):
        """Test successful CSV export for COMPANION user"""
        # Create a companion user
        self.test_user = TestUser(id=2, email='companion@example.com', user_type='COMPANION')
        self.login()

        # Mock ReportService instance and its generate_csv_report method
        mock_report_service = MagicMock()
        mock_report_service.generate_csv_report.return_value = BytesIO(b'id,name\n2,Companion User')
        mock_report_service_class.return_value = mock_report_service

        # Mock send_file to return a response
        mock_send_file.return_value = ('CSV content', 200)

        # Perform POST request to export CSV
        response = self.client.post('/export/csv')

        # Assertions
        mock_report_service.generate_csv_report.assert_called_once_with()
        mock_send_file.assert_called_once_with(
            mock_report_service.generate_csv_report.return_value,
            as_attachment=True,
            download_name=unittest.mock.ANY,  # Filename includes current date; use ANY to ignore
            mimetype='text/csv'
        )
        self.assertEqual(response.status_code, 200)

    @patch('app.controllers.report.send_file')
    @patch('app.controllers.report.ReportService')
    def test_export_csv_failure(self, mock_report_service_class, mock_send_file):
        """Test CSV export failure due to exception in ReportService"""
        self.login()

        # Configure ReportService to raise an exception
        mock_report_service = MagicMock()
        mock_report_service.generate_csv_report.side_effect = Exception('CSV Generation Error')
        mock_report_service_class.return_value = mock_report_service

        response = self.client.post('/export/csv', follow_redirects=True)

        # Assertions
        mock_report_service.generate_csv_report.assert_called_once_with()
        mock_send_file.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error exporting CSV: CSV Generation Error', response.data)

    @patch('app.controllers.report.send_file')
    @patch('app.controllers.report.ReportService')
    def test_export_pdf_success_patient(self, mock_report_service_class, mock_send_file):
        """Test successful PDF export for PATIENT user"""
        self.login()

        # Mock ReportService instance and its generate_pdf_report method
        mock_report_service = MagicMock()
        mock_report_service.generate_pdf_report.return_value = BytesIO(b'%PDF-1.4...')
        mock_report_service_class.return_value = mock_report_service

        # Mock send_file to return a response
        mock_send_file.return_value = ('PDF content', 200)

        # Perform POST request to export PDF
        response = self.client.post('/export/pdf')

        # Assertions
        mock_report_service.generate_pdf_report.assert_called_once_with()
        mock_send_file.assert_called_once_with(
            mock_report_service.generate_pdf_report.return_value,
            as_attachment=True,
            download_name=unittest.mock.ANY,  # Filename includes current date; use ANY to ignore
            mimetype='application/pdf'
        )
        self.assertEqual(response.status_code, 200)

    @patch('app.controllers.report.send_file')
    @patch('app.controllers.report.ReportService')
    def test_export_pdf_success_companion(self, mock_report_service_class, mock_send_file):
        """Test successful PDF export for COMPANION user"""
        # Create a companion user
        self.test_user = TestUser(id=2, email='companion@example.com', user_type='COMPANION')
        self.login()

        # Mock ReportService instance and its generate_pdf_report method
        mock_report_service = MagicMock()
        mock_report_service.generate_pdf_report.return_value = BytesIO(b'%PDF-1.4... Companion User Data')
        mock_report_service_class.return_value = mock_report_service

        # Mock send_file to return a response
        mock_send_file.return_value = ('PDF content', 200)

        # Perform POST request to export PDF
        response = self.client.post('/export/pdf')

        # Assertions
        mock_report_service.generate_pdf_report.assert_called_once_with()
        mock_send_file.assert_called_once_with(
            mock_report_service.generate_pdf_report.return_value,
            as_attachment=True,
            download_name=unittest.mock.ANY,  # Filename includes current date; use ANY to ignore
            mimetype='application/pdf'
        )
        self.assertEqual(response.status_code, 200)

    @patch('app.controllers.report.send_file')
    @patch('app.controllers.report.ReportService')
    def test_export_pdf_failure(self, mock_report_service_class, mock_send_file):
        """Test PDF export failure due to exception in ReportService"""
        self.login()

        # Configure ReportService to raise an exception
        mock_report_service = MagicMock()
        mock_report_service.generate_pdf_report.side_effect = Exception('PDF Generation Error')
        mock_report_service_class.return_value = mock_report_service

        response = self.client.post('/export/pdf', follow_redirects=True)

        # Assertions
        mock_report_service.generate_pdf_report.assert_called_once_with()
        mock_send_file.assert_not_called()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error generating PDF report: PDF Generation Error', response.data)

    @patch('app.controllers.report.ReportService')
    def test_export_csv_no_data(self, mock_report_service_class):
        """Test CSV export when there is no data to export"""
        self.login()

        # Mock ReportService to return empty BytesIO
        mock_report_service = MagicMock()
        mock_report_service.generate_csv_report.return_value = BytesIO(b'')
        mock_report_service_class.return_value = mock_report_service

        with patch('app.controllers.report.send_file') as mock_send_file:
            # Mock send_file to return a response
            mock_send_file.return_value = ('Empty CSV content', 200)

            # Perform POST request to export CSV
            response = self.client.post('/export/csv')

            # Assertions
            mock_report_service.generate_csv_report.assert_called_once_with()
            mock_send_file.assert_called_once_with(
                mock_report_service.generate_csv_report.return_value,
                as_attachment=True,
                download_name=unittest.mock.ANY,
                mimetype='text/csv'
            )
            self.assertEqual(response.status_code, 200)
            # Optionally, verify that the CSV is indeed empty or contains no records

    @patch('app.controllers.report.ReportService')
    def test_export_pdf_no_data(self, mock_report_service_class):
        """Test PDF export when there is no data to export"""
        self.login()

        # Mock ReportService to return empty BytesIO
        mock_report_service = MagicMock()
        mock_report_service.generate_pdf_report.return_value = BytesIO(b'')
        mock_report_service_class.return_value = mock_report_service

        with patch('app.controllers.report.send_file') as mock_send_file:
            # Mock send_file to return a response
            mock_send_file.return_value = ('Empty PDF content', 200)

            # Perform POST request to export PDF
            response = self.client.post('/export/pdf')

            # Assertions
            mock_report_service.generate_pdf_report.assert_called_once_with()
            mock_send_file.assert_called_once_with(
                mock_report_service.generate_pdf_report.return_value,
                as_attachment=True,
                download_name=unittest.mock.ANY,
                mimetype='application/pdf'
            )
            self.assertEqual(response.status_code, 200)
            # Optionally, verify that the PDF is indeed empty or contains no records

    @patch('app.controllers.report.ReportService')
    def test_health_reports_page_authenticated_post_with_data(self, mock_report_service):
        """Test POST request to /health-reports with data (if applicable)"""
        self.login()
        # Assuming that POST to /health-reports might handle form submissions
        response = self.client.post('/health-reports', data={'key': 'value'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Health Reports', response.data)  # Adjust based on the actual template content

    @patch('app.controllers.report.ReportService')
    def test_export_csv_send_file_args(self, mock_report_service_class):
        """Test that send_file is called with correct arguments for CSV export"""
        self.login()

        # Mock ReportService instance and its generate_csv_report method
        mock_report_service = MagicMock()
        mock_report_service.generate_csv_report.return_value = BytesIO(b'id,name\n1,Test User')
        mock_report_service_class.return_value = mock_report_service

        with patch('app.controllers.report.send_file') as mock_send_file:
            # Mock send_file to return a response
            mock_send_file.return_value = ('CSV content', 200)

            # Perform POST request to export CSV
            response = self.client.post('/export/csv')

            # Assertions
            mock_send_file.assert_called_once()
            args, kwargs = mock_send_file.call_args
            self.assertEqual(args[0], mock_report_service.generate_csv_report.return_value)
            self.assertTrue(kwargs['as_attachment'])
            self.assertTrue(kwargs['download_name'].startswith('health_report_') and kwargs['download_name'].endswith('.csv'))
            self.assertEqual(kwargs['mimetype'], 'text/csv')

    @patch('app.controllers.report.ReportService')
    def test_export_pdf_send_file_args(self, mock_report_service_class):
        """Test that send_file is called with correct arguments for PDF export"""
        self.login()

        # Mock ReportService instance and its generate_pdf_report method
        mock_report_service = MagicMock()
        mock_report_service.generate_pdf_report.return_value = BytesIO(b'%PDF-1.4...')
        mock_report_service_class.return_value = mock_report_service

        with patch('app.controllers.report.send_file') as mock_send_file:
            # Mock send_file to return a response
            mock_send_file.return_value = ('PDF content', 200)

            # Perform POST request to export PDF
            response = self.client.post('/export/pdf')

            # Assertions
            mock_send_file.assert_called_once()
            args, kwargs = mock_send_file.call_args
            self.assertEqual(args[0], mock_report_service.generate_pdf_report.return_value)
            self.assertTrue(kwargs['as_attachment'])
            self.assertTrue(kwargs['download_name'].startswith('health_report_') and kwargs['download_name'].endswith('.pdf'))
            self.assertEqual(kwargs['mimetype'], 'application/pdf')

    @patch('app.controllers.report.ReportService')
    def test_export_csv_redirect_on_failure(self, mock_report_service_class):
        """Test that export_csv redirects to health_reports on failure"""
        self.login()

        # Configure ReportService to raise an exception
        mock_report_service = MagicMock()
        mock_report_service.generate_csv_report.side_effect = Exception('CSV Generation Failure')
        mock_report_service_class.return_value = mock_report_service

        response = self.client.post('/export/csv', follow_redirects=True)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error exporting CSV: CSV Generation Failure', response.data)
        # Ensure redirection to '/health-reports'
        self.assertIn(b'Health Reports', response.data)

    @patch('app.controllers.report.ReportService')
    def test_export_pdf_redirect_on_failure(self, mock_report_service_class):
        """Test that export_pdf redirects to health_reports on failure"""
        self.login()

        # Configure ReportService to raise an exception
        mock_report_service = MagicMock()
        mock_report_service.generate_pdf_report.side_effect = Exception('PDF Generation Failure')
        mock_report_service_class.return_value = mock_report_service

        response = self.client.post('/export/pdf', follow_redirects=True)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Error generating PDF report: PDF Generation Failure', response.data)
        # Ensure redirection to '/health-reports'
        self.assertIn(b'Health Reports', response.data)

    @patch('app.controllers.report.ReportService')
    def test_export_csv_invalid_user(self, mock_report_service_class):
        """Test CSV export with invalid user (e.g., user without access)"""
        # Create a user with no access or invalid user_type
        self.test_user = TestUser(id=3, email='invalid@example.com', user_type='INVALID')
        self.login()

        # Mock ReportService instance and its generate_csv_report method
        mock_report_service = MagicMock()
        mock_report_service.generate_csv_report.return_value = BytesIO(b'id,name\n3,Invalid User')
        mock_report_service_class.return_value = mock_report_service

        with patch('app.controllers.report.send_file') as mock_send_file:
            # Mock send_file to return a response
            mock_send_file.return_value = ('CSV content', 200)

            # Perform POST request to export CSV
            response = self.client.post('/export/csv')

            # Assertions
            mock_report_service.generate_csv_report.assert_called_once_with()
            mock_send_file.assert_called_once_with(
                mock_report_service.generate_csv_report.return_value,
                as_attachment=True,
                download_name=unittest.mock.ANY,
                mimetype='text/csv'
            )
            self.assertEqual(response.status_code, 200)

    @patch('app.controllers.report.ReportService')
    def test_export_pdf_invalid_user(self, mock_report_service_class):
        """Test PDF export with invalid user (e.g., user without access)"""
        # Create a user with no access or invalid user_type
        self.test_user = TestUser(id=4, email='invalidpdf@example.com', user_type='INVALID')
        self.login()

        # Mock ReportService instance and its generate_pdf_report method
        mock_report_service = MagicMock()
        mock_report_service.generate_pdf_report.return_value = BytesIO(b'')

        mock_report_service_class.return_value = mock_report_service

        with patch('app.controllers.report.send_file') as mock_send_file:
            # Mock send_file to return a response
            mock_send_file.return_value = ('PDF content', 200)

            # Perform POST request to export PDF
            response = self.client.post('/export/pdf')

            # Assertions
            mock_report_service.generate_pdf_report.assert_called_once_with()
            mock_send_file.assert_called_once_with(
                mock_report_service.generate_pdf_report.return_value,
                as_attachment=True,
                download_name=unittest.mock.ANY,
                mimetype='application/pdf'
            )
            self.assertEqual(response.status_code, 200)