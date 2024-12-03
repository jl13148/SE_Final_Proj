# tests/unit/services/test_companion_service.py

import unittest
from datetime import datetime, time
from unittest.mock import patch, MagicMock
from app.services.companion_service import CompanionService
from app.models import (
    User,
    CompanionAccess,
    GlucoseRecord,
    BloodPressureRecord,
    Medication,
    Notification
)
from app.extensions import db
from tests.base import BaseTestCase


class TestCompanionService(BaseTestCase):
    """Test suite for the CompanionService class."""

    def setUp(self):
        """Set up test environment."""
        super().setUp()
        self.companion_service = CompanionService(db)

    def create_companion_user(self, email: str) -> User:
        """Helper method to create a companion user."""
        return self.create_test_user(email, user_type='COMPANION')

    def create_patient_user(self, email: str) -> User:
        """Helper method to create a patient user."""
        return self.create_test_user(email, user_type='PATIENT')

    def test_link_patient_success(self):
        """Test successfully linking a companion to a patient."""
        # Create a companion user
        companion = self.create_companion_user('companion@test.com')

        # Create a patient user
        patient = self.create_patient_user('patient@test.com')

        # Attempt to link
        success, message = self.companion_service.link_patient(
            companion_id=companion.id,
            patient_email=patient.email
        )

        # Assertions
        self.assertTrue(success)
        self.assertEqual(message, 'Successfully linked with patient. Waiting for access approval.')

        # Verify the link exists in the database
        link = CompanionAccess.query.filter_by(
            patient_id=patient.id,
            companion_id=companion.id
        ).first()
        self.assertIsNotNone(link)
        self.assertEqual(link.medication_access, 'NONE')
        self.assertEqual(link.glucose_access, 'NONE')
        self.assertEqual(link.blood_pressure_access, 'NONE')
        self.assertFalse(link.export_access)

    def test_link_patient_no_patient_found(self):
        """Test linking a companion to a non-existent patient."""
        # Create a companion user
        companion = self.create_companion_user('companion2@test.com')

        # Attempt to link to a non-existent patient
        success, message = self.companion_service.link_patient(
            companion_id=companion.id,
            patient_email='nonexistent@test.com'
        )

        # Assertions
        self.assertFalse(success)
        self.assertEqual(message, 'No patient account found with that email.')

    def test_link_patient_already_linked(self):
        """Test linking a companion to a patient when already linked."""
        # Create a companion user
        companion = self.create_companion_user('companion3@test.com')

        # Create a patient user
        patient = self.create_patient_user('patient3@test.com')

        # First link
        success, message = self.companion_service.link_patient(
            companion_id=companion.id,
            patient_email=patient.email
        )
        self.assertTrue(success)

        # Attempt to link again
        success, message = self.companion_service.link_patient(
            companion_id=companion.id,
            patient_email=patient.email
        )
        self.assertFalse(success)
        self.assertEqual(message, 'You are already linked with this patient.')

    def test_get_companion_patients_success(self):
        """Test retrieving companion's patients with granted access."""
        # Create a companion user
        companion = self.create_companion_user('companion4@test.com')

        # Create patient users
        patient1 = self.create_patient_user('patient4a@test.com')
        patient2 = self.create_patient_user('patient4b@test.com')

        # Link companions with access
        link1 = CompanionAccess(
            patient_id=patient1.id,
            companion_id=companion.id,
            medication_access='VIEW',  
            glucose_access='EDIT',     
            blood_pressure_access='VIEW', 
            export_access=True
        )
        link2 = CompanionAccess(
            patient_id=patient2.id,
            companion_id=companion.id,
            medication_access='EDIT', 
            glucose_access='NONE',
            blood_pressure_access='EDIT', 
            export_access=False
        )
        db.session.add_all([link1, link2])
        db.session.commit()

        # Retrieve companion's patients
        success, connections = self.companion_service.get_companion_patients(companion_id=companion.id)

        # Assertions
        self.assertTrue(success)
        self.assertEqual(len(connections), 2)
        self.assertIn(link1, connections)
        self.assertIn(link2, connections)

    def test_get_companion_patients_no_access(self):
        """Test retrieving companion's patients when no access is granted."""
        # Create a companion user
        companion = self.create_companion_user('companion5@test.com')

        # Create a patient user without access
        patient = self.create_patient_user('patient5@test.com')

        # Link companion with no access
        link = CompanionAccess(
            patient_id=patient.id,
            companion_id=companion.id,
            medication_access='NONE',
            glucose_access='NONE',
            blood_pressure_access='NONE',
            export_access=False
        )
        db.session.add(link)
        db.session.commit()

        # Retrieve companion's patients
        success, connections = self.companion_service.get_companion_patients(companion_id=companion.id)

        # Assertions
        self.assertTrue(success)
        self.assertEqual(len(connections), 0)  # No patients should be returned

    def test_get_pending_connections_success(self):
        """Test retrieving pending connection requests for a companion."""
        # Create a companion user
        companion = self.create_companion_user('companion7@test.com')

        # Create patient users
        patient1 = self.create_patient_user('patient7a@test.com')
        patient2 = self.create_patient_user('patient7b@test.com')

        # Link companions without granting access (pending)
        link1 = CompanionAccess(
            patient_id=patient1.id,
            companion_id=companion.id,
            medication_access='NONE',
            glucose_access='NONE',
            blood_pressure_access='NONE',
            export_access=False
        )
        link2 = CompanionAccess(
            patient_id=patient2.id,
            companion_id=companion.id,
            medication_access='NONE',
            glucose_access='NONE',
            blood_pressure_access='NONE',
            export_access=False
        )
        db.session.add_all([link1, link2])
        db.session.commit()

        # Retrieve pending connections
        success, pending_connections = self.companion_service.get_pending_connections(companion_id=companion.id)

        # Assertions
        self.assertTrue(success)
        self.assertEqual(len(pending_connections), 2)
        self.assertIn(link1, pending_connections)
        self.assertIn(link2, pending_connections)

    def test_get_patient_data_success(self):
        """Test retrieving patient data with granted access."""
        # Create a companion user
        companion = self.create_companion_user('companion9@test.com')

        # Create a patient user
        patient = self.create_patient_user('patient9@test.com')

        # Link companion with access
        link = CompanionAccess(
            patient_id=patient.id,
            companion_id=companion.id,
            medication_access='VIEW', 
            glucose_access='EDIT',    
            blood_pressure_access='VIEW', 
            export_access=True
        )
        db.session.add(link)
        db.session.commit()

        # Add patient data with correct data types
        glucose_record = GlucoseRecord(
            user_id=patient.id,
            date='2024-12-03',  # String in 'YYYY-MM-DD'
            time='14:44',        # String in 'HH:MM'
            glucose_level=110,
            glucose_type='FASTING'
        )
        blood_pressure_record = BloodPressureRecord(
            user_id=patient.id,
            date='2024-12-03',  # String in 'YYYY-MM-DD'
            time='14:44',        # String in 'HH:MM'
            systolic=130,
            diastolic=85
        )
        medication = Medication(
            user_id=patient.id,
            name='Med9',
            dosage='200mg',
            frequency='twice_daily',
            time=time(8, 0)  # datetime.time is acceptable for db.Time
        )
        db.session.add_all([glucose_record, blood_pressure_record, medication])
        db.session.commit()

        # Retrieve patient data
        success, message, retrieved_patient, retrieved_access, glucose_data, bp_data, medication_data = self.companion_service.get_patient_data(
            companion_id=companion.id,
            patient_id=patient.id
        )

        # Assertions
        self.assertTrue(success)
        self.assertEqual(message, '')
        self.assertEqual(retrieved_patient, patient)
        self.assertEqual(retrieved_access, link)
        self.assertEqual(len(glucose_data), 1)
        self.assertEqual(glucose_data[0], glucose_record)
        self.assertEqual(len(bp_data), 1)
        self.assertEqual(bp_data[0], blood_pressure_record)
        self.assertEqual(len(medication_data), 1)
        self.assertEqual(medication_data[0], medication)

    def test_get_patient_data_no_access(self):
        """Test retrieving patient data without granted access."""
        # Create a companion user
        companion = self.create_companion_user('companion10@test.com')

        # Create a patient user
        patient = self.create_patient_user('patient10@test.com')

        # Link companion with no access
        link = CompanionAccess(
            patient_id=patient.id,
            companion_id=companion.id,
            medication_access='NONE',
            glucose_access='NONE',
            blood_pressure_access='NONE',
            export_access=False
        )
        db.session.add(link)
        db.session.commit()

        # Attempt to retrieve patient data
        success, message, retrieved_patient, retrieved_access, glucose_data, bp_data, medication_data = self.companion_service.get_patient_data(
            companion_id=companion.id,
            patient_id=patient.id
        )

        # Since access levels are 'NONE', data lists should be empty, but success should still be True
        self.assertTrue(success)
        self.assertEqual(message, '')
        self.assertEqual(retrieved_patient, patient)
        self.assertEqual(retrieved_access, link)
        self.assertEqual(len(glucose_data), 0)
        self.assertEqual(len(bp_data), 0)
        self.assertEqual(len(medication_data), 0)

    def test_get_notifications_success(self):
        """Test retrieving unread notifications for a companion."""
        # Create a companion user
        companion = self.create_companion_user('companion15@test.com')

        # Create notifications
        notification1 = Notification(
            user_id=companion.id,
            message='Notification 1',
            is_read=False,
            timestamp=datetime.now()
        )
        notification2 = Notification(
            user_id=companion.id,
            message='Notification 2',
            is_read=False,
            timestamp=datetime.now()
        )
        notification3 = Notification(
            user_id=companion.id,
            message='Notification 3',
            is_read=True,
            timestamp=datetime.now()
        )
        db.session.add_all([notification1, notification2, notification3])
        db.session.commit()

        # Retrieve notifications
        success, notifications = self.companion_service.get_notifications(companion_id=companion.id)

        # Assertions
        self.assertTrue(success)
        self.assertEqual(len(notifications), 2)
        self.assertIn(notification1, notifications)
        self.assertIn(notification2, notifications)
        self.assertNotIn(notification3, notifications)

    def test_mark_notification_read_success(self):
        """Test successfully marking a notification as read."""
        # Create a companion user
        companion = self.create_companion_user('companion16@test.com')

        # Create a notification
        notification = Notification(
            user_id=companion.id,
            message='Notification to be read',
            is_read=False,
            timestamp=datetime.now()
        )
        db.session.add(notification)
        db.session.commit()

        # Mark as read
        success, message = self.companion_service.mark_notification_read(
            companion_id=companion.id,
            notification_id=notification.id
        )

        # Assertions
        self.assertTrue(success)
        self.assertEqual(message, 'Notification marked as read.')

        # Verify the notification is marked as read
        updated_notification = Notification.query.get(notification.id)
        self.assertTrue(updated_notification.is_read)

    def test_mark_notification_read_unauthorized(self):
        """Test marking another user's notification as read (unauthorized)."""
        # Create two companion users
        companion1 = self.create_companion_user('companion17a@test.com')
        companion2 = self.create_companion_user('companion17b@test.com')

        # Create a notification for companion1
        notification = Notification(
            user_id=companion1.id,
            message='Companion1 Notification',
            is_read=False,
            timestamp=datetime.now()
        )
        db.session.add(notification)
        db.session.commit()

        # Attempt to mark companion1's notification as read using companion2
        success, message = self.companion_service.mark_notification_read(
            companion_id=companion2.id,
            notification_id=notification.id
        )

        # Assertions
        self.assertFalse(success)
        self.assertEqual(message, 'Unauthorized action.')

        # Verify the notification is still unread
        updated_notification = Notification.query.get(notification.id)
        self.assertFalse(updated_notification.is_read)

    @patch('app.services.companion_service.Notification.query.filter_by')
    def test_get_notifications_no_unread(self, mock_filter_by):
        """Test retrieving notifications when there are no unread notifications."""
        # Create a companion user
        companion = self.create_companion_user('companion18@test.com')

        # Create read notifications
        notification1 = Notification(
            user_id=companion.id,
            message='Read Notification 1',
            is_read=True,
            timestamp=datetime.now()
        )
        notification2 = Notification(
            user_id=companion.id,
            message='Read Notification 2',
            is_read=True,
            timestamp=datetime.now()
        )
        db.session.add_all([notification1, notification2])
        db.session.commit()

        # Configure the mock to return no unread notifications
        mock_filter_by.return_value.order_by.return_value.all.return_value = []

        # Retrieve notifications
        success, notifications = self.companion_service.get_notifications(companion_id=companion.id)

        # Assertions
        self.assertTrue(success)
        self.assertEqual(len(notifications), 0)

if __name__ == '__main__':
    unittest.main()
