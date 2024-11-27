from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_required, current_user
from app.forms import ExportPDFForm, ExportCSVForm
from app.models import GlucoseRecord, BloodPressureRecord, GlucoseType, CompanionAccess, Notification, User
from app.extensions import db


#-----------Helper functions----------------
def is_duplicate_record(model, user_id, date_str, time_str):
    return model.query.filter_by(user_id=user_id, date=date_str, time=time_str).first() is not None

def notify_companions(user_id, data_type, value):
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
            'valid_normal_max': 99,
            'valid_risky_high': 180,     # Risky high
            'severe_hypo': 54,           # Severe hypoglycemia
            'severe_hyper': 250          # Diabetic Ketoacidosis (DKA)
        },
        'postprandial_glucose': {
            'valid_risky_low': 70,       # Hypoglycemia
            'valid_normal_max': 140,
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
                db.session.add(notification)

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

        db.session.commit()
#------------------------------------------

health = Blueprint('health', __name__)

@health.route('/health-logger')
@login_required
def health_logger():
    return render_template('pages/health_logger.html')

@health.route('/health-logger/glucose/')
@login_required
# @check_companion_access('glucose')
def glucose_logger():
    return render_template('pages/glucose_logger.html')

@health.route('/health-logger/blood_pressure')
@login_required
# @check_companion_access('blood_pressure')
def blood_pressure_logger():
    return render_template('pages/blood_pressure_logger.html')

@health.route('/glucose', methods=['GET', 'POST'])
@login_required
def record_glucose():
    if request.method == 'POST':
        try:
            glucose_level = int(request.form['glucose_level'])
            glucose_type = request.form['glucose_type']
            if glucose_type not in [gt.value for gt in GlucoseType]:
                flash('Invalid glucose type selected.', 'danger')
                return render_template('pages/glucose_logger.html')
        except (ValueError, KeyError):
            flash('Invalid input.', 'danger')
            return render_template('pages/glucose_logger.html')
        
        MIN_GLUCOSE = 50
        MAX_GLUCOSE = 350

        if not (MIN_GLUCOSE <= glucose_level <= MAX_GLUCOSE):
            flash(f'Glucose level must be between {MIN_GLUCOSE} and {MAX_GLUCOSE} mg/dL.', 'danger')
            return render_template('pages/glucose_logger.html')
        
        date_str = request.form['date']
        time_str = request.form['time']

        if is_duplicate_record(GlucoseRecord, current_user.id, date_str, time_str):
            flash('A glucose record for this date and time already exists.', 'warning')
            return render_template('pages/glucose_logger.html')

        new_record = GlucoseRecord(
            glucose_level=glucose_level,
            glucose_type=GlucoseType(glucose_type),
            date=date_str,
            time=time_str,
            user_id=current_user.id
        )

        db.session.add(new_record)
        db.session.commit()

        data_type = 'fasting_glucose' if glucose_type == "FASTING" else 'postprandial_glucose'
        value = {'glucose_level': glucose_level}
        notify_companions(current_user.id, data_type, value)

        flash('Glucose data logged successfully!', 'success')
        return redirect(url_for('health.glucose_logger'))

    return render_template('pages/glucose_logger.html')

@health.route('/blood_pressure', methods=['GET', 'POST'])
@login_required
def record_blood_pressure():
    if request.method == 'POST':
        try:
            systolic = int(request.form['systolic'])
            diastolic = int(request.form['diastolic'])
        except ValueError:
            flash('Systolic and Diastolic values must be integers.', 'danger')
            return render_template('pages/blood_pressure_logger.html')

        # Valid ranges
        MIN_SYSTOLIC = 50
        MAX_SYSTOLIC = 300
        MIN_DIASTOLIC = 30
        MAX_DIASTOLIC = 200

        if not (MIN_SYSTOLIC <= systolic <= MAX_SYSTOLIC):
            flash(f'Systolic value must be between {MIN_SYSTOLIC} and {MAX_SYSTOLIC} mm Hg.', 'danger')
            return render_template('pages/blood_pressure_logger.html')

        if not (MIN_DIASTOLIC <= diastolic <= MAX_DIASTOLIC):
            flash(f'Diastolic value must be between {MIN_DIASTOLIC} and {MAX_DIASTOLIC} mm Hg.', 'danger')
            return render_template('pages/blood_pressure_logger.html')

        date_str = request.form['date']
        time_str = request.form['time']

        if is_duplicate_record(BloodPressureRecord, current_user.id, date_str, time_str):
            flash('A blood pressure record for this date and time already exists.', 'warning')
            return render_template('pages/blood_pressure_logger.html')
        # Create a new BloodPressureRecord
        new_record = BloodPressureRecord(
            systolic=systolic,
            diastolic=diastolic,
            date=date_str,
            time=time_str,
            user_id=current_user.id
        )

        # Add and commit the new record
        db.session.add(new_record)
        db.session.commit()

        # Notify companions if the data is in the risky range
        value = {'systolic': systolic, 'diastolic': diastolic}
        notify_companions(current_user.id, 'blood_pressure', value)

        flash('Blood pressure data logged successfully!', 'success')
        return redirect(url_for('health.blood_pressure_logger'))

    return render_template('pages/blood_pressure_logger.html')


@health.route('/glucose/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_glucose_record(id):
    """
    Edit an existing glucose record.
    """
    record = GlucoseRecord.query.get_or_404(id)

    # Check permissions (either owner or authorized companion)
    has_permission = False
    if record.user_id == current_user.id:
        has_permission = True
    elif current_user.user_type == "COMPANION":
        # Check companion access
        access = CompanionAccess.query.filter_by(
            patient_id=record.user_id,
            companion_id=current_user.id,
        ).first()
        if access and access.glucose_access == "EDIT":
            has_permission = True

    if not has_permission:
        flash("You do not have permission to edit this record.", 'danger')
        return redirect(url_for('health.glucose_logger'))

    if request.method == 'POST':
        try:
            new_glucose_level = int(request.form['glucose_level'])
        except ValueError:
            flash('Glucose level must be an integer.', 'danger')
            return render_template('pages/edit_glucose_record.html', record=record)
        
        # Validate glucose level boundaries
        MIN_GLUCOSE = 70
        MAX_GLUCOSE = 180

        if not (MIN_GLUCOSE <= new_glucose_level <= MAX_GLUCOSE):
            flash(f'Glucose level must be between {MIN_GLUCOSE} and {MAX_GLUCOSE} mg/dL.', 'danger')
            return render_template('pages/edit_glucose_record.html', record=record)

        date_str = request.form['date']
        time_str = request.form['time']

        # Check for duplicate record
        if (date_str != record.date or time_str != record.time) and is_duplicate_record(GlucoseRecord, record.user_id, date_str, time_str):
            flash('A glucose record for this date and time already exists.', 'warning')
            return render_template('pages/edit_glucose_record.html', record=record)

        # Update the record
        record.glucose_level = new_glucose_level
        record.date = date_str
        record.time = time_str

        try:
            db.session.commit()
            flash('Glucose record updated successfully!', 'success')
            # Redirect to appropriate view based on user type
            if current_user.user_type == "COMPANION":
                return redirect(url_for('connection.view_patient_data', patient_id=record.user_id))
            return redirect(url_for('health.glucose_logger'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating glucose record: {str(e)}', 'danger')
            return render_template('pages/edit_glucose_record.html', record=record)

    return render_template('pages/edit_glucose_record.html', record=record)

@health.route('/blood_pressure_records')
@login_required
def blood_pressure_records():
    records = BloodPressureRecord.query.filter_by(user_id=current_user.id).order_by(
        BloodPressureRecord.date.desc(), BloodPressureRecord.time.desc()).all()
    return render_template('pages/blood_pressure_records.html', records=records)

@health.route('/glucose_records')
@login_required
def glucose_records():
    records = GlucoseRecord.query.filter_by(user_id=current_user.id).order_by(
        GlucoseRecord.date.desc(), GlucoseRecord.time.desc()).all()
    return render_template('pages/glucose_records.html', records=records)

@health.route('/glucose_records/delete/<int:id>', methods=['POST'])
@login_required
def delete_glucose_record(id):
    record = GlucoseRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('health.glucose_records'))
    db.session.delete(record)
    db.session.commit()
    flash('Glucose record deleted.', 'success')
    return redirect(url_for('health.glucose_records'))

@health.route('/blood_pressure_records/delete/<int:id>', methods=['POST'])
@login_required
def delete_blood_pressure_record(id):
    record = BloodPressureRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('health.blood_pressure_records'))
    db.session.delete(record)
    db.session.commit()
    flash('Blood pressure record deleted.', 'success')
    return redirect(url_for('health.blood_pressure_records'))
