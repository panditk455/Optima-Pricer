from app.models import User


def load_user(user_id):
    """Load user by ID for Flask-Login"""
    return User.query.get(user_id)
