from flask import render_template, redirect, url_for, flash, request, session, jsonify, Blueprint
from flask_login import login_required, current_user
from app.extensions import db
from app.models import CompanionAccess

connection = Blueprint('connection', __name__)


@connection.route('/connections')
@login_required
def manage_connections():
    if current_user.user_type != "PATIENT":
    # if not current_user.is_patient():
        flash('Only patients can manage connections.', 'danger')
        return redirect(url_for('pages.home'))
    
    # Get pending connections (where all access levels are NONE)
    # pending_connections = CompanionAccess.query.filter_by(
    #     patient_id=current_user.id
    # ).filter(
    #     db.and_(
    #         CompanionAccess.medication_access == "NONE",
    #         CompanionAccess.glucose_access == "NONE",
    #         CompanionAccess.blood_pressure_access == "NONE"
    #     )
    # ).all()
    pending_connections = CompanionAccess.query.filter_by(
        patient_id=current_user.id,
        medication_access="NONE",
        glucose_access="NONE",
        blood_pressure_access="NONE"
    ).all()
    
    # Get active connections (where at least one access level is not NONE)
    active_connections = CompanionAccess.query.filter_by(
        patient_id=current_user.id
    ).filter(
        db.or_(
            CompanionAccess.medication_access != "NONE",
            CompanionAccess.glucose_access != "NONE",
            CompanionAccess.blood_pressure_access != "NONE"
        )
    ).all()
    
    return render_template('pages/connections.html',
                         pending_connections=pending_connections,
                         active_connections=active_connections)


@connection.route('/connections/<int:connection_id>/approve', methods=['POST'])
@login_required
def approve_connection(connection_id):
    if current_user.user_type != "PATIENT":
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('pages.home'))
        
    connection = CompanionAccess.query.get_or_404(connection_id)
    if connection.patient_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('connection.manage_connections'))
        
    try:
        # Set initial access levels to NONE
        connection.medication_access = "NONE"
        connection.glucose_access = "NONE"
        connection.blood_pressure_access = "NONE"
        connection.export_access = False
        
        db.session.commit()
        flash(f'Connection approved. Please set access levels for {connection.companion.username}.', 'success')
        # Redirect to access setting page
        return redirect(url_for('connection.update_access', connection_id=connection.id))
    except Exception as e:
        db.session.rollback()
        flash('Error approving connection.', 'danger')
        
    return redirect(url_for('connection.manage_connections'))

@connection.route('/connections/<int:connection_id>/reject', methods=['POST'])
@login_required
def reject_connection(connection_id):
    if current_user.user_type != "PATIENT":
        return jsonify({'error': 'Unauthorized'}), 403
        
    connection = CompanionAccess.query.get_or_404(connection_id)
    if connection.patient_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    try:
        db.session.delete(connection)
        db.session.commit()
        flash('Connection rejected.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error rejecting connection.', 'danger')
        
    return redirect(url_for('connection.manage_connections'))

@connection.route('/connections/<int:connection_id>/access', methods=['GET', 'POST'])
@login_required
def update_access(connection_id):
    if current_user.user_type != "PATIENT":
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('pages.home'))
        
    connection = CompanionAccess.query.get_or_404(connection_id)
    if connection.patient_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('connection.manage_connections'))
    
    if request.method == 'GET':
        # Clear any existing messages when loading the form
        session['_flashes'] = []
        return render_template('pages/companion_access.html',
                             access=connection)
    
    if request.method == 'POST':
        try:
            # Get current values
            old_values = {
                'medication': connection.medication_access,
                'glucose': connection.glucose_access,
                'blood_pressure': connection.blood_pressure_access,
            }
            
            # Get new values
            new_values = {
                'medication': request.form.get('medication_access', 'NONE'),
                'glucose': request.form.get('glucose_access', 'NONE'),
                'blood_pressure': request.form.get('blood_pressure_access', 'NONE'),
            }
            
            # Only update if there are actual changes
            if old_values != new_values:
                connection.medication_access = new_values['medication']
                connection.glucose_access = new_values['glucose']
                connection.blood_pressure_access = new_values['blood_pressure']
                
                db.session.commit()
                # Clear any existing messages before adding new one
                session['_flashes'] = []
                flash('Access levels updated successfully!', 'success')
            
        except Exception as e:
            db.session.rollback()
            # Clear any existing messages before adding new one
            session['_flashes'] = []
            flash(f'Error updating access levels: {str(e)}', 'danger')
            return render_template('pages/companion_access.html', access=connection)
            
    return redirect(url_for('connection.manage_connections'))

@connection.route('/connections/<int:connection_id>/remove', methods=['POST'])
@login_required
def remove_connection(connection_id):
    if current_user.user_type != "PATIENT":
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('pages.home'))
        
    connection = CompanionAccess.query.get_or_404(connection_id)
    if connection.patient_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('connection.manage_connections'))
        
    try:
        db.session.delete(connection)
        db.session.commit()
        # Clear any existing "Connection removed" messages before adding new one
        session['_flashes'] = [(category, message) for category, message in session.get('_flashes', [])
                             if message != 'Connection removed successfully.']
        flash('Connection removed successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        session['_flashes'] = [(category, message) for category, message in session.get('_flashes', [])
                             if message != 'Error removing connection.']
        flash('Error removing connection.', 'danger')
        
    return redirect(url_for('connection.manage_connections'))
