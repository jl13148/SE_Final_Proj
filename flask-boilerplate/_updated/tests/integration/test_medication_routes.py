from tests.base import BaseTestCase
from app.models import Medication, MedicationLog
from datetime import time

class TestMedicationRoutes(BaseTestCase):
    def test_medications_redirect(self):
        """Test /medications redirects to manage medications"""
        self.login()
        response = self.client.get('/medications')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/medications/manage', response.location)

    def test_manage_medications_requires_login(self):
        """Test medication management requires login"""
        response = self.client.get('/medications/manage')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_manage_medications_logged_in(self):
        """Test viewing medications while logged in"""
        self.login()
        response = self.client.get('/medications/manage')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Med', response.data)
        self.assertIn(b'100mg', response.data)

    def test_manage_medications_empty(self):
        """Test viewing medications with no medications"""
        # Create and login as new user with no medications
        new_user = self.create_test_user('newuser@test.com')
        self.login('newuser@test.com', 'password123')
        
        response = self.client.get('/medications/manage')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'You haven\'t added any medications yet', response.data)

    def test_add_medication_get(self):
        """Test GET request to add medication page"""
        self.login()
        response = self.client.get('/medications/add')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Add New Medication', response.data)

    def test_add_medication_post_success(self):
        """Test successfully adding a new medication"""
        self.login()
        response = self.client.post('/medications/add', data={
            'name': 'New Med',
            'dosage': '200mg',
            'frequency': 'daily',
            'time': '09:00'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Medication added successfully!', response.data)
        
        medication = Medication.query.filter_by(name='New Med').first()
        self.assertIsNotNone(medication)
        self.assertEqual(medication.dosage, '200mg')

    def test_add_medication_invalid_data(self):
        """Test adding medication with invalid data"""
        self.login()
        response = self.client.post('/medications/add', data={
            'name': '',  # Invalid: empty name
            'dosage': '200mg',
            'frequency': 'daily',
            'time': '09:00'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'This field is required', response.data)

    def test_delete_medication_success(self):
        """Test successfully deleting a medication"""
        self.login()
        response = self.client.post(f'/medications/{self.test_medication.id}/delete',
                                  follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Medication deleted successfully', response.data)
        
        medication = Medication.query.get(self.test_medication.id)
        self.assertIsNone(medication)

    def test_delete_medication_unauthorized(self):
        """Test deleting medication without authorization"""
        # Create and login as different user
        other_user = self.create_test_user('other@test.com')
        self.login('other@test.com', 'password123')
        
        response = self.client.post(f'/medications/{self.test_medication.id}/delete',
                                  follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Unauthorized action', response.data)
        
        # Verify medication still exists
        medication = Medication.query.get(self.test_medication.id)
        self.assertIsNotNone(medication)

    def test_edit_medication_get_success(self):
        """Test GET request to edit medication"""
        self.login()
        response = self.client.get(f'/medications/{self.test_medication.id}/edit')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Test Med', response.data)
        self.assertIn(b'100mg', response.data)

    def test_edit_medication_post_success(self):
        """Test successfully updating a medication"""
        self.login()
        response = self.client.post(f'/medications/{self.test_medication.id}/edit', data={
            'name': 'Updated Med',
            'dosage': '300mg',
            'frequency': 'twice_daily',
            'time': '10:00'
        }, follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Medication updated successfully!', response.data)
        
        medication = Medication.query.get(self.test_medication.id)
        self.assertEqual(medication.name, 'Updated Med')
        self.assertEqual(medication.dosage, '300mg')

    def test_medication_schedule(self):
        """Test viewing medication schedule"""
        self.login()
        response = self.client.get('/medication-schedule')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Daily Medication Schedule', response.data)

    def test_get_daily_medications(self):
        """Test getting daily medications JSON"""
        self.login()
        response = self.client.get('/medications/daily')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')
        
        data = response.get_json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Test Med')
        self.assertEqual(data[0]['dosage'], '100mg')

    def test_check_reminders(self):
        """Test checking for medication reminders"""
        self.login()
        response = self.client.get('/medications/check-reminders')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'application/json')