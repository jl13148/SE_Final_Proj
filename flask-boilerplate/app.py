#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request, flash, redirect, url_for, send_file, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import ExportPDFForm, ExportCSVForm, LoginForm, RegisterForm, ForgotForm, MedicationForm
from datetime import datetime
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
app.config.from_object('config')  # Ensure you have a config.py with necessary configurations

# Initialize the database
db = SQLAlchemy(app)

# Initialize Flask-Migrate
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to 'login' route if not authenticated

#----------------------------------------------------------------------------#
# Models
#----------------------------------------------------------------------------#

# Assuming models are defined in a separate file (models.py), but defining here for completeness
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    # Relationships
    medications = db.relationship('Medication', backref='user', lazy=True)
    glucose_records = db.relationship('GlucoseRecord', backref='user', lazy=True)
    blood_pressure_records = db.relationship('BloodPressureRecord', backref='user', lazy=True)
    medication_logs = db.relationship('MedicationLog', backref='user', lazy=True)

    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, password)

class Medication(db.Model):
    __tablename__ = 'medications'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    dosage = db.Column(db.String(64), nullable=False)
    frequency = db.Column(db.String(64), nullable=False)
    time = db.Column(db.Time, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    # Relationships
    medication_logs = db.relationship('MedicationLog', backref='medication', lazy=True)

class MedicationLog(db.Model):
    __tablename__ = 'medication_logs'
    id = db.Column(db.Integer, primary_key=True)
    taken_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    medication_id = db.Column(db.Integer, db.ForeignKey('medications.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class GlucoseRecord(db.Model):
    __tablename__ = 'glucose_records'
    id = db.Column(db.Integer, primary_key=True)
    glucose_level = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class BloodPressureRecord(db.Model):
    __tablename__ = 'blood_pressure_records'
    id = db.Column(db.Integer, primary_key=True)
    systolic = db.Column(db.Integer, nullable=False)
    diastolic = db.Column(db.Integer, nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

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
    return render_template('pages/placeholder.home.html')  # Ensure this template exists

@app.route('/about')
def about():
    return render_template('pages/about.html')  # Ensure this template exists

# Medication Management Routes

@app.route('/medications')
@login_required
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

# Health Logger Routes

@app.route('/health-logger')
@login_required
def health_logger():
    return render_template('pages/health_logger.html')  # Ensure this template exists

@app.route('/health-logger/glucose')
@login_required
def glucose_logger():
    return render_template('pages/glucose_logger.html')  # Ensure this template exists

@app.route('/health-logger/blood_pressure')
@login_required
def blood_pressure_logger():
    return render_template('pages/blood_pressure_logger.html')  # Ensure this template exists

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

        new_record = GlucoseRecord(
            glucose_level=glucose_level,
            date=datetime.strptime(date_str, '%Y-%m-%d').date(),
            time=datetime.strptime(time_str, '%H:%M').time(),
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

        # Create a new BloodPressureRecord
        new_record = BloodPressureRecord(
            systolic=systolic,
            diastolic=diastolic,
            date=datetime.strptime(date_str, '%Y-%m-%d').date(),
            time=datetime.strptime(time_str, '%H:%M').time(),
            user_id=current_user.id
        )

        # Add and commit the new record
        db.session.add(new_record)
        db.session.commit()

        flash('Blood pressure data logged successfully!', 'success')
        return redirect(url_for('blood_pressure_logger'))

    return render_template('pages/blood_pressure_logger.html')

# Medication Logging Route

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

# Medication Schedule Route

@app.route('/medication-schedule')
@login_required
def medication_schedule():
    try:
        return render_template('pages/medication_schedule.html')  # Ensure this template exists
    except Exception as e:
        flash('Error loading schedule. Please try again.', 'danger')
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
                    record.date.strftime('%Y-%m-%d'),
                    record.time.strftime('%I:%M %p'),
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
                    record.date.strftime('%Y-%m-%d'),
                    record.time.strftime('%I:%M %p'),
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
        # Create a PDF in memory using ReportLab
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        p.setFont("Helvetica-Bold", 16)
        p.drawString(100, height - 50, f"Health Report for {current_user.username}")
        p.setFont("Helvetica", 12)
        p.drawString(100, height - 80, f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Fetch Glucose Records
        glucose_records = GlucoseRecord.query.filter_by(user_id=current_user.id).order_by(GlucoseRecord.date.desc(), GlucoseRecord.time.desc()).all()
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, height - 120, "Glucose Levels:")
        p.setFont("Helvetica", 12)
        y = height - 140
        if glucose_records:
            for record in glucose_records:
                if y < 50:
                    p.showPage()
                    y = height - 50
                p.drawString(120, y, f"• {record.date.strftime('%Y-%m-%d')} at {record.time.strftime('%I:%M %p')}: {record.glucose_level} mg/dL")
                y -= 20
        else:
            p.drawString(120, y, "No glucose records found.")
            y -= 20

        # Fetch Blood Pressure Records
        y -= 20  # Extra space before next section
        blood_pressure_records = BloodPressureRecord.query.filter_by(user_id=current_user.id).order_by(BloodPressureRecord.date.desc(), BloodPressureRecord.time.desc()).all()
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y, "Blood Pressure Levels:")
        y -= 20
        p.setFont("Helvetica", 12)
        if blood_pressure_records:
            for record in blood_pressure_records:
                if y < 50:
                    p.showPage()
                    y = height - 50
                p.drawString(120, y, f"• {record.date.strftime('%Y-%m-%d')} at {record.time.strftime('%I:%M %p')}: {record.systolic}/{record.diastolic} mm Hg")
                y -= 20
        else:
            p.drawString(120, y, "No blood pressure records found.")
            y -= 20

        # Summary Section
        y -= 20
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, y, "Summary:")
        y -= 20
        p.setFont("Helvetica", 12)
        summary_text = "This report contains your logged health data entries, \nincluding glucose levels and blood pressure readings."
        text_object = p.beginText(100, y)
        text_object.textLines(summary_text)
        p.drawText(text_object)

        p.showPage()
        p.save()
        buffer.seek(0)

        # Logging the export action
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
