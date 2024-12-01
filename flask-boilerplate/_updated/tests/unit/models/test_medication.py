from datetime import datetime, time
from tests.base import BaseTestCase
from app.models import Medication, MedicationLog, User
from app.extensions import db

class TestMedicationModel(BaseTestCase):
    def test_create_medication(self):
        """Test creating a new medication"""
        medication = Medication(
            name='Test Medication',
            dosage='100mg',
            frequency='daily',
            time=time(8, 0),
            user_id=self.test_user.id
        )
        db.session.add(medication)
        db.session.commit()

        # Verify medication was created
        saved_med = Medication.query.filter_by(name='Test Medication').first()
        self.assertIsNotNone(saved_med)
        self.assertEqual(saved_med.dosage, '100mg')
        self.assertEqual(saved_med.frequency, 'daily')
        self.assertEqual(saved_med.time, time(8, 0))

    def test_medication_user_relationship(self):
        """Test relationship between medication and user"""
        # Already have test_medication from BaseTestCase
        user = User.query.get(self.test_medication.user_id)
        self.assertEqual(user.id, self.test_user.id)
        self.assertIn(self.test_medication, user.medications)

    def test_medication_logs_relationship(self):
        """Test relationship between medication and its logs"""
        # Create a medication log
        log = MedicationLog(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id,
            taken_at=datetime.now()
        )
        db.session.add(log)
        db.session.commit()

        # Verify relationship
        self.assertIn(log, self.test_medication.logs)
        self.assertEqual(log.medication, self.test_medication)

    # def test_cascade_delete_logs(self):
    #     """Test that deleting a medication also deletes its logs"""
    #     # Create multiple logs for the medication
    #     log1 = MedicationLog(
    #         medication_id=self.test_medication.id,
    #         user_id=self.test_user.id,
    #         taken_at=datetime.now()
    #     )
    #     log2 = MedicationLog(
    #         medication_id=self.test_medication.id,
    #         user_id=self.test_user.id,
    #         taken_at=datetime.now()
    #     )
    #     db.session.add_all([log1, log2])
    #     db.session.commit()

    #     # Get log IDs before deletion
    #     log_ids = [log.id for log in self.test_medication.logs]

    #     # Delete medication
    #     db.session.delete(self.test_medication)
    #     db.session.commit()

    #     # Verify logs were deleted
    #     for log_id in log_ids:
    #         self.assertIsNone(MedicationLog.query.get(log_id))

    def test_medication_required_fields(self):
        """Test that required fields raise error when missing"""
        # Try creating medication without required fields
        medication = Medication(
            name=None,  # Required field
            dosage='100mg',
            frequency='daily',
            time=time(8, 0),
            user_id=self.test_user.id
        )
        
        with self.assertRaises(Exception):
            db.session.add(medication)
            db.session.commit()
        
        db.session.rollback()

    def test_duplicate_medication_allowed(self):
        """Test that same user can have multiple medications with same name"""
        # Create medication with same name
        duplicate_med = Medication(
            name=self.test_medication.name,
            dosage='200mg',  # Different dosage
            frequency='daily',
            time=time(9, 0),  # Different time
            user_id=self.test_user.id
        )
        
        try:
            db.session.add(duplicate_med)
            db.session.commit()
            # Should succeed
            self.assertIsNotNone(duplicate_med.id)
        except Exception as e:
            self.fail(f"Should allow duplicate medication names: {str(e)}")

    def test_invalid_frequency(self):
        """Test creating medication with invalid frequency"""
        medication = Medication(
            name='Test Med',
            dosage='100mg',
            frequency='invalid_frequency',  # Invalid value
            time=time(8, 0),
            user_id=self.test_user.id
        )
        
        # Should still work as we don't have frequency validation
        db.session.add(medication)
        db.session.commit()
        self.assertIsNotNone(medication.id)

    # def test_medication_repr(self):
    #     """Test the string representation of Medication"""
    #     if hasattr(Medication, '__repr__'):
    #         repr_string = repr(self.test_medication)
    #         self.assertIsInstance(repr_string, str)
    #         self.assertIn(self.test_medication.name, repr_string)

    def test_user_id_foreign_key(self):
        """Test that user_id foreign key constraint works"""
        # Try to create medication with non-existent user_id
        medication = Medication(
            name='Test Med',
            dosage='100mg',
            frequency='daily',
            time=time(8, 0),
            user_id=9999  # Non-existent user_id
        )
        
        with self.assertRaises(Exception):
            db.session.add(medication)
            db.session.commit()
        
        db.session.rollback()

    def test_medication_time_conversion(self):
        """Test time field stores and retrieves correctly"""
        test_time = time(14, 30)  # 2:30 PM
        
        medication = Medication(
            name='Time Test Med',
            dosage='100mg',
            frequency='daily',
            time=test_time,
            user_id=self.test_user.id
        )
        
        db.session.add(medication)
        db.session.commit()
        
        # Fetch from database and verify time
        saved_med = Medication.query.get(medication.id)
        self.assertEqual(saved_med.time.hour, 14)
        self.assertEqual(saved_med.time.minute, 30)

    def test_medication_update(self):
        """Test updating medication fields"""
        self.test_medication.name = 'Updated Name'
        self.test_medication.dosage = 'Updated Dosage'
        db.session.commit()
        
        # Fetch fresh from database
        updated_med = Medication.query.get(self.test_medication.id)
        self.assertEqual(updated_med.name, 'Updated Name')
        self.assertEqual(updated_med.dosage, 'Updated Dosage')

    def test_bulk_medication_operations(self):
        """Test bulk operations with medications"""
        # Create multiple medications
        medications = [
            Medication(
                name=f'Bulk Med {i}',
                dosage='100mg',
                frequency='daily',
                time=time(8, 0),
                user_id=self.test_user.id
            ) for i in range(3)
        ]
        
        # Bulk insert
        db.session.add_all(medications)
        db.session.commit()
        
        # Verify all were created
        count = Medication.query.filter(
            Medication.name.like('Bulk Med%')
        ).count()
        self.assertEqual(count, 3)