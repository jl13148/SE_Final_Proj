from flask import Blueprint, redirect, url_for
from flask_login import login_required

medication = Blueprint('medication', __name__)

@medication.route('/medications')
@login_required
def medications():
    return redirect(url_for('manage_medications'))

