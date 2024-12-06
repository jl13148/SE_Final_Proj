# tests/unit/models/test_models.py
from datetime import datetime
from tests.base import BaseTestCase
from app.models import User, UserType, AccessLevel, CompanionAccess, Notification
from app.extensions import db

# tests/unit/models/test_models.py
from datetime import datetime
from tests.base import BaseTestCase
from app.models import User, UserType, AccessLevel, CompanionAccess, Notification

class TestUserModel(BaseTestCase):
    def test_user_companion_relationship(self):
        """Test user-companion relationship"""
        # Create companion user
        companion = User(
            username='companion',
            email='companion@test.com',
            user_type='COMPANION'
        )
        companion.set_password('password123')
        db.session.add(companion)
        db.session.commit()

        # Create companion access
        access = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=companion.id,
            medication_access=AccessLevel.VIEW.value,
            glucose_access=AccessLevel.VIEW.value,
            blood_pressure_access=AccessLevel.VIEW.value,
            export_access=False
        )
        db.session.add(access)
        db.session.commit()

        # Verify relationship using correct relationship names
        # Test patient's companions
        self.assertIn(access, self.test_user.companions)
        
        # Test companion's patients
        self.assertIn(access, companion.patients)

    def test_user_type_enum(self):
        """Test user type enum property"""
        # Test patient type
        patient = User(
            username='patient',
            email='patient@test.com',
            user_type=UserType.PATIENT.value
        )
        self.assertEqual(patient.user_type_enum, UserType.PATIENT)

        # Test companion type
        companion = User(
            username='companion',
            email='companion@test.com',
            user_type=UserType.COMPANION.value
        )
        self.assertEqual(companion.user_type_enum, UserType.COMPANION)

    def test_access_level_enums(self):
        """Test access level enum properties"""
        companion = User(
            username='companion',
            email='companion@test.com',
            user_type=UserType.COMPANION.value
        )
        db.session.add(companion)
        db.session.commit()

        access = CompanionAccess(
            patient_id=self.test_user.id,
            companion_id=companion.id,
            medication_access=AccessLevel.VIEW.value,
            glucose_access=AccessLevel.EDIT.value,
            blood_pressure_access=AccessLevel.NONE.value,
            export_access=False
        )
        db.session.add(access)
        db.session.commit()

        # Test enum properties
        self.assertEqual(access.medication_access_enum, AccessLevel.VIEW)
        self.assertEqual(access.glucose_access_enum, AccessLevel.EDIT)
        self.assertEqual(access.blood_pressure_access_enum, AccessLevel.NONE)

class TestNotificationModel(BaseTestCase):
    def test_create_notification(self):
        """Test notification creation and relationship"""
        notification = Notification(
            user_id=self.test_user.id,
            message='Test notification',
            is_read=False
        )
        db.session.add(notification)
        db.session.commit()

        # Test direct query
        saved_notification = Notification.query.filter_by(user_id=self.test_user.id).first()
        self.assertIsNotNone(saved_notification)
        self.assertEqual(saved_notification.message, 'Test notification')
        
        # Test relationship
        self.assertIn(notification, self.test_user.notifications)
        self.assertEqual(notification.user, self.test_user)

    def test_notification_repr(self):
        """Test notification string representation"""
        notification = Notification(
            user_id=self.test_user.id,
            message='Test notification'
        )
        expected_repr = f'<Notification Test notification to User {self.test_user.id}>'
        self.assertEqual(repr(notification), expected_repr)