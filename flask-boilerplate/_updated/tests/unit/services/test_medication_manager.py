import unittest
from unittest.mock import patch
from datetime import time, datetime, timedelta
from tests.base import BaseTestCase
from app.services.medication_service import MedicationManager
from app.models import Medication, MedicationLog, User, CompanionAccess
from app.extensions import db

class TestMedicationManager(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.med_manager = MedicationManager(db)
        
        # Create a companion user
        self.companion = self.create_test_user('companion_manager@test.com', user_type='COMPANION')
        
        # Create companion access
        self.companion_access = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access='EDIT',
            glucose_access='VIEW',
            blood_pressure_access='NONE'
        )
        db.session.add(self.companion_access)
        db.session.commit()
        
        # Create a test medication called 'Manager Med'
        self.test_medication = self.create_test_medication('Manager Med', time(10, 0))

    
    def create_test_user(self, email: str, user_type: str = 'PATIENT') -> User:
        """Helper method to create a test user."""
        user = User(
            username=email.split('@')[0],
            email=email,
            user_type=user_type
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return user
    
    def create_test_medication(self, name, med_time, user_id=None):
        """Helper method to create a test medication."""
        if not user_id:
            user_id = self.test_user.id
        medication = Medication(
            name=name,
            dosage="100mg",
            frequency="daily",
            time=med_time,
            user_id=user_id
        )
        db.session.add(medication)
        db.session.commit()
        return medication
    
    # Test get_medications
    def test_get_medications_success(self):
        """Test successfully retrieving medications for a user."""
        success, medications, error = self.med_manager.get_medications(self.test_user.id)
        
        self.assertTrue(success)
        self.assertEqual(len(medications), 2)
        self.assertEqual(medications[0]['name'], 'Test Med')
        self.assertIsNone(error)
    
    def test_get_medications_no_medications(self):
        """Test retrieving medications for a user with no medications."""
        new_user = self.create_test_user('nomeds@test.com')
        success, medications, error = self.med_manager.get_medications(new_user.id)
        
        self.assertTrue(success)
        self.assertEqual(len(medications), 0)
        self.assertIsNone(error)
    
    # Test add_medication
    def test_add_medication_success(self):
        """Test successfully adding a new medication."""
        success, error = self.med_manager.add_medication(
            user_id=self.test_user.id,
            name="Added Med",
            dosage="200mg",
            frequency="twice_daily",
            time=time(12, 0)
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        medication = Medication.query.filter_by(
            user_id=self.test_user.id,
            name="Added Med"
        ).first()
        self.assertIsNotNone(medication)
        self.assertEqual(medication.dosage, "200mg")
        self.assertEqual(medication.frequency, "twice_daily")
        self.assertEqual(medication.time, time(12, 0))
    
    def test_add_medication_failure(self):
        """Test adding medication with invalid data."""
        # Missing user_id
        success, error = self.med_manager.add_medication(
            user_id=None,
            name="Invalid Med",
            dosage="",
            frequency="",
            time=time(0, 0)
        )
        self.assertFalse(success)
        self.assertIsNotNone(error)
    
    # Test delete_medication
    def test_delete_medication_success(self):
        """Test successfully deleting a medication."""
        success, error = self.med_manager.delete_medication(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        medication = Medication.query.get(self.test_medication.id)
        self.assertIsNone(medication)
    
    def test_delete_medication_unauthorized(self):
        """Test deleting a medication that does not belong to the user."""
        # Create another user and medication
        another_user = self.create_test_user('another@test.com')
        another_med = self.create_test_medication('Another Med', time(11, 0), user_id=another_user.id)
        
        success, error = self.med_manager.delete_medication(
            medication_id=another_med.id,
            user_id=self.test_user.id  # Not the owner
        )
        
        self.assertFalse(success)
        self.assertEqual(error, "Unauthorized action")
        
        # Ensure medication still exists
        medication = Medication.query.get(another_med.id)
        self.assertIsNotNone(medication)
    
    def test_delete_medication_with_logs(self):
        """Test deleting a medication that has logs."""
        # Create logs
        log1 = MedicationLog(medication_id=self.test_medication.id, user_id=self.test_user.id)
        log2 = MedicationLog(medication_id=self.test_medication.id, user_id=self.test_user.id)
        db.session.add_all([log1, log2])
        db.session.commit()
        
        success, error = self.med_manager.delete_medication(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        # Verify logs were deleted
        logs = MedicationLog.query.filter_by(medication_id=self.test_medication.id).all()
        self.assertEqual(len(logs), 0)
    
    def test_delete_medication_nonexistent(self):
        """Test deleting a non-existent medication."""
        success, error = self.med_manager.delete_medication(
            medication_id=9999,  # Assuming this ID does not exist
            user_id=self.test_user.id
        )
        
        self.assertFalse(success)
        self.assertIsNotNone(error)
    
    # Test update_medication
    def test_update_medication_success(self):
        """Test successfully updating a medication."""
        success, error = self.med_manager.update_medication(
            medication_id=self.test_medication.id,
            name="Updated Manager Med",
            dosage="150mg",
            frequency="once_daily",
            time=time(14, 0)
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        medication = Medication.query.get(self.test_medication.id)
        self.assertEqual(medication.name, "Updated Manager Med")
        self.assertEqual(medication.dosage, "150mg")
        self.assertEqual(medication.frequency, "once_daily")
        self.assertEqual(medication.time, time(14, 0))
    
    def test_update_medication_nonexistent(self):
        """Test updating a non-existent medication."""
        success, error = self.med_manager.update_medication(
            medication_id=9999,  # Assuming this ID does not exist
            name="Ghost Med",
            dosage="500mg",
            frequency="once_daily",
            time=time(12, 0)
        )
        
        self.assertFalse(success)
        self.assertIsNotNone(error)
    
    # Test check_edit_permission
    def test_check_edit_permission_owner(self):
        """Test check_edit_permission when the user is the owner."""
        success, medication, error = self.med_manager.check_edit_permission(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(medication)
        self.assertIsNone(error)
    
    def test_check_edit_permission_companion_edit(self):
        """Test check_edit_permission when companion has EDIT access."""
        success, medication, error = self.med_manager.check_edit_permission(
            medication_id=self.test_medication.id,
            user_id=self.companion.id
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(medication)
        self.assertIsNone(error)
    
    def test_check_edit_permission_companion_view(self):
        """Test check_edit_permission when companion has VIEW access."""
        # Change companion access to 'VIEW'
        self.companion_access.medication_access = 'VIEW'
        db.session.commit()
        
        success, medication, error = self.med_manager.check_edit_permission(
            medication_id=self.test_medication.id,
            user_id=self.companion.id
        )
        
        self.assertFalse(success)
        self.assertIsNone(medication)
        self.assertEqual(error, "Unauthorized access")
    
    def test_check_edit_permission_no_access(self):
        """Test check_edit_permission when companion has no access."""
        # Remove companion access
        db.session.delete(self.companion_access)
        db.session.commit()
        
        success, medication, error = self.med_manager.check_edit_permission(
            medication_id=self.test_medication.id,
            user_id=self.companion.id
        )
        
        self.assertFalse(success)
        self.assertIsNone(medication)
        self.assertEqual(error, "Unauthorized access")
    
    # Testing exception handling using mocking 
    @patch('app.models.Medication.query')
    def test_delete_medication_exception(self, mock_query):
        """Test delete_medication method when an exception occurs."""
        mock_query.get_or_404.side_effect = Exception("Database delete error")
        
        success, error = self.med_manager.delete_medication(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id
        )
        
        self.assertFalse(success)
        self.assertEqual(error, "Database delete error")
    
    @patch('app.models.CompanionAccess.query')
    def test_check_edit_permission_exception(self, mock_query):
        """Test check_edit_permission method when an exception occurs."""
        mock_query.filter_by.side_effect = Exception("Database access error")
        
        success, medication, error = self.med_manager.check_edit_permission(
            medication_id=self.test_medication.id,
            user_id=self.companion.id
        )
        
        self.assertFalse(success)
        self.assertIsNone(medication)
        self.assertEqual(error, "Database access error")

if __name__ == '__main__':
    unittest.main()