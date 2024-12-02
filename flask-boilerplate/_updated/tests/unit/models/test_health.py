from datetime import datetime, time
from tests.base import BaseTestCase
from app.models import GlucoseRecord, BloodPressureRecord, GlucoseType
from app.extensions import db
from sqlalchemy.exc import IntegrityError

class TestHealthModel(BaseTestCase):
    def test_create_glucose_record(self):
        """Test creating a new glucose record"""
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        current_time = datetime.now().time().strftime('%H:%M:%S')
        
        record = GlucoseRecord(
            user_id=self.test_user.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,  # Use the Enum
            date=current_date,
            time=current_time
        )
        db.session.add(record)
        db.session.commit()

        saved_record = GlucoseRecord.query.filter_by(user_id=self.test_user.id).first()
        self.assertIsNotNone(saved_record)
        self.assertEqual(saved_record.glucose_level, 100)
        self.assertEqual(saved_record.glucose_type, GlucoseType.FASTING)

    def test_create_blood_pressure_record(self):
        """Test creating a new blood pressure record"""
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        current_time = datetime.now().time().strftime('%H:%M:%S')
        
        record = BloodPressureRecord(
            user_id=self.test_user.id,
            systolic=120,
            diastolic=80,
            date=current_date,
            time=current_time
        )
        db.session.add(record)
        db.session.commit()

        saved_record = BloodPressureRecord.query.filter_by(user_id=self.test_user.id).first()
        self.assertIsNotNone(saved_record)
        self.assertEqual(saved_record.systolic, 120)
        self.assertEqual(saved_record.diastolic, 80)

    def test_glucose_record_user_relationship(self):
        """Test relationship between glucose record and user"""
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        current_time = datetime.now().time().strftime('%H:%M:%S')
        
        record = GlucoseRecord(
            user_id=self.test_user.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,  # Use the Enum
            date=current_date,
            time=current_time
        )
        db.session.add(record)
        db.session.commit()

        self.assertIn(record, self.test_user.glucose_records)

    def test_blood_pressure_record_user_relationship(self):
        """Test relationship between blood pressure record and user"""
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        current_time = datetime.now().time().strftime('%H:%M:%S')
        
        record = BloodPressureRecord(
            user_id=self.test_user.id,
            systolic=120,
            diastolic=80,
            date=current_date,
            time=current_time
        )
        db.session.add(record)
        db.session.commit()

        self.assertIn(record, self.test_user.blood_pressure_records)

    def test_glucose_record_required_fields(self):
        """Test that required fields raise IntegrityError when missing"""
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        current_time = datetime.now().time().strftime('%H:%M:%S')
        
        # Test missing glucose_level
        with self.assertRaises(IntegrityError):
            record = GlucoseRecord(
                user_id=self.test_user.id,
                glucose_type=GlucoseType.FASTING,
                date=current_date,
                time=current_time
                # Missing glucose_level
            )
            db.session.add(record)
            db.session.commit()
        db.session.rollback()

        # Test missing user_id
        with self.assertRaises(IntegrityError):
            record = GlucoseRecord(
                glucose_level=100,
                glucose_type=GlucoseType.FASTING,
                date=current_date,
                time=current_time
                # Missing user_id
            )
            db.session.add(record)
            db.session.commit()
        db.session.rollback()

    def test_blood_pressure_record_required_fields(self):
        """Test that required fields raise IntegrityError when missing"""
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        current_time = datetime.now().time().strftime('%H:%M:%S')
        
        # Test missing systolic
        with self.assertRaises(IntegrityError):
            record = BloodPressureRecord(
                user_id=self.test_user.id,
                diastolic=80,
                date=current_date,
                time=current_time
                # Missing systolic
            )
            db.session.add(record)
            db.session.commit()
        db.session.rollback()

        # Test missing diastolic
        with self.assertRaises(IntegrityError):
            record = BloodPressureRecord(
                user_id=self.test_user.id,
                systolic=120,
                date=current_date,
                time=current_time
                # Missing diastolic
            )
            db.session.add(record)
            db.session.commit()
        db.session.rollback()

    def test_glucose_record_invalid_user_id(self):
        """Test creating glucose record with invalid user_id"""
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        current_time = datetime.now().time().strftime('%H:%M:%S')
        
        with self.assertRaises(IntegrityError):
            record = GlucoseRecord(
                user_id=9999,  # Non-existent user_id
                glucose_level=100,
                glucose_type=GlucoseType.FASTING,
                date=current_date,
                time=current_time
            )
            db.session.add(record)
            db.session.commit()
        db.session.rollback()

    def test_blood_pressure_record_invalid_user_id(self):
        """Test creating blood pressure record with invalid user_id"""
        current_date = datetime.now().date().strftime('%Y-%m-%d')
        current_time = datetime.now().time().strftime('%H:%M:%S')
        
        with self.assertRaises(IntegrityError):
            record = BloodPressureRecord(
                user_id=9999,  # Non-existent user_id
                systolic=120,
                diastolic=80,
                date=current_date,
                time=current_time
            )
            db.session.add(record)
            db.session.commit()
        db.session.rollback()