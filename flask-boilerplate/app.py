#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

from flask import Flask, render_template, request, flash, redirect, url_for
# from flask.ext.sqlalchemy import SQLAlchemy
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from forms import *
from datetime import datetime
import os
from flask_login import login_required, current_user, LoginManager, login_user, logout_user

# Import models and forms after initializing db
from models import db, User, Medication
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
def medications():
    """Public view of medications, with different displays for logged-in vs anonymous users"""
    if current_user.is_authenticated:
        # Show personal medications for logged-in users
        medications = Medication.query.filter_by(user_id=current_user.id).order_by(Medication.time).all()
        return render_template('pages/medications.html', 
                             medications=medications, 
                             is_personal=True)
    else:
        # Show sample medications or public info for anonymous users
        sample_medications = [
            {
                'name': 'Metformin',
                'dosage': '500mg',
                'frequency': 'twice_daily',
                'time': datetime.strptime('09:00', '%H:%M').time(),
                'description': 'Common diabetes medication that helps control blood sugar levels.'
            },
            {
                'name': 'Insulin',
                'dosage': '10 units',
                'frequency': 'daily',
                'time': datetime.strptime('08:00', '%H:%M').time(),
                'description': 'Hormone medication that helps your body process glucose.'
            },
            {
                'name': 'Glipizide',
                'dosage': '5mg',
                'frequency': 'daily',
                'time': datetime.strptime('12:00', '%H:%M').time(),
                'description': 'Medication that helps your pancreas produce more insulin.'
            }
        ]
        return render_template('pages/medications.html', 
                             medications=sample_medications, 
                             is_personal=False)

@app.route('/medications/add', methods=['GET', 'POST'])
@login_required  # Keep this protected
def add_medication():
    form = MedicationForm()
    if form.validate_on_submit():
        medication = Medication(
            name=form.name.data,
            dosage=form.dosage.data,
            frequency=form.frequency.data,
            time=form.time.data,
            user_id=current_user.id
        )
        db.session.add(medication)
        db.session.commit()
        flash('Medication added successfully!')
        return redirect(url_for('medications'))
    return render_template('forms/medication.html', form=form)

@app.route('/medications/<int:id>/delete', methods=['POST'])
@login_required  # Keep this protected
def delete_medication(id):
    medication = Medication.query.get_or_404(id)
    if medication.user_id != current_user.id:
        flash('Unauthorized access.')
        return redirect(url_for('medications'))
    db.session.delete(medication)
    db.session.commit()
    flash('Medication deleted.')
    return redirect(url_for('medications'))


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
    glucose_records = GlucoseRecord.query.all()
    blood_pressure_records = BloodPressureRecord.query.all()

    glucose_dates = [record.date for record in glucose_records]
    glucose_levels = [record.glucose_level for record in glucose_records]

    blood_pressure_dates = [record.date for record in blood_pressure_records]
    systolic_levels = [record.systolic for record in blood_pressure_records]
    diastolic_levels = [record.diastolic for record in blood_pressure_records]

    return render_template('/pages/visual_insights.html',
                           glucose_dates=glucose_dates,
                           glucose_levels=glucose_levels,
                           blood_pressure_dates=blood_pressure_dates,
                           systolic_levels=systolic_levels,
                           diastolic_levels=diastolic_levels)
    # return render_template('pages/visual_insights.html')

class GlucoseRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    glucose_level = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(5), nullable=False)

@app.route('/glucose', methods=['GET', 'POST'])
def record_glucose():
    if request.method == 'POST':
        glucose_level = request.form['glucose_level']
        date = request.form['date']
        time = request.form['time']
        new_record = GlucoseRecord(glucose_level=glucose_level, date=date, time=time)
        db.session.add(new_record)
        db.session.commit()
        return redirect(url_for('glucose'))
    return render_template('glucose_logger.html')

class BloodPressureRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    systolic = db.Column(db.Integer, nullable=False)
    diastolic = db.Column(db.Integer, nullable=False)
    date = db.Column(db.String(10), nullable=False)
    time = db.Column(db.String(5), nullable=False)

@app.route('/blood_pressure', methods=['GET', 'POST'])
def record_blood_pressure():
    if request.method == 'POST':
        systolic = request.form['systolic']
        diastolic = request.form['diastolic']
        date = request.form['date']
        time = request.form['time']
        new_record = BloodPressureRecord(systolic=systolic, diastolic=diastolic, date=date, time=time)
        db.session.add(new_record)
        db.session.commit()
        return redirect(url_for('blood_pressure'))
    return render_template('blood_pressure_logger.html')

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


def init_db():
    with app.app_context():
        db.create_all()

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    init_db()
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
