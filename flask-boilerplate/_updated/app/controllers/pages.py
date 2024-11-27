from flask import session
from flask import Flask, Blueprint, render_template, request, flash, redirect, url_for, send_file, jsonify
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import logging
from django.db import IntegrityError
from logging import Formatter, FileHandler
from app.models import db, User, Medication, GlucoseRecord, BloodPressureRecord, MedicationLog, UserType, AccessLevel, CompanionAccess, GlucoseType, Notification
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
from app.forms import ExportPDFForm, ExportCSVForm, LoginForm, RegisterForm, ForgotForm, MedicationForm, CompanionLinkForm

blueprint = Blueprint('pages', __name__)


################
#### routes ####
################


@blueprint.route('/')
def home():
    return render_template('pages/placeholder.home.html')


@blueprint.route('/about')
def about():
    return render_template('pages/placeholder.about.html')


@blueprint.route('/login', methods=['GET', 'POST'])
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

@blueprint.route('/register', methods=['GET', 'POST'])
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


@blueprint.route('/forgot')
def forgot():
    form = ForgotForm(request.form)
    return render_template('forms/forgot.html', form=form)
