from flask import Blueprint, request, jsonify
from app import db
from app.models import Recommendation, Product, Store, MarketData
from app.utils import login_required_api
from app.services.scraper import scraper
from app.services.price_optimizer import price_optimizer, Product as OptimizerProduct
from flask_login import current_user
from sqlalchemy import and_
from datetime import datetime, timedelta

recommendations_bp = Blueprint('recommendations', __name__)


@recommendations_bp.route('', methods=['GET'])
@login_required_api
def get_recommendations():
    """Get all recommendations for current user"""
    try:
        status = request.args.get('status')
        product_id = request.args.get('productId')
        
        query = Recommendation.query.join(Product).join(Store).filter(
            Store.user_id == current_user.id
        )
        
        if status:
            query = query.filter(Recommendation.status == status)
        
        if product_id:
            query = query.filter(Recommendation.product_id == product_id)
        
        recommendations = query.order_by(Recommendation.created_at.desc()).all()
        
        # Include market data average for each recommendation
        result = []
        for rec in recommendations:
            rec_dict = rec.to_dict(include_product=True)
            
            # Get recent market data average (last 24 hours)
            twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
            recent_market_data = MarketData.query.filter(
                and_(
                    MarketData.product_id == rec.product_id,
                    MarketData.scraped_at >= twenty_four_hours_ago
                )
            ).all()
            
            if recent_market_data:
                market_prices = [md.price for md in recent_market_data]
                rec_dict['marketAveragePrice'] = sum(market_prices) / len(market_prices)
                rec_dict['marketPriceCount'] = len(market_prices)
            else:
                # Fallback to product competitor price if no recent market data
                rec_dict['marketAveragePrice'] = rec.product.competitor_price if rec.product.competitor_price else None
                rec_dict['marketPriceCount'] = 0
            
            result.append(rec_dict)
        
        return jsonify(result), 200
    except Exception as e:
        print(f'Error fetching recommendations: {e}')
        return jsonify({'error': 'Failed to fetch recommendations'}), 500


