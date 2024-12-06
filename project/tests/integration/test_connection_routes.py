from unittest.mock import patch, MagicMock
from tests.base import BaseTestCase
from app.models import CompanionAccess, AccessLevel

class TestConnectionRoutes(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.companion = User(
            username='companion',
            email='companion@test.com',
            user_type='COMPANION'
        )
        self.companion.set_password('password123')
        self.db.session.add(self.companion)
        self.db.session.commit()

    def test_manage_connections_requires_patient(self):
        """Test only patients can manage connections"""
        self.login()  # Login as patient
        self.test_user.user_type = 'COMPANION'  # Change to companion
        
        response = self.client.get('/connections')
        
        self.assertEqual(response.status_code, 302)
        self.assertIn(b'Only patients can manage connections', response.data)

    def test_manage_connections_success(self):
        """Test successful connections management"""
        self.login()
        response = self.client.get('/connections')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Manage Connections', response.data)

    def test_approve_connection(self):
        """Test approving a connection request"""
        self.login()
        # Create pending connection
        connection = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access=AccessLevel.NONE.value,
            glucose_access=AccessLevel.NONE.value,
            blood_pressure_access=AccessLevel.NONE.value
        )
        self.db.session.add(connection)
        self.db.session.commit()

        response = self.client.post(f'/connections/{connection.id}/approve', follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Connection approved', response.data)

    def test_remove_connection(self):
        """Test removing a connection"""
        self.login()
        connection = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access=AccessLevel.VIEW.value,
            glucose_access=AccessLevel.VIEW.value,
            blood_pressure_access=AccessLevel.VIEW.value
        )
        self.db.session.add(connection)
        self.db.session.commit()

        response = self.client.post(f'/connections/{connection.id}/remove', follow_redirects=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Connection removed successfully', response.data)
        
        # Verify connection was deleted
        deleted_connection = CompanionAccess.query.get(connection.id)
        self.assertIsNone(deleted_connection)