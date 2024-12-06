from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from app.forms import CompanionLinkForm

companion = Blueprint('companion', __name__)

@companion.route('/companion-setup', methods=['GET', 'POST'])
@login_required
def companion_setup():
    if current_user.user_type != 'COMPANION':
        return redirect(url_for('pages.home'))
        
    form = CompanionLinkForm()
    if form.validate_on_submit():
        success, message = current_app.companion_service.link_patient(
            companion_id=current_user.id,
            patient_email=form.patient_email.data
        )
        if success:
            flash(message, 'success')
            return redirect(url_for('pages.home'))
        else:
            flash(message, 'danger')
                    
    return render_template('pages/companion_setup.html', form=form)

@companion.route('/companion/patients', methods=['GET', 'POST'])
@login_required
def companion_patients():
    if current_user.user_type != "COMPANION":
        flash('Access denied.', 'danger')
        return redirect(url_for('pages.home'))
    
    form = CompanionLinkForm()
    if request.method == 'POST' and form.validate_on_submit():
        success, message = current_app.companion_service.link_patient(
            companion_id=current_user.id,
            patient_email=form.patient_email.data
        )
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        
    success, connections = current_app.companion_service.get_companion_patients(current_user.id)
    if not success:
        connections = []
        
    success, pending_connections = current_app.companion_service.get_pending_connections(current_user.id)
    if not success:
        pending_connections = []
        
    return render_template('pages/companion_patients.html', 
                           form=form,
                           connections=connections,
                           pending_connections=pending_connections)

@companion.route('/companion/patient/<int:patient_id>')
@login_required
def view_patient_data(patient_id):
    if current_user.user_type != "COMPANION":
        flash('Access denied.', 'danger')
        return redirect(url_for('pages.home'))
        
    success, message, patient, access, glucose_data, blood_pressure_data, medication_data = \
        current_app.companion_service.get_patient_data(current_user.id, patient_id)
        
    if not success:
        flash(message, 'danger')
        return redirect(url_for('companion.companion_patients'))
        
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
    success, notifications = current_app.companion_service.get_notifications(current_user.id)
    if not success:
        notifications = []
    return render_template('pages/notifications.html', notifications=notifications)

@companion.route('/companion/notifications/mark_read/<int:id>', methods=['POST'])
@login_required
def mark_notification_read(id):
    success, message = current_app.companion_service.mark_notification_read(
        companion_id=current_user.id,
        notification_id=id
    )
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('companion.view_notifications'))
