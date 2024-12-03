from typing import Optional, Tuple
from werkzeug.security import check_password_hash
from app.models import User
from app.extensions import db

class AuthService:
    def __init__(self, db):
        self.db = db

    def authenticate_user(self, email: str, password: str, user_type: str) -> Tuple[bool, Optional[User], Optional[str], Optional[str]]:
        """
        Authenticate a user and determine their redirect path.
        Returns: (success, user, redirect_url, error_message)
        """
        try:
            user = User.query.filter_by(email=email, user_type=user_type).first()
            
            if not user:
                return False, None, None, 'User not found.'
                
            if not user.check_password(password):
                return False, None, None, 'Invalid password.'

            # Determine redirect for companion users
            redirect_url = None
            if user.user_type == 'COMPANION' and not user.patients:
                redirect_url = 'companion.companion_setup'
                
            return True, user, redirect_url, None
            
        except Exception as e:
            return False, None, None, f'Authentication error: {str(e)}'

    def register_user(self, username: str, email: str, password: str, user_type: str) -> Tuple[bool, Optional[User], Optional[str], Optional[str]]:
        """
        Register a new user.
        Returns: (success, user, redirect_url, error_message)
        """
        try:
            # Check for existing user
            if User.query.filter_by(email=email).first():
                return False, None, None, 'Email already registered.'
            
            if User.query.filter_by(username=username).first():
                return False, None, None, 'Username already taken.'

            # Create new user
            user = User(
                username=username,
                email=email,
                user_type=user_type
            )
            user.set_password(password)
            
            self.db.session.add(user)
            self.db.session.commit()
            
            # Determine redirect path
            redirect_url = 'companion.companion_setup' if user_type == 'COMPANION' else 'auth.login'
            
            return True, user, redirect_url, None
            
        except Exception as e:
            self.db.session.rollback()
            return False, None, None, f'Registration error: {str(e)}'

    def initiate_password_reset(self, email: str) -> Tuple[bool, Optional[str]]:
        """
        Start password reset process for user.
        Returns: (success, error_message)
        """
        try:
            user = User.query.filter_by(email=email).first()
            if not user:
                return False, 'No account found with this email.'
            
            # TODO: Implement password reset token generation and email sending
            # For now, just return success
            return True, None
            
        except Exception as e:
            return False, f'Password reset error: {str(e)}'