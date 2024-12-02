# tests/unit/services/test_health_service.py
from unittest.mock import patch, MagicMock
from datetime import datetime
from tests.base import BaseTestCase
from app.services.health_service import HealthService
from app.extensions import db

class TestHealthService(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.health_service = HealthService(db)

    def test_add_glucose_record_success(self):
        """Test successfully adding a glucose record"""
        success, record, error = self.health_service.add_glucose_record(
            user_id=self.test_user.id,
            glucose_level=100,
            glucose_type='FASTING',
            date=datetime.now().date().strftime('%Y-%m-%d'),
            time=datetime.now().time().strftime('%H:%M')
        )

        self.assertTrue(success)
        self.assertIsNotNone(record)
        self.assertIsNone(error)

    def test_add_glucose_record_invalid_level(self):
        """Test adding glucose record with invalid level"""
        success, record, error = self.health_service.add_glucose_record(
            user_id=self.test_user.id,
            glucose_level=400,  # Invalid level
            glucose_type='FASTING',
            date=datetime.now().date().strftime('%Y-%m-%d'),
            time=datetime.now().time().strftime('%H:%M')
        )

        self.assertFalse(success)
        self.assertIsNone(record)
        self.assertIn('must be between', error)

    def test_add_blood_pressure_record_success(self):
        """Test successfully adding a blood pressure record"""
        success, record, error = self.health_service.add_blood_pressure_record(
            user_id=self.test_user.id,
            systolic=120,
            diastolic=80,
            date=datetime.now().date().strftime('%Y-%m-%d'),
            time=datetime.now().time().strftime('%H:%M')
        )

        self.assertTrue(success)
        self.assertIsNotNone(record)
        self.assertIsNone(error)

    def test_add_blood_pressure_record_invalid_values(self):
        """Test adding blood pressure record with invalid values"""
        success, record, error = self.health_service.add_blood_pressure_record(
            user_id=self.test_user.id,
            systolic=400,  # Invalid systolic
            diastolic=80,
            date=datetime.now().date().strftime('%Y-%m-%d'),
            time=datetime.now().time().strftime('%H:%M')
        )

        self.assertFalse(success)
        self.assertIsNone(record)
        self.assertIn('must be between', error)

    def test_get_glucose_records(self):
        """Test retrieving glucose records"""
        # Add a test record first
        self.health_service.add_glucose_record(
            user_id=self.test_user.id,
            glucose_level=100,
            glucose_type='FASTING',
            date=datetime.now().date().strftime('%Y-%m-%d'),
            time=datetime.now().time().strftime('%H:%M')
        )

        success, records, error = self.health_service.get_glucose_records(self.test_user.id)
        
        self.assertTrue(success)
        self.assertGreater(len(records), 0)
        self.assertIsNone(error)

    def test_get_blood_pressure_records(self):
        """Test retrieving blood pressure records"""
        # Add a test record first
        self.health_service.add_blood_pressure_record(
            user_id=self.test_user.id,
            systolic=120,
            diastolic=80,
            date=datetime.now().date().strftime('%Y-%m-%d'),
            time=datetime.now().time().strftime('%H:%M')
        )

        success, records, error = self.health_service.get_blood_pressure_records(self.test_user.id)
        
        self.assertTrue(success)
        self.assertGreater(len(records), 0)
        self.assertIsNone(error)