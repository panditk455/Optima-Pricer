import os
from datetime import timedelta


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///optima_pricer.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    
    # Scraping configuration
    SCRAPING_TIMEOUT = 30  # seconds
    SCRAPING_CACHE_DURATION = 3600  # 1 hour in seconds
    
    # Security configuration (for production)
    # Set FORCE_HTTPS = True in production to enable HTTPS redirect and HSTS
    # Set ENFORCE_COEP = True to enable Cross-Origin-Embedder-Policy (may break some features)
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() == 'true'
    ENFORCE_COEP = os.environ.get('ENFORCE_COEP', 'False').lower() == 'true'

