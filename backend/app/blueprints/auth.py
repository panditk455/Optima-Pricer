from flask import Blueprint, request, jsonify, session, render_template, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app.utils import login_required_api
import bcrypt

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'User already exists'}), 400
        
        # Hash password
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Create user
        user = User(
            email=email,
            password=hashed_password,
            name=name
        )
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'id': user.id,
            'email': user.email,
            'name': user.name
        }), 201
    
    except Exception as e:
        db.session.rollback()
        print(f'Error registering user: {e}')
        return jsonify({'error': 'Failed to register user'}), 500


@auth_bp.route('/login', methods=['POST'])
def login_api():
    """Login user"""
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not bcrypt.checkpw(password.encode('utf-8'), user.password.encode('utf-8')):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        login_user(user, remember=True)
        
        return jsonify({
            'id': user.id,
            'email': user.email,
            'name': user.name
        }), 200
    
    except Exception as e:
        print(f'Error logging in: {e}')
        return jsonify({'error': 'Failed to login'}), 500


@auth_bp.route('/logout', methods=['POST'])
@login_required_api
def logout_api():
    """Logout user"""
    try:
        logout_user()
        return jsonify({'message': 'Logged out successfully'}), 200
    except Exception as e:
        print(f'Error logging out: {e}')
        return jsonify({'error': 'Failed to logout'}), 500


@auth_bp.route('/me', methods=['GET'])
@login_required_api
def get_current_user():
    """Get current authenticated user"""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'name': current_user.name
    }), 200
