from flask import Flask
from flask_login import LoginManager

from models import supabase, Users

from index import index
from login import login
from logout import logout
from register import register
from home import home

app = Flask(__name__, static_folder='../frontend/static')

app.config['SECRET_KEY'] = 'secret_key'

login_manager = LoginManager()
login_manager.init_app(app)

app.register_blueprint(index)
app.register_blueprint(login)
app.register_blueprint(logout)
app.register_blueprint(register)
app.register_blueprint(home)

@login_manager.user_loader
def load_user(user_id):
    response = Users.get_user_by_id(user_id)
    if response['data']:
        user_data = response['data'][0]
        return Users(user_data['user_id'], user_data['account_name'], user_data['email'], user_data['password'])
    return None

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)