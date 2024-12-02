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
