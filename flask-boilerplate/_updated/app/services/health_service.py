from app.models import GlucoseRecord, CompanionAccess, GlucoseType, User, BloodPressureRecord, Notification
from app.extensions import db
from flask_login import current_user

class HealthService:
    def __init__(self, db):
        self.db = db
        self.glucose_manager = GlucoseManager(db, self)
        self.blood_pressure_manager = BloodPressureManager(db, self)

    # Glucose methods
    def get_glucose_records(self, user_id):
        return self.glucose_manager.get_glucose_records(user_id)

    def add_glucose_record(self, user_id, glucose_level, glucose_type, date, time):
        return self.glucose_manager.add_glucose_record(user_id, glucose_level, glucose_type, date, time)

    def update_glucose_record(self, record_id, user_id, glucose_level, glucose_type, date, time):
        return self.glucose_manager.update_glucose_record(record_id, user_id, glucose_level, glucose_type, date, time)

    def delete_glucose_record(self, record_id, user_id):
        return self.glucose_manager.delete_glucose_record(record_id, user_id)

    # Blood Pressure methods
    def get_blood_pressure_records(self, user_id):
        return self.blood_pressure_manager.get_blood_pressure_records(user_id)

    def add_blood_pressure_record(self, user_id, systolic, diastolic, date, time):
        return self.blood_pressure_manager.add_blood_pressure_record(user_id, systolic, diastolic, date, time)

    def update_blood_pressure_record(self, record_id, user_id, systolic, diastolic, date, time):
        return self.blood_pressure_manager.update_blood_pressure_record(record_id, user_id, systolic, diastolic, date, time)

    def delete_blood_pressure_record(self, record_id, user_id):
        return self.blood_pressure_manager.delete_blood_pressure_record(record_id, user_id)
    
    def notify_companions(self, user_id, data_type, value):
        """
        Notify companion users when health data is in a risky range.
        """
        companions = CompanionAccess.query.filter_by(patient_id=user_id).all()
        thresholds = {
            'fasting_glucose': {
                'low': 70,
                'normal_max': 100,
                'high': 180,
                'severe_low': 54,
                'severe_high': 250
            },
            'postprandial_glucose': {
                'low': 90,
                'normal_max': 180,
                'high': 200,
                'severe_low': 54,
                'severe_high': 250
            },
            'blood_pressure': {
                'systolic': {
                    'low': 90,
                    'normal_max': 120,
                    'high': 140,
                    'severe_low': 70,
                    'severe_high': 180
                },
                'diastolic': {
                    'low': 60,
                    'normal_max': 80,
                    'high': 90,
                    'severe_low': 40,
                    'severe_high': 120
                }
            }
        }

        messages = []

        if data_type in ['fasting_glucose', 'postprandial_glucose']:
            glucose_level = value.get('glucose_level')
            if glucose_level is not None:
                gt = thresholds[data_type]
                reading_type = 'Fasting' if data_type == 'fasting_glucose' else 'Postprandial'

                if glucose_level < gt['severe_low']:
                    severity = 'Critical Low'
                    advice = 'Immediate medical attention recommended.'
                elif glucose_level < gt['low']:
                    severity = 'Low'
                    advice = 'Consider consuming fast-acting carbohydrates.'
                elif glucose_level > gt['severe_high']:
                    severity = 'Critical High'
                    advice = 'Immediate medical attention recommended.'
                elif glucose_level > gt['high']:
                    severity = 'High'
                    advice = 'Consult with healthcare provider.'
                else:
                    severity = None  # Normal readings don't need notifications

                if severity:
                    for companion in companions:
                        if companion.glucose_access == 'NONE':
                            continue
                        else:
                            message = (f"{reading_type} glucose level: {glucose_level} mg/dL - {severity}. {advice}")
                            messages.append(message)

        elif data_type == 'blood_pressure':
            systolic = value.get('systolic')
            diastolic = value.get('diastolic')
            if systolic is not None and diastolic is not None:
                st = thresholds['blood_pressure']['systolic']
                dt = thresholds['blood_pressure']['diastolic']

                bp_reading = f"{systolic}/{diastolic} mm Hg"

                # Determine severity for systolic
                if systolic < st['severe_low']:
                    sys_severity = 'Critical Low'
                elif systolic < st['low']:
                    sys_severity = 'Low'
                elif systolic > st['severe_high']:
                    sys_severity = 'Critical High'
                elif systolic > st['high']:
                    sys_severity = 'High'
                else:
                    sys_severity = None

                # Determine severity for diastolic
                if diastolic < dt['severe_low']:
                    dia_severity = 'Critical Low'
                elif diastolic < dt['low']:
                    dia_severity = 'Low'
                elif diastolic > dt['severe_high']:
                    dia_severity = 'Critical High'
                elif diastolic > dt['high']:
                    dia_severity = 'High'
                else:
                    dia_severity = None

                # Consolidate severity
                severities = set(filter(None, [sys_severity, dia_severity]))
                if severities:
                    for companion in companions:
                        if companion.blood_pressure_access == 'NONE':
                            continue
                        else:
                            severity = ', '.join(severities)
                            advice = 'Consult with healthcare provider.' if 'High' in severities or 'Low' in severities else 'Immediate medical attention recommended.'
                            message = (f"Blood pressure reading: {bp_reading} - {severity}. {advice}")
                            messages.append(message)

        # Send notifications if there are any messages
        if messages:
            full_message = ' '.join(messages)
            for companion in companions:
                companion_user = User.query.get(companion.companion_id)
                if companion_user:
                    notification = Notification(
                        user_id=companion_user.id,
                        message=full_message
                    )
                    self.db.session.add(notification)

            self.db.session.commit()
        
        return messages
    #------------------------------------------


class GlucoseManager:
    def __init__(self, db, health_service):
        self.db = db
        self.health_service = health_service

    def get_glucose_records(self, user_id):
        """
        Retrieve all glucose records for a user.
        """
        try:
            records = GlucoseRecord.query.filter_by(user_id=user_id).order_by(
                GlucoseRecord.date.desc(), GlucoseRecord.time.desc()
            ).all()
            return True, records, None
        except Exception as e:
            return False, None, str(e)

    def add_glucose_record(self, user_id, glucose_level, glucose_type, date, time):
        """
        Add a new glucose record.
        """
        try:
            # Validate glucose level boundaries
            MIN_GLUCOSE = 50
            MAX_GLUCOSE = 350

            if not (MIN_GLUCOSE <= glucose_level <= MAX_GLUCOSE):
                return False, None, f"Glucose level must be between {MIN_GLUCOSE} and {MAX_GLUCOSE} mg/dL."

            if self.is_duplicate_record(user_id, date, time):
                return False, None, "A glucose record for this date and time already exists."

            record = GlucoseRecord(
                user_id=user_id,
                glucose_level=glucose_level,
                glucose_type=glucose_type,
                date=date,
                time=time
            )

            value = {'glucose_level': glucose_level}
            data_type = 'fasting_glucose' if glucose_type == 'FASTING' else 'postprandial_glucose'
            msg = self.health_service.notify_companions(user_id, data_type, value)

            self.db.session.add(record)
            self.db.session.commit()
            return True, record, None, msg
        except Exception as e:
            self.db.session.rollback()
            return False, None, str(e), []

    def update_glucose_record(self, record_id, user_id, glucose_level, glucose_type, date, time):
        """
        Update an existing glucose record.
        """
        try:
            record = GlucoseRecord.query.get_or_404(record_id)

            if not self.has_permission(record, user_id):
                return False, "You do not have permission to edit this record."

            # Validate glucose level boundaries
            MIN_GLUCOSE = 50
            MAX_GLUCOSE = 350

            if not (MIN_GLUCOSE <= glucose_level <= MAX_GLUCOSE):
                return False, f"Glucose level must be between {MIN_GLUCOSE} and {MAX_GLUCOSE} mg/dL."

            if (date != record.date or time != record.time) and self.is_duplicate_record(user_id, date, time):
                return False, "A glucose record for this date and time already exists."

            # Update the record
            record.glucose_level = glucose_level
            record.glucose_type = glucose_type
            record.date = date
            record.time = time
            value = {'glucose_level': glucose_level}
            data_type = 'fasting_glucose' if glucose_type == GlucoseType.FASTING else 'postprandial_glucose'
            msg = self.health_service.notify_companions(user_id, data_type, value)
            self.db.session.commit()
            return True, None, msg
        except Exception as e:
            self.db.session.rollback()
            return False, str(e), []

    def delete_glucose_record(self, record_id, user_id):
        """
        Delete an existing glucose record.
        """
        try:
            record = GlucoseRecord.query.get_or_404(record_id)

            if not self.has_permission(record, user_id):
                return False, "You do not have permission to delete this record."

            self.db.session.delete(record)
            self.db.session.commit()
            return True, None
        except Exception as e:
            self.db.session.rollback()
            return False, str(e)

    def has_permission(self, record, user_id):
        """
        Check if the current user has permission to edit or delete the record.
        """
        if record.user_id == user_id:
            return True
        elif current_user.user_type == "COMPANION":
            # Check companion access
            access = CompanionAccess.query.filter_by(
                patient_id=record.user_id,
                companion_id=user_id,
            ).first()
            if access and access.glucose_access in ["EDIT", "VIEW"]:
                return True
        return False

    def is_duplicate_record(self, user_id, date_str, time_str):
        """
        Check if a record with the same date and time already exists for the user.
        """
        return GlucoseRecord.query.filter_by(user_id=user_id, date=date_str, time=time_str).first() is not None

