from datetime import datetime
from tests.base import BaseTestCase
from app.models import User, CompanionAccess, AccessLevel
from sqlalchemy.exc import IntegrityError
from app.extensions import db

class TestConnectionModel(BaseTestCase):
    def setUp(self):
        super().setUp()
        # Create a companion user for testing
        self.companion = User(
            username='companion',
            email='companion@test.com',
            user_type='COMPANION'
        )
        self.companion.set_password('password123')
        db.session.add(self.companion)
        db.session.commit()

    def test_create_connection(self):
        """Test creating a companion connection"""
        connection = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access=AccessLevel.VIEW.value,
            glucose_access=AccessLevel.VIEW.value,
            blood_pressure_access=AccessLevel.VIEW.value,
            export_access=False
        )
        db.session.add(connection)
        db.session.commit()

        saved_connection = CompanionAccess.query.filter_by(
            patient_id=self.test_user.id,
            companion_id=self.companion.id
        ).first()
        self.assertIsNotNone(saved_connection)
        self.assertEqual(saved_connection.medication_access, AccessLevel.VIEW.value)

    def test_unique_connection_constraint(self):
        """Test that duplicate connections are prevented"""
        connection1 = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access=AccessLevel.VIEW.value,
            glucose_access=AccessLevel.VIEW.value,
            blood_pressure_access=AccessLevel.VIEW.value
        )
        db.session.add(connection1)
        db.session.commit()

        # Try to create duplicate connection
        connection2 = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=self.companion.id,
            medication_access=AccessLevel.EDIT.value,
            glucose_access=AccessLevel.EDIT.value,
            blood_pressure_access=AccessLevel.EDIT.value
        )
        with self.assertRaises(IntegrityError):
            db.session.add(connection2)
            db.session.commit()
        db.session.rollback()