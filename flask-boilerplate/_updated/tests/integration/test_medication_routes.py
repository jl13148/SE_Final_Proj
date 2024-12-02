from unittest.mock import patch, MagicMock, ANY
from datetime import datetime, time, timedelta
from tests.base import BaseTestCase

class TestMedicationRoutes(BaseTestCase):
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
            mock_query.filter_by.assert_called_with(user_id=self.test_user.id)

    def test_add_medication_get(self):
        """Test GET request to add medication page"""
        response = self.client.get('/medications/add')
        self.assertEqual(response.status_code, 200)

    def test_add_medication_success(self):
        """Test successful medication addition"""
        with patch('app.MedicationForm') as MockForm:
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.name.data = "TestMed"
            mock_form.dosage.data = "10mg"
            mock_form.frequency.data = "daily"
            mock_form.time.data = time(8, 0)
            MockForm.return_value = mock_form

            with patch('app.flash') as mock_flash:
                response = self.client.post('/medications/add')
                
                self.assertEqual(response.status_code, 302)
                mock_flash.assert_called_with(
                    'Medication added successfully!', 
                    'success'
                )

    def test_add_medication_database_error(self):
        """Test database error handling in medication addition"""
        with patch('app.MedicationForm') as MockForm, \
             patch('app.db.session.rollback') as mock_rollback, \
             patch('app.flash') as mock_flash:
            
            mock_form = MagicMock()
            mock_form.validate_on_submit.return_value = True
            mock_form.name.data = "Test Medicine"
            mock_form.dosage.data = "100mg"
            mock_form.frequency.data = "Daily"
            mock_form.time.data = time(9, 0)
            MockForm.return_value = mock_form

            with patch('app.db.session.commit') as mock_commit:
                mock_commit.side_effect = Exception("Database error")
                
                response = self.client.post('/medications/add')
                
                self.assertEqual(response.status_code, 302)
                mock_rollback.assert_called_once()
                mock_flash.assert_called_with(
                    'Error adding medication: Database error', 
                    'danger'
                )

    def test_delete_medication_success(self):
        """Test successful medication deletion"""
        with patch('app.Medication.query') as mock_query, \
             patch('app.MedicationLog.query') as mock_log_query, \
             patch('app.flash') as mock_flash:
            
            mock_med = MagicMock()
            mock_med.user_id = self.test_user.id
            mock_query.get_or_404.return_value = mock_med
            
            mock_log_query.filter_by.return_value.delete.return_value = None
            
            response = self.client.post('/medications/1/delete')
            
            self.assertEqual(response.status_code, 302)
            mock_flash.assert_called_with('Medication deleted successfully.', 'success')

    def test_delete_medication_unauthorized(self):
        """Test unauthorized medication deletion"""
        with patch('app.Medication.query') as mock_query, \
             patch('app.flash') as mock_flash:
            
            mock_med = MagicMock()
            mock_med.user_id = 999  # Different user
            mock_query.get_or_404.return_value = mock_med
            
            response = self.client.post('/medications/1/delete')
            
            self.assertEqual(response.status_code, 302)
            mock_flash.assert_called_with('Unauthorized action.', 'danger')

    def test_medication_schedule_success(self):
        """Test medication schedule page"""
        response = self.client.get('/medication-schedule')
        self.assertEqual(response.status_code, 200)

    def test_medication_schedule_exception(self):
        """Test medication schedule page with exception"""
        with patch('app.render_template') as mock_render, \
             patch('app.flash') as mock_flash:
            
            mock_render.side_effect = Exception("Template error")
            
            response = self.client.get('/medication-schedule')
            
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
            data = response.get_json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], "TestMed")

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
            data = response.get_json()
            self.assertEqual(len(data), 1)
            self.assertEqual(data[0]['name'], 'TestMed')

    def test_log_medication_success(self):
        """Test successful medication logging"""
        with patch('app.Medication.query') as mock_query:
            mock_med = MagicMock()
            mock_med.user_id = self.test_user.id
            mock_query.get_or_404.return_value = mock_med
            
            with patch('app.MedicationLog.query') as mock_log_query:
                mock_log_query.filter.return_value.first.return_value = None
                
                response = self.client.post('/medications/log/1')
                
                self.assertEqual(response.status_code, 200)
                data = response.get_json()
                self.assertEqual(data['message'], 'Medication logged successfully')
