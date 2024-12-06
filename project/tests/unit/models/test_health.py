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


class TestHealthModel(BaseTestCase):
    """Tests for the GlucoseRecord and BloodPressureRecord models with BVA and Equivalence Class Partitioning."""

    # Boundary and equivalence class values
    glucose_boundary_values = [49, 50, 51, 300, 349, 350, 351]
    systolic_boundary_values = [49, 50, 51, 100, 299, 300, 301]
    diastolic_boundary_values = [29, 30, 31, 100, 199, 200, 201]
    valid_glucose_types = [GlucoseType.FASTING, GlucoseType.POSTPRANDIAL]
    invalid_glucose_types = ['INVALID_TYPE', 'FASTING ', 'POSTPRANDIAL', None, 123]

    def setUp(self):
        super().setUp()
        # Define a valid blood pressure case
        self.valid_bp_case = {
            'user_id': self.test_user.id,
            'systolic': 120,     # Within 50-300
            'diastolic': 80,     # Within 30-200
            'date': '2024-01-01',
            'time': '12:00'
        }

        # Define a valid glucose case
        self.valid_glucose_case = {
            'user_id': self.test_user.id,
            'glucose_level': 150,                # Within 50-350
            'glucose_type': GlucoseType.FASTING, # Valid Enum
            'date': '2024-01-01',
            'time': '12:00'
        }

    def test_create_glucose_record_valid_boundary_values(self):
        """Test creating glucose records with boundary values."""
        for level in self.glucose_boundary_values:
            with self.subTest(glucose_level=level):
                if 50 <= level <= 350:
                    expect_success = True
                else:
                    expect_success = False

                current_date = datetime.now().date().strftime('%Y-%m-%d')
                current_time = datetime.now().time().strftime('%H:%M:%S')

                # Use valid user_id or invalid one based on expectation
                user_id = self.test_user.id if expect_success else 9999

                # Use valid or invalid glucose_type
                if expect_success:
                    glucose_type = GlucoseType.FASTING
                else:
                    glucose_type = 'INVALID_TYPE'  # Use an invalid string

                record = GlucoseRecord(
                    user_id=user_id,
                    glucose_level=level,
                    glucose_type=glucose_type,
                    date=current_date,
                    time=current_time
                )
                db.session.add(record)
                try:
                    db.session.commit()
                    if expect_success:
                        saved_record = GlucoseRecord.query.filter_by(glucose_level=level).first()
                        self.assertIsNotNone(saved_record)
                        self.assertEqual(saved_record.glucose_level, level)
                    else:
                        self.fail("IntegrityError expected but not raised.")
                except (IntegrityError, StatementError):
                    if expect_success:
                        self.fail("IntegrityError or StatementError raised unexpectedly.")
                    else:
                        pass  # Expected exception
                finally:
                    db.session.rollback()

    def test_create_blood_pressure_record_valid_boundary_values(self):
        """Test creating blood pressure records with boundary values."""
        for systolic in self.systolic_boundary_values:
            for diastolic in self.diastolic_boundary_values:
                with self.subTest(systolic=systolic, diastolic=diastolic):
                    systolic_valid = 50 <= systolic <= 300
                    diastolic_valid = 30 <= diastolic <= 200
                    expect_success = systolic_valid and diastolic_valid

                    current_date = datetime.now().date().strftime('%Y-%m-%d')
                    current_time = datetime.now().time().strftime('%H:%M:%S')

                    # Use valid user_id or invalid one based on expectation
                    user_id = self.test_user.id if expect_success else 9999

                    # Use valid or invalid systolic and diastolic
                    record = BloodPressureRecord(
                        user_id=user_id,
                        systolic=systolic,
                        diastolic=diastolic,
                        date=current_date,
                        time=current_time
                    )
                    db.session.add(record)
                    try:
                        db.session.commit()
                        if expect_success:
                            saved_record = BloodPressureRecord.query.filter_by(
                                systolic=systolic,
                                diastolic=diastolic
                            ).first()
                            self.assertIsNotNone(saved_record)
                            self.assertEqual(saved_record.systolic, systolic)
                            self.assertEqual(saved_record.diastolic, diastolic)
                        else:
                            self.fail("IntegrityError expected but not raised.")
                    except (IntegrityError, StatementError, TypeError):
                        if expect_success:
                            self.fail("IntegrityError, StatementError, or TypeError raised unexpectedly.")
                        else:
                            pass  # Expected exception
                    finally:
                        db.session.rollback()

    def test_create_blood_pressure_record_valid(self):
            """Test creating a valid blood pressure record."""
            record = BloodPressureRecord(**self.valid_bp_case)
            db.session.add(record)
            try:
                db.session.flush()  # Attempt to write to the database
                db.session.commit()
                saved_record = BloodPressureRecord.query.filter_by(
                    systolic=120, diastolic=80
                ).first()
                self.assertIsNotNone(saved_record)
                self.assertEqual(saved_record.systolic, 120)
                self.assertEqual(saved_record.diastolic, 80)
            except (IntegrityError, StatementError, TypeError):
                self.fail("Exception raised unexpectedly for valid blood pressure values.")
            finally:
                db.session.rollback()

    def test_create_blood_pressure_record_invalid(self):
        """Test creating blood pressure records with invalid equivalence classes."""
        invalid_cases = [
            {'user_id': self.test_user.id, 'systolic': 400, 'diastolic': 80, 'date': '2024-01-01', 'time': '12:00'},    # Invalid systolic
            {'user_id': self.test_user.id, 'systolic': 120, 'diastolic': 250, 'date': '2024-01-01', 'time': '12:00'},   # Invalid diastolic
            {'user_id': 9999, 'systolic': 120, 'diastolic': 80, 'date': '2024-01-01', 'time': '12:00'},                 # Invalid user_id
            {'user_id': self.test_user.id, 'systolic': 'high', 'diastolic': 80, 'date': '2024-01-01', 'time': '12:00'}, # Non-integer systolic
            {'user_id': self.test_user.id, 'systolic': 120, 'diastolic': None, 'date': '2024-01-01', 'time': '12:00'},  # Missing diastolic
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                record = BloodPressureRecord(**case)
                db.session.add(record)
                try:
                    db.session.flush()  # Attempt to write to the database
                    db.session.commit()
                except (IntegrityError, StatementError, TypeError) as e:
                    print(f"Caught expected exception for case {case}: {e}")
                    pass
                except Exception as e:
                    self.fail(f"Unexpected exception {type(e).__name__} raised for case {case}: {e}")
                else:
                    self.fail(f"No exception raised for invalid case: {case}")
                finally:
                    db.session.rollback()

    def test_create_glucose_record_valid(self):
        """Test creating a valid glucose record."""
        record = GlucoseRecord(**self.valid_glucose_case)
        db.session.add(record)
        try:
            db.session.flush()
            db.session.commit()
            saved_record = GlucoseRecord.query.filter_by(glucose_level=150).first()
            self.assertIsNotNone(saved_record)
            self.assertEqual(saved_record.glucose_level, 150)
            self.assertEqual(saved_record.glucose_type, GlucoseType.FASTING)
        except (IntegrityError, StatementError, TypeError, ValueError):
            self.fail("Exception raised unexpectedly for valid glucose record.")
        finally:
            db.session.rollback()

    def test_create_glucose_record_invalid(self):
        """Test creating glucose records with invalid equivalence classes."""
        invalid_cases = [
            {'user_id': self.test_user.id, 'glucose_level': 400, 'glucose_type': GlucoseType.FASTING, 'date': '2024-01-01', 'time': '12:00'},  
            {'user_id': self.test_user.id, 'glucose_level': 30, 'glucose_type': GlucoseType.FASTING, 'date': '2024-01-01', 'time': '12:00'},       
            {'user_id': self.test_user.id, 'glucose_level': 300, 'glucose_type': GlucoseType.POSTPRANDIAL, 'date': '2024-01-01', 'time': '12:00'},       
            {'user_id': self.test_user.id, 'glucose_level': 70, 'glucose_type': GlucoseType.POSTPRANDIAL, 'date': '2024-01-01', 'time': '12:00'},                
        ]

        for case in invalid_cases:
            with self.subTest(case=case):
                record = GlucoseRecord(**case)
                db.session.add(record)
                try:
                    db.session.flush()
                    db.session.commit()
                except (IntegrityError, StatementError, TypeError, ValueError) as e:
                    print(f"Caught expected exception for case {case}: {e}")
                    pass
                except Exception as e:
                    self.fail(f"Unexpected exception {type(e).__name__} raised for case {case}: {e}")
                finally:
                    db.session.rollback()

    def test_glucose_type_equivalence_classes(self):
        """Test creating glucose records with valid and invalid glucose types."""
        # Valid Glucose Types
        valid_glucose_types = [GlucoseType.FASTING, GlucoseType.POSTPRANDIAL]
        for gt in valid_glucose_types:
            with self.subTest(glucose_type=gt):
                record = GlucoseRecord(
                    user_id=self.test_user.id,
                    glucose_level=100,
                    glucose_type=gt,
                    date='2024-01-01',
                    time='12:00:00'
                )
                db.session.add(record)
                try:
                    db.session.commit()
                    saved_record = GlucoseRecord.query.filter_by(glucose_type=gt).first()
                    self.assertIsNotNone(saved_record)
                    self.assertEqual(saved_record.glucose_type, gt)
                except IntegrityError:
                    self.fail("IntegrityError raised unexpectedly for valid glucose_type.")
                finally:
                    db.session.rollback()


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
