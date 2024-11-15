#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request, flash, redirect, url_for, send_file, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import logging
from django.db import IntegrityError
from logging import Formatter, FileHandler
from forms import ExportPDFForm, ExportCSVForm, LoginForm, RegisterForm, ForgotForm, MedicationForm, MedicationTimeForm
from models import db, User, Medication, GlucoseRecord, BloodPressureRecord, MedicationLog, MedicationTime
from datetime import datetime
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField, FieldList, FormField, TimeField
from wtforms.validators import DataRequired, Length, NumberRange
from sqlalchemy.exc import IntegrityError
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

@app.route('/medications')
@login_required
def medications():
    return redirect(url_for('manage_medications'))

@app.route('/medications/manage')
@login_required
def manage_medications():
    medications = Medication.query.filter_by(user_id=current_user.id).all()
    return render_template('pages/medications.html', medications=medications, is_personal=True)

@app.route('/medications/add', methods=['GET', 'POST'])
@login_required
def add_medication():
    form = MedicationForm()
    if form.validate_on_submit():
        try:
            medication = Medication(
                name=form.name.data,
                dosage=form.dosage.data,
                frequency=form.frequency.data,
                user_id=current_user.id
            )
            db.session.add(medication)
            db.session.flush()  # Get medication.id

            for time_form in form.times.entries:
                med_time = MedicationTime(
                    time=time_form.form.time.data,
                    medication_id=medication.id
                )
                db.session.add(med_time)

            db.session.commit()
            flash('Medication added successfully!', 'success')
            return redirect(url_for('manage_medications'))
        except IntegrityError:
            db.session.rollback()
            flash('Medication with this name already exists.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')

    return render_template('pages/add_medication.html', form=form)

@app.route('/medications/daily')
@login_required
def get_daily_medications():
    try:
        today = datetime.now().date()
        medications = Medication.query.filter_by(user_id=current_user.id).all()
        schedule = []
        for med in medications:
            for med_time in med.times:
                taken = MedicationLog.query.filter_by(
                    medication_id=med.id,
                    user_id=current_user.id
                ).filter(
                    db.func.date(MedicationLog.taken_at) == today,
                    db.func.time(MedicationLog.taken_at) == med_time.time
                ).first() is not None
                schedule.append({
                    'id': med.id,
                    'name': med.name,
                    'dosage': med.dosage,
                    'time': med_time.time.strftime('%I:%M %p'),
                    'taken': taken
                })
        schedule.sort(key=lambda x: datetime.strptime(x['time'], '%I:%M %p'))
        return jsonify(schedule), 200
    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500

