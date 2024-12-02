# app/services/connection_service.py
from typing import Optional, Tuple, List, Dict
from app.models import CompanionAccess
from app.extensions import db

class ConnectionService:
    def __init__(self, db):
        self.db = db

    def get_pending_connections(self, user_id: int) -> Tuple[bool, List[CompanionAccess], str]:
        """Get all pending connections for a user"""
        try:
            pending_connections = CompanionAccess.query.filter_by(
                companion_id=user_id,
                medication_access="NONE",
                glucose_access="NONE",
                blood_pressure_access="NONE"
            ).all()
            return True, pending_connections, None
        except Exception as e:
            return False, [], str(e)

    def get_connections(self, patient_id: int) -> Tuple[bool, Dict, str]:
        """Get both pending and active connections for a patient"""
        try:
            pending_connections = CompanionAccess.query.filter_by(
                patient_id=patient_id,
                medication_access="NONE",
                glucose_access="NONE",
                blood_pressure_access="NONE"
            ).all()
            
            active_connections = CompanionAccess.query.filter(
                CompanionAccess.patient_id == patient_id,
                db.or_(
                    CompanionAccess.medication_access != "NONE",
                    CompanionAccess.glucose_access != "NONE",
                    CompanionAccess.blood_pressure_access != "NONE"
                )
            ).all()
            
            return True, {
                'pending': pending_connections,
                'active': active_connections
            }, None
        except Exception as e:
            return False, None, str(e)

    def update_access_levels(self, connection_id: int, patient_id: int, access_levels: Dict) -> Tuple[bool, Optional[CompanionAccess], str]:
        try:
            connection = CompanionAccess.query.get_or_404(connection_id)
            if connection.patient_id != patient_id:
                return False, None, "Unauthorized access"
                
            connection.medication_access = access_levels.get('medication', 'NONE')
            connection.glucose_access = access_levels.get('glucose', 'NONE')
            connection.blood_pressure_access = access_levels.get('blood_pressure', 'NONE')
            
            self.db.session.commit()
            return True, connection, None
        except Exception as e:
            self.db.session.rollback()
            return False, None, str(e)

    def remove_connection(self, connection_id: int, patient_id: int) -> Tuple[bool, None, str]:
        try:
            connection = CompanionAccess.query.get_or_404(connection_id)
            if connection.patient_id != patient_id:
                return False, None, "Unauthorized access"
            
            self.db.session.delete(connection)
            self.db.session.commit()
            return True, None, None
        except Exception as e:
            self.db.session.rollback()
            return False, None, str(e)