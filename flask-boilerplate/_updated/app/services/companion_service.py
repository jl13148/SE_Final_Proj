from typing import Optional, Tuple, List, Dict
from app.models import User, CompanionAccess, Notification

class CompanionService:
    def __init__(self, db):
        self.db = db

    def setup_companion_link(self, companion_id: int, patient_email: str) -> Tuple[bool, Optional[CompanionAccess], str]:
        try:
            patient = User.query.filter_by(email=patient_email, user_type='PATIENT').first()
            if not patient:
                return False, None, "Patient not found"
                
            existing_link = CompanionAccess.query.filter_by(
                patient_id=patient.id,
                companion_id=companion_id
            ).first()
            
            if existing_link:
                return False, None, "Link already exists"
                
            link = CompanionAccess(
                patient_id=patient.id,
                companion_id=companion_id,
                medication_access='NONE',
                glucose_access='NONE',
                blood_pressure_access='NONE'
            )
            
            self.db.session.add(link)
            self.db.session.commit()
            return True, link, None
        except Exception as e:
            self.db.session.rollback()
            return False, None, str(e)

    def get_patient_connections(self, companion_id: int) -> Tuple[bool, List[CompanionAccess], str]:
        try:
            connections = CompanionAccess.query.filter(
                CompanionAccess.companion_id == companion_id,
                self.db.or_(
                    CompanionAccess.medication_access != "NONE",
                    CompanionAccess.glucose_access != "NONE",
                    CompanionAccess.blood_pressure_access != "NONE"
                )
            ).all()
            return True, connections, None
        except Exception as e:
            return False, [], str(e)

    def get_notifications(self, companion_id: int) -> Tuple[bool, List[Notification], str]:
        try:
            notifications = Notification.query.filter_by(
                user_id=companion_id,
                is_read=False
            ).order_by(Notification.timestamp.desc()).all()
            return True, notifications, None
        except Exception as e:
            return False, [], str(e)

    def mark_notification_read(self, notification_id: int, user_id: int) -> Tuple[bool, None, str]:
        try:
            notification = Notification.query.get_or_404(notification_id)
            if notification.user_id != user_id:
                return False, None, "Unauthorized action"
            notification.is_read = True
            self.db.session.commit()
            return True, None, None
        except Exception as e:
            self.db.session.rollback()
            return False, None, str(e)