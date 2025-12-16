from flask import Flask, request, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_cors import CORS
from app.config import Config

db = SQLAlchemy()
login_manager = LoginManager()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'main.signin'
    login_manager.login_message = 'Please log in to access this page.'
    
    # Set up user loader (must be after db is initialized)
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)
    
    # Enable CORS for React frontend
    CORS(app, supports_credentials=True, origins=['http://localhost:3000', 'http://localhost:3001', 'http://localhost:3002'])
    
    # Security headers middleware
    @app.after_request
    def set_security_headers(response):
        # Content Security Policy with Trusted Types support
        # Note: 'unsafe-inline' is required for Tailwind CDN and inline scripts
        # For full Trusted Types enforcement, refactor to remove inline scripts and use event listeners
        # script-src-attr is not set to 'none' to allow onclick handlers (can be enabled after refactoring)
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https:; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers['Content-Security-Policy'] = csp
        
        # X-Frame-Options (prevents clickjacking)
        response.headers['X-Frame-Options'] = 'DENY'
        
        # X-Content-Type-Options
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Cross-Origin-Opener-Policy
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        
        # Cross-Origin-Embedder-Policy (only in production, can break some features)
        if app.config.get('ENFORCE_COEP'):
            response.headers['Cross-Origin-Embedder-Policy'] = 'require-corp'
        
        # HSTS (strong policy - only in production with HTTPS)
        if request.is_secure or app.config.get('FORCE_HTTPS'):
            # max-age=31536000 = 1 year, includeSubDomains, preload
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response
    
    # HTTPS redirect (only in production)
    @app.before_request
    def force_https():
        # Check if we should force HTTPS (production only)
        if app.config.get('FORCE_HTTPS'):
            # Check if request is not secure (HTTP)
            if not request.is_secure:
                # Check for X-Forwarded-Proto header (common in reverse proxies)
                if request.headers.get('X-Forwarded-Proto') == 'https':
                    # Request is actually HTTPS, just not detected as secure
                    return None
                # Redirect to HTTPS
                url = request.url.replace('http://', 'https://', 1)
                return redirect(url, code=301)
    
    # Register blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.auth import auth_bp
    from app.blueprints.products import products_bp
    from app.blueprints.stores import stores_bp
    from app.blueprints.recommendations import recommendations_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    # Frontend auth routes are handled in main_bp
    app.register_blueprint(products_bp, url_prefix='/api/products')
    app.register_blueprint(stores_bp, url_prefix='/api/stores')
    app.register_blueprint(recommendations_bp, url_prefix='/api/recommendations')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
