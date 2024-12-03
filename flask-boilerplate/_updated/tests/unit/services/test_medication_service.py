# tests/unit/services/test_medication_service.py
from datetime import time, datetime, timedelta
from tests.base import BaseTestCase
from app.services.medication_service import MedicationService
from app.models import Medication, MedicationLog, User, CompanionAccess
from app.extensions import db

class TestMedicationService(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.medication_service = MedicationService(db)
        
        # Create companion user and access for testing
        self.companion = User(
            username='companion',
            email='companion@test.com',
            user_type='COMPANION'
        )
        self.companion.set_password('password123')
        db.session.add(self.companion)
        db.session.commit()
        
        self.companion_access = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access='EDIT',
            glucose_access='VIEW',
            blood_pressure_access='NONE'
        )
        db.session.add(self.companion_access)
        db.session.commit()

    def test_get_medications_success(self):
        """Test successfully retrieving medications for a user"""
        success, medications, error = self.medication_service.get_medications(self.test_user.id)
        
        self.assertTrue(success)
        self.assertEqual(len(medications), 1)
        self.assertEqual(medications[0]['name'], 'Test Med')
        self.assertIsNone(error)

    def test_get_medications_empty(self):
        """Test getting medications for user with no medications"""
        new_user = self.create_test_user('newuser@test.com')
        success, medications, error = self.medication_service.get_medications(new_user.id)
        
        self.assertTrue(success)
        self.assertEqual(len(medications), 0)
        self.assertIsNone(error)

    def test_get_medications_invalid_user(self):
        """Test getting medications for non-existent user"""
        success, medications, error = self.medication_service.get_medications(9999)
        
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
        """Test adding medication with invalid data combinations"""
        test_cases = [
            {'user_id': None, 'name': "New Med", 'dosage': "200mg", 'frequency': "daily", 'time': time(9, 0)},
            {'user_id': self.test_user.id, 'name': None, 'dosage': "200mg", 'frequency': "daily", 'time': time(9, 0)},
            {'user_id': self.test_user.id, 'name': "New Med", 'dosage': None, 'frequency': "daily", 'time': time(9, 0)},
            {'user_id': 9999, 'name': "New Med", 'dosage': "200mg", 'frequency': "daily", 'time': time(9, 0)}
        ]
        
        for test_case in test_cases:
            success, error = self.medication_service.add_medication(**test_case)
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
        
        medication = Medication.query.get(self.test_medication.id)
        self.assertIsNone(medication)

    def test_delete_medication_with_logs(self):
        """Test deleting a medication that has logs"""
        # Create logs
        log1 = MedicationLog(medication_id=self.test_medication.id, user_id=self.test_user.id)
        log2 = MedicationLog(medication_id=self.test_medication.id, user_id=self.test_user.id)
        db.session.add_all([log1, log2])
        db.session.commit()
        
        success, error = self.medication_service.delete_medication(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        # Verify logs were deleted
        logs = MedicationLog.query.filter_by(medication_id=self.test_medication.id).all()
        self.assertEqual(len(logs), 0)

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

    def test_companion_edit_permission(self):
        """Test companion edit permissions"""
        # Test with edit access
        success, medication, error = self.medication_service.check_edit_permission(
            medication_id=self.test_medication.id,
            user_id=self.companion.id
        )
        self.assertTrue(success)
        self.assertIsNotNone(medication)
        self.assertIsNone(error)
        
        # Change to view access and test again
        self.companion_access.medication_access = 'VIEW'
        db.session.commit()
        
        success, medication, error = self.medication_service.check_edit_permission(
            medication_id=self.test_medication.id,
            user_id=self.companion.id
        )
        self.assertFalse(success)
        self.assertIsNone(medication)
        self.assertEqual(error, "Unauthorized access")

    def test_get_daily_medications(self):
        """Test getting daily medications list"""
        # Create a medication taken today and one not taken
        med2 = self.create_test_medication("Evening Med", time(20, 0))
        
        # Log one medication as taken
        self.medication_service.log_medication_taken(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id
        )
        
        success, medications, error = self.medication_service.get_daily_medications(
            self.test_user.id
        )
        
        self.assertTrue(success)
        self.assertEqual(len(medications), 2)
        
        # Verify taken status
        taken_med = next(m for m in medications if m['id'] == self.test_medication.id)
        not_taken_med = next(m for m in medications if m['id'] == med2.id)
        self.assertTrue(taken_med['taken'])
        self.assertFalse(not_taken_med['taken'])

    def test_get_upcoming_reminders(self):
        """Test getting upcoming medication reminders"""
        # Create medications with different times
        current_time = datetime.now().time()
        
        # Medication due in 5 minutes
        due_soon = self.create_test_medication(
            "Due Soon Med",
            time((current_time.hour + ((current_time.minute + 5) // 60)) % 24,
                 (current_time.minute + 5) % 60)
        )
        
        # Medication due in 30 minutes (should not be included in 15-minute window)
        due_later = self.create_test_medication(
            "Due Later Med",
            time((current_time.hour + ((current_time.minute + 30) // 60)) % 24,
                 (current_time.minute + 30) % 60)
        )
        
        success, reminders, error = self.medication_service.get_upcoming_reminders(
            user_id=self.test_user.id,
            minutes_ahead=15
        )
        
        self.assertTrue(success)
        self.assertEqual(len(reminders), 1)
        self.assertEqual(reminders[0]['name'], "Due Soon Med")
        self.assertIsNone(error)

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
        self.assertIsInstance(log.taken_at, datetime)