@app.route('/medications/log/<int:medication_id>', methods=['POST'])
@login_required
def log_medication(medication_id):
    try:
        med = Medication.query.get_or_404(medication_id)
        if med.user_id != current_user.id:
            return jsonify({'message': 'Unauthorized access.'}), 403

        data = request.get_json()
        intake_time_str = data.get('time')
        if not intake_time_str:
            return jsonify({'message': 'Intake time not provided.'}), 400

        intake_time = datetime.strptime(intake_time_str, '%I:%M %p').time()
        today = datetime.now().date()

        existing_log = MedicationLog.query.filter_by(
            medication_id=med.id,
            user_id=current_user.id
        ).filter(
            db.func.date(MedicationLog.taken_at) == today,
            db.func.time(MedicationLog.taken_at) == intake_time
        ).first()

        if existing_log:
            return jsonify({'message': 'Medication already marked as taken.'}), 400

        log = MedicationLog(
            medication_id=med.id,
            user_id=current_user.id,
            taken_at=datetime.now()
        )
        db.session.add(log)
        db.session.commit()
        return jsonify({'message': 'Medication logged successfully.'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500

@app.route('/medications/delete/<int:id>', methods=['POST'])
@login_required
def delete_medication(id):
    med = Medication.query.get_or_404(id)
    if med.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('manage_medications'))
    try:
        db.session.delete(med)
        db.session.commit()
        flash('Medication deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    return redirect(url_for('manage_medications'))

@app.route('/medications/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_medication(id):
    med = Medication.query.get_or_404(id)
    if med.user_id != current_user.id:
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('manage_medications'))
    
    form = MedicationForm(obj=med)
    if request.method == 'GET':
        form.times.entries = []
        for med_time in med.times:
            form.times.append_entry({'time': med_time.time.strftime('%H:%M')})
    
    if form.validate_on_submit():
        try:
            med.name = form.name.data
            med.dosage = form.dosage.data
            med.frequency = form.frequency.data

            # Clear existing times
            MedicationTime.query.filter_by(medication_id=med.id).delete()

            # Add updated times
            for time_form in form.times.entries:
                new_time = MedicationTime(
                    time=time_form.form.time.data,
                    medication_id=med.id
                )
                db.session.add(new_time)
            
            db.session.commit()
            flash('Medication updated successfully.', 'success')
            return redirect(url_for('manage_medications'))
        except IntegrityError:
            db.session.rollback()
            flash('Medication with this name already exists.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
    
    return render_template('pages/edit_medication.html', form=form, medication=med)

@app.route('/medication-schedule')
@login_required
def medication_schedule():
    return render_template('pages/medication-schedule.html')

@app.route('/medications/check-reminders')
@login_required
def check_reminders():
    try:
        now = datetime.now()
        current_time = now.time().replace(second=0, microsecond=0)
        today = now.date()

        medications = Medication.query.filter_by(user_id=current_user.id).all()
        reminders = []

        for med in medications:
            for med_time in med.times:
                if med_time.time.hour == current_time.hour and med_time.time.minute == current_time.minute:
                    taken = MedicationLog.query.filter_by(
                        medication_id=med.id,
                        user_id=current_user.id
                    ).filter(
                        db.func.date(MedicationLog.taken_at) == today,
                        db.func.time(MedicationLog.taken_at) == med_time.time
                    ).first() is not None
                    if not taken:
                        reminders.append({
                            'name': med.name,
                            'dosage': med.dosage
                        })

        return jsonify(reminders), 200
    except Exception as e:
        return jsonify({'message': f'An error occurred: {str(e)}'}), 500


# Health Logger Routes
def is_duplicate_record(model, user_id, date_str, time_str):
    return model.query.filter_by(user_id=user_id, date=date_str, time=time_str).first() is not None
   
@app.route('/health-logger')
@login_required
def health_logger():
    return render_template('pages/health_logger.html')

@app.route('/health-logger/glucose')
@login_required
def glucose_logger():
    return render_template('pages/glucose_logger.html')

@app.route('/health-logger/blood_pressure')
@login_required
def blood_pressure_logger():
    return render_template('pages/blood_pressure_logger.html')

@app.route('/glucose', methods=['GET', 'POST'])
@login_required
def record_glucose():
    if request.method == 'POST':
        try:
            glucose_level = int(request.form['glucose_level'])
        except ValueError:
            flash('Glucose level must be an integer.', 'danger')
            return render_template('pages/glucose_logger.html')
        
        # Validate glucose level boundaries
        MIN_GLUCOSE = 70    # Minimum acceptable glucose level in mg/dL
        MAX_GLUCOSE = 180   # Maximum acceptable glucose level in mg/dL

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
            date=date_str,
            time=time_str,
            user_id=current_user.id
        )

        db.session.add(new_record)
        db.session.commit()

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
        MIN_SYSTOLIC = 90
        MAX_SYSTOLIC = 180
        MIN_DIASTOLIC = 60
        MAX_DIASTOLIC = 120

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

        flash('Blood pressure data logged successfully!', 'success')
        return redirect(url_for('blood_pressure_logger'))

    return render_template('pages/blood_pressure_logger.html')

@app.route('/glucose/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_glucose_record(id):
    """
    Edit an existing glucose record.

    :param id: ID of the glucose record to edit.
    """
    record = GlucoseRecord.query.get_or_404(id)

    # Verify ownership
    if record.user_id != current_user.id:
        flash("You do not have permission to edit this record.", 'danger')
        return redirect(url_for('glucose_logger'))

    if request.method == 'POST':
        try:
            new_glucose_level = int(request.form['glucose_level'])
        except ValueError:
            flash('Glucose level must be an integer.', 'danger')
            return render_template('pages/edit_glucose_record.html', record=record)
        
        # Validate glucose level boundaries
        MIN_GLUCOSE = 70    # Minimum acceptable glucose level in mg/dL
        MAX_GLUCOSE = 180   # Maximum acceptable glucose level in mg/dL

        if not (MIN_GLUCOSE <= new_glucose_level <= MAX_GLUCOSE):
            flash(f'Glucose level must be between {MIN_GLUCOSE} and {MAX_GLUCOSE} mg/dL.', 'danger')
            return render_template('pages/edit_glucose_record.html', record=record)

        date_str = request.form['date']
        time_str = request.form['time']

        # Check for duplicate record only if date or time has changed
        if (date_str != record.date or time_str != record.time) and is_duplicate_record(GlucoseRecord, current_user.id, date_str, time_str):
            flash('A glucose record for this date and time already exists.', 'warning')
            return render_template('pages/edit_glucose_record.html', record=record)

        # Update the record
        record.glucose_level = new_glucose_level
        record.date = date_str
        record.time = time_str

        try:
            db.session.commit()
            flash('Glucose record updated successfully!', 'success')
            return redirect(url_for('glucose_logger'))
        except IntegrityError:
            db.session.rollback()
            flash('A glucose record for this date and time already exists.', 'warning')
            return render_template('pages/edit_glucose_record.html', record=record)
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

    :param id: ID of the blood pressure record to edit.
    """
    record = BloodPressureRecord.query.get_or_404(id)

    # Verify ownership
    if record.user_id != current_user.id:
        flash("You do not have permission to edit this record.", 'danger')
        return redirect(url_for('blood_pressure_logger'))

    if request.method == 'POST':
        try:
            new_systolic = int(request.form['systolic'])
            new_diastolic = int(request.form['diastolic'])
        except ValueError:
            flash('Systolic and Diastolic values must be integers.', 'danger')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

        # Validate blood pressure ranges
        MIN_SYSTOLIC = 90
        MAX_SYSTOLIC = 180
        MIN_DIASTOLIC = 60
        MAX_DIASTOLIC = 120

        if not (MIN_SYSTOLIC <= new_systolic <= MAX_SYSTOLIC):
            flash(f'Systolic value must be between {MIN_SYSTOLIC} and {MAX_SYSTOLIC} mm Hg.', 'danger')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

        if not (MIN_DIASTOLIC <= new_diastolic <= MAX_DIASTOLIC):
            flash(f'Diastolic value must be between {MIN_DIASTOLIC} and {MAX_DIASTOLIC} mm Hg.', 'danger')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

        date_str = request.form['date']
        time_str = request.form['time']

        # Check for duplicate record only if date or time has changed
        if (date_str != record.date or time_str != record.time) and is_duplicate_record(BloodPressureRecord, current_user.id, date_str, time_str):
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
            return redirect(url_for('blood_pressure_logger'))
        except IntegrityError:
            db.session.rollback()
            flash('A blood pressure record for this date and time already exists.', 'warning')
            return render_template('pages/edit_blood_pressure_record.html', record=record)
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating blood pressure record: {str(e)}', 'danger')
            return render_template('pages/edit_blood_pressure_record.html', record=record)

    return render_template('pages/edit_blood_pressure_record.html', record=record)

# Medication Logging Route

# Medication Schedule Route

#----------------------------------------------------------------------------#
# Authentication Routes
#----------------------------------------------------------------------------#

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login unsuccessful. Please check email and password.', 'danger')
    return render_template('forms/login.html', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Your account has been created! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
            return render_template('forms/register.html', form=form)
            
    return render_template('forms/register.html', form=form)

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

@app.cli.command("init_db")
def init_db():
    """Initialize the database."""
    with app.app_context():
        db.create_all()
        print('Database initialized!')

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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This will create all tables if they don't exist
    app.run(debug=True)  # Set debug=False in production
