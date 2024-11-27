#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#
from flask import session
from flask import Flask, render_template, request, flash, redirect, url_for, send_file, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import logging
from django.db import IntegrityError
from logging import Formatter, FileHandler
from forms import ExportPDFForm, ExportCSVForm, LoginForm, RegisterForm, ForgotForm, MedicationForm, CompanionLinkForm
from models import db, User, Medication, GlucoseRecord, BloodPressureRecord, MedicationLog, UserType, AccessLevel, CompanionAccess, GlucoseType, Notification
from datetime import datetime
from functools import wraps
import io
import csv
import os
from flask_login import (
    LoginManager,
    login_required,
    current_user,
    login_user,
    logout_user,
    UserMixin,
)

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__,
            static_folder='static',  # Path to your static folder
            static_url_path='/static'  # URL prefix for static files
           )
app.config.from_object('config')

# Initialize the database
db.init_app(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to 'login' route if not authenticated


#----------------------------------------------------------------------------#
# Decorators
#----------------------------------------------------------------------------#

def check_companion_access(access_type):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if current_user.user_type == UserType.COMPANION:
                patient_id = kwargs.get('patient_id')
                if not patient_id:
                    flash('Patient not specified.', 'danger')
                    return redirect(url_for('home'))
                
                access = CompanionAccess.query.filter_by(
                    patient_id=patient_id,
                    companion_id=current_user.id
                ).first()
                
                if not access:
                    flash('No access to this patient\'s data.', 'danger')
                    return redirect(url_for('home'))
                
                access_level = getattr(access, f"{access_type}_access")
                if access_level == AccessLevel.NONE:
                    flash('You don\'t have access to this feature.', 'danger')
                    return redirect(url_for('home'))
                
                if access_level == AccessLevel.VIEW and request.method != 'GET':
                    flash('You only have view access to this feature.', 'danger')
                    return redirect(url_for('home'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

#----------------------------------------------------------------------------#
# Updated Notification Function for Risky Ranges Only
#----------------------------------------------------------------------------#

# app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')          # Replace with your mail server
# app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))                     # Replace with your mail port
# app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
# app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')                        # Your email username
# app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')                        # Your email password
# app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')            # Your default sender email

# mail = Mail(app)

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


def is_companion():
    return current_user.user_type == 'COMPANION'

# app.py

@app.route('/companion/notifications')
@login_required
def view_notifications():
    if not is_companion():
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    notifications = Notification.query.filter_by(
        user_id=current_user.id,
        is_read=False
    ).order_by(Notification.timestamp.desc()).all()
    print(f"Notifications: {notifications}")
    return render_template('pages/notifications.html', notifications=notifications)

@app.route('/companion/notifications/mark_read/<int:id>', methods=['POST'])
@login_required
def mark_notification_read(id):
    notification = Notification.query.get_or_404(id)
    if notification.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('view_notifications'))
    notification.is_read = True
    db.session.commit()
    flash('Notification marked as read.', 'success')
    return redirect(url_for('view_notifications'))

#----------------------------------------------------------------------------#
# User Loader for Flask-Login
#----------------------------------------------------------------------------#

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def home():
    return render_template('pages/placeholder.home.html')

@app.route('/about')
def about():
    return render_template('pages/about.html')

#----------------------------------------------------------------------------#
# Health Logger Routes
#----------------------------------------------------------------------------#

def is_duplicate_record(model, user_id, date_str, time_str):
    return model.query.filter_by(user_id=user_id, date=date_str, time=time_str).first() is not None
   
@app.route('/health-logger')
@login_required
def health_logger():
    return render_template('pages/health_logger.html')

@app.route('/health-logger/glucose/')
@login_required
# @check_companion_access('glucose')
def glucose_logger():
    return render_template('pages/glucose_logger.html')

@app.route('/health-logger/blood_pressure')
@login_required
@check_companion_access('blood_pressure')
def blood_pressure_logger():
    return render_template('pages/blood_pressure_logger.html')

@app.route('/glucose', methods=['GET', 'POST'])
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
        return redirect(url_for('glucose_logger'))

    return render_template('pages/glucose_logger.html')

@app.route('/blood_pressure', methods=['GET', 'POST'])
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
        return redirect(url_for('blood_pressure_logger'))

    return render_template('pages/blood_pressure_logger.html')


@app.route('/glucose/edit/<int:id>', methods=['GET', 'POST'])
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
        return redirect(url_for('glucose_logger'))

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
                return redirect(url_for('view_patient_data', patient_id=record.user_id))
            return redirect(url_for('glucose_logger'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating glucose record: {str(e)}', 'danger')
            return render_template('pages/edit_glucose_record.html', record=record)

    return render_template('pages/edit_glucose_record.html', record=record)

#----------------------------------------------------------------------------#
# Edit Blood Pressure Record Route
#----------------------------------------------------------------------------#

@app.route('/blood_pressure/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_blood_pressure_record(id):
    """
    Edit an existing blood pressure record.
    """
    record = BloodPressureRecord.query.get_or_404(id)

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
        if access and access.blood_pressure_access == "EDIT":
            has_permission = True

    if not has_permission:
        flash("You do not have permission to edit this record.", 'danger')
        return redirect(url_for('blood_pressure_logger'))

    if request.method == 'POST':
        try:
            new_systolic = int(request.form['systolic'])
            new_diastolic = int(request.form['diastolic'])
        except ValueError:
            flash('Systolic and Diastolic values must be integers.', 'danger')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

        # Validate ranges
        MIN_SYSTOLIC, MAX_SYSTOLIC = 90, 180
        MIN_DIASTOLIC, MAX_DIASTOLIC = 60, 120

        if not (MIN_SYSTOLIC <= new_systolic <= MAX_SYSTOLIC):
            flash(f'Systolic value must be between {MIN_SYSTOLIC} and {MAX_SYSTOLIC} mm Hg.', 'danger')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

        if not (MIN_DIASTOLIC <= new_diastolic <= MAX_DIASTOLIC):
            flash(f'Diastolic value must be between {MIN_DIASTOLIC} and {MAX_DIASTOLIC} mm Hg.', 'danger')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

        date_str = request.form['date']
        time_str = request.form['time']

        # Check for duplicate record
        if (date_str != record.date or time_str != record.time) and is_duplicate_record(BloodPressureRecord, record.user_id, date_str, time_str):
            flash('A blood pressure record for this date and time already exists.', 'warning')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

        # Update the record
        record.systolic = new_systolic
        record.diastolic = new_diastolic
        record.date = date_str
        record.time = time_str

        try:
            db.session.commit()
            flash('Blood pressure record updated successfully!', 'success')
            # Redirect to appropriate view based on user type
            if current_user.user_type == "COMPANION":
                return redirect(url_for('view_patient_data', patient_id=record.user_id))
            return redirect(url_for('blood_pressure_logger'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating blood pressure record: {str(e)}', 'danger')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

    return render_template('pages/edit_blood_pressure_record.html', record=record)

#----------------------------------------------------------------------------#
# Medication Management Routes
#----------------------------------------------------------------------------#

@app.route('/medications')
@login_required
@check_companion_access('medication')
def medications():
    return redirect(url_for('manage_medications'))

@app.route('/medications/manage')
@login_required
def manage_medications():
    try:
        medications = Medication.query.filter_by(user_id=current_user.id).all()
        return render_template('pages/medications.html', 
                               medications=medications,
                               is_personal=True)
    except Exception as e:
        flash('Error loading medications. Please try again.', 'danger')
        return redirect(url_for('home'))

@app.route('/medications/add', methods=['GET', 'POST'])
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
            return redirect(url_for('manage_medications'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding medication: {str(e)}', 'danger')
            return redirect(url_for('add_medication'))
    
    return render_template('pages/add_medication.html', form=form)

@app.route('/medications/<int:id>/delete', methods=['POST'])
@login_required
def delete_medication(id):
    try:
        medication = Medication.query.get_or_404(id)
        # Check if the medication belongs to the current user
        if medication.user_id != current_user.id:
            flash('Unauthorized action.', 'danger')
            return redirect(url_for('medications'))
            
        # Delete associated logs first
        MedicationLog.query.filter_by(medication_id=id).delete()
        
        # Delete the medication
        db.session.delete(medication)
        db.session.commit()
        
        flash('Medication deleted successfully.', 'success')
        return redirect(url_for('manage_medications'))
    except Exception as e:
        db.session.rollback()
        flash('An error occurred while deleting the medication.', 'danger')
        return redirect(url_for('manage_medications'))

@app.route('/medications/<int:id>/edit', methods=['GET', 'POST'])
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
        return redirect(url_for('manage_medications'))
    
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
                return redirect(url_for('view_patient_data', patient_id=medication.user_id))
            return redirect(url_for('manage_medications'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating medication: {str(e)}', 'danger')
            
    return render_template('pages/edit_medication.html', 
                         form=form, 
                         medication=medication,
                         is_companion=current_user.user_type == "COMPANION")

#----------------------------------------------------------------------------#
# Medication Logging Route
#----------------------------------------------------------------------------#

@app.route('/medications/log/<int:medication_id>', methods=['POST'])
@login_required
def log_medication(medication_id):
    try:
        medication = Medication.query.get_or_404(medication_id)
        if medication.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Check if already logged today
        today = datetime.now().date()
        existing_log = MedicationLog.query.filter(
            MedicationLog.medication_id == medication_id,
            MedicationLog.taken_at >= datetime.combine(today, datetime.min.time())
        ).first()
        
        if existing_log:
            return jsonify({'message': 'Medication already logged today'}), 400
            
        # Create new log
        log = MedicationLog(
            medication_id=medication_id,
            user_id=current_user.id,
            taken_at=datetime.now()
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'message': 'Medication logged successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

#----------------------------------------------------------------------------#
# Medication Schedule Route
#----------------------------------------------------------------------------#

@app.route('/medication-schedule')
@login_required
def medication_schedule():
    try:
        return render_template('pages/medication-schedule.html')
    except Exception as e:
        flash(f'Error loading schedule. Please try again. {e}', 'danger')
        return redirect(url_for('home'))

@app.route('/medications/daily')
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

@app.route('/medications/check-reminders')
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

#----------------------------------------------------------------------------#
# Manage connection access
#----------------------------------------------------------------------------#

@app.route('/connections')
@login_required
def manage_connections():
    if current_user.user_type != "PATIENT":
    # if not current_user.is_patient():
        flash('Only patients can manage connections.', 'danger')
        return redirect(url_for('home'))
    
    # Get pending connections (where all access levels are NONE)
    # pending_connections = CompanionAccess.query.filter_by(
    #     patient_id=current_user.id
    # ).filter(
    #     db.and_(
    #         CompanionAccess.medication_access == "NONE",
    #         CompanionAccess.glucose_access == "NONE",
    #         CompanionAccess.blood_pressure_access == "NONE"
    #     )
    # ).all()
    pending_connections = CompanionAccess.query.filter_by(
        patient_id=current_user.id,
        medication_access="NONE",
        glucose_access="NONE",
        blood_pressure_access="NONE"
    ).all()
    
    # Get active connections (where at least one access level is not NONE)
    active_connections = CompanionAccess.query.filter_by(
        patient_id=current_user.id
    ).filter(
        db.or_(
            CompanionAccess.medication_access != "NONE",
            CompanionAccess.glucose_access != "NONE",
            CompanionAccess.blood_pressure_access != "NONE"
        )
    ).all()
    
    return render_template('pages/connections.html',
                         pending_connections=pending_connections,
                         active_connections=active_connections)


@app.route('/connections/<int:connection_id>/approve', methods=['POST'])
@login_required
def approve_connection(connection_id):
    if current_user.user_type != "PATIENT":
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('home'))
        
    connection = CompanionAccess.query.get_or_404(connection_id)
    if connection.patient_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('manage_connections'))
        
    try:
        # Set initial access levels to NONE
        connection.medication_access = "NONE"
        connection.glucose_access = "NONE"
        connection.blood_pressure_access = "NONE"
        connection.export_access = False
        
        db.session.commit()
        flash(f'Connection approved. Please set access levels for {connection.companion.username}.', 'success')
        # Redirect to access setting page
        return redirect(url_for('update_access', connection_id=connection.id))
    except Exception as e:
        db.session.rollback()
        flash('Error approving connection.', 'danger')
        
    return redirect(url_for('manage_connections'))

@app.route('/connections/<int:connection_id>/reject', methods=['POST'])
@login_required
def reject_connection(connection_id):
    if current_user.user_type != "PATIENT":
        return jsonify({'error': 'Unauthorized'}), 403
        
    connection = CompanionAccess.query.get_or_404(connection_id)
    if connection.patient_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        db.session.delete(connection)
        db.session.commit()
        flash('Connection rejected.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error rejecting connection.', 'danger')
        
    return redirect(url_for('manage_connections'))

@app.route('/connections/<int:connection_id>/access', methods=['GET', 'POST'])
@login_required
def update_access(connection_id):
    if current_user.user_type != "PATIENT":
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('home'))
        
    connection = CompanionAccess.query.get_or_404(connection_id)
    if connection.patient_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('manage_connections'))
    
    if request.method == 'GET':
        # Clear any existing messages when loading the form
        session['_flashes'] = []
        return render_template('pages/companion_access.html',
                             access=connection)
    
    if request.method == 'POST':
        try:
            # Get current values
            old_values = {
                'medication': connection.medication_access,
                'glucose': connection.glucose_access,
                'blood_pressure': connection.blood_pressure_access,
            }
            
            # Get new values
            new_values = {
                'medication': request.form.get('medication_access', 'NONE'),
                'glucose': request.form.get('glucose_access', 'NONE'),
                'blood_pressure': request.form.get('blood_pressure_access', 'NONE'),
            }
            
            # Only update if there are actual changes
            if old_values != new_values:
                connection.medication_access = new_values['medication']
                connection.glucose_access = new_values['glucose']
                connection.blood_pressure_access = new_values['blood_pressure']
                
                db.session.commit()
                # Clear any existing messages before adding new one
                session['_flashes'] = []
                flash('Access levels updated successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            # Clear any existing messages before adding new one
            session['_flashes'] = []
            flash(f'Error updating access levels: {str(e)}', 'danger')
            return render_template('pages/companion_access.html', access=connection)
            
    return redirect(url_for('manage_connections'))

@app.route('/connections/<int:connection_id>/remove', methods=['POST'])
@login_required
def remove_connection(connection_id):
    if current_user.user_type != "PATIENT":
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('home'))
        
    connection = CompanionAccess.query.get_or_404(connection_id)
    if connection.patient_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('manage_connections'))
        
    try:
        db.session.delete(connection)
        db.session.commit()
        # Clear any existing "Connection removed" messages before adding new one
        session['_flashes'] = [(category, message) for category, message in session.get('_flashes', [])
                             if message != 'Connection removed successfully.']
        flash('Connection removed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        session['_flashes'] = [(category, message) for category, message in session.get('_flashes', [])
                             if message != 'Error removing connection.']
        flash('Error removing connection.', 'danger')
        
    return redirect(url_for('manage_connections'))

@app.context_processor
def utility_processor():
    def get_pending_connections_count():
        if not current_user.is_authenticated or current_user.user_type != "PATIENT":
            return 0
        return CompanionAccess.query.filter_by(
            patient_id=current_user.id
        ).filter(
            db.and_(
                CompanionAccess.medication_access == "NONE",
                CompanionAccess.glucose_access == "NONE",
                CompanionAccess.blood_pressure_access == "NONE"
            )
        ).count()
    
    return dict(pending_connections_count=get_pending_connections_count())

#----------------------------------------------------------------------------#
# Authentication Routes
#----------------------------------------------------------------------------#

@app.context_processor
def inject_debug_info():
    def get_user_type():
        if current_user.is_authenticated:
            return f"{current_user.user_type} (type: {type(current_user.user_type)})"
        return "Not authenticated"
    return dict(debug_user_type=get_user_type())
    

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data, user_type=form.user_type.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            
            if user.user_type == 'companion':
                # Check if companion has any linked patients
                if not user.patients:
                    return redirect(url_for('companion_setup'))
                    
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email, password and account type.', 'danger')
    return render_template('forms/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data,
            user_type=form.user_type.data
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            
            flash('Your account has been created! You can now log in.', 'success')
            if form.user_type.data == 'COMPANION':
                # Redirect companions to a page where they can link with patients
                login_user(user)
                return redirect(url_for('companion_setup'))
            return redirect(url_for('login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
            return render_template('forms/register.html', form=form)
            
    return render_template('forms/register.html', form=form)


@app.route('/companion/setup', methods=['GET', 'POST'])
@login_required
def companion_setup():
    if current_user.user_type != 'COMPANION':
        return redirect(url_for('home'))
        
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
                return redirect(url_for('home'))
            except Exception as e:
                db.session.rollback()
                flash('An error occurred while linking with patient.', 'danger')
                
    return render_template('pages/companion_setup.html', form=form)

@app.route('/companion/patients', methods=['GET', 'POST'])
@login_required
def companion_patients():
    if current_user.user_type != "COMPANION":
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    
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

@app.route('/companion/patient/<int:patient_id>')
@login_required
def view_patient_data(patient_id):
    if current_user.user_type != "COMPANION":
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
    
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


@app.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    form = ForgotForm()
    if form.validate_on_submit():
        # Implement password reset functionality here
        flash('Password reset functionality not yet implemented.', 'info')
        return redirect(url_for('login'))
    return render_template('forms/forgot.html', form=form)

#----------------------------------------------------------------------------#
# Health Report Feature Implementation
#----------------------------------------------------------------------------#

@app.route('/health-reports', methods=['GET', 'POST'])
@login_required
def health_reports():
    pdf_form = ExportPDFForm()
    csv_form = ExportCSVForm()
    
    if pdf_form.validate_on_submit() and pdf_form.submit.data:
        return redirect(url_for('export_pdf'))
    if csv_form.validate_on_submit() and csv_form.submit.data:
        return redirect(url_for('export_csv'))
    
    return render_template('pages/health_reports.html', pdf_form=pdf_form, csv_form=csv_form)

#----------------------------------------------------------------------------#
# CSV Exportation Functionality
#----------------------------------------------------------------------------#

@app.route('/export/csv', methods=['POST'])
@login_required
def export_csv():
    try:
        # Create a CSV in memory
        si = io.StringIO()
        cw = csv.writer(si)

        # Write Glucose Records
        cw.writerow(['Glucose Levels'])
        cw.writerow(['Date', 'Time', 'Glucose Level (mg/dL)'])
        glucose_records = GlucoseRecord.query.filter_by(user_id=current_user.id).order_by(GlucoseRecord.date.desc(), GlucoseRecord.time.desc()).all()
        if glucose_records:
            for record in glucose_records:
                cw.writerow([
                    record.date,
                    record.time,
                    record.glucose_level
                ])
        else:
            cw.writerow(['No glucose records found.'])

        # Add a blank row for separation
        cw.writerow([])

        # Write Blood Pressure Records
        cw.writerow(['Blood Pressure Levels'])
        cw.writerow(['Date', 'Time', 'Systolic (mm Hg)', 'Diastolic (mm Hg)'])
        blood_pressure_records = BloodPressureRecord.query.filter_by(user_id=current_user.id).order_by(BloodPressureRecord.date.desc(), BloodPressureRecord.time.desc()).all()
        if blood_pressure_records:
            for record in blood_pressure_records:
                cw.writerow([
                    record.date,
                    record.time,
                    record.systolic,
                    record.diastolic
                ])
        else:
            cw.writerow(['No blood pressure records found.'])

        # Generate the CSV data
        output = io.BytesIO()
        output.write(si.getvalue().encode('utf-8'))
        output.seek(0)

        # Define the filename with the current date
        csv_filename = f"health_report_{datetime.now().strftime('%Y%m%d')}.csv"

        # Logging the export action
        app.logger.info(f'CSV report exported for user: {current_user.username}')

        return send_file(
            output,
            as_attachment=True,
            download_name=csv_filename,
            mimetype='text/csv'
        )
    except Exception as e:
        app.logger.error(f'Error exporting CSV: {e}')
        flash(f'Error exporting CSV: {str(e)}', 'danger')
        return redirect(url_for('health_reports'))


#----------------------------------------------------------------------------#
# PDF Report Generation Functionality
#----------------------------------------------------------------------------#
@app.route('/export/pdf', methods=['POST'])
@login_required
def export_pdf():
    try:
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, height - 50, f"Health Report for {current_user.username}")
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 80, f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        y = height - 120

        glucose_records = GlucoseRecord.query.filter_by(user_id=current_user.id).order_by(
            GlucoseRecord.date.desc(),
            GlucoseRecord.time.desc()
        ).all()
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y, "Glucose Levels:")
        y -= 20
        p.setFont("Helvetica", 12)
        if glucose_records:
            for record in glucose_records:
                if y < 50:
                    p.showPage()
                    y = height - 50
                y -= 20
                p.drawString(120, y, f"Date: {record.date}")
                y -= 20
                p.drawString(120, y, f"Time: {record.time}")
                y -= 20
                p.drawString(120, y, f"Glucose Level: {record.glucose_level} mg/dL")
                y -= 30
        else:
            p.drawString(120, y, "No glucose records found.")
            y -= 20

        y -= 20 
        blood_pressure_records = BloodPressureRecord.query.filter_by(user_id=current_user.id).order_by(
            BloodPressureRecord.date.desc(),
            BloodPressureRecord.time.desc()
        ).all()
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y, "Blood Pressure Levels:")
        y -= 20
        p.setFont("Helvetica", 12)
        if blood_pressure_records:
            for record in blood_pressure_records:
                if y < 50:
                    p.showPage()
                    y = height - 50
                p.drawString(120, y, f"Date: {record.date}")
                y -= 20
                p.drawString(120, y, f"Time: {record.time}")
                y -= 20
                p.drawString(120, y, f"Systolic: {record.systolic} mm/Hg")
                y -= 20
                p.drawString(120, y, f"Diastolic: {record.diastolic} mm/Hg")
                y -= 30 
        else:
            p.drawString(120, y, "No blood pressure records found.")
            y -= 20

        y -= 20
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y, "Summary:")
        y -= 20
        p.setFont("Helvetica", 12)
        summary_text = "This report contains your logged health data entries,\nincluding glucose levels and blood pressure readings."
        text_object = p.beginText(100, y)
        text_object.textLines(summary_text)
        p.drawText(text_object)

        p.showPage()
        p.save()
        buffer.seek(0)

        app.logger.info(f'PDF report exported for user: {current_user.username}')

        return send_file(buffer, as_attachment=True, download_name='health_report.pdf', mimetype='application/pdf')
    except Exception as e:
        app.logger.error(f'Error exporting PDF: {e}')
        flash(f'Error generating PDF report: {str(e)}', 'danger')
        return redirect(url_for('health_reports'))

#----------------------------------------------------------------------------#
# Error Handlers
#----------------------------------------------------------------------------#

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(403)
def forbidden(e):
    print("403 error occurred")
    return render_template('errors/403.html'), 403

# @app.before_request
# def before_request():
#     print(f"Request path: {request.path}")
#     print(f"User authenticated: {current_user.is_authenticated}")
#     if current_user.is_authenticated:
#         print(f"User type: {current_user.user_type}")

#----------------------------------------------------------------------------#
# Logging Configuration
#----------------------------------------------------------------------------#

if not app.debug:
    if not os.path.exists('logs'):
        os.mkdir('logs')
    file_handler = FileHandler('logs/error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('App startup')

#----------------------------------------------------------------------------#
# Database Initialization Commands
#----------------------------------------------------------------------------#

@app.cli.command("reset_db")
def reset_db():
    """Reset the database."""
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Create all tables
        db.create_all()
        print('Database has been reset!')

def init_db():
    """Initialize database and check schema"""
    with app.app_context():
        try:
            # Verify database connection
            db.engine.connect()
            
            # Check if tables exist
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if not existing_tables:
                print("No tables found. Creating database schema...")
                db.create_all()
                print("Database schema created successfully!")
            else:
                print(f"Found existing tables: {existing_tables}")
                
                # Verify each model's table exists
                models = [User, Medication, GlucoseRecord, BloodPressureRecord, 
                         MedicationLog, CompanionAccess]
                
                for model in models:
                    if model.__tablename__ not in existing_tables:
                        print(f"Creating missing table: {model.__tablename__}")
                        model.__table__.create(db.engine)
            
            return True
            
        except Exception as e:
            print(f"Database initialization error: {e}")
            return False


#----------------------------------------------------------------------------#
# View Routes for Records
#----------------------------------------------------------------------------#

@app.route('/blood_pressure_records')
@login_required
def blood_pressure_records():
    records = BloodPressureRecord.query.filter_by(user_id=current_user.id).order_by(
        BloodPressureRecord.date.desc(), BloodPressureRecord.time.desc()).all()
    return render_template('pages/blood_pressure_records.html', records=records)

@app.route('/glucose_records')
@login_required
def glucose_records():
    records = GlucoseRecord.query.filter_by(user_id=current_user.id).order_by(
        GlucoseRecord.date.desc(), GlucoseRecord.time.desc()).all()
    return render_template('pages/glucose_records.html', records=records)

@app.route('/glucose_records/delete/<int:id>', methods=['POST'])
@login_required
def delete_glucose_record(id):
    record = GlucoseRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('glucose_records'))
    db.session.delete(record)
    db.session.commit()
    flash('Glucose record deleted.', 'success')
    return redirect(url_for('glucose_records'))

@app.route('/blood_pressure_records/delete/<int:id>', methods=['POST'])
@login_required
def delete_blood_pressure_record(id):
    record = BloodPressureRecord.query.get_or_404(id)
    if record.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('blood_pressure_records'))
    db.session.delete(record)
    db.session.commit()
    flash('Blood pressure record deleted.', 'success')
    return redirect(url_for('blood_pressure_records'))

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()  # This will create all tables if they don't exist
#     app.run(debug=True)  # Set debug=False in production

# if __name__ == '__main__':
#     with app.app_context():
#         # Update existing user types to lowercase
#         users = User.query.all()
#         for user in users:
#             user.user_type = user.user_type.lower()
#         db.session.commit()
#         print("Updated all user types to lowercase")
#     app.run(debug=True)

if __name__ == '__main__':
    if init_db():
        app.run(debug=True)
    else:
        print("Error initializing database. Please check configuration.")