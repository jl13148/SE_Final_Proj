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

    def test_get_connections_no_connections(self):
        """Test getting patient's connections when none exist"""
        success, connections, error = self.connection_service.get_connections(self.test_user.id)
        
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(len(connections['active']), 0)
        self.assertEqual(len(connections['pending']), 0)

    def test_get_pending_connections(self):
        """Test getting pending connections for a user"""
        # Create a pending connection
        connection = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access=AccessLevel.NONE.value,
            glucose_access=AccessLevel.NONE.value,
            blood_pressure_access=AccessLevel.NONE.value
        )
        db.session.add(connection)
        db.session.commit()

        success, pending_connections, error = self.connection_service.get_pending_connections(self.companion.id)
        
        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(len(pending_connections), 1)

    def test_get_pending_connections_no_pending(self):
        """Test getting pending connections when there are no pending connections"""
        success, pending_connections, error = self.connection_service.get_pending_connections(self.companion.id)

        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(len(pending_connections), 0)

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

    def test_update_access_levels_unauthorized(self):
        """Test updating access levels with unauthorized access"""
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

        # Update access levels with wrong patient_id
        new_levels = {
            'medication': AccessLevel.VIEW.value,
            'glucose': AccessLevel.EDIT.value,
            'blood_pressure': AccessLevel.VIEW.value
        }

        success, updated_connection, error = self.connection_service.update_access_levels(
            connection.id, patient_id=-1, access_levels=new_levels  # Invalid patient_id
        )

        self.assertFalse(success)
        self.assertIsNone(updated_connection)
        self.assertEqual(error, "Unauthorized access")

    def test_update_access_levels_not_found(self):
        """Test updating access levels for a non-existent connection"""
        new_levels = {
            'medication': AccessLevel.VIEW.value,
            'glucose': AccessLevel.EDIT.value,
            'blood_pressure': AccessLevel.VIEW.value
        }

        success, updated_connection, error = self.connection_service.update_access_levels(
            connection_id=-1, patient_id=self.test_user.id, access_levels=new_levels  # Invalid connection_id
        )

        self.assertFalse(success)
        self.assertIsNone(updated_connection)
        self.assertIsNotNone(error)

    def test_remove_connection(self):
        """Test removing a connection"""
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

        # Remove the connection
        success, error = self.connection_service.remove_connection(connection.id, self.test_user.id)

        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertIsNone(CompanionAccess.query.get(connection.id))

    def test_remove_connection_unauthorized(self):
        """Test removing a connection with unauthorized access"""
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

        # Attempt to remove the connection with the wrong patient_id
        success, error = self.connection_service.remove_connection(connection.id, patient_id=-1)  # Invalid patient_id

        self.assertFalse(success)
        self.assertEqual(error, "Unauthorized access")
        self.assertIsNotNone(CompanionAccess.query.get(connection.id))

    def test_remove_connection_not_found(self):
        """Test removing a connection that does not exist"""
        success, error = self.connection_service.remove_connection(connection_id=-1, patient_id=self.test_user.id)  # Invalid connection_id

        self.assertFalse(success)
        self.assertIsNotNone(error)




    def test_update_access_levels_no_changes(self):
        """Test updating access levels with no changes"""
        # Create initial connection
        connection = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access=AccessLevel.VIEW.value,
            glucose_access=AccessLevel.VIEW.value,
            blood_pressure_access=AccessLevel.VIEW.value
        )
        db.session.add(connection)
        db.session.commit()

        # Update access levels with the same values
        new_levels = {
            'medication': AccessLevel.VIEW.value,
            'glucose': AccessLevel.VIEW.value,
            'blood_pressure': AccessLevel.VIEW.value
        }

        success, updated_connection, error = self.connection_service.update_access_levels(
            connection.id, self.test_user.id, new_levels
        )

        self.assertTrue(success)
        self.assertIsNone(error)
        self.assertEqual(updated_connection.medication_access, AccessLevel.VIEW.value)
        self.assertEqual(updated_connection.glucose_access, AccessLevel.VIEW.value)
        self.assertEqual(updated_connection.blood_pressure_access, AccessLevel.VIEW.value)

    def test_get_connections_exception(self):
        """Test exception handling in get_connections"""
        # Arrange
        # Patch 'CompanionAccess.query.filter_by' to raise an exception
        with patch('app.models.CompanionAccess.query') as mock_query:
            # Configure the mock to raise an exception when 'filter_by' is called
            mock_query.filter_by.side_effect = Exception('Database Error')

            # Act
            success, connections, error = self.connection_service.get_connections(self.test_user.id)

            # Assert
            self.assertFalse(success)
            self.assertIsNone(connections)
            self.assertEqual(error, 'Database Error')
    
    def test_pending_connections_exception(self):
        with patch('app.models.CompanionAccess.query') as mock_query:
            mock_query.filter_by.side_effect = Exception("Database error")
            success, pending_connections, error = self.connection_service.get_pending_connections(self.companion.id)
            self.assertFalse(success)
            self.assertEqual(pending_connections, [])
            self.assertTrue(error.startswith('Database error'))