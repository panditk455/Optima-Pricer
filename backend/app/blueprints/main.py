from flask import Blueprint, render_template, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import Product, Store, Recommendation
from app.utils import login_required_api
from sqlalchemy import and_, func
from datetime import datetime, timedelta, timezone

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Redirect to dashboard if authenticated, otherwise to signin"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.signin'))


@main_bp.route('/auth/signin')
def signin():
    """Sign in page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('auth/signin.html')


@main_bp.route('/auth/register')
def register():
    """Register page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('auth/register.html')


@main_bp.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html')


@main_bp.route('/products')
@login_required
def products():
    """Products page"""
    return render_template('products.html')


@main_bp.route('/optimization')
@login_required
def optimization():
    """Optimization page"""
    return render_template('optimization.html')


@main_bp.route('/settings')
@login_required
def settings():
    """Settings page"""
    return render_template('settings.html')


@main_bp.route('/api/dashboard')
@login_required_api
def dashboard_data():
    """Get dashboard statistics and data"""
    try:
        # Get all products for current user
        products = Product.query.join(Store).filter(
            Store.user_id == current_user.id
        ).all()
        
        # Calculate metrics
        total_products = len(products)
        
        # Calculate average margin
        avg_margin = 0
        if products:
            products_with_valid_prices = [
                p for p in products 
                if p.current_price and p.current_price > 0 and p.cost_price is not None
            ]
            if products_with_valid_prices:
                total_margin = sum(
                    ((p.current_price - p.cost_price) / p.current_price * 100) 
                    for p in products_with_valid_prices
                )
                avg_margin = total_margin / len(products_with_valid_prices)
        
        # Get pending recommendations (actionable items)
        pending_recommendations = Recommendation.query.join(Product).join(Store).filter(
            and_(
                Store.user_id == current_user.id,
                Recommendation.status == 'pending'
            )
        ).all()
        
        pending_recommendations_count = len(pending_recommendations)
        
        # Calculate potential revenue uplift from pending recommendations
        potential_uplift = 0
        for rec in pending_recommendations:
            try:
                if hasattr(rec, 'revenue_impact') and rec.revenue_impact and rec.revenue_impact > 0:
                    potential_uplift += rec.revenue_impact
            except (AttributeError, TypeError):
                # Skip if revenue_impact doesn't exist or is invalid
                pass
        
        # Count products that need scanning (haven't been scanned in last 7 days or never scanned)
        from app.models import MarketData
        
        products_needing_scan = 0
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        
        for product in products:
            try:
                latest_market_data = MarketData.query.filter_by(
                    product_id=product.id
                ).order_by(MarketData.scraped_at.desc()).first()
                
                if not latest_market_data:
                    products_needing_scan += 1
                else:
                    # Handle timezone-aware and timezone-naive datetimes
                    scraped_at = latest_market_data.scraped_at
                    if scraped_at:
                        # Make timezone-aware if it's naive
                        if scraped_at.tzinfo is None:
                            scraped_at = scraped_at.replace(tzinfo=timezone.utc)
                        # Compare with timezone-aware datetime
                        if scraped_at < seven_days_ago:
                            products_needing_scan += 1
                    else:
                        products_needing_scan += 1
            except Exception as e:
                # If there's an error checking this product, assume it needs scanning
                print(f'Error checking scan status for product {product.id}: {e}')
                products_needing_scan += 1
        
        return jsonify({
            'metrics': {
                'totalProducts': total_products,
                'avgMargin': round(avg_margin, 1),
                'pendingRecommendations': pending_recommendations_count,
                'potentialUplift': round(potential_uplift, 2),
                'productsNeedingScan': products_needing_scan
            }
        }), 200
        
    except Exception as e:
        print(f'Error fetching dashboard data: {e}')
        return jsonify({'error': 'Failed to fetch dashboard data'}), 500


@main_bp.route('/api/test-scrape')
@login_required_api
def test_scrape():
    """Test endpoint to verify web scraping is working"""
    try:
        from app.services.scraper import scraper
        
        test_product = request.args.get('product', 'iPhone 15')
        test_category = request.args.get('category', 'Electronics')
        test_cost = float(request.args.get('cost', '1200'))
        test_current = float(request.args.get('current', '1500'))
        
        results = {
            'product': test_product,
            'category': test_category,
            'scraping_results': {}
        }
        
        # Test web scraper
        print(f'[Test] Testing web scraper for: {test_product}')
        scraped_prices = scraper.scrape_all_sources(test_product, test_category)
        
        # Validate prices
        validated_prices = []
        for price_data in scraped_prices:
            # Basic validation
            if price_data.price < 0.01 or price_data.price > 1000000:
                continue
            if test_cost > 0 and price_data.price < test_cost * 0.5:
                continue
            if test_current > 0:
                min_reasonable = test_current * 0.1
                max_reasonable = test_current * 5.0
                if price_data.price < min_reasonable or price_data.price > max_reasonable:
                    continue
            validated_prices.append(price_data)
        
        results['scraping_results'] = {
            'total_prices_found': len(scraped_prices),
            'validated_prices': len(validated_prices),
            'prices': [
                {
                    'price': p.price,
                    'source': p.source,
                    'url': p.url,
                    'validated': p in validated_prices
                }
                for p in scraped_prices[:20]  # Show first 20
            ],
            'validated_price_list': [p.price for p in validated_prices],
            'average_price': sum([p.price for p in validated_prices]) / len(validated_prices) if validated_prices else None
        }
        
        return jsonify(results), 200
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500
