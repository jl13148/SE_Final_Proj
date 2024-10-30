import re
from supabase import create_client
import os

# Load Supabase URL and API Key from environment variables
SUPABASE_URL = "https://ayrzwmekrzvmlyhzeulv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF5cnp3bWVrcnp2bWx5aHpldWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzAyOTQ4MzAsImV4cCI6MjA0NTg3MDgzMH0.RtYFkvNocUlUuXcfvJMkUsNoepXyZghWMI4-ElXulx8"

# Initialize the Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

class Users:
    def __init__(self, username, email, password):
        # self.id = id
        self.username = username
        self.email = email
        self.password = password

    @staticmethod
    def create_user(username, email, password):
        if not username or not email or not password:
            return {'error': 'Please fill in all fields'}
        if len(password) < 6:
            return {'error': 'Password must be at least 6 characters long'}
        check_repeat = supabase.table('accountInfo').select('*').eq('account_name', username).execute()
        print(check_repeat)
        if len(check_repeat.data) > 0:
            return {'error': 'Username already exists'}
        response = supabase.table('accountInfo').insert({
            'account_name': username,
            'email': email,
            'password': password
        }).execute()
        result = True
        return result

    @staticmethod
    def get_user_by_id(user_id):
        response = supabase.table('accountInfo').select('*').eq('id', user_id).execute()
        return response

    @staticmethod
    def get_user_by_username(username):
        response = supabase.table('accountInfo').select('*').eq('account_name', username).execute()
        return response

    @staticmethod
    def update_user(user_id, **kwargs):
        response = supabase.table('accountInfo').update(kwargs).eq('id', user_id).execute()
        return response

    @staticmethod
    def delete_user(user_id):
        response = supabase.table('accountInfo').delete().eq('id', user_id).execute()
        return response
