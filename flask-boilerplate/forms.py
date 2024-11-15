from flask_wtf import Form, FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TimeField, SelectField, HiddenField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
from models import User

# Set your classes here.

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', 
                                   validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose another one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')


class ForgotForm(Form):
    email = StringField(
        'Email', validators=[DataRequired(), Length(min=6, max=40)]
    )


class MedicationForm(FlaskForm):
    name = StringField('Medication Name', validators=[DataRequired()])
    dosage = StringField('Dosage', validators=[DataRequired()])
    frequency = SelectField('Frequency', 
                          choices=[
                              ('daily', 'Once Daily'),
                              ('twice_daily', 'Twice Daily'),
                              ('three_times_daily', 'Three Times Daily')
                          ],
                          validators=[DataRequired()])
    time = TimeField('Time', validators=[DataRequired()])
    submit = SubmitField('Save Medication')

class ExportPDFForm(FlaskForm):
    submit = SubmitField('Download PDF')

class ExportCSVForm(FlaskForm):
    submit = SubmitField('Download CSV')
