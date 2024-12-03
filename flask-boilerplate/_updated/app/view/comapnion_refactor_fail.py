from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.models import GlucoseRecord, BloodPressureRecord, CompanionAccess, User, Notification, Medication
from app.forms import CompanionLinkForm
from app.extensions import db

companion = Blueprint('companion', __name__)

@companion.route('/companion-setup', methods=['GET', 'POST'])
@login_required
def companion_setup():
    if current_user.user_type != 'COMPANION':
        return redirect(url_for('pages.home'))
        
    form = CompanionLinkForm()
    if form.validate_on_submit():
        success, link, error = current_app.companion_service.setup_companion_link(
            companion_id=current_user.id,
            patient_email=form.patient_email.data
        )
        
        if success:
            flash('Successfully linked with patient. Waiting for access approval.', 'success')
            return redirect(url_for('pages.home'))
        else:
            flash(error, 'danger')
                
    return render_template('pages/companion_setup.html', form=form)

@companion.route('/companion/patient/<int:patient_id>')
@login_required
def view_patient_data(patient_id):    # This function name needs to match url_for calls
    if current_user.user_type != "COMPANION":
        flash('Access denied.', 'danger')
        return redirect(url_for('pages.home'))
    
    access = CompanionAccess.query.filter_by(
        patient_id=patient_id,
        companion_id=current_user.id
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
    
    return render_template('pages/patient_data.html',
                         patient=patient,
                         access=access,
                         glucose_data=glucose_data,
                         blood_pressure_data=blood_pressure_data,
                         medication_data=medication_data)

@companion.route('/companion/notifications')
@login_required
def view_notifications():
    if current_user.user_type != "COMPANION":
        flash('Access denied.', 'danger')
        return redirect(url_for('pages.home'))
        
    success, notifications, error = current_app.companion_service.get_notifications(current_user.id)
    if not success:
        flash(error, 'danger')
        notifications = []
        
    return render_template('pages/notifications.html', notifications=notifications)

@companion.route('/companion/notifications/mark_read/<int:id>', methods=['POST'])
@login_required
def mark_notification_read(id):
    success, _, error = current_app.companion_service.mark_notification_read(id, current_user.id)
    if not success:
        flash(error, 'danger')
    else:
        flash('Notification marked as read.', 'success')
    return redirect(url_for('companion.view_notifications'))