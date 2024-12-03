from flask_wtf import Form, FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TimeField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from app.models import User

# Set your classes here.

# USER_TYPE_CHOICES = [('patient', 'Patient'), ('companion', 'Companion')]
USER_TYPE_CHOICES = [('PATIENT', 'Patient'), ('COMPANION', 'Companion')]

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    user_type = SelectField('Login as', 
                          choices=USER_TYPE_CHOICES,  # Use the constant
                          validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                   validators=[DataRequired(), EqualTo('password')])
    user_type = SelectField('Register as',
                          choices=USER_TYPE_CHOICES,  # Use the same constant
                          validators=[DataRequired()])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose another one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')

class CompanionLinkForm(FlaskForm):
    patient_email = StringField('Patient Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Link with Patient')

    def validate_patient_email(self, patient_email):
        patient = User.query.filter_by(email=patient_email.data, user_type='PATIENT').first()
        if not patient:
            raise ValidationError('No patient found with this email address.')

class ForgotForm(Form):
    email = StringField(
        'Email', validators=[DataRequired(), Length(min=6, max=40)]
    )


class MedicationForm(FlaskForm):
    name = StringField('Medication Name', validators=[DataRequired()])
    dosage = StringField('Dosage', validators=[DataRequired()])
    frequency = StringField('Frequency', default='daily')
    time = TimeField('Time', validators=[DataRequired()])
    submit = SubmitField('Save Medication')

class ExportPDFForm(FlaskForm):
    submit = SubmitField('Download PDF')

class ExportCSVForm(FlaskForm):
    submit = SubmitField('Download CSV')
