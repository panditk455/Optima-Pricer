from datetime import datetime
from app import db
from flask_login import UserMixin
import uuid


def generate_id():
    return str(uuid.uuid4())


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String, primary_key=True, default=generate_id)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    stores = db.relationship('Store', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<User {self.email}>'


class Store(db.Model):
    __tablename__ = 'stores'
    
    id = db.Column(db.String, primary_key=True, default=generate_id)
    user_id = db.Column(db.String, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    platform = db.Column(db.String(50), nullable=False)  # "shopify", "amazon", "ebay", "etsy", "other"
    api_key = db.Column(db.String(255), nullable=True)
    api_secret = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    products = db.relationship('Product', backref='store', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'userId': self.user_id,
            'name': self.name,
            'platform': self.platform,
            'apiKey': self.api_key,
            'apiSecret': self.api_secret,
            'isActive': self.is_active,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
            '_count': {
                'products': len(self.products)
            }
        }
    
    def __repr__(self):
        return f'<Store {self.name}>'


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.String, primary_key=True, default=generate_id)
    store_id = db.Column(db.String, db.ForeignKey('stores.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    sku = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100), default='Other', nullable=False)
    cost_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    competitor_price = db.Column(db.Float, nullable=True)
    sales_velocity = db.Column(db.Float, default=0.0, nullable=False)  # Units per week
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    recommendations = db.relationship('Recommendation', backref='product', lazy=True, cascade='all, delete-orphan')
    market_data = db.relationship('MarketData', backref='product', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self, include_store=False):
        data = {
            'id': self.id,
            'storeId': self.store_id,
            'name': self.name,
            'sku': self.sku,
            'category': self.category,
            'costPrice': self.cost_price,
            'currentPrice': self.current_price,
            'competitorPrice': self.competitor_price,
            'salesVelocity': self.sales_velocity,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_store:
            data['store'] = self.store.to_dict() if self.store else None
        return data
    
    def __repr__(self):
        return f'<Product {self.name}>'


class Recommendation(db.Model):
    __tablename__ = 'recommendations'
    
    id = db.Column(db.String, primary_key=True, default=generate_id)
    product_id = db.Column(db.String, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    suggested_price = db.Column(db.Float, nullable=False)
    predicted_margin = db.Column(db.Float, nullable=False)
    confidence_score = db.Column(db.Integer, nullable=False)  # 0-100
    rationale = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(50), default='pending', nullable=False)  # "pending", "applied", "rejected"
    risk_level = db.Column(db.String(50), default='low', nullable=False)  # "low", "medium", "high"
    competitor_min_price = db.Column(db.Float, nullable=True)
    competitor_max_price = db.Column(db.Float, nullable=True)
    market_position = db.Column(db.String(100), nullable=True)
    strategy = db.Column(db.String(100), nullable=True)
    implementation_timing = db.Column(db.String(255), nullable=True)
    revenue_impact = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self, include_product=False):
        data = {
            'id': self.id,
            'productId': self.product_id,
            'suggestedPrice': self.suggested_price,
            'predictedMargin': self.predicted_margin,
            'confidenceScore': self.confidence_score,
            'rationale': self.rationale,
            'status': self.status,
            'riskLevel': self.risk_level,
            'competitorMinPrice': self.competitor_min_price,
            'competitorMaxPrice': self.competitor_max_price,
            'marketPosition': self.market_position,
            'strategy': self.strategy,
            'implementationTiming': self.implementation_timing,
            'revenueImpact': self.revenue_impact,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_product:
            data['product'] = self.product.to_dict(include_store=True) if self.product else None
        return data
    
    def __repr__(self):
        return f'<Recommendation {self.id}>'


class MarketData(db.Model):
    __tablename__ = 'market_data'
    
    id = db.Column(db.String, primary_key=True, default=generate_id)
    product_id = db.Column(db.String, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    source = db.Column(db.String(100), nullable=False)  # Retailer name extracted from Google Shopping (e.g., "amazon", "walmart", "target", "bestbuy", "homedepot", "wayfair", "ebay", "etsy", "google_shopping", etc.)
    price = db.Column(db.Float, nullable=False)
    url = db.Column(db.String(500), nullable=True)
    scraped_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'productId': self.product_id,
            'source': self.source,
            'price': self.price,
            'url': self.url,
            'scrapedAt': self.scraped_at.isoformat() if self.scraped_at else None,
        }
    
    def __repr__(self):
        return f'<MarketData {self.source} - {self.price}>'
