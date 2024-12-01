from flask import Blueprint, redirect, url_for, render_template, flash, request, jsonify, current_app
from flask_login import login_required, current_user
from app.forms import MedicationForm

medication = Blueprint('medication', __name__)

@medication.route('/medications')
@login_required
def medications():
    return redirect(url_for('medication.manage_medications'))

@medication.route('/medications/manage')
@login_required
def manage_medications():
    success, medications, error = current_app.medication_service.get_medications(current_user.id)
    
    if not success:
        flash(f'Error loading medications: {error}', 'danger')
        return redirect(url_for('pages.home'))
    
    if medications is None:
        medications = []  # Ensure we always have a list
        
    return render_template('pages/medications.html', 
                         medications=medications,
                         is_personal=True)

@medication.route('/medications/add', methods=['GET', 'POST'])
@login_required
def add_medication():
    form = MedicationForm()
    if form.validate_on_submit():
        success, error = current_app.medication_service.add_medication(
            user_id=current_user.id,
            name=form.name.data,
            dosage=form.dosage.data,
            frequency=form.frequency.data,
            time=form.time.data
        )
        
        if success:
            flash('Medication added successfully!', 'success')
            return redirect(url_for('medication.manage_medications'))
            
        flash(error, 'danger')
        return redirect(url_for('medication.add_medication'))
    
    return render_template('pages/add_medication.html', form=form)

@medication.route('/medications/<int:id>/delete', methods=['POST'])
@login_required
def delete_medication(id):
    success, error = current_app.medication_service.delete_medication(
        medication_id=id,
        user_id=current_user.id
    )
    
    if success:
        flash('Medication deleted successfully.', 'success')
    else:
        flash(error, 'danger')
        
    return redirect(url_for('medication.manage_medications'))

@medication.route('/medications/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_medication(id):
    # Check permissions first
    has_permission, medication, error = current_app.medication_service.check_edit_permission(
        medication_id=id,
        user_id=current_user.id
    )
    
    if not has_permission:
        flash(error, 'danger')
        return redirect(url_for('medication.manage_medications'))
    
    form = MedicationForm()
    
    if request.method == 'GET':
        form.name.data = medication.name
        form.dosage.data = medication.dosage
        form.frequency.data = medication.frequency
        form.time.data = medication.time
    
    if form.validate_on_submit():
        success, error = current_app.medication_service.update_medication(
            medication_id=id,
            name=form.name.data,
            dosage=form.dosage.data,
            frequency=form.frequency.data,
            time=form.time.data
        )
        
        if success:
            flash('Medication updated successfully!', 'success')
            if current_user.user_type == "COMPANION":
                return redirect(url_for('companion.view_patient_data', patient_id=medication.user_id))
            return redirect(url_for('medication.manage_medications'))
            
        flash(error, 'danger')
    
    return render_template('pages/edit_medication.html',
                         form=form,
                         medication=medication,
                         is_companion=current_user.user_type == "COMPANION")

@medication.route('/medication-schedule')
@login_required
def medication_schedule():
    return render_template('pages/medication-schedule.html')

@medication.route('/medications/daily')
@login_required
def get_daily_medications():
    success, medications, error = current_app.medication_service.get_daily_medications(
        user_id=current_user.id
    )
    
    if not success:
        return jsonify({'error': error}), 500
        
    return jsonify(medications)

@medication.route('/medications/check-reminders')
@login_required
def check_reminders():
    success, reminders, error = current_app.medication_service.get_upcoming_reminders(
        user_id=current_user.id
    )
    
    if not success:
        return jsonify({'error': error}), 500
        
    return jsonify(reminders) 