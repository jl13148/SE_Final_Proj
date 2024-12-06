from flask import Blueprint, render_template

pages = Blueprint('pages', __name__)

@pages.route('/')
def home():
    return render_template('pages/placeholder.home.html')

@pages.route('/about')
def about():
    return render_template('pages/placeholder.about.html')