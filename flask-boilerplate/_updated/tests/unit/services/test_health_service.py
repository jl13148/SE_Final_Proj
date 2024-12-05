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
from unittest.mock import patch, MagicMock

class TestHealthService(BaseTestCase):
    """Tests for the HealthService, GlucoseManager, and BloodPressureManager with BVA and Equivalence Class Partitioning."""
    def setUp(self):
        super().setUp()
        self.health_service = HealthService(db)
        
        # Create test users
        self.patient = self.create_test_user('patient@test.com', 'PATIENT')
        self.companion = self.create_test_user('companion@test.com', 'COMPANION')
        self.another_patient = self.create_test_user('another@test.com', 'PATIENT')
        
        # Create companion access
        self.companion_access = CompanionAccess(
            patient_id=self.patient.id,
            companion_id=self.companion.id,
            glucose_access='EDIT',
            blood_pressure_access='EDIT'
        )
        db.session.add(self.companion_access)
        db.session.commit()

        # Base timestamp for tests
        self.base_datetime = datetime.now()
        self.valid_date = self.base_datetime.strftime('%Y-%m-%d')
        self.valid_time = datetime.now().strftime('%H:%M')

        
        # Helper method to generate unique times for tests
        self.current_time_index = 0

    def get_unique_time(self):
        """Helper method to generate unique times for tests"""
        self.current_time_index += 1
        test_time = self.base_datetime + timedelta(minutes=self.current_time_index)
        return test_time.strftime('%H:%M')

    def test_get_glucose_records_success(self):
        """Test retrieving glucose records successfully."""
        # Create test records with unique times
        record1 = GlucoseRecord(
            user_id=self.patient.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        record2 = GlucoseRecord(
            user_id=self.patient.id,
            glucose_level=120,
            glucose_type=GlucoseType.POSTPRANDIAL,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        db.session.add_all([record1, record2])
        db.session.commit()

        success, records, error = self.health_service.get_glucose_records(self.patient.id)
        
        self.assertTrue(success)
        self.assertEqual(len(records), 2)
        self.assertIsNone(error)

    def test_add_glucose_record_with_notification(self):
        """Test adding a glucose record that triggers notifications."""
        # First add a valid record to ensure the method works
        result = self.health_service.add_glucose_record(
            user_id=self.patient.id,
            glucose_level=100,  # Normal value
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        
        if len(result) == 4:
            success, record, error, notifications = result
        else:
            success, record, error = result
            notifications = None  # Or set to a default value like []
        
        self.assertTrue(success)
        self.assertIsNotNone(record)
        self.assertIsNone(error)
        self.assertEqual(len(notifications), 0)  # No notifications for normal values
        
        # Now test the critical value
        result = self.health_service.add_glucose_record(
            user_id=self.patient.id,
            glucose_level=45,  # Critical low
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        
        if len(result) == 4:
            success, record, error, notifications = result
        else:
            success, record, error = result
            notifications = None  # Or set to a default value like []
        
        self.assertFalse(success)  # Should fail due to being below minimum
        self.assertIsNone(record)
        self.assertIn("between 50 and 350", error)
        self.assertIsNone(notifications)  # Adjust based on your method's behavior



    @patch('app.services.health_service.current_user')
    def test_update_glucose_record_success(self, mock_current_user):
        """Test updating a glucose record successfully."""
        # Set up mock with all required attributes
        mock_current_user.configure_mock(**{
            'user_type': 'COMPANION',
            'id': None  # Will be set to companion.id
        })
        mock_current_user.id = self.companion.id
        
        # Create initial record
        record = GlucoseRecord(
            user_id=self.patient.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        db.session.add(record)
        db.session.commit()
        
        success, error, notifications = self.health_service.update_glucose_record(
            record_id=record.id,
            user_id=self.companion.id,
            glucose_level=120,
            glucose_type=GlucoseType.POSTPRANDIAL,
            date=self.valid_date,
            time=record.time  # Use same time since it's an update
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        updated_record = GlucoseRecord.query.get(record.id)
        self.assertEqual(updated_record.glucose_level, 120)

    def test_delete_glucose_record_success(self):
        """Test deleting a glucose record successfully."""
        record = GlucoseRecord(
            user_id=self.patient.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.valid_time
        )
        db.session.add(record)
        db.session.commit()
        
        success, error = self.health_service.delete_glucose_record(record.id, self.patient.id)
        
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNone(GlucoseRecord.query.get(record.id))

    def test_add_glucose_record_valid_cases(self):
        """Test adding glucose records with valid data."""
        # Test normal reading
        success, record, error, messages = self.health_service.add_glucose_record(
            user_id=self.patient.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        self.assertTrue(success)
        self.assertIsNotNone(record)
        self.assertIsNone(error)
        self.assertEqual(len(messages), 0)  # Normal reading, no notifications

        # Test boundary values - minimum
        success, record, error, messages = self.health_service.add_glucose_record(
            user_id=self.patient.id,
            glucose_level=50,
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        self.assertTrue(success)
        self.assertIsNotNone(record)
        self.assertIsNone(error)

        # Test boundary values - maximum
        success, record, error, messages = self.health_service.add_glucose_record(
            user_id=self.patient.id,
            glucose_level=350,
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        self.assertTrue(success)
        self.assertIsNotNone(record)
        self.assertIsNone(error)

    def test_add_blood_pressure_record_invalid_cases(self):
        """Test adding blood pressure records with invalid data."""
        # Define test cases
        test_cases = [
            {'systolic': 49, 'diastolic': 80, 'error_field': 'Systolic'},
            {'systolic': 120, 'diastolic': 29, 'error_field': 'Diastolic'},
        ]

        for case in test_cases:
            with self.subTest(case=case):
                result = self.health_service.add_blood_pressure_record(
                    user_id=self.patient.id,
                    systolic=case['systolic'],
                    diastolic=case['diastolic'],
                    date=self.valid_date,
                    time=self.get_unique_time()
                )

                # Dynamically unpack based on the length of the result
                if len(result) == 4:
                    success, record, error, messages = result
                elif len(result) == 3:
                    success, record, error = result
                    messages = []
                else:
                    self.fail(f"Unexpected number of return values: {len(result)}")

                self.assertFalse(success)
                self.assertIsNone(record)
                self.assertIn(case['error_field'], error)
                self.assertEqual(messages, [])  # No messages expected on failure


    def test_add_blood_pressure_record_valid_cases(self):
        """Test adding blood pressure records with valid data."""
        # Test normal reading
        success, record, error, messages = self.health_service.add_blood_pressure_record(
            user_id=self.patient.id,
            systolic=120,
            diastolic=80,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        self.assertTrue(success)
        self.assertIsNotNone(record)
        self.assertIsNone(error)
        self.assertEqual(len(messages), 0)

        # Test boundary values
        success, record, error, messages = self.health_service.add_blood_pressure_record(
            user_id=self.patient.id,
            systolic=50,
            diastolic=30,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        self.assertTrue(success)
        self.assertIsNotNone(record)
        self.assertIsNone(error)

    def test_add_blood_pressure_record_invalid_cases(self):
        """Test adding blood pressure records with invalid data."""
        # Test invalid systolic
        result = self.health_service.add_blood_pressure_record(
            user_id=self.patient.id,
            systolic=49,  # Below minimum
            diastolic=80,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        
        if len(result) == 4:
            success, record, error, messages = result
        else:
            success, record, error = result
            messages = None  # Or set to a default value like []
        
        self.assertFalse(success)
        self.assertIsNone(record)
        self.assertIn("Systolic", error)
        self.assertIsNone(messages)  # Adjust based on your method's behavior

        # Test invalid diastolic
        result = self.health_service.add_blood_pressure_record(
            user_id=self.patient.id,
            systolic=120,
            diastolic=29,  # Below minimum
            date=self.valid_date,
            time=self.get_unique_time()
        )
        
        if len(result) == 4:
            success, record, error, messages = result
        else:
            success, record, error = result
            messages = None  # Or set to a default value like []
        
        self.assertFalse(success)
        self.assertIsNone(record)
        self.assertIn("Diastolic", error)
        self.assertIsNone(messages)  # Adjust based on your method's behavior

    def test_duplicate_prevention(self):
        """Test prevention of duplicate records."""
        test_time = self.get_unique_time()
        
        # Add initial record
        result = self.health_service.add_glucose_record(
            user_id=self.patient.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=test_time
        )
        
        if len(result) == 4:
            success, record, error, messages = result
        else:
            success, record, error = result
            messages = None  # Or set to a default value like []
        
        self.assertTrue(success)
        self.assertIsNotNone(record)
        
        # Try to add duplicate
        result = self.health_service.add_glucose_record(
            user_id=self.patient.id,
            glucose_level=110,
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=test_time
        )
        
        if len(result) == 4:
            success, record, error, messages = result
        else:
            success, record, error = result
            messages = None  # Or set to a default value like []
        
        self.assertFalse(success)
        self.assertIsNone(record)
        self.assertIn("already exists", error)
        self.assertIsNone(messages)  # Adjust based on your method's behavior

    @patch('app.services.health_service.current_user')
    def test_companion_access_permissions(self, mock_current_user):
        """Test companion access permissions for various operations."""
        # Set up mock user with proper attributes
        mock_user = MagicMock()
        mock_user.user_type = "COMPANION"
        mock_user.id = self.companion.id
        mock_current_user.return_value = mock_user

        # Create a glucose record as the patient
        record = GlucoseRecord(
            user_id=self.patient.id,
            glucose_level=100,
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        db.session.add(record)
        db.session.commit()

        # Test VIEW access - should not allow deletion
        self.companion_access.glucose_access = "VIEW"
        db.session.commit()

        result = self.health_service.delete_glucose_record(record.id, self.companion.id)
        
        if len(result) == 3:
            success, error, _ = result
        else:
            success, error = result
            _ = None  # Placeholder for the third value
        
        self.assertFalse(success)
        self.assertIn("permission", error)

        # Test EDIT access - should allow deletion
        self.companion_access.glucose_access = "EDIT"
        db.session.commit()

        result = self.health_service.delete_glucose_record(record.id, self.companion.id)
        
        if len(result) == 3:
            success, error, _ = result
        else:
            success, error = result
            _ = None  # Placeholder for the third value

        self.assertTrue(success)
        self.assertIsNone(error)


    def test_notification_thresholds(self):
        """Test notification generation for various health data thresholds."""
        # Test critical low glucose
        result = self.health_service.add_glucose_record(
            user_id=self.patient.id,
            glucose_level=45,  # Critical low
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        
        if len(result) == 4:
            success, record, error, messages = result
        else:
            success, record, error = result
            messages = None  # Or set to a default value like []
        
        self.assertFalse(success)  # Should fail due to being below minimum
        self.assertIsNone(record)
        self.assertIn("between 50 and 350", error)
        self.assertIsNone(messages)  # Adjust based on your method's behavior
        
        # Test high but valid glucose (should trigger notification)
        result = self.health_service.add_glucose_record(
            user_id=self.patient.id,
            glucose_level=200,  # High value
            glucose_type=GlucoseType.FASTING,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        
        if len(result) == 4:
            success, record, error, messages = result
        else:
            success, record, error = result
            messages = None  # Or set to a default value like []
        
        self.assertTrue(success)
        self.assertIsNotNone(record)
        self.assertIsNone(error)
        self.assertTrue(len(messages) > 0)
        self.assertIn("High", messages[0])


    def test_error_handling(self):
        """Test error handling for various scenarios."""
        # Test invalid record ID
        success, error = self.health_service.delete_glucose_record(999999, self.patient.id)
        self.assertFalse(success)
        
        # Test database errors
        with patch('app.extensions.db.session.commit') as mock_commit:
            mock_commit.side_effect = IntegrityError(None, None, None)
            success, _, error, _ = self.health_service.add_glucose_record(
                user_id=self.patient.id,
                glucose_level=100,
                glucose_type=GlucoseType.FASTING,
                date=self.valid_date,
                time=self.valid_time
            )
            self.assertFalse(success)
            self.assertIsNotNone(error)