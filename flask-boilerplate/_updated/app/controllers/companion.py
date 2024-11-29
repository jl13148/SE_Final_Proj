from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, current_user, login_required, logout_user
from app.models import User, CompanionAccess, GlucoseRecord, BloodPressureRecord, Medication, Notification
from app.forms import LoginForm, RegisterForm, ForgotForm, CompanionLinkForm
from app.extensions import db

companion = Blueprint('companion', __name__)


@companion.route('/companion-setup', methods=['GET', 'POST'])
@login_required
def companion_setup():
    if current_user.user_type != 'COMPANION':
        return redirect(url_for('pages.home'))
        
    form = CompanionLinkForm()
    if form.validate_on_submit():
        patient = User.query.filter_by(email=form.patient_email.data, user_type='PATIENT').first()
        
        # Check if already linked
        existing_link = CompanionAccess.query.filter_by(
            patient_id=patient.id,
            companion_id=current_user.id
        ).first()
        
        if existing_link:
            flash('You are already linked with this patient.', 'warning')
        else:
            link = CompanionAccess(
                patient_id=patient.id,
                companion_id=current_user.id,
                # Default access levels
                medication_access='NONE',
                glucose_access='NONE',
                blood_pressure_access='NONE',
                export_access=False
            )
            
            try:
                db.session.add(link)
                db.session.commit()
                flash('Successfully linked with patient. Waiting for access approval.', 'success')
                return redirect(url_for('pages.home'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while linking with patient.', 'danger')
                
    return render_template('pages/companion_setup.html', form=form)

@companion.route('/companion/patients', methods=['GET', 'POST'])
@login_required
def companion_patients():
    if current_user.user_type != "COMPANION":
        flash('Access denied.', 'danger')
        return redirect(url_for('pages.home'))
    
    # Add form handling for linking new patients
    form = CompanionLinkForm()
    if request.method == 'POST' and form.validate_on_submit():
        patient = User.query.filter_by(email=form.patient_email.data, user_type='PATIENT').first()
        
        if not patient:
            flash('No patient account found with that email.', 'danger')
        else:
            # Check if already linked
            existing_link = CompanionAccess.query.filter_by(
                patient_id=patient.id,
                companion_id=current_user.id
            ).first()
            
            if existing_link:
                flash('You are already linked with this patient.', 'warning')
            else:
                link = CompanionAccess(
                    patient_id=patient.id,
                    companion_id=current_user.id,
                    medication_access='NONE',
                    glucose_access='NONE',
                    blood_pressure_access='NONE',
                    export_access=False
                )
                
                try:
                    db.session.add(link)
                    db.session.commit()
                    flash('Successfully linked with patient. Waiting for access approval.', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash('An error occurred while linking with patient.', 'danger')
    
    connections = CompanionAccess.query.filter(
        CompanionAccess.companion_id == current_user.id,
        db.or_(
            CompanionAccess.medication_access != "NONE",
            CompanionAccess.glucose_access != "NONE",
            CompanionAccess.blood_pressure_access != "NONE"
        )
    ).all()
    
    pending_connections = CompanionAccess.query.filter_by(
        companion_id=current_user.id,
        medication_access="NONE",
        glucose_access="NONE",
        blood_pressure_access="NONE"
    ).all()
    
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
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(Notification.timestamp.desc()).all()
    print(f"Notifications: {notifications}")
    return render_template('pages/notifications.html', notifications=notifications)

@companion.route('/companion/notifications/mark_read/<int:id>', methods=['POST'])
@login_required
def mark_notification_read(id):
    notification = Notification.query.get_or_404(id)
    if notification.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('companion.view_notifications'))
    notification.is_read = True
    db.session.commit()
    flash('Notification marked as read.', 'success')
    return redirect(url_for('companion.view_notifications'))