@recommendations_bp.route('', methods=['POST'])
@login_required_api
def create_recommendation():
    """Create a new price recommendation"""
    try:
        data = request.get_json()
        product_id = data.get('productId')
        
        if not product_id:
            return jsonify({'error': 'Product ID is required'}), 400
        
        # Verify product belongs to user
        product = Product.query.join(Store).filter(
            and_(Product.id == product_id, Store.user_id == current_user.id)
        ).first()
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        # Get recent market data (last 24 hours) first
        twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
        recent_market_data = MarketData.query.filter(
            and_(
                MarketData.product_id == product_id,
                MarketData.scraped_at >= twenty_four_hours_ago
            )
        ).all()
        
        # Check if pending recommendation already exists
        # If new market data is available (last 24 hours), update the recommendation
        existing_rec = Recommendation.query.filter_by(
            product_id=product_id,
            status='pending'
        ).first()
        
        # Check if there's fresh market data (scraped in last 24 hours)
        has_fresh_data = recent_market_data and len(recent_market_data) > 0
        
        # If recommendation exists, update it with fresh data instead of creating duplicate
        if existing_rec:
            if has_fresh_data:
                print(f'[Recommendations] Updating existing recommendation with fresh market data')
                # Continue to update the recommendation below
            else:
                # No fresh data, return existing recommendation
                return jsonify(existing_rec.to_dict(include_product=True)), 200
        
        competitor_prices = []
        
        if recent_market_data:
            competitor_prices = [md.price for md in recent_market_data]
        elif product.competitor_price:
            competitor_prices = [product.competitor_price]
        
        # If no competitor data, scrape it using web scraping
        if not competitor_prices:
            print(f'[Recommendations] Scraping prices for: {product.name}')
            scraped_prices = scraper.scrape_all_sources(product.name, product.category)
            
            # Validate scraped prices
            validated_prices = []
            for price_data in scraped_prices:
                # Validate against cost and current price
                if product.cost_price > 0 and price_data.price < product.cost_price * 0.5:
                    print(f'[Recommendations] Rejecting price ${price_data.price:.2f} - too low compared to cost')
                    continue
                if product.current_price > 0:
                    min_reasonable = product.current_price * 0.1
                    max_reasonable = product.current_price * 5.0
                    if price_data.price < min_reasonable or price_data.price > max_reasonable:
                        print(f'[Recommendations] Rejecting price ${price_data.price:.2f} - outside reasonable range')
                        continue
                validated_prices.append(price_data)
            
            if validated_prices:
                competitor_prices = [p.price for p in validated_prices]
                # Save scraped data
                for price_data in validated_prices:
                    market_data = MarketData(
                        product_id=product.id,
                        source=price_data.source,
                        price=price_data.price,
                        url=price_data.url
                    )
                    db.session.add(market_data)
                print(f'[Recommendations] Found {len(validated_prices)} valid competitor prices')
            else:
                print(f'[Recommendations] No valid prices found after validation')
        
        # Calculate price range
        price_range = None
        if competitor_prices:
            price_range = {
                'min': min(competitor_prices),
                'max': max(competitor_prices),
                'average': sum(competitor_prices) / len(competitor_prices)
            }
        
        # Generate optimization
        optimizer_product = OptimizerProduct(
            id=product.id,
            name=product.name,
            sku=product.sku,
            category=product.category,
            cost_price=product.cost_price,
            current_price=product.current_price,
            competitor_price=product.competitor_price,
            sales_velocity=product.sales_velocity
        )
        
        optimization = price_optimizer.optimize_price(
            optimizer_product,
            competitor_prices,
            price_range
        )
        
        # Update existing recommendation or create new one
        if existing_rec:
            # Update existing recommendation
            existing_rec.suggested_price = optimization['suggestedPrice']
            existing_rec.predicted_margin = optimization['predictedMargin']
            existing_rec.confidence_score = optimization['confidenceScore']
            existing_rec.rationale = optimization['rationale']
            existing_rec.risk_level = optimization['riskLevel']
            existing_rec.competitor_min_price = optimization['competitorMinPrice']
            existing_rec.competitor_max_price = optimization['competitorMaxPrice']
            existing_rec.market_position = optimization['marketPosition']
            existing_rec.strategy = optimization['strategy']
            existing_rec.implementation_timing = optimization['implementationTiming']
            existing_rec.revenue_impact = optimization['revenueImpact']
            recommendation = existing_rec
            print(f'[Recommendations] Updated existing recommendation for product: {product.name}')
        else:
            # Create new recommendation
            recommendation = Recommendation(
                product_id=product_id,
                suggested_price=optimization['suggestedPrice'],
                predicted_margin=optimization['predictedMargin'],
                confidence_score=optimization['confidenceScore'],
                rationale=optimization['rationale'],
                status='pending',
                risk_level=optimization['riskLevel'],
                competitor_min_price=optimization['competitorMinPrice'],
                competitor_max_price=optimization['competitorMaxPrice'],
                market_position=optimization['marketPosition'],
                strategy=optimization['strategy'],
                implementation_timing=optimization['implementationTiming'],
                revenue_impact=optimization['revenueImpact']
            )
            db.session.add(recommendation)
            print(f'[Recommendations] Created new recommendation for product: {product.name}')
        
        db.session.commit()
        
        return jsonify(recommendation.to_dict(include_product=True)), 200 if existing_rec else 201
    
    except Exception as e:
        db.session.rollback()
        print(f'Error creating recommendation: {e}')
        return jsonify({'error': 'Failed to create recommendation'}), 500


