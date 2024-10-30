from flask import Blueprint, url_for, render_template, redirect, request
from flask_login import login_user
from werkzeug.security import check_password_hash

from models import Users

login = Blueprint('login', __name__, template_folder='../frontend')

@login.route('/login', methods=['GET', 'POST'])
def show():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Fetch user from Supabase
        response = Users.get_user_by_username(username)
        print(response)
        if response['data']:
            user_data = response['data'][0]
            user = Users(user_data['id'], user_data['username'], user_data['email'], user_data['password'])

            # Check password
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for('home.show'))
            else:
                return redirect(url_for('login.show') + '?error=incorrect-password')
        else:
            return redirect(url_for('login.show') + '?error=user-not-found')
    else:
        return render_template('login.html')