from supabase import create_client
import os

# Load Supabase URL and API Key from environment variables
SUPABASE_URL = "https://ayrzwmekrzvmlyhzeulv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImF5cnp3bWVrcnp2bWx5aHpldWx2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzAyOTQ4MzAsImV4cCI6MjA0NTg3MDgzMH0.RtYFkvNocUlUuXcfvJMkUsNoepXyZghWMI4-ElXulx8"

# Initialize the Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_connection():
    try:
        response = supabase.table('accountInfo').select('*').execute()
        print(response)
        print("Connection to Supabase successful")
    except Exception as e:
        print("Error:", e)

if __name__ == '__main__':
    print(test_connection())