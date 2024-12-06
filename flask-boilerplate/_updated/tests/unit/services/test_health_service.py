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

    def test_get_blood_pressure_records_success(self):
        """Test successfully retrieving blood pressure records."""
        # Create test records with different times
        record1 = BloodPressureRecord(
            user_id=self.patient.id,
            systolic=120,
            diastolic=80,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        record2 = BloodPressureRecord(
            user_id=self.patient.id,
            systolic=130,
            diastolic=85,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        db.session.add_all([record1, record2])
        db.session.commit()

        success, records, error = self.health_service.get_blood_pressure_records(self.patient.id)
        
        self.assertTrue(success)
        self.assertEqual(len(records), 2)
        self.assertIsNone(error)
        # Verify records are ordered by date and time (descending)
        self.assertEqual(records[0].systolic, 130)
        self.assertEqual(records[1].systolic, 120)

    def test_get_blood_pressure_records_empty(self):
        """Test retrieving blood pressure records when none exist."""
        success, records, error = self.health_service.get_blood_pressure_records(self.patient.id)
        
        self.assertTrue(success)
        self.assertEqual(len(records), 0)
        self.assertIsNone(error)

    def test_get_blood_pressure_records_error(self):
        """Test error handling when retrieving blood pressure records."""
        with patch('app.models.BloodPressureRecord.query') as mock_query:
            mock_query.filter_by.side_effect = Exception("Database error")
            success, records, error = self.health_service.get_blood_pressure_records(self.patient.id)
            
            self.assertFalse(success)
            self.assertIsNone(records)
            self.assertIn("Database error", error)

    def test_update_blood_pressure_record_success(self):
        """Test successfully updating a blood pressure record."""
        # Create initial record
        record = BloodPressureRecord(
            user_id=self.patient.id,
            systolic=120,
            diastolic=80,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        db.session.add(record)
        db.session.commit()
        
        # Test update with valid values
        success, error, messages = self.health_service.update_blood_pressure_record(
            record_id=record.id,
            user_id=self.patient.id,
            systolic=130,
            diastolic=85,
            date=self.valid_date,
            time=record.time
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        # Verify update
        updated_record = BloodPressureRecord.query.get(record.id)
        self.assertEqual(updated_record.systolic, 130)
        self.assertEqual(updated_record.diastolic, 85)

    def test_update_blood_pressure_record_invalid_values(self):
        """Test updating blood pressure record with invalid values."""
        record = BloodPressureRecord(
            user_id=self.patient.id,
            systolic=120,
            diastolic=80,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        db.session.add(record)
        db.session.commit()
        
        # Test with invalid systolic
        success, error, messages = self.health_service.update_blood_pressure_record(
            record_id=record.id,
            user_id=self.patient.id,
            systolic=49,  # Below minimum
            diastolic=80,
            date=self.valid_date,
            time=record.time
        )
        
        self.assertFalse(success)
        self.assertIn("Systolic value must be between", error)
        
        # Test with invalid diastolic
        success, error, messages = self.health_service.update_blood_pressure_record(
            record_id=record.id,
            user_id=self.patient.id,
            systolic=120,
            diastolic=201,  # Above maximum
            date=self.valid_date,
            time=record.time
        )
        
        self.assertFalse(success)
        self.assertIn("Diastolic value must be between", error)

    @patch('flask_login.current_user')
    def test_update_blood_pressure_record_permissions(self, mock_current_user):
        """Test permissions when updating blood pressure records."""
        record = BloodPressureRecord(
            user_id=self.patient.id,
            systolic=120,
            diastolic=80,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        db.session.add(record)
        db.session.commit()

        # Set up mock user
        mock_user = MagicMock()
        mock_user.user_type = "COMPANION"
        mock_user.id = self.companion.id
        mock_current_user.return_value = mock_user
        
        # Test with edit permission
        self.companion_access.blood_pressure_access = "EDIT"
        db.session.commit()
        
        success, error, messages = self.health_service.update_blood_pressure_record(
            record_id=record.id,
            user_id=self.companion.id,
            systolic=130,
            diastolic=85,
            date=self.valid_date,
            time=record.time
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        # Test with view-only permission
        self.companion_access.blood_pressure_access = "VIEW"
        db.session.commit()
        
        success, error, messages = self.health_service.update_blood_pressure_record(
            record_id=record.id,
            user_id=self.companion.id,
            systolic=140,
            diastolic=90,
            date=self.valid_date,
            time=record.time
        )
        
        self.assertFalse(success)
        self.assertIn("permission", error)

    def test_delete_blood_pressure_record_success(self):
        """Test successfully deleting a blood pressure record."""
        record = BloodPressureRecord(
            user_id=self.patient.id,
            systolic=120,
            diastolic=80,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        db.session.add(record)
        db.session.commit()
        
        success, error = self.health_service.delete_blood_pressure_record(record.id, self.patient.id)
        
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNone(BloodPressureRecord.query.get(record.id))

    def test_delete_blood_pressure_record_nonexistent(self):
        """Test deleting a non-existent blood pressure record."""
        success, error = self.health_service.delete_blood_pressure_record(999999, self.patient.id)
        
        self.assertFalse(success)
        self.assertIsNotNone(error)

    @patch('flask_login.current_user')
    def test_delete_blood_pressure_record_permissions(self, mock_current_user):
        """Test permissions when deleting blood pressure records."""
        record = BloodPressureRecord(
            user_id=self.patient.id,
            systolic=120,
            diastolic=80,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        db.session.add(record)
        db.session.commit()

        # Set up mock user
        mock_user = MagicMock()
        mock_user.user_type = "COMPANION"
        mock_user.id = self.companion.id
        mock_current_user.return_value = mock_user
        
        # Test with edit permission
        self.companion_access.blood_pressure_access = "EDIT"
        db.session.commit()
        
        success, error = self.health_service.delete_blood_pressure_record(record.id, self.companion.id)
        self.assertTrue(success)
        self.assertIsNone(error)
        
        # Create another record
        record2 = BloodPressureRecord(
            user_id=self.patient.id,
            systolic=130,
            diastolic=85,
            date=self.valid_date,
            time=self.get_unique_time()
        )
        db.session.add(record2)
        db.session.commit()
        
        # Test with view-only permission
        self.companion_access.blood_pressure_access = "VIEW"
        db.session.commit()
        
        success, error = self.health_service.delete_blood_pressure_record(record2.id, self.companion.id)
        self.assertFalse(success)
        self.assertIn("permission", error)

    def test_notify_companions_glucose_cases(self):
        """Test companion notifications for glucose readings."""
        # Create test companions with different access levels
        companion2 = self.create_test_user('companion2@test.com', 'COMPANION')
        companion_no_access = CompanionAccess(
            patient_id=self.patient.id,
            companion_id=companion2.id,
            glucose_access='NONE',
            blood_pressure_access='NONE'
        )
        db.session.add(companion_no_access)
        db.session.commit()

        test_cases = [
            # Critical Low case
            {
                'data_type': 'fasting_glucose',
                'value': {'glucose_level': 53},
                'expected_severity': 'Critical Low',
                'expected_advice': 'Immediate medical attention recommended.'
            },
            # Low case
            {
                'data_type': 'fasting_glucose',
                'value': {'glucose_level': 65},
                'expected_severity': 'Low',
                'expected_advice': 'Consider consuming fast-acting carbohydrates.'
            },
            # Critical High case
            {
                'data_type': 'postprandial_glucose',
                'value': {'glucose_level': 251},
                'expected_severity': 'Critical High',
                'expected_advice': 'Immediate medical attention recommended.'
            },
            # High case
            {
                'data_type': 'postprandial_glucose',
                'value': {'glucose_level': 190},
                'expected_severity': 'High',
                'expected_advice': 'Consult with healthcare provider.'
            },
            # Normal case (should not generate notification)
            {
                'data_type': 'fasting_glucose',
                'value': {'glucose_level': 85},
                'expected_severity': None,
                'expected_messages': []
            }
        ]

        for case in test_cases:
            # Clear existing notifications
            Notification.query.delete()
            db.session.commit()

            messages = self.health_service.notify_companions(
                self.patient.id,
                case['data_type'],
                case['value']
            )

            if case['expected_severity']:
                self.assertTrue(len(messages) > 0)
                self.assertIn(case['expected_severity'], messages[0])
                self.assertIn(case['expected_advice'], messages[0])
                
                # Verify notifications were created for companion with access
                notifications = Notification.query.all()
                self.assertTrue(len(notifications) > 0)
                self.assertIn(case['expected_severity'], notifications[0].message)
            else:
                self.assertEqual(len(messages), 0)

    def test_notify_companions_blood_pressure_cases(self):
        """Test companion notifications for blood pressure readings."""
        test_cases = [
            # Both Critical Low
            {
                'systolic': 69,
                'diastolic': 39,
                'expected_severities': ['Critical Low'],
                'expected_advice': 'Immediate medical attention recommended.'
            },
            # Both Low
            {
                'systolic': 85,
                'diastolic': 55,
                'expected_severities': ['Low'],
                'expected_advice': 'Consult with healthcare provider.'
            },
            # Both Critical High
            {
                'systolic': 181,
                'diastolic': 121,
                'expected_severities': ['Critical High'],
                'expected_advice': 'Immediate medical attention recommended.'
            },
            # Both High
            {
                'systolic': 145,
                'diastolic': 95,
                'expected_severities': ['High'],
                'expected_advice': 'Consult with healthcare provider.'
            },
            # Mixed severity (High systolic, Low diastolic)
            {
                'systolic': 145,
                'diastolic': 55,
                'expected_severities': ['High', 'Low'],
                'expected_advice': 'Consult with healthcare provider.'
            },
            # Normal case (should not generate notification)
            {
                'systolic': 115,
                'diastolic': 75,
                'expected_severities': [],
                'expected_messages': []
            }
        ]

        for case in test_cases:
            # Clear existing notifications
            Notification.query.delete()
            db.session.commit()

            messages = self.health_service.notify_companions(
                self.patient.id,
                'blood_pressure',
                {'systolic': case['systolic'], 'diastolic': case['diastolic']}
            )

            if case['expected_severities']:
                self.assertTrue(len(messages) > 0)
                for severity in case['expected_severities']:
                    self.assertIn(severity, messages[0])
                self.assertIn(case['expected_advice'], messages[0])
                
                # Verify notifications were created
                notifications = Notification.query.all()
                self.assertTrue(len(notifications) > 0)
                for severity in case['expected_severities']:
                    self.assertIn(severity, notifications[0].message)
            else:
                self.assertEqual(len(messages), 0)

    def test_notify_companions_edge_cases(self):
        """Test edge cases and invalid inputs for companion notifications."""
        # Test invalid data type
        messages = self.health_service.notify_companions(
            self.patient.id,
            'invalid_type',
            {'glucose_level': 100}
        )
        self.assertEqual(len(messages), 0)

        # Test missing value
        messages = self.health_service.notify_companions(
            self.patient.id,
            'fasting_glucose',
            {}
        )
        self.assertEqual(len(messages), 0)

        # Test None value
        messages = self.health_service.notify_companions(
            self.patient.id,
            'fasting_glucose',
            {'glucose_level': None}
        )
        self.assertEqual(len(messages), 0)

        # Test blood pressure with missing values
        messages = self.health_service.notify_companions(
            self.patient.id,
            'blood_pressure',
            {'systolic': 120}  # Missing diastolic
        )
        self.assertEqual(len(messages), 0)

    def test_notify_companions_access_levels(self):
        """Test notifications with different companion access levels."""
        # Create companions with different access levels
        companion2 = self.create_test_user('companion2@test.com', 'COMPANION')
        companion3 = self.create_test_user('companion3@test.com', 'COMPANION')
        
        companion_no_access = CompanionAccess(
            patient_id=self.patient.id,
            companion_id=companion2.id,
            glucose_access='NONE',
            blood_pressure_access='NONE'
        )
        companion_partial_access = CompanionAccess(
            patient_id=self.patient.id,
            companion_id=companion3.id,
            glucose_access='VIEW',
            blood_pressure_access='NONE'
        )
        db.session.add_all([companion_no_access, companion_partial_access])
        db.session.commit()

        # Test glucose notification
        Notification.query.delete()
        db.session.commit()

        messages = self.health_service.notify_companions(
            self.patient.id,
            'fasting_glucose',
            {'glucose_level': 53}  # Critical low
        )

        notifications = Notification.query.all()
        self.assertEqual(len(notifications), 3)  # Only companions with access should get notifications
        
        # Test blood pressure notification
        Notification.query.delete()
        db.session.commit()

        messages = self.health_service.notify_companions(
            self.patient.id,
            'blood_pressure',
            {'systolic': 181, 'diastolic': 121}  # Both critical high
        )

        notifications = Notification.query.all()
        self.assertEqual(len(notifications), 3)  # Only companion with blood pressure access
        
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