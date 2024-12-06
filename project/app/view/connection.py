from flask import Blueprint, render_template, redirect, url_for, flash, request, session, current_app
from flask_login import login_required, current_user
from app.models import CompanionAccess
from app.extensions import db

connection = Blueprint('connection', __name__)

@connection.route('/connections')
@login_required
def manage_connections():
    if current_user.user_type != "PATIENT":
        flash('Only patients can manage connections.', 'danger')
        return redirect(url_for('pages.home'))
    
    success, connections, error = current_app.connection_service.get_connections(current_user.id)
    if not success:
        flash(error, 'danger')
        return redirect(url_for('pages.home'))
    
    return render_template('pages/connections.html',
                         pending_connections=connections['pending'],
                         active_connections=connections['active'])

@connection.route('/connections/<int:connection_id>/approve', methods=['POST'])
@login_required
def approve_connection(connection_id):
    if current_user.user_type != "PATIENT":
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('pages.home'))
    
    # Set initial access levels to NONE
    access_levels = {
        'medication': 'NONE',
        'glucose': 'NONE',
        'blood_pressure': 'NONE'
    }
    
    success, connection, error = current_app.connection_service.update_access_levels(
        connection_id=connection_id,
        patient_id=current_user.id,
        access_levels=access_levels
    )
    
    if success:
        flash(f'Connection approved. Please set access levels for {connection.companion.username}.', 'success')
        return redirect(url_for('connection.update_access', connection_id=connection_id))
    else:
        flash(error, 'danger')
        return redirect(url_for('connection.manage_connections'))

@connection.route('/connections/<int:connection_id>/access', methods=['GET', 'POST'])
@login_required
def update_access(connection_id):
    if current_user.user_type != "PATIENT":
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('pages.home'))
    
    if request.method == 'POST':
        access_levels = {
            'medication': request.form.get('medication_access', 'NONE'),
            'glucose': request.form.get('glucose_access', 'NONE'),
            'blood_pressure': request.form.get('blood_pressure_access', 'NONE')
        }
        
        success, _, error = current_app.connection_service.update_access_levels(
            connection_id=connection_id,
            patient_id=current_user.id,
            access_levels=access_levels
        )
        
        if success:
            flash('Access levels updated successfully!', 'success')
            return redirect(url_for('connection.manage_connections'))
        else:
            flash(error, 'danger')
    
    # Get current access levels for display
    connection = CompanionAccess.query.get_or_404(connection_id)
    if connection.patient_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('connection.manage_connections'))
    
    return render_template('pages/companion_access.html', access=connection)

@connection.route('/connections/<int:connection_id>/remove', methods=['POST'])
@login_required
def remove_connection(connection_id):
    if current_user.user_type != "PATIENT":
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('pages.home'))
    
    success, error = current_app.connection_service.remove_connection(
        connection_id=connection_id,
        patient_id=current_user.id
    )
    
    if success:
        flash('Connection removed successfully.', 'success')
    else:
        flash(error, 'danger')
        
    return redirect(url_for('connection.manage_connections'))