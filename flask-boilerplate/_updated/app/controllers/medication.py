from flask import Blueprint, redirect, url_for, render_template, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import Medication, MedicationLog, CompanionAccess
from app.forms import MedicationForm
from app.extensions import db
from datetime import datetime


medication = Blueprint('medication', __name__)

@medication.route('/medications')
@login_required
def medications():
    return redirect(url_for('medication.manage_medications'))

@medication.route('/medications/manage')
@login_required
def manage_medications():
    try:
        medications = Medication.query.filter_by(user_id=current_user.id).all()
        return render_template('pages/medications.html', 
                               medications=medications,
                               is_personal=True)
    except Exception as e:
        print(f"Error in manage_medications: {str(e)}")
        flash('Error loading medications. Please try again.', 'danger')
        return redirect(url_for('pages.home'))

@medication.route('/medications/add', methods=['GET', 'POST'])
@login_required
def add_medication():
    form = MedicationForm()
    if form.validate_on_submit():
        try:
            # Create new medication with the form data
            medication = Medication(
                name=form.name.data,
                dosage=form.dosage.data,
                frequency=form.frequency.data,
                time=form.time.data,
                user_id=current_user.id
            )
            
            db.session.add(medication)
            db.session.commit()
            
            flash('Medication added successfully!', 'success')
            return redirect(url_for('medication.manage_medications'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding medication: {str(e)}', 'danger')
            return redirect(url_for('medication.add_medication'))
    
    return render_template('pages/add_medication.html', form=form)

@medication.route('/medications/<int:id>/delete', methods=['POST'])
@login_required
def delete_medication(id):
    try:
        medication = Medication.query.get_or_404(id)
        # Check if the medication belongs to the current user
        if medication.user_id != current_user.id:
            flash('Unauthorized action.', 'danger')
            return redirect(url_for('medication.medications'))
            
        # Delete associated logs first
        MedicationLog.query.filter_by(medication_id=id).delete()
        
        # Delete the medication
        db.session.delete(medication)
        db.session.commit()
        
        flash('Medication deleted successfully.', 'success')
        return redirect(url_for('medication.manage_medications'))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the medication.', 'danger')
        return redirect(url_for('medication.manage_medications'))

@medication.route('/medications/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_medication(id):
    medication = Medication.query.get_or_404(id)
    
    # Check permissions (either owner or authorized companion)
    has_permission = False
    if medication.user_id == current_user.id:
        has_permission = True
    elif current_user.user_type == "COMPANION":
        # Check companion access
        access = CompanionAccess.query.filter_by(
            patient_id=medication.user_id,
            companion_id=current_user.id
        ).first()
        if access and access.medication_access == "EDIT":
            has_permission = True

    if not has_permission:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('medication.manage_medications'))
    
    form = MedicationForm()
    
    if request.method == 'GET':
        # Populate form with existing data
        form.name.data = medication.name
        form.dosage.data = medication.dosage
        form.frequency.data = medication.frequency
        form.time.data = medication.time
    
    if form.validate_on_submit():
        try:
            medication.name = form.name.data
            medication.dosage = form.dosage.data
            medication.frequency = form.frequency.data
            medication.time = form.time.data
            
            db.session.commit()
            flash('Medication updated successfully!', 'success')
            
            # Redirect based on user type
            if current_user.user_type == "COMPANION":
                return redirect(url_for('companion.view_patient_data', patient_id=medication.user_id))
            return redirect(url_for('medication.manage_medications'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating medication: {str(e)}', 'danger')
            
    return render_template('pages/edit_medication.html', 
                         form=form, 
                         medication=medication,
                         is_companion=current_user.user_type == "COMPANION")

#----------------------------------------------------------------------------#
# Medication Schedule Route
#----------------------------------------------------------------------------#

@medication.route('/medication-schedule')
@login_required
def medication_schedule():
    try:
        return render_template('pages/medication-schedule.html')
    except Exception as e:
        flash(f'Error loading schedule. Please try again. {e}', 'danger')
        return redirect(url_for('pages.home'))

@medication.route('/medications/daily')
@login_required
def get_daily_medications():
    try:
        medications = Medication.query.filter_by(user_id=current_user.id).all()
        medication_list = []
        
        for med in medications:
            medication_list.append({
                'id': med.id,
                'name': med.name,
                'dosage': med.dosage,
                'time': med.time.strftime('%I:%M %p'),
                'frequency': med.frequency,
                'taken': False  # You can implement the taken status logic here
            })
        
        return jsonify(medication_list)
    except Exception as e:
        print(f"Error in get_daily_medications: {str(e)}")
        return jsonify({'error': str(e)}), 500

@medication.route('/medications/check-reminders')
@login_required
def check_reminders():
    try:
        now = datetime.now()
        current_time = now.time()
        today = now.date()
        
        # Look for medications due in the next 15 minutes
        upcoming_medications = []
        medications = Medication.query.filter_by(user_id=current_user.id).all()
        
        for med in medications:
            # Calculate the next dose time
            med_time = datetime.combine(today, med.time)
            
            # Check if medication is due in the next 15 minutes
            time_diff = (med_time - now).total_seconds() / 60
            if 0 <= time_diff <= 15:
                # Check if it hasn't been taken yet today
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
        
        return jsonify(upcoming_medications)
    except Exception as e:
        return jsonify({'error': str(e)}), 500