@recommendations_bp.route('/<recommendation_id>', methods=['PATCH'])
@login_required_api
def update_recommendation(recommendation_id):
    """Update a recommendation"""
    try:
        recommendation = Recommendation.query.join(Product).join(Store).filter(
            and_(Recommendation.id == recommendation_id, Store.user_id == current_user.id)
        ).first()
        
        if not recommendation:
            return jsonify({'error': 'Recommendation not found'}), 404
        
        data = request.get_json()
        
        # If applying recommendation, update product price
        if data.get('status') == 'applied' and data.get('applyPrice'):
            product = Product.query.get(recommendation.product_id)
            if product:
                product.current_price = recommendation.suggested_price
                db.session.add(product)
        
        # Update recommendation status
        if 'status' in data:
            recommendation.status = data['status']
        
        db.session.commit()
        
        return jsonify(recommendation.to_dict(include_product=True)), 200
    
    except Exception as e:
        db.session.rollback()
        print(f'Error updating recommendation: {e}')
        return jsonify({'error': 'Failed to update recommendation'}), 500

@recommendations_bp.route('/<recommendation_id>/elasticity', methods=['GET'])
@login_required_api
def get_elasticity_curve(recommendation_id):
    """Get elasticity curve data for a recommendation"""
    try:
        recommendation = Recommendation.query.join(Product).join(Store).filter(
            and_(Recommendation.id == recommendation_id, Store.user_id == current_user.id)
        ).first()
        
        if not recommendation:
            return jsonify({'error': 'Recommendation not found'}), 404
        
        product = recommendation.product
        
        # Use sales velocity as base demand, or default to 100 if not available
        base_demand = product.sales_velocity if product.sales_velocity > 0 else 100.0
        
        # Calculate elasticity curve
        optimizer_product = OptimizerProduct(
            id=product.id,
            name=product.name,
            sku=product.sku,
            category=product.category,
            cost_price=product.cost_price,
            current_price=product.current_price,
            competitor_price=product.competitor_price,
            sales_velocity=product.sales_velocity
        )
        
        curve_data = price_optimizer.calculate_elasticity_curve(
            optimizer_product,
            product.current_price,
            recommendation.suggested_price,
            base_demand
        )
        
        # Calculate demand at current and suggested prices
        current_margin = ((product.current_price - product.cost_price) / product.current_price) * 100 if product.current_price > 0 else 0
        elasticity = price_optimizer._estimate_elasticity(optimizer_product, current_margin)
        
        # Demand at current price (base)
        current_demand = base_demand
        
        # Demand at suggested price
        price_ratio = product.current_price / recommendation.suggested_price if recommendation.suggested_price > 0 else 1
        suggested_demand = base_demand * (price_ratio ** elasticity)
        suggested_demand = max(0, min(suggested_demand, base_demand * 3))
        
        # Calculate revenue and profit for current and suggested prices
        current_revenue = current_demand * product.current_price
        suggested_revenue = suggested_demand * recommendation.suggested_price
        revenue_change = suggested_revenue - current_revenue
        revenue_change_percent = ((revenue_change / current_revenue) * 100) if current_revenue > 0 else 0
        
        current_profit = current_demand * (product.current_price - product.cost_price)
        suggested_profit = suggested_demand * (recommendation.suggested_price - product.cost_price)
        profit_change = suggested_profit - current_profit
        profit_change_percent = ((profit_change / current_profit) * 100) if current_profit > 0 else 0
        
        # Calculate revenue and profit for each point in the curve
        curve_with_metrics = []
        for point in curve_data:
            revenue = point['demand'] * point['price']
            profit = point['demand'] * (point['price'] - product.cost_price)
            profit_margin = ((point['price'] - product.cost_price) / point['price'] * 100) if point['price'] > 0 else 0
            curve_with_metrics.append({
                'price': point['price'],
                'demand': point['demand'],
                'revenue': round(revenue, 2),
                'profit': round(profit, 2),
                'profitMargin': round(profit_margin, 1)
            })
        
        # Calculate optimal price using mathematical optimization
        # Profit(P) = Demand(P) × (P - Cost)
        #           = Base_Demand × (Current_Price / P)^Elasticity × (P - Cost)
        # Taking derivative and setting to zero gives:
        # Optimal_Price = Cost × Elasticity / (Elasticity - 1)
        # This formula is valid when Elasticity > 1 (price elastic demand)
        optimal_price = None
        optimal_demand = None
        optimal_profit = None
        
        try:
            if elasticity > 1.0 and product.cost_price > 0:
                # Calculate mathematically optimal price
                # Optimal_Price = Cost × Elasticity / (Elasticity - 1)
                optimal_price_calc = product.cost_price * elasticity / (elasticity - 1.0)
                
                # Ensure optimal price is within reasonable bounds
                optimal_price_calc = max(product.cost_price * 1.1, optimal_price_calc)  # At least 10% above cost
                optimal_price_calc = min(optimal_price_calc, product.current_price * 2.0)  # Not more than 2x current price
                
                # Calculate demand at optimal price
                optimal_price_ratio = product.current_price / optimal_price_calc if optimal_price_calc > 0 else 1
                optimal_demand_calc = base_demand * (optimal_price_ratio ** elasticity)
                optimal_demand_calc = max(0, min(optimal_demand_calc, base_demand * 3))
                
                # Calculate profit at optimal price
                optimal_profit_calc = optimal_demand_calc * (optimal_price_calc - product.cost_price)
                
                # Verify this is better than the discrete maximum
                discrete_max = max(curve_with_metrics, key=lambda x: x['profit'])
                if optimal_profit_calc >= discrete_max['profit']:
                    optimal_price = round(optimal_price_calc, 2)
                    optimal_demand = round(optimal_demand_calc, 1)
                    optimal_profit = round(optimal_profit_calc, 2)
                else:
                    # Use discrete maximum if it's better (edge case)
                    optimal_price = discrete_max['price']
                    optimal_demand = discrete_max['demand']
                    optimal_profit = discrete_max['profit']
            else:
                # If elasticity <= 1 or cost_price is 0, demand is inelastic - higher price generally better
                # Use the discrete maximum from the curve
                optimal_point = max(curve_with_metrics, key=lambda x: x['profit'])
                optimal_price = optimal_point['price']
                optimal_demand = optimal_point['demand']
                optimal_profit = optimal_point['profit']
        except (ZeroDivisionError, ValueError, TypeError) as e:
            # Fallback to discrete maximum if calculation fails
            print(f'Error calculating optimal price mathematically: {e}, using discrete maximum')
            optimal_point = max(curve_with_metrics, key=lambda x: x['profit'])
            optimal_price = optimal_point['price']
            optimal_demand = optimal_point['demand']
            optimal_profit = optimal_point['profit']
        
        return jsonify({
            'curve': curve_with_metrics,
            'currentPrice': product.current_price,
            'suggestedPrice': recommendation.suggested_price,
            'currentDemand': round(current_demand, 1),
            'suggestedDemand': round(suggested_demand, 1),
            'demandChange': round(suggested_demand - current_demand, 1),
            'demandChangePercent': round(((suggested_demand - current_demand) / current_demand * 100) if current_demand > 0 else 0, 1),
            'baseDemand': base_demand,
            'costPrice': product.cost_price,
            'currentRevenue': round(current_revenue, 2),
            'suggestedRevenue': round(suggested_revenue, 2),
            'revenueChange': round(revenue_change, 2),
            'revenueChangePercent': round(revenue_change_percent, 1),
            'currentProfit': round(current_profit, 2),
            'suggestedProfit': round(suggested_profit, 2),
            'profitChange': round(profit_change, 2),
            'profitChangePercent': round(profit_change_percent, 1),
            'optimalPrice': optimal_price,
            'optimalProfit': optimal_profit,
            'optimalDemand': optimal_demand
        }), 200
    
    except Exception as e:
        print(f'Error fetching elasticity curve: {e}')
        return jsonify({'error': 'Failed to fetch elasticity curve'}), 500

