#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request, flash, redirect, url_for
from flask_migrate import Migrate
# from flask.ext.sqlalchemy import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *
from datetime import time, datetime
from flask import jsonify
import os
from flask_login import login_required, current_user, LoginManager, login_user, logout_user

# Import models and forms after initializing db
from models import db, User, Medication, GlucoseRecord, BloodPressureRecord, MedicationLog
from forms import LoginForm, RegisterForm, ForgotForm, MedicationForm

#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

# app = Flask(__name__)
# app.config.from_object('config')
app = Flask(__name__,
           static_folder='static',  # path to your static folder
           static_url_path='/static'  # URL prefix for static files
)
app.config.from_object('config')

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Initialize Migrate
migrate = Migrate(app, db)
# Automatically tear down SQLAlchemy.
'''
@app.teardown_request
def shutdown_session(exception=None):
    db_session.remove()
'''

# Login required decorator.
'''
def login_required(test):
    @wraps(test)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return test(*args, **kwargs)
        else:
            flash('You need to login first.')
            return redirect(url_for('login'))
    return wrap
'''
#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))

@app.route('/')
def home():
    return render_template('pages/placeholder.home.html')


@app.route('/about')
def about():
    return render_template('pages/placeholder.about.html')

@app.route('/medications')
@login_required
def medications():
    return redirect(url_for('medication_schedule'))

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


# Jinting: Health Logger Function Implementation
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

@app.route('/health-logger/visual_insight_page')
@login_required
def visual_insight_page():
    glucose_records = GlucoseRecord.query.filter_by(user_id=current_user.id).order_by(GlucoseRecord.date).all()
    blood_pressure_records = BloodPressureRecord.query.filter_by(user_id=current_user.id).order_by(BloodPressureRecord.date).all()

    # Format dates to ISO format for better compatibility with JavaScript
    glucose_dates = [record.date for record in glucose_records]  # Assuming record.date is a string in 'YYYY-MM-DD'T'HH:MM:SS' format
    glucose_levels = [record.glucose_level for record in glucose_records]

    blood_pressure_dates = [record.date for record in blood_pressure_records]  # Same assumption as above
    systolic_levels = [record.systolic for record in blood_pressure_records]
    diastolic_levels = [record.diastolic for record in blood_pressure_records]

    return render_template('pages/visual_insights.html',
                           glucose_dates=glucose_dates,
                           glucose_levels=glucose_levels,
                           blood_pressure_dates=blood_pressure_dates,
                           systolic_levels=systolic_levels,
                           diastolic_levels=diastolic_levels)

@app.route('/glucose', methods=['GET', 'POST'])
@login_required
def record_glucose():
    if request.method == 'POST':
        glucose_level = request.form['glucose_level']
        date = request.form['date']
        time = request.form['time']
        new_record = GlucoseRecord(
            glucose_level=glucose_level,
            date=date,
            time=time,
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
        systolic = request.form['systolic']
        diastolic = request.form['diastolic']
        date = request.form['date']
        time = request.form['time']
        new_record = BloodPressureRecord(
            systolic=systolic,
            diastolic=diastolic,
            date=date,
            time=time,
            user_id=current_user.id
        )
        db.session.add(new_record)
        db.session.commit()
        flash('Blood pressure data logged successfully!', 'success')
        return redirect(url_for('blood_pressure_logger'))
    return render_template('pages/blood_pressure_logger.html')

# @app.route('/visual_insights')
# def visual_insights():
#     glucose_records = GlucoseRecord.query.all()
#     blood_pressure_records = BloodPressureRecord.query.all()

#     glucose_dates = [record.date for record in glucose_records]
#     glucose_levels = [record.glucose_level for record in glucose_records]

#     blood_pressure_dates = [record.date for record in blood_pressure_records]
#     systolic_levels = [record.systolic for record in blood_pressure_records]
#     diastolic_levels = [record.diastolic for record in blood_pressure_records]

#     return render_template('/pages/visual_insights.html',
#                            glucose_dates=glucose_dates,
#                            glucose_levels=glucose_levels,
#                            blood_pressure_dates=blood_pressure_dates,
#                            systolic_levels=systolic_levels,
#                            diastolic_levels=diastolic_levels)
# @app.route('/login')
# def login():
#     form = LoginForm(request.form)
#     return render_template('forms/login.html', form=form)


# @app.route('/register')
# def register():
#     form = RegisterForm(request.form)
#     return render_template('forms/register.html', form=form)

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


@app.route('/medication-schedule')
@login_required
def medication_schedule():
    try:
        return render_template('pages/medication-schedule.html')
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form = LoginForm()
    if request.method == 'POST' and form.validate():
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
    if request.method == 'POST' and form.validate():
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


@app.route('/forgot')
def forgot():
    form = ForgotForm(request.form)
    return render_template('forms/forgot.html', form=form)

# Error handlers.

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')


# def init_db():
#     with app.app_context():
#         db.create_all()

# #----------------------------------------------------------------------------#
# # Launch.
# #----------------------------------------------------------------------------#

# # Default port:
# if __name__ == '__main__':
#     init_db()
#     app.run()

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
    db.create_all()
    print('Database initialized!')

# Jinting: Check db:
@app.route('/blood_pressure_records')
@login_required
def blood_pressure_records():
    records = BloodPressureRecord.query.filter_by(user_id=current_user.id).order_by(BloodPressureRecord.date.desc(), BloodPressureRecord.time.desc()).all()
    return render_template('pages/blood_pressure_records.html', records=records)

@app.route('/glucose_records')
@login_required
def glucose_records():
    records = GlucoseRecord.query.filter_by(user_id=current_user.id).order_by(GlucoseRecord.date.desc(), GlucoseRecord.time.desc()).all()
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

# Default port:
if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # This will create all tables
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
