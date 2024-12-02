from app.models import User, CompanionAccess, GlucoseRecord, BloodPressureRecord, Medication, Notification
from app.extensions import db
from sqlalchemy import or_
from flask_login import current_user


class CompanionService:
    def __init__(self, db):
        self.db = db
        self.companion_manager = CompanionManager(db)

    def link_patient(self, *args, **kwargs):
        return self.companion_manager.link_patient(*args, **kwargs)

    def get_companion_patients(self, *args, **kwargs):
        return self.companion_manager.get_companion_patients(*args, **kwargs)

    def get_pending_connections(self, *args, **kwargs):
        return self.companion_manager.get_pending_connections(*args, **kwargs)

    def get_patient_data(self, *args, **kwargs):
        return self.companion_manager.get_patient_data(*args, **kwargs)

    def get_notifications(self, *args, **kwargs):
        return self.companion_manager.get_notifications(*args, **kwargs)

    def mark_notification_read(self, *args, **kwargs):
        return self.companion_manager.mark_notification_read(*args, **kwargs)
    
    
class CompanionManager:
    def __init__(self, db):
        self.db = db

    def link_patient(self, companion_id, patient_email):
        try:
            patient = User.query.filter_by(email=patient_email, user_type='PATIENT').first()
            if not patient:
                return False, 'No patient account found with that email.'

            existing_link = CompanionAccess.query.filter_by(
                patient_id=patient.id,
                companion_id=companion_id
            ).first()

            if existing_link:
                return False, 'You are already linked with this patient.'

            link = CompanionAccess(
                patient_id=patient.id,
                companion_id=companion_id,
                medication_access='NONE',
                glucose_access='NONE',
                blood_pressure_access='NONE',
                export_access=False
            )

            self.db.session.add(link)
            self.db.session.commit()
            return True, 'Successfully linked with patient. Waiting for access approval.'
        except Exception as e:
            self.db.session.rollback()
            return False, 'An error occurred while linking with patient.'

    def get_companion_patients(self, companion_id):
        try:
            connections = CompanionAccess.query.filter(
                CompanionAccess.companion_id == companion_id,
                or_(
                    CompanionAccess.medication_access != "NONE",
                    CompanionAccess.glucose_access != "NONE",
                    CompanionAccess.blood_pressure_access != "NONE"
                )
            ).all()
            return True, connections
        except Exception as e:
            return False, []

    def get_pending_connections(self, companion_id):
        try:
            pending_connections = CompanionAccess.query.filter_by(
                companion_id=companion_id,
                medication_access="NONE",
                glucose_access="NONE",
                blood_pressure_access="NONE"
            ).all()
            return True, pending_connections
        except Exception as e:
            return False, []

    def get_patient_data(self, companion_id, patient_id):
        try:
            access = CompanionAccess.query.filter_by(
                patient_id=patient_id,
                companion_id=companion_id
            ).first_or_404()

            patient = User.query.get_or_404(patient_id)

            glucose_data = []
            if access.glucose_access != "NONE":
                glucose_data = GlucoseRecord.query.filter_by(user_id=patient_id).all()

            blood_pressure_data = []
            if access.blood_pressure_access != "NONE":
                blood_pressure_data = BloodPressureRecord.query.filter_by(user_id=patient_id).all()

            medication_data = []
            if access.medication_access != "NONE":
                medication_data = Medication.query.filter_by(user_id=patient_id).all()

            return True, '', patient, access, glucose_data, blood_pressure_data, medication_data
        except Exception as e:
            return False, 'An error occurred while retrieving patient data.', None, None, None, None, None

    def get_notifications(self, companion_id):
        try:
            notifications = Notification.query.filter_by(
                user_id=companion_id,
                is_read=False
            ).order_by(Notification.timestamp.desc()).all()
            return True, notifications
        except Exception as e:
            return False, []

    def mark_notification_read(self, companion_id, notification_id):
        try:
            notification = Notification.query.get_or_404(notification_id)
            if notification.user_id != companion_id:
                return False, 'Unauthorized action.'
            notification.is_read = True
            self.db.session.commit()
            return True, 'Notification marked as read.'
        except Exception as e:
            self.db.session.rollback()
            return False, 'An error occurred while updating the notification.'