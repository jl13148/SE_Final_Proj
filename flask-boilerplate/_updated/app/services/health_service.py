from app.models import GlucoseRecord, CompanionAccess, User, BloodPressureRecord, Notification
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

    def update_glucose_record(self, record_id, user_id, glucose_level, date, time):
        return self.glucose_manager.update_glucose_record(record_id, user_id, glucose_level, date, time)

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
        Notify companion users via email and in-app flash messages when the input health data is in the risky range.

        Args:
            user_id (int): ID of the patient.
            data_type (str): Type of health data ('fasting_glucose', 'postprandial_glucose', 'blood_pressure').
            value (dict): Dictionary containing relevant health metrics.
                        For 'fasting_glucose' and 'postprandial_glucose', expect {'glucose_level': int}.
                        For 'blood_pressure', expect {'systolic': int, 'diastolic': int}.
        """
        # Define medically accepted risky thresholds
        thresholds = {
            'fasting_glucose': {
                'valid_risky_low': 70,       # Hypoglycemia
                'valid_normal_max': 100,
                'valid_risky_high': 180,     # Risky high
                'severe_hypo': 54,           # Severe hypoglycemia
                'severe_hyper': 250          # Diabetic Ketoacidosis (DKA)
            },
            'postprandial_glucose': {
                'valid_risky_low': 70,       # Hypoglycemia
                'valid_normal_max': 180,
                'valid_risky_high': 200,     # Risky high
                'severe_hypo': 54,           # Severe hypoglycemia
                'severe_hyper': 250          # Diabetic Ketoacidosis (DKA)
            },
            'blood_pressure': {
                'systolic': {
                    'risky_hypotension': 90,
                    'risky_elevated': 140,
                    'risky_hypertension_max': 300,
                    'severe_hypo': 70,
                    'severe_hyper': 180
                },
                'diastolic': {
                    'risky_hypotension': 60,
                    'risky_elevated': 90,
                    'risky_hypertension_max': 200,
                    'severe_hypo': 40,
                    'severe_hyper': 120
                }
            }
        }

        is_risky = False
        messages = []

        if data_type in ['fasting_glucose', 'postprandial_glucose']:
            glucose = value.get('glucose_level')
            if glucose is not None:
                gt = thresholds[data_type]
                if data_type == 'fasting_glucose':
                    if data_type == 'fasting_glucose':
                        if glucose < gt['valid_risky_low']:
                            is_risky = True
                            messages.append(f"Fasting glucose level {glucose} mg/dL is in the hypoglycemia range.")
                    else:  # postprandial_glucose
                        if glucose < gt['valid_risky_low']:
                            is_risky = True
                            messages.append(f"Postprandial glucose level {glucose} mg/dL is in the hypoglycemia range.")
                
                if data_type == 'fasting_glucose' and gt['valid_normal_max'] < glucose <= gt['valid_risky_high']:
                    is_risky = True
                    messages.append(f"Fasting glucose level {glucose} mg/dL is in the risky high range.")
                elif data_type == 'postprandial_glucose' and gt['valid_normal_max'] < glucose <= gt['valid_risky_high']:
                    is_risky = True
                    messages.append(f"Postprandial glucose level {glucose} mg/dL is in the risky high range.")
                
                # Check for severe risk
                if glucose < gt['severe_hypo']:
                    is_risky = True
                    messages.append(f"Glucose level {glucose} mg/dL is in the severe hypoglycemia range.")
                elif glucose > gt['severe_hyper']:
                    is_risky = True
                    messages.append(f"Glucose level {glucose} mg/dL is in the severe hyperglycemia range (DKA).")

        elif data_type == 'blood_pressure':
            systolic = value.get('systolic')
            diastolic = value.get('diastolic')
            if systolic is not None and diastolic is not None:
                st = thresholds['blood_pressure']['systolic']
                dt = thresholds['blood_pressure']['diastolic']
                
                # Systolic checks
                if st['risky_hypotension'] <= systolic < st['risky_elevated']:
                    is_risky = True
                    messages.append(f"Systolic pressure {systolic} mm Hg is in the hypotension range.")
                elif st['risky_elevated'] < systolic <= st['risky_hypertension_max']:
                    is_risky = True
                    messages.append(f"Systolic pressure {systolic} mm Hg is in the hypertension range.")
                
                # Diastolic checks
                if dt['risky_hypotension'] <= diastolic < dt['risky_elevated']:
                    is_risky = True
                    messages.append(f"Diastolic pressure {diastolic} mm Hg is in the hypotension range.")
                elif dt['risky_elevated'] < diastolic <= dt['risky_hypertension_max']:
                    is_risky = True
                    messages.append(f"Diastolic pressure {diastolic} mm Hg is in the hypertension range.")
                
                # Severe risk conditions
                if systolic < st['severe_hypo'] and diastolic < dt['severe_hypo']:
                    is_risky = True
                    messages.append(f"Blood pressure reading {systolic}/{diastolic} mm Hg indicates shock.")
                elif systolic > st['severe_hyper'] or diastolic > dt['severe_hyper']:
                    is_risky = True
                    messages.append(f"Blood pressure reading {systolic}/{diastolic} mm Hg indicates crisis.")

        if is_risky and messages:
            print('risky data:', messages)
            message = " ".join(messages)
            # Fetch companions
            companions = CompanionAccess.query.filter_by(patient_id=user_id).all()
            for companion in companions:
                companion_user = User.query.get(companion.companion_id)
                if companion_user:
                    # In-App Notification: Store in the database
                    notification = Notification(
                        user_id=companion_user.id,
                        message=message
                    )
                    self.db.session.add(notification)

                    # Email Notification
                    # if companion_user.email:
                    #     try:
                    #         msg = Message(
                    #             subject="Health Alert Notification",
                    #             recipients=[companion_user.email],
                    #             body=f"Dear {companion_user.username},\n\n{message}\n\nBest regards,\nDiabetesEase Team"
                    #         )
                    #         mail.send(msg)
                    #     except Exception as e:
                    #         # Log the exception or handle it as needed
                    #         app.logger.error(f"Failed to send email to {companion_user.email}: {e}")

            self.db.session.commit()
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
            self.health_service.notify_companions(user_id, data_type, value)

            self.db.session.add(record)
            self.db.session.commit()
            return True, record, None
        except Exception as e:
            self.db.session.rollback()
            return False, None, str(e)

    def update_glucose_record(self, record_id, user_id, glucose_level, date, time):
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
            record.date = date
            record.time = time
            self.db.session.commit()
            return True, None
        except Exception as e:
            self.db.session.rollback()
            return False, str(e)

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
            self.health_service.notify_companions(user_id, 'blood_pressure', value)

            self.db.session.add(record)
            self.db.session.commit()
            return True, record, None
        except Exception as e:
            self.db.session.rollback()
            return False, None, str(e)

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
            self.db.session.commit()
            return True, None
        except Exception as e:
            self.db.session.rollback()
            return False, str(e)

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