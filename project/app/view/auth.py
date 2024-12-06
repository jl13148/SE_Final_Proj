from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, current_user, logout_user
from app.forms import LoginForm, RegisterForm, ForgotForm
from app.services.auth_service import AuthService
from app.extensions import db

# Create blueprint
auth = Blueprint('auth', __name__)

# Initialize service
auth_service = AuthService(db)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('pages.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        success, user, redirect_url, error = auth_service.authenticate_user(
            email=form.email.data,
            password=form.password.data,
            user_type=form.user_type.data
        )
        
        if success:
            flash('Your account has been created! You are now logged in.', 'success')
            login_user(user)
            
            # Handle companion registration
            if form.user_type.data == 'COMPANION':
                login_user(user)
                return redirect(url_for(redirect_url))
                
            return redirect(url_for(redirect_url))
        
        flash(error, 'danger')
    
    return render_template('forms/login.html', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('pages.home'))
    
    form = RegisterForm()
    if form.validate_on_submit():
        success, user, redirect_url, error = auth_service.register_user(
            username=form.username.data,
            email=form.email.data,
            password=form.password.data,
            user_type=form.user_type.data
        )
        
        if success:
            flash('Your account has been created! You can now log in.', 'success')
            
            # Handle companion registration
            if form.user_type.data == 'COMPANION':
                # login_user(user)
                return redirect(url_for(redirect_url))
                
            return redirect(url_for(redirect_url))
        
        flash(error, 'danger')
    
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
        success, error = auth_service.initiate_password_reset(form.email.data)
        
        if success:
            flash('Password reset instructions have been sent to your email.', 'info')
            return redirect(url_for('auth.login'))
        
        flash(error, 'danger')
        
    return render_template('forms/forgot.html', form=form)
