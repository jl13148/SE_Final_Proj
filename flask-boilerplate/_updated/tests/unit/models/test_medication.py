# tests/unit/models/test_medication.py
from datetime import datetime, time, timedelta
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

        saved_med = Medication.query.filter_by(name='Test Medication').first()
        self.assertIsNotNone(saved_med)
        self.assertEqual(saved_med.dosage, '100mg')
        self.assertEqual(saved_med.frequency, 'daily')
        self.assertEqual(saved_med.time, time(8, 0))

    def test_medication_user_relationship(self):
        """Test relationship between medication and user"""
        user = User.query.get(self.test_medication.user_id)
        self.assertEqual(user.id, self.test_user.id)
        self.assertIn(self.test_medication, user.medications)

    def test_medication_logs_relationship(self):
        """Test relationship between medication and its logs"""
        log = MedicationLog(
            medication_id=self.test_medication.id,
            user_id=self.test_user.id,
            taken_at=datetime.now()
        )
        db.session.add(log)
        db.session.commit()

        self.assertIn(log, self.test_medication.logs)
        self.assertEqual(log.medication, self.test_medication)

    def test_medication_required_fields(self):
        """Test that required fields raise error when missing"""
        required_fields = ['name', 'dosage', 'frequency', 'time', 'user_id']
        
        for field in required_fields:
            data = {
                'name': 'Test Med',
                'dosage': '100mg',
                'frequency': 'daily',
                'time': time(8, 0),
                'user_id': self.test_user.id
            }
            data[field] = None
            
            medication = Medication(**data)
            with self.assertRaises(Exception):
                db.session.add(medication)
                db.session.commit()
            db.session.rollback()

    def test_multiple_frequencies(self):
        """Test creating medications with different frequencies"""
        frequencies = ['daily', 'twice_daily', 'weekly', 'monthly']
        
        for freq in frequencies:
            medication = Medication(
                name=f'Test Med {freq}',
                dosage='100mg',
                frequency=freq,
                time=time(8, 0),
                user_id=self.test_user.id
            )
            db.session.add(medication)
            db.session.commit()
            
            saved_med = Medication.query.filter_by(name=f'Test Med {freq}').first()
            self.assertEqual(saved_med.frequency, freq)

    def test_multiple_logs_per_medication(self):
        """Test creating multiple logs for a single medication"""
        base_time = datetime.now()
        log_times = [
            base_time - timedelta(days=2),
            base_time - timedelta(days=1),
            base_time
        ]
        
        for taken_at in log_times:
            log = MedicationLog(
                medication_id=self.test_medication.id,
                user_id=self.test_user.id,
                taken_at=taken_at
            )
            db.session.add(log)
        
        db.session.commit()
        
        logs = MedicationLog.query.filter_by(
            medication_id=self.test_medication.id
        ).order_by(MedicationLog.taken_at.desc()).all()
        
        self.assertEqual(len(logs), len(log_times))
        for log, expected_time in zip(logs, reversed(log_times)):
            self.assertEqual(log.taken_at, expected_time)