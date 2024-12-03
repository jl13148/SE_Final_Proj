from typing import Optional, Tuple, List, Dict
from datetime import datetime, time
from app.models import Medication, MedicationLog, CompanionAccess
from app.extensions import db

class MedicationManager:
    """
    Handles core medication operations - adding, editing, deleting medications
    Focuses on single medication operations
    """
    def __init__(self, db):
        self.db = db

    def get_medications(self, user_id: int) -> Tuple[bool, Optional[List[Dict]], Optional[str]]:
        """Get all medications with formatted time for display"""
        medications = Medication.query.filter_by(user_id=user_id).all()
        if medications is None:
            return True, [], None  # Return empty list instead of None
        
        # Format medications for template
        formatted_medications = []
        for med in medications:
            formatted_medications.append({
                'id': med.id,
                'name': med.name,
                'dosage': med.dosage,
                'frequency': med.frequency,
                'time': med.time
            })
        
        return True, formatted_medications, None

    def add_medication(self, user_id: int, name: str, dosage: str, frequency: str, time: time) -> Tuple[bool, Optional[str]]:
        try:
            medication = Medication(
                name=name,
                dosage=dosage,
                frequency=frequency,
                time=time,
                user_id=user_id
            )
            
            self.db.session.add(medication)
            self.db.session.commit()
            return True, None
        except Exception as e:
            self.db.session.rollback()
            return False, str(e)

    def delete_medication(self, medication_id: int, user_id: int) -> Tuple[bool, Optional[str]]:
        try:
            medication = Medication.query.get_or_404(medication_id)
            if medication.user_id != user_id:
                return False, "Unauthorized action"
                
            # Delete associated logs first
            MedicationLog.query.filter_by(medication_id=medication_id).delete()
            
            self.db.session.delete(medication)
            self.db.session.commit()
            return True, None
        except Exception as e:
            self.db.session.rollback()
            return False, str(e)

    def update_medication(self, medication_id: int, name: str, dosage: str, 
                         frequency: str, time: time) -> Tuple[bool, Optional[str]]:
        try:
            medication = Medication.query.get_or_404(medication_id)
            
            medication.name = name
            medication.dosage = dosage
            medication.frequency = frequency
            medication.time = time
            
            self.db.session.commit()
            return True, None
        except Exception as e:
            self.db.session.rollback()
            return False, str(e)

    def check_edit_permission(self, medication_id: int, user_id: int) -> Tuple[bool, Optional[Medication], Optional[str]]:
        try:
            medication = Medication.query.get_or_404(medication_id)
            
            if medication.user_id == user_id:
                return True, medication, None
                
            access = CompanionAccess.query.filter_by(
                patient_id=medication.user_id,
                companion_id=user_id
            ).first()
            
            if access and access.medication_access == "EDIT":
                return True, medication, None
                
            return False, None, "Unauthorized access"
        except Exception as e:
            return False, None, str(e)


class ScheduleManager:
    """
    Handles medication scheduling and reminder operations
    Focuses on time-based operations across multiple medications
    """
    def __init__(self, db):
        self.db = db

    def get_daily_medications(self, user_id: int) -> Tuple[bool, List[Dict], Optional[str]]:
        medications = Medication.query.filter_by(user_id=user_id).all()
        today = datetime.now().date()
        medication_list = []
        
        for med in medications:
            # Check if medication was taken today
            taken = MedicationLog.query.filter(
                MedicationLog.medication_id == med.id,
                MedicationLog.taken_at >= datetime.combine(today, datetime.min.time())
            ).first() is not None
            
            medication_list.append({
                'id': med.id,
                'name': med.name,
                'dosage': med.dosage,
                'time': med.time.strftime('%I:%M %p'),
                'taken': taken
            })
        
        return True, medication_list, None

    def get_upcoming_reminders(self, user_id: int, minutes_ahead: int = 15) -> Tuple[bool, List[Dict], Optional[str]]:
        now = datetime.now()
        today = now.date()
        medications = Medication.query.filter_by(user_id=user_id).all()
        upcoming_medications = []

        for med in medications:
            med_time = datetime.combine(today, med.time)
            time_diff = (med_time - now).total_seconds() / 60
            
            if 0 <= time_diff <= minutes_ahead:
                taken = MedicationLog.query.filter(
                    MedicationLog.medication_id == med.id,
                    MedicationLog.taken_at >= datetime.combine(today, datetime.min.time())
                ).first() is not None
                
                if not taken:
                    upcoming_medications.append({
                        'id': med.id,
                        'name': med.name,
                        'dosage': med.dosage,
                        'time': med.time.strftime('%I:%M %p')
                    })
        
        return True, upcoming_medications, None

    def log_medication_taken(self, medication_id: int, user_id: int) -> Tuple[bool, Optional[str]]:
        try:
            log = MedicationLog(
                medication_id=medication_id,
                user_id=user_id,
                taken_at=datetime.now()
            )
            
            self.db.session.add(log)
            self.db.session.commit()
            return True, None
        except Exception as e:
            self.db.session.rollback()
            return False, str(e)

class MedicationService:
    """
    Main service that coordinates between MedicationManager and ScheduleManager
    Provides a single interface for the controllers
    """
    def __init__(self, db):
        self.db = db
        self.medication_manager = MedicationManager(db)
        self.schedule_manager = ScheduleManager(db)

    # Delegate to MedicationManager
    def get_medications(self, user_id: int) -> Tuple[bool, Optional[List[Medication]], Optional[str]]:
        return self.medication_manager.get_medications(user_id)

    def add_medication(self, *args, **kwargs):
        return self.medication_manager.add_medication(*args, **kwargs)

    def delete_medication(self, *args, **kwargs):
        return self.medication_manager.delete_medication(*args, **kwargs)

    def update_medication(self, *args, **kwargs):
        return self.medication_manager.update_medication(*args, **kwargs)

    def check_edit_permission(self, *args, **kwargs):
        return self.medication_manager.check_edit_permission(*args, **kwargs)

    # Delegate to ScheduleManager
    def get_daily_medications(self, *args, **kwargs):
        return self.schedule_manager.get_daily_medications(*args, **kwargs)

    def get_upcoming_reminders(self, *args, **kwargs):
        return self.schedule_manager.get_upcoming_reminders(*args, **kwargs)

    def log_medication_taken(self, *args, **kwargs):
        return self.schedule_manager.log_medication_taken(*args, **kwargs)