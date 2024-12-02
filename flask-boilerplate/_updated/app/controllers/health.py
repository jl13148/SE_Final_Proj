from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from app.models import GlucoseType
from app.models import GlucoseRecord, BloodPressureRecord, CompanionAccess, User, Notification
from app.extensions import db

health = Blueprint('health', __name__)

@health.route('/health-logger')
@login_required
def health_logger():
    return render_template('pages/health_logger.html')

@health.route('/glucose/logger', methods=['GET', 'POST'])
@login_required
def glucose_logger():
    """
    Route for adding a new glucose record.
    """
    if request.method == 'POST':
        health_service = current_app.health_service
        try:
            glucose_level = int(request.form['glucose_level'])
            glucose_type = request.form['glucose_type']
            date = request.form['date']
            time = request.form['time']
        except (ValueError, KeyError):
            flash('Invalid input. Please check your entries.', 'danger')
            return render_template('pages/glucose_logger.html')

        success, record, error = health_service.add_glucose_record(
            user_id=current_user.id,
            glucose_level=glucose_level,
            glucose_type=glucose_type,
            date=date,
            time=time
        )

        if success:
            flash('Glucose record added successfully!', 'success')
            return redirect(url_for('health.glucose_records'))
        else:
            flash(f'Error adding glucose record: {error}', 'danger')
            return render_template('pages/glucose_logger.html')

    return render_template('pages/glucose_logger.html')

@health.route('/glucose/records')
@login_required
def glucose_records():
    """
    Route for viewing all glucose records.
    """
    health_service = current_app.health_service
    success, records, error = health_service.get_glucose_records(current_user.id)
    if success:
        return render_template('pages/glucose_records.html', records=records)
    else:
        flash(f'Error retrieving records: {error}', 'danger')
        return redirect(url_for('pages.home'))

@health.route('/glucose/edit/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_glucose_record(record_id):
    """
    Route for editing an existing glucose record.
    """
    record = GlucoseRecord.query.get_or_404(record_id)

    # Check permissions
    health_service = current_app.health_service
    if not health_service.glucose_manager.has_permission(record, current_user.id):
        flash('You do not have permission to edit this record.', 'danger')
        return redirect(url_for('health.glucose_records'))

    if request.method == 'POST':
        try:
            glucose_level = int(request.form['glucose_level'])
            date = request.form['date']
            time = request.form['time']
        except ValueError:
            flash('Invalid input. Please check your entries.', 'danger')
            return render_template('pages/edit_glucose_record.html', record=record)

        success, error = health_service.update_glucose_record(
            record_id=record_id,
            user_id=current_user.id,
            glucose_level=glucose_level,
            date=date,
            time=time
        )

        if success:
            flash('Glucose record updated successfully!', 'success')
            return redirect(url_for('health.glucose_records'))
        else:
            flash(f'Error updating record: {error}', 'danger')
            return render_template('pages/edit_glucose_record.html', record=record)

    return render_template('pages/edit_glucose_record.html', record=record)

@health.route('/glucose/delete/<int:record_id>', methods=['POST'])
@login_required
def delete_glucose_record(record_id):
    """
    Route for deleting a glucose record.
    """
    health_service = current_app.health_service
    success, error = health_service.delete_glucose_record(record_id, current_user.id)
    if success:
        flash('Glucose record deleted successfully.', 'success')
    else:
        flash(f'Error deleting record: {error}', 'danger')
    return redirect(url_for('health.glucose_records'))

@health.route('/blood_pressure/logger', methods=['GET', 'POST'])
@login_required
def blood_pressure_logger():
    """
    Route for adding a new blood pressure record.
    """
    health_service = current_app.health_service
    if request.method == 'POST':
        try:
            systolic = int(request.form['systolic'])
            diastolic = int(request.form['diastolic'])
            date = request.form['date']
            time = request.form['time']
        except (ValueError, KeyError):
            flash('Invalid input. Please check your entries.', 'danger')
            return render_template('pages/blood_pressure_logger.html')

        success, record, error = health_service.add_blood_pressure_record(
            user_id=current_user.id,
            systolic=systolic,
            diastolic=diastolic,
            date=date,
            time=time
        )

        if success:
            flash('Blood pressure record added successfully!', 'success')
            return redirect(url_for('health.blood_pressure_records'))
        else:
            flash(f'Error adding blood pressure record: {error}', 'danger')
            return render_template('pages/blood_pressure_logger.html')

    return render_template('pages/blood_pressure_logger.html')

@health.route('/blood_pressure/records')
@login_required
def blood_pressure_records():
    """
    Route for viewing all blood pressure records.
    """
    health_service = current_app.health_service
    success, records, error = health_service.get_blood_pressure_records(current_user.id)
    if success:
        return render_template('pages/blood_pressure_records.html', records=records)
    else:
        flash(f'Error retrieving records: {error}', 'danger')
        return redirect(url_for('pages.home'))

@health.route('/blood_pressure/edit/<int:record_id>', methods=['GET', 'POST'])
@login_required
def edit_blood_pressure_record(record_id):
    """
    Route for editing an existing blood pressure record.
    """
    record = BloodPressureRecord.query.get_or_404(record_id)

    # Check permissions
    health_service = current_app.health_service
    if not health_service.blood_pressure_manager.has_permission(record, current_user.id):
        flash('You do not have permission to edit this record.', 'danger')
        return redirect(url_for('health.blood_pressure_records'))

    if request.method == 'POST':
        try:
            systolic = int(request.form['systolic'])
            diastolic = int(request.form['diastolic'])
            date = request.form['date']
            time = request.form['time']
        except ValueError:
            flash('Invalid input. Please check your entries.', 'danger')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

        success, error = health_service.update_blood_pressure_record(
            record_id=record_id,
            user_id=current_user.id,
            systolic=systolic,
            diastolic=diastolic,
            date=date,
            time=time
        )

        if success:
            flash('Blood pressure record updated successfully!', 'success')
            return redirect(url_for('health.blood_pressure_records'))
        else:
            flash(f'Error updating record: {error}', 'danger')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

    return render_template('pages/edit_blood_pressure_record.html', record=record)

@health.route('/blood_pressure/delete/<int:record_id>', methods=['POST'])
@login_required
def delete_blood_pressure_record(record_id):
    """
    Route for deleting a blood pressure record.
    """
    health_service = current_app.health_service
    success, error = health_service.delete_blood_pressure_record(record_id, current_user.id)
    if success:
        flash('Blood pressure record deleted successfully.', 'success')
    else:
        flash(f'Error deleting record: {error}', 'danger')
    return redirect(url_for('health.blood_pressure_records'))


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