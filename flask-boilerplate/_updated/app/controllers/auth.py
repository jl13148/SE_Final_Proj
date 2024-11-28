from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, current_user, login_required, logout_user
from app.models import User
from app.forms import LoginForm, RegisterForm, ForgotForm
from app.extensions import db

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('pages.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data, user_type=form.user_type.data).first()
        
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            
            if user.user_type == 'companion':
                if not user.patients:
                    return redirect(url_for('companion_setup'))
                    
            flash('Login successful!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('pages.home'))
        else:
            flash('Login unsuccessful. Please check email, password and account type.', 'danger')
    return render_template('forms/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('pages.home'))
    
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
                login_user(user)
                return redirect(url_for('companion_setup'))
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred. Please try again.', 'danger')
            return render_template('forms/register.html', form=form)
            
    return render_template('forms/register.html', form=form)

@auth.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('pages.home'))

@auth.route('/forgot', methods=['GET', 'POST'])
def forgot():
    form = ForgotForm()
    if form.validate_on_submit():
        # Implement password reset functionality here
        flash('Password reset functionality not yet implemented.', 'info')
        return redirect(url_for('login'))
    return render_template('forms/forgot.html', form=form)