class BloodPressureManager:
    def __init__(self, db, health_service):
        self.db = db
        self.health_service = health_service

    def get_blood_pressure_records(self, user_id):
        """
        Retrieve all blood pressure records for a user.
        """
        try:
            records = BloodPressureRecord.query.filter_by(user_id=user_id).order_by(
                BloodPressureRecord.date.desc(), BloodPressureRecord.time.desc()
            ).all()
            return True, records, None
        except Exception as e:
            return False, None, str(e)

    def add_blood_pressure_record(self, user_id, systolic, diastolic, date, time):
        """
        Add a new blood pressure record.
        """
        try:
            # Validate blood pressure values
            MIN_SYSTOLIC = 50
            MAX_SYSTOLIC = 300
            MIN_DIASTOLIC = 30
            MAX_DIASTOLIC = 200

            if not (MIN_SYSTOLIC <= systolic <= MAX_SYSTOLIC):
                return False, None, f"Systolic value must be between {MIN_SYSTOLIC} and {MAX_SYSTOLIC} mm Hg."
            if not (MIN_DIASTOLIC <= diastolic <= MAX_DIASTOLIC):
                return False, None, f"Diastolic value must be between {MIN_DIASTOLIC} and {MAX_DIASTOLIC} mm Hg."

            if self.is_duplicate_record(user_id, date, time):
                return False, None, "A blood pressure record for this date and time already exists."

            record = BloodPressureRecord(
                user_id=user_id,
                systolic=systolic,
                diastolic=diastolic,
                date=date,
                time=time
            )

            value = {'systolic': systolic, 'diastolic': diastolic}
            msg = self.health_service.notify_companions(user_id, 'blood_pressure', value)

            self.db.session.add(record)
            self.db.session.commit()
            return True, record, None, msg
        except Exception as e:
            self.db.session.rollback()
            return False, None, str(e), []

    def update_blood_pressure_record(self, record_id, user_id, systolic, diastolic, date, time):
        """
        Update an existing blood pressure record.
        """
        try:
            record = BloodPressureRecord.query.get_or_404(record_id)

            if not self.has_permission(record, user_id):
                return False, "You do not have permission to edit this record."

            # Validate blood pressure values
            MIN_SYSTOLIC = 50
            MAX_SYSTOLIC = 300
            MIN_DIASTOLIC = 30
            MAX_DIASTOLIC = 200

            if not (MIN_SYSTOLIC <= systolic <= MAX_SYSTOLIC):
                return False, f"Systolic value must be between {MIN_SYSTOLIC} and {MAX_SYSTOLIC} mm Hg."
            if not (MIN_DIASTOLIC <= diastolic <= MAX_DIASTOLIC):
                return False, f"Diastolic value must be between {MIN_DIASTOLIC} and {MAX_DIASTOLIC} mm Hg."

            if (date != record.date or time != record.time) and self.is_duplicate_record(user_id, date, time):
                return False, "A blood pressure record for this date and time already exists."

            # Update the record
            record.systolic = systolic
            record.diastolic = diastolic
            record.date = date
            record.time = time
            value = {'systolic': systolic, 'diastolic': diastolic}
            msg = self.health_service.notify_companions(user_id, 'blood_pressure', value)
            self.db.session.commit()
            return True, None, msg
        except Exception as e:
            self.db.session.rollback()
            return False, str(e), []

    def delete_blood_pressure_record(self, record_id, user_id):
        """
        Delete an existing blood pressure record.
        """
        try:
            record = BloodPressureRecord.query.get_or_404(record_id)

            if not self.has_permission(record, user_id):
                return False, "You do not have permission to delete this record."

            self.db.session.delete(record)
            self.db.session.commit()
            return True, None
        except Exception as e:
            self.db.session.rollback()
            return False, str(e)

    def has_permission(self, record, user_id):
        """
        Check if the current user has permission to edit or delete the record.
        """
        if record.user_id == user_id:
            return True
        elif current_user.user_type == "COMPANION":
            # Check companion access
            access = CompanionAccess.query.filter_by(
                patient_id=record.user_id,
                companion_id=user_id,
            ).first()
            if access and access.blood_pressure_access in ["EDIT", "VIEW"]:
                return True
        return False

    def is_duplicate_record(self, user_id, date_str, time_str):
        """
        Check if a record with the same date and time already exists for the user.
        """
        return BloodPressureRecord.query.filter_by(user_id=user_id, date=date_str, time=time_str).first() is not None