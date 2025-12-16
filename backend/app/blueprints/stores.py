from flask import Blueprint, request, jsonify
from app import db
from app.models import Store
from app.utils import login_required_api
from flask_login import current_user

stores_bp = Blueprint('stores', __name__)


@stores_bp.route('', methods=['GET'])
@login_required_api
def get_stores():
    """Get all stores for current user"""
    try:
        stores = Store.query.filter_by(user_id=current_user.id).order_by(Store.created_at.desc()).all()
        return jsonify([store.to_dict() for store in stores]), 200
    except Exception as e:
        print(f'Error fetching stores: {e}')
        return jsonify({'error': 'Failed to fetch stores'}), 500


@stores_bp.route('/<store_id>', methods=['GET'])
@login_required_api
def get_store(store_id):
    """Get a single store"""
    try:
        store = Store.query.filter_by(id=store_id, user_id=current_user.id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        return jsonify(store.to_dict()), 200
    except Exception as e:
        print(f'Error fetching store: {e}')
        return jsonify({'error': 'Failed to fetch store'}), 500


@stores_bp.route('', methods=['POST'])
@login_required_api
def create_store():
    """Create a new store"""
    try:
        data = request.get_json()
        name = data.get('name')
        platform = data.get('platform', 'other')
        api_key = data.get('apiKey')
        api_secret = data.get('apiSecret')
        
        if not name:
            return jsonify({'error': 'Store name is required'}), 400
        
        store = Store(
            user_id=current_user.id,
            name=name,
            platform=platform,
            api_key=api_key,
            api_secret=api_secret
        )
        
        db.session.add(store)
        db.session.commit()
        
        return jsonify(store.to_dict()), 201
    
    except Exception as e:
        db.session.rollback()
        print(f'Error creating store: {e}')
        return jsonify({'error': 'Failed to create store'}), 500


@stores_bp.route('/<store_id>', methods=['PATCH'])
@login_required_api
def update_store(store_id):
    """Update a store"""
    try:
        store = Store.query.filter_by(id=store_id, user_id=current_user.id).first()
        
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            store.name = data['name']
        if 'platform' in data:
            store.platform = data['platform']
        if 'apiKey' in data:
            store.api_key = data['apiKey']
        if 'apiSecret' in data:
            store.api_secret = data['apiSecret']
        if 'isActive' in data:
            store.is_active = bool(data['isActive'])
        
        db.session.commit()
        
        return jsonify(store.to_dict()), 200
    
    except Exception as e:
        db.session.rollback()
        print(f'Error updating store: {e}')
        return jsonify({'error': 'Failed to update store'}), 500
