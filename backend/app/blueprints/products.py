from flask import Blueprint, request, jsonify
from app import db
from app.models import Product, Store, MarketData
from app.utils import login_required_api
from app.services.scraper import scraper
from datetime import datetime, timezone


def _validate_scraped_price(price: float, cost_price: float, current_price: float, source: str = None) -> bool:
    """Validate if a scraped price makes sense for the product"""
    # Basic range check
    if price < 0.01 or price > 1000000:
        return False
    
    # Major retailers are more trusted - use slightly looser validation
    major_retailers = ['amazon', 'walmart', 'target', 'bestbuy', 'homedepot', 'wayfair']
    is_major_retailer = source and source.lower() in major_retailers
    
    # If we have cost price, competitor price should be at least 50% of cost
    # For major retailers, allow 40% minimum (they might have better deals)
    min_cost_ratio = 0.4 if is_major_retailer else 0.5
    if cost_price and cost_price > 0:
        if price < cost_price * min_cost_ratio:
            return False
        # Also reject if price is more than 10x cost (unless it's a luxury item)
        max_cost_ratio = 15 if is_major_retailer else 10
        if price > cost_price * max_cost_ratio and cost_price > 100:
            return False
    
    # If we have current price, competitor price should be within reasonable range
    # For major retailers, allow wider range (0.05x to 6x instead of 0.1x to 5x)
    if current_price and current_price > 0:
        if is_major_retailer:
            min_reasonable = current_price * 0.05
            max_reasonable = current_price * 6.0
        else:
            min_reasonable = current_price * 0.1
            max_reasonable = current_price * 5.0
        
        if price < min_reasonable or price > max_reasonable:
            return False
    
    return True
from flask_login import current_user
from sqlalchemy import and_

products_bp = Blueprint('products', __name__)


@products_bp.route('', methods=['GET'])
@login_required_api
def get_products():
    """Get all products for current user"""
    try:
        store_id = request.args.get('storeId')
        
        query = Product.query.join(Store).filter(Store.user_id == current_user.id)
        
        if store_id:
            query = query.filter(Product.store_id == store_id)
        
        products = query.order_by(Product.created_at.desc()).all()
        
        # Include last scan time for each product
        result = []
        for product in products:
            product_dict = product.to_dict(include_store=True)
            
            # Get most recent market data timestamp
            from app.models import MarketData
            latest_market_data = MarketData.query.filter_by(
                product_id=product.id
            ).order_by(MarketData.scraped_at.desc()).first()
            
            if latest_market_data:
                # Ensure timestamp is sent as UTC with timezone info for proper timezone handling
                if latest_market_data.scraped_at:
                    if latest_market_data.scraped_at.tzinfo is None:
                        # If timezone-naive, assume it's UTC and add timezone info
                        product_dict['lastScannedAt'] = latest_market_data.scraped_at.replace(tzinfo=timezone.utc).isoformat()
                    else:
                        product_dict['lastScannedAt'] = latest_market_data.scraped_at.isoformat()
                else:
                    product_dict['lastScannedAt'] = None
            else:
                product_dict['lastScannedAt'] = None
            
            result.append(product_dict)
        
        return jsonify(result), 200
    except Exception as e:
        print(f'Error fetching products: {e}')
        return jsonify({'error': 'Failed to fetch products'}), 500


@products_bp.route('', methods=['POST'])
@login_required_api
def create_product():
    """Create a new product"""
    try:
        data = request.get_json()
        store_id = data.get('storeId')
        name = data.get('name')
        sku = data.get('sku')
        category = data.get('category', 'Other')
        cost_price = float(data.get('costPrice', 0))
        current_price = float(data.get('currentPrice', 0))
        competitor_price = float(data.get('competitorPrice')) if data.get('competitorPrice') else None
        sales_velocity = float(data.get('salesVelocity', 0))
        
        # Verify store belongs to user
        store = Store.query.filter_by(id=store_id, user_id=current_user.id).first()
        if not store:
            return jsonify({'error': 'Store not found'}), 404
        
        product = Product(
            store_id=store_id,
            name=name,
            sku=sku,
            category=category,
            cost_price=cost_price,
            current_price=current_price,
            competitor_price=competitor_price,
            sales_velocity=sales_velocity
        )
        
        db.session.add(product)
        db.session.commit()
        
        return jsonify(product.to_dict(include_store=True)), 201
    
    except Exception as e:
        db.session.rollback()
        print(f'Error creating product: {e}')
        return jsonify({'error': 'Failed to create product'}), 500


@products_bp.route('/<product_id>', methods=['GET'])
@login_required_api
def get_product(product_id):
    """Get a single product"""
    try:
        product = Product.query.join(Store).filter(
            and_(Product.id == product_id, Store.user_id == current_user.id)
        ).first()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        return jsonify(product.to_dict(include_store=True)), 200
    except Exception as e:
        print(f'Error fetching product: {e}')
        return jsonify({'error': 'Failed to fetch product'}), 500


