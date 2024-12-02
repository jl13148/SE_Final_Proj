from unittest.mock import patch, MagicMock
from tests.base import BaseTestCase
from app.services.connection_service import ConnectionService
from app.models import User, CompanionAccess, AccessLevel
from app.extensions import db

class TestConnectionService(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.connection_service = ConnectionService(db)
        self.companion = User(
            username='companion',
            email='companion@test.com',
            user_type='COMPANION'
        )
        self.companion.set_password('password123')
        db.session.add(self.companion)
        db.session.commit()

    def test_get_connections(self):
        """Test getting patient's connections"""
        # Create a connection
        connection = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access=AccessLevel.VIEW.value,
            glucose_access=AccessLevel.VIEW.value,
            blood_pressure_access=AccessLevel.VIEW.value
        )
        db.session.add(connection)
        db.session.commit()

        success, connections, error = self.connection_service.get_connections(self.test_user.id)
        
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(len(connections['active']), 1)
        self.assertEqual(len(connections['pending']), 0)

    def test_update_access_levels(self):
        """Test updating access levels"""
        # Create initial connection
        connection = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access=AccessLevel.NONE.value,
            glucose_access=AccessLevel.NONE.value,
            blood_pressure_access=AccessLevel.NONE.value
        )
        db.session.add(connection)
        db.session.commit()

        # Update access levels
        new_levels = {
            'medication': AccessLevel.VIEW.value,
            'glucose': AccessLevel.EDIT.value,
            'blood_pressure': AccessLevel.VIEW.value
        }

        success, updated_connection, error = self.connection_service.update_access_levels(
            connection.id, self.test_user.id, new_levels
        )

        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(updated_connection.medication_access, AccessLevel.VIEW.value)
        self.assertEqual(updated_connection.glucose_access, AccessLevel.EDIT.value)
        self.assertEqual(updated_connection.blood_pressure_access, AccessLevel.VIEW.value)