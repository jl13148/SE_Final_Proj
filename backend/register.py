from os import error
from flask import Blueprint, url_for, render_template, redirect, request
from flask_login import LoginManager
from werkzeug.security import generate_password_hash

from models import Users

register = Blueprint('register', __name__, template_folder='../frontend')
login_manager = LoginManager()
login_manager.init_app(register)

@register.route('/register', methods=['GET', 'POST'])
def show():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm-password']

        if username and email and password and confirm_password:
            if password == confirm_password:
                # Use the correct hashing method
                hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
                try:
                    # Create a new user in Supabase
                    result = Users.create_user(username=username, email=email, password=hashed_password)
                    if result:
                        return redirect(url_for('login.show') + '?success=account-created')
                    else:
                        return redirect(url_for('register.show') + f'?error')
                except Exception as e:
                    return redirect(url_for('register.show') + f'?error={str(e)}')
            else:
                return redirect(url_for('register.show') + '?error=passwords-do-not-match')
        else:
            return redirect(url_for('register.show') + '?error=missing-fields')
    else:
        return render_template('register.html')