@products_bp.route('/<product_id>', methods=['PATCH'])
@login_required_api
def update_product(product_id):
    """Update a product"""
    try:
        product = Product.query.join(Store).filter(
            and_(Product.id == product_id, Store.user_id == current_user.id)
        ).first()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        data = request.get_json()
        
        if 'name' in data:
            product.name = data['name']
        if 'sku' in data:
            product.sku = data['sku']
        if 'category' in data:
            product.category = data['category']
        if 'costPrice' in data:
            product.cost_price = float(data['costPrice'])
        if 'currentPrice' in data:
            product.current_price = float(data['currentPrice'])
        if 'competitorPrice' in data:
            product.competitor_price = float(data['competitorPrice']) if data['competitorPrice'] else None
        if 'salesVelocity' in data:
            product.sales_velocity = float(data['salesVelocity'])
        
        db.session.commit()
        
        return jsonify(product.to_dict(include_store=True)), 200
    
    except Exception as e:
        db.session.rollback()
        print(f'Error updating product: {e}')
        return jsonify({'error': 'Failed to update product'}), 500


@products_bp.route('/<product_id>/market-data', methods=['GET'])
@login_required_api
def get_product_market_data(product_id):
    """Get market data history for a product"""
    try:
        # Verify product belongs to user
        product = Product.query.join(Store).filter(
            and_(Product.id == product_id, Store.user_id == current_user.id)
        ).first()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Get all market data for this product, ordered by date
        market_data = MarketData.query.filter_by(
            product_id=product_id
        ).order_by(MarketData.scraped_at.asc()).all()
        
        # If no market data, return empty structure
        if not market_data:
            return jsonify({
                'trend': [],
                'currentDistribution': [],
                'allPrices': [],
                'productPrice': product.current_price,
                'totalDataPoints': 0
            }), 200
        
        # Group by scan session (group by date and hour to capture individual scans)
        from collections import defaultdict
        from datetime import datetime, timedelta, timezone
        
        # Group by scan session - if scans are on the same day/hour, they're likely from the same scan
        scan_sessions = defaultdict(list)
        for md in market_data:
            if md.scraped_at:
                # Group by date and hour to capture individual scan sessions
                session_key = md.scraped_at.strftime('%Y-%m-%d %H:00')
                # Ensure timestamp is sent as UTC with timezone info for proper timezone handling
                # datetime.utcnow() returns timezone-naive, so we need to explicitly mark it as UTC
                if md.scraped_at.tzinfo is None:
                    # If timezone-naive, assume it's UTC and add timezone info
                    timestamp_str = md.scraped_at.replace(tzinfo=timezone.utc).isoformat()
                else:
                    timestamp_str = md.scraped_at.isoformat()
                scan_sessions[session_key].append({
                    'price': md.price,
                    'timestamp': timestamp_str,
                    'source': md.source
                })
        
        # Create trend data - show each scan session as a data point
        trend_data = []
        all_prices = []
        for session_key in sorted(scan_sessions.keys()):
            session_data = scan_sessions[session_key]
            prices = [item['price'] for item in session_data]
            if prices:
                # Use the first timestamp in the session as the date
                session_date = session_data[0]['timestamp'].split('T')[0]
                trend_data.append({
                    'date': session_date,
                    'timestamp': session_data[0]['timestamp'],
                    'average': sum(prices) / len(prices),
                    'min': min(prices),
                    'max': max(prices),
                    'count': len(prices),
                    'sources': len(set(item['source'] for item in session_data))
                })
                all_prices.extend(prices)
        
        # For distribution, use all prices from the most recent scan (or all if only one scan)
        # This gives a better view of the current market landscape
        if len(scan_sessions) == 1:
            # Only one scan - use all prices from that scan
            recent_prices = all_prices
        else:
            # Multiple scans - use the most recent scan's prices
            most_recent_session = sorted(scan_sessions.keys())[-1]
            recent_prices = [item['price'] for item in scan_sessions[most_recent_session]]
        
        # Fallback: if no recent prices, use all prices
        if not recent_prices:
            recent_prices = all_prices
        
        return jsonify({
            'trend': trend_data,
            'currentDistribution': recent_prices,
            'allPrices': all_prices,
            'productPrice': product.current_price,
            'totalDataPoints': len(market_data),
            'scanSessions': len(scan_sessions),
            'dataSource': 'MarketData table - scraped prices from Google Shopping'
        }), 200
    
    except Exception as e:
        print(f'Error fetching market data: {e}')
        return jsonify({'error': 'Failed to fetch market data'}), 500


@products_bp.route('/<product_id>', methods=['DELETE'])
@login_required_api
def delete_product(product_id):
    """Delete a product"""
    try:
        product = Product.query.join(Store).filter(
            and_(Product.id == product_id, Store.user_id == current_user.id)
        ).first()
        
        if not product:
            print(f'[Products] Delete failed: Product {product_id} not found for user {current_user.id}')
            return jsonify({'error': 'Product not found'}), 404
        
        product_name = product.name
        print(f'[Products] Deleting product: {product_name} (ID: {product_id})')
        
        # Delete the product (cascade will handle recommendations and market_data)
        db.session.delete(product)
        db.session.commit()
        
        print(f'[Products] Successfully deleted product: {product_name}')
        return jsonify({'success': True, 'message': 'Product deleted successfully'}), 200
    
    except Exception as e:
        db.session.rollback()
        import traceback
        print(f'[Products] Error deleting product {product_id}: {e}')
        print(traceback.format_exc())
        return jsonify({'error': f'Failed to delete product: {str(e)}'}), 500


@products_bp.route('/<product_id>/scan', methods=['POST'])
@login_required_api
def scan_prices(product_id):
    """Scan prices for a product"""
    try:
        product = Product.query.join(Store).filter(
            and_(Product.id == product_id, Store.user_id == current_user.id)
        ).first()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Use web scraping to get competitor prices - always force fresh scan
        print(f'[Products] Starting fresh web scraping for: {product.name}')
        scraped_prices = scraper.scrape_all_sources(product.name, product.category, force_refresh=True)
        
        if not scraped_prices:
            return jsonify({
                'error': 'No market data found. Please try again or manually enter competitor price.',
                'sources_checked': 0
            }), 404
        
        # Validate and filter scraped prices
        validated_prices = []
        rejected_by_source = {}
        for price_data in scraped_prices:
            if _validate_scraped_price(price_data.price, product.cost_price, product.current_price, price_data.source):
                validated_prices.append(price_data)
            else:
                source = price_data.source
                if source not in rejected_by_source:
                    rejected_by_source[source] = []
                rejected_by_source[source].append(price_data.price)
                print(f'[Products] Rejecting invalid price: ${price_data.price:.2f} from {price_data.source}')
        
        # Log validation summary
        if rejected_by_source:
            print(f'[Products] Validation summary - Rejected prices by source:')
            for source, prices in rejected_by_source.items():
                print(f'  {source}: {len(prices)} prices rejected')
        
        print(f'[Products] Validation summary - Accepted: {len(validated_prices)} prices from {len(set(p.source for p in validated_prices))} sources')
        
        if not validated_prices:
            return jsonify({
                'error': 'No valid market data found. The scraped prices may be for accessories, shipping, or unrelated products. Please try again or manually enter competitor price.',
                'sources_checked': len(scraped_prices),
                'total_prices_found': len(scraped_prices)
            }), 400
        
        # Save validated market data to database
        # Use current UTC time for all records in this scan session to ensure consistency
        current_utc_time = datetime.now(timezone.utc)
        
        for price_data in validated_prices:
            market_data = MarketData(
                product_id=product.id,
                source=price_data.source,
                price=price_data.price,
                url=price_data.url,
                scraped_at=current_utc_time  # Explicitly set timestamp to current time
            )
            db.session.add(market_data)
        
        # Calculate average competitor price from validated prices
        prices_list = [p.price for p in validated_prices]
        avg_price = sum(prices_list) / len(prices_list) if prices_list else None
        price_range = {
            'min': min(prices_list),
            'max': max(prices_list),
            'average': avg_price
        } if prices_list else None
        
        # Final validation before saving
        if avg_price:
            if product.cost_price > 0:
                if avg_price < product.cost_price * 0.5:
                    print(f'[Products] Rejecting average price ${avg_price:.2f} - too low compared to cost ${product.cost_price:.2f}')
                    avg_price = None
                elif avg_price > product.cost_price * 10 and product.cost_price > 100:
                    print(f'[Products] Rejecting average price ${avg_price:.2f} - too high compared to cost ${product.cost_price:.2f}')
                    avg_price = None
            
            if product.current_price > 0:
                min_reasonable = product.current_price * 0.1
                max_reasonable = product.current_price * 5.0
                if avg_price < min_reasonable or avg_price > max_reasonable:
                    print(f'[Products] Rejecting average price ${avg_price:.2f} - outside reasonable range')
                    avg_price = None
        
        # Update product with competitor price only if valid
        if avg_price:
            print(f'[Products] Saving competitor price: ${avg_price:.2f} for product: {product.name}')
            product.competitor_price = avg_price
            
            # Update any pending recommendations with the new market data
            from app.models import Recommendation
            pending_recs = Recommendation.query.filter_by(
                product_id=product.id,
                status='pending'
            ).all()
            
            if pending_recs:
                print(f'[Products] Found {len(pending_recs)} pending recommendations to update')
                # The recommendations will be refreshed when the user views the optimization page
                # or creates a new recommendation, which will use the fresh market data
        else:
            print(f'[Products] No valid competitor price found for product: {product.name}')
        
        db.session.commit()
        
        if not avg_price:
            return jsonify({
                'success': False,
                'error': 'No valid competitor prices found. The scraped prices may be for accessories, shipping, or unrelated products. Please try again or manually enter competitor price.',
                'sources': len(scraped_prices) if 'scraped_prices' in locals() else 0
            }), 400
        
        return jsonify({
            'success': True,
            'averagePrice': avg_price,
            'priceRange': price_range if 'price_range' in locals() else None,
            'sources': len(scraped_prices) if 'scraped_prices' in locals() else 0
        }), 200
    
    except Exception as e:
        db.session.rollback()
        print(f'Error scanning prices: {e}')
        return jsonify({'error': 'Failed to scan prices'}), 500
