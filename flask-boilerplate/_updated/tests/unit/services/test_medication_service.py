from datetime import time, datetime
from tests.base import BaseTestCase
from app.services.medication_service import MedicationService
from app.models import Medication, MedicationLog
from app.extensions import db

class TestMedicationService(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.medication_service = MedicationService(db)

    def test_get_medications_success(self):
        """Test successfully retrieving medications for a user"""
        success, medications, error = self.medication_service.get_medications(self.test_user.id)
        
        self.assertTrue(success)
        self.assertEqual(len(medications), 1)
        self.assertEqual(medications[0]['name'], 'Test Med')  # Updated to use dict access
        self.assertIsNone(error)

    def test_get_medications_empty(self):
        """Test getting medications for user with no medications"""
        # Create new user without medications
        new_user = self.create_test_user('newuser@test.com')
        success, medications, error = self.medication_service.get_medications(new_user.id)
        
        self.assertTrue(success)
        self.assertEqual(len(medications), 0)
        self.assertIsNone(error)

    def test_add_medication_success(self):
        """Test successfully adding a new medication"""
        success, error = self.medication_service.add_medication(
            user_id=self.test_user.id,
            name="New Med",
            dosage="200mg",
            frequency="daily",
            time=time(9, 0)
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        medication = Medication.query.filter_by(
            user_id=self.test_user.id,
            name="New Med"
        ).first()
        self.assertIsNotNone(medication)
        self.assertEqual(medication.dosage, "200mg")

    def test_add_medication_invalid_data(self):
        """Test adding medication with invalid data"""
        success, error = self.medication_service.add_medication(
            user_id=None,  # Invalid user_id
            name="New Med",
            dosage="200mg",
            frequency="daily",
            time=time(9, 0)
        )
        
        self.assertFalse(success)
        self.assertIsNotNone(error)

    def test_delete_medication_success(self):
        """Test successfully deleting a medication"""
        success, error = self.medication_service.delete_medication(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        # Verify medication was deleted
        medication = Medication.query.get(self.test_medication.id)
        self.assertIsNone(medication)

    def test_delete_medication_unauthorized(self):
        """Test deleting medication without authorization"""
        other_user = self.create_test_user('other@test.com')
        success, error = self.medication_service.delete_medication(
            medication_id=self.test_medication.id,
            user_id=other_user.id
        )
        
        self.assertFalse(success)
        self.assertEqual(error, "Unauthorized action")
        
        # Verify medication still exists
        medication = Medication.query.get(self.test_medication.id)
        self.assertIsNotNone(medication)

    def test_update_medication_success(self):
        """Test successfully updating a medication"""
        success, error = self.medication_service.update_medication(
            medication_id=self.test_medication.id,
            name="Updated Med",
            dosage="300mg",
            frequency="twice_daily",
            time=time(10, 0)
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        medication = Medication.query.get(self.test_medication.id)
        self.assertEqual(medication.name, "Updated Med")
        self.assertEqual(medication.dosage, "300mg")
        self.assertEqual(medication.frequency, "twice_daily")

    def test_update_medication_not_found(self):
        """Test updating non-existent medication"""
        success, error = self.medication_service.update_medication(
            medication_id=9999,
            name="Updated Med",
            dosage="300mg",
            frequency="twice_daily",
            time=time(10, 0)
        )
        
        self.assertFalse(success)
        self.assertIsNotNone(error)

    def test_check_edit_permission_owner(self):
        """Test edit permission check for medication owner"""
        success, medication, error = self.medication_service.check_edit_permission(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(medication)
        self.assertIsNone(error)

    def test_check_edit_permission_unauthorized(self):
        """Test edit permission check for unauthorized user"""
        other_user = self.create_test_user('other@test.com')
        success, medication, error = self.medication_service.check_edit_permission(
            medication_id=self.test_medication.id,
            user_id=other_user.id
        )
        
        self.assertFalse(success)
        self.assertIsNone(medication)
        self.assertEqual(error, "Unauthorized access")

    def test_get_daily_medications(self):
        """Test getting daily medications list"""
        success, medications, error = self.medication_service.get_daily_medications(
            self.test_user.id
        )
        
        self.assertTrue(success)
        self.assertEqual(len(medications), 1)
        self.assertEqual(medications[0]['name'], 'Test Med')
        self.assertEqual(medications[0]['dosage'], '100mg')
        self.assertIn('time', medications[0])
        self.assertIsNone(error)

    # def test_get_upcoming_reminders(self):
    #     """Test getting upcoming medication reminders"""
    #     # Create a medication due soon
    #     current_time = datetime.now().time()
    #     med = self.create_test_medication(
    #         name="Soon Med",
    #         test_time=current_time  # Changed to test_time
    #     )
        
    #     success, reminders, error = self.medication_service.get_upcoming_reminders(
    #         user_id=self.test_user.id,
    #         minutes_ahead=15
    #     )
        
    #     self.assertTrue(success)
    #     self.assertGreaterEqual(len(reminders), 1)
    #     self.assertIsNone(error)

    def test_log_medication_taken(self):
        """Test logging a taken medication"""
        success, error = self.medication_service.log_medication_taken(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        # Verify log was created
        log = MedicationLog.query.filter_by(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id
        ).first()
        self.assertIsNotNone(log)