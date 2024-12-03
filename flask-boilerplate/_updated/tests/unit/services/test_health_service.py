# tests/unit/services/test_health_service.py
from datetime import datetime, timedelta
import unittest
from tests.base import BaseTestCase
from app.models import (
    GlucoseRecord,
    BloodPressureRecord,
    GlucoseType,
    User,
    CompanionAccess,
    Notification
)
from app.extensions import db
from sqlalchemy.exc import IntegrityError, StatementError
from flask_login import current_user
from app.services.health_service import HealthService  # Adjust the import path as necessary
from unittest.mock import patch

class TestHealthService(BaseTestCase):
    """Tests for the HealthService, GlucoseManager, and BloodPressureManager with BVA and Equivalence Class Partitioning."""

    # Define boundary values within this class
    glucose_boundary_values = [49, 50, 51, 300, 349, 350, 351]
    systolic_boundary_values = [49, 50, 51, 100, 299, 300, 301]
    diastolic_boundary_values = [29, 30, 31, 100, 199, 200, 201]

    def setUp(self):
        super().setUp()
        self.health_service = HealthService(db)

    # GlucoseManager Tests
    def test_add_glucose_record_bva(self):
        """Test adding glucose records with boundary values."""
        base_datetime = datetime(2024, 1, 1, 12, 0, 0)
        for i, level in enumerate(self.glucose_boundary_values):
            with self.subTest(glucose_level=level):
                expect_success = 50 <= level <= 350

                user_id = self.test_user.id if expect_success else 9999
                glucose_type = GlucoseType.FASTING if expect_success else 'INVALID_TYPE'
                current_datetime = base_datetime + timedelta(seconds=i)

                result, record, error = self.health_service.add_glucose_record(
                    user_id=user_id,
                    glucose_level=level,
                    glucose_type=glucose_type,
                    date=current_datetime.date().isoformat(),
                    time=current_datetime.time().isoformat()
                )

                if expect_success:
                    self.assertTrue(result, f"Failed for glucose_level={level}")
                    self.assertIsNotNone(record)
                    self.assertEqual(record.glucose_level, level)
                else:
                    self.assertFalse(result)
                    self.assertIsNone(record)
                    self.assertIsNotNone(error)

    def test_add_glucose_record_equivalence_classes(self):
        """Test adding glucose records with valid and invalid equivalence classes."""
        # Valid Equivalence Class
        result, record, error = self.health_service.add_glucose_record(
            user_id=self.test_user.id,
            glucose_level=150,
            glucose_type=GlucoseType.FASTING,
            date='2024-01-01',
            time='12:00:00'
        )
        self.assertTrue(result)
        self.assertIsNotNone(record)
        self.assertEqual(record.glucose_level, 150)

        # Invalid Equivalence Classes
        invalid_cases = [
            {'user_id': self.test_user.id, 'glucose_level': 400, 'glucose_type': GlucoseType.FASTING},
            {'user_id': self.test_user.id, 'glucose_level': 30, 'glucose_type': GlucoseType.FASTING},
            {'user_id': 9999, 'glucose_level': 100, 'glucose_type': GlucoseType.FASTING},  # Invalid user_id
            {'user_id': self.test_user.id, 'glucose_level': 100, 'glucose_type': 'INVALID_TYPE'},  # Invalid type
            {'user_id': self.test_user.id, 'glucose_level': 100, 'glucose_type': None},  # Missing type
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                result, record, error = self.health_service.add_glucose_record(
                    user_id=case['user_id'],
                    glucose_level=case['glucose_level'],
                    glucose_type=case['glucose_type'],
                    date='2024-01-01',
                    time='12:00:00'
                )
                self.assertFalse(result)
                self.assertIsNone(record)
                self.assertIsNotNone(error)

    def test_add_blood_pressure_record_bva(self):
        """Test adding blood pressure records with boundary values."""
        base_datetime = datetime(2024, 1, 1, 12, 0, 0)
        for i, systolic in enumerate(self.systolic_boundary_values):
            for j, diastolic in enumerate(self.diastolic_boundary_values):
                with self.subTest(systolic=systolic, diastolic=diastolic):
                    systolic_valid = 50 <= systolic <= 300
                    diastolic_valid = 30 <= diastolic <= 200
                    expect_success = systolic_valid and diastolic_valid

                    user_id = self.test_user.id if expect_success else 9999
                    current_datetime = base_datetime + timedelta(seconds=i*len(self.diastolic_boundary_values) + j)

                    result, record, error = self.health_service.add_blood_pressure_record(
                        user_id=user_id,
                        systolic=systolic,
                        diastolic=diastolic,
                        date=current_datetime.date().isoformat(),
                        time=current_datetime.time().isoformat()
                    )

                    if expect_success:
                        self.assertTrue(result)
                        self.assertIsNotNone(record)
                        self.assertEqual(record.systolic, systolic)
                        self.assertEqual(record.diastolic, diastolic)
                    else:
                        self.assertFalse(result)
                        self.assertIsNone(record)
                        self.assertIsNotNone(error)

    def test_add_blood_pressure_record_equivalence_classes(self):
        """Test adding blood pressure records with valid and invalid equivalence classes."""
        # Valid Equivalence Class
        result, record, error = self.health_service.add_blood_pressure_record(
            user_id=self.test_user.id,
            systolic=120,
            diastolic=80,
            date='2024-01-01',
            time='12:00:00'
        )
        self.assertTrue(result)
        self.assertIsNotNone(record)
        self.assertEqual(record.systolic, 120)
        self.assertEqual(record.diastolic, 80)

        # Invalid Equivalence Classes
        invalid_cases = [
            {'user_id': self.test_user.id, 'systolic': 400, 'diastolic': 80},    # Invalid systolic
            {'user_id': self.test_user.id, 'systolic': 120, 'diastolic': 250},   # Invalid diastolic
            {'user_id': 9999, 'systolic': 120, 'diastolic': 80},                 # Invalid user_id
            {'user_id': self.test_user.id, 'systolic': 'high', 'diastolic': 80}, # Non-integer systolic
            {'user_id': self.test_user.id, 'systolic': 120, 'diastolic': None},  # Missing diastolic
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                result, record, error = self.health_service.add_blood_pressure_record(
                    user_id=case['user_id'],
                    systolic=case['systolic'],
                    diastolic=case['diastolic'],
                    date='2024-01-01',
                    time='12:00:00'
                )
                self.assertFalse(result)
                self.assertIsNone(record)
                self.assertIsNotNone(error)

    def test_duplicate_glucose_record(self):
        """Test that adding duplicate glucose records is handled properly."""
        # Add initial record
        result, record, error = self.health_service.add_glucose_record(
            user_id=self.test_user.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,
            date='2024-01-01',
            time='12:00:00'
        )
        self.assertTrue(result)
        self.assertIsNotNone(record)

        # Attempt to add duplicate
        result, record, error = self.health_service.add_glucose_record(
            user_id=self.test_user.id,
            glucose_level=110,
            glucose_type=GlucoseType.POSTPRANDIAL,
            date='2024-01-01',
            time='12:00:00'
        )
        self.assertFalse(result)
        self.assertIsNone(record)
        self.assertEqual(error, "A glucose record for this date and time already exists.")

    def test_duplicate_blood_pressure_record(self):
        """Test that adding duplicate blood pressure records is handled properly."""
        # Add initial record
        result, record, error = self.health_service.add_blood_pressure_record(
            user_id=self.test_user.id,
            systolic=120,
            diastolic=80,
            date='2024-01-01',
            time='12:00:00'
        )
        self.assertTrue(result)
        self.assertIsNotNone(record)

        # Attempt to add duplicate
        result, record, error = self.health_service.add_blood_pressure_record(
            user_id=self.test_user.id,
            systolic=130,
            diastolic=85,
            date='2024-01-01',
            time='12:00:00'
        )
        self.assertFalse(result)
        self.assertIsNone(record)
        self.assertEqual(error, "A blood pressure record for this date and time already exists.")

    def test_update_glucose_record_bva(self):
        """Test updating glucose records with boundary values."""
        # Add initial record
        result, record, error = self.health_service.add_glucose_record(
            user_id=self.test_user.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,
            date='2024-01-01',
            time='12:00:00'
        )
        self.assertTrue(result)
        record_id = record.id

        for level in self.glucose_boundary_values:
            with self.subTest(glucose_level=level):
                if 50 <= level <= 350:
                    expect_success = True
                else:
                    expect_success = False

                user_id = self.test_user.id if expect_success else 9999
                glucose_type = GlucoseType.FASTING if expect_success else 'INVALID_TYPE'

                result, error = self.health_service.update_glucose_record(
                    record_id=record_id,
                    user_id=user_id,
                    glucose_level=level,
                    glucose_type=glucose_type,
                    date='2024-01-02',
                    time='13:00:00'
                )

                if expect_success:
                    self.assertTrue(result)
                    updated_record = GlucoseRecord.query.get(record_id)
                    self.assertEqual(updated_record.glucose_level, level)
                else:
                    self.assertFalse(result)
                    self.assertIsNotNone(error)

    def test_delete_glucose_record(self):
        """Test deleting a glucose record."""
        # Add initial record
        result, record, error = self.health_service.add_glucose_record(
            user_id=self.test_user.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,
            date='2024-01-01',
            time='12:00:00'
        )
        self.assertTrue(result)
        record_id = record.id

        # Delete the record
        result, error = self.health_service.delete_glucose_record(
            record_id=record_id,
            user_id=self.test_user.id
        )
        self.assertTrue(result)
        deleted_record = GlucoseRecord.query.get(record_id)
        self.assertIsNone(deleted_record)

    def test_notify_companions_glucose(self):
        """Test that companions are notified when glucose levels are risky."""
        # Set up companion
        companion = User(
            username='companion_user',
            email='companion@example.com',
            user_type='COMPANION'
        )
        db.session.add(companion)
        db.session.commit()

        access = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=companion.id,
            glucose_access='VIEW'
        )
        db.session.add(access)
        db.session.commit()

        # Mock current_user to be the patient (not the companion)
        # To simulate that the patient is adding a glucose record which should notify companions
        with patch('app.services.health_service.current_user', self.test_user):
            # Add a risky glucose record
            result, record, error = self.health_service.add_glucose_record(
                user_id=self.test_user.id,
                glucose_level=55,  # Below normal_min (70) for fasting_glucose
                glucose_type=GlucoseType.FASTING,
                date='2024-01-03',
                time='08:00:00'
            )
            self.assertTrue(result)
            self.assertIsNotNone(record)

            # Check that a notification was created for the companion
            notifications = Notification.query.filter_by(user_id=companion.id).all()
            self.assertTrue(len(notifications) > 0)
            self.assertIn("Low", notifications[0].message)  


class TestReportController(BaseTestCase):
    """Tests for the ReportController."""

    def test_health_reports_page_unauthenticated_get(self):
        """Test accessing the health reports page with GET as an unauthenticated user."""
        response = self.client.get('/health-reports')  # Adjust the URL as necessary
        self.assertEqual(response.status_code, 302)  # Expect 302 Redirect to login

    def test_health_reports_page_unauthenticated_post(self):
        """Test accessing the health reports page with POST as an unauthenticated user."""
        response = self.client.post('/health-reports')  # Adjust the URL as necessary
        self.assertEqual(response.status_code, 302)  # Expect 302 Redirect to login


if __name__ == '__main__':
    unittest.main()
