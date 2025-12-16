from typing import List, Optional, Dict


class Product:
    """Product data structure for price optimization"""
    def __init__(self, id: str, name: str, sku: str, category: str, 
                 cost_price: float, current_price: float, 
                 competitor_price: Optional[float], sales_velocity: float):
        self.id = id
        self.name = name
        self.sku = sku
        self.category = category
        self.cost_price = cost_price
        self.current_price = current_price
        self.competitor_price = competitor_price
        self.sales_velocity = sales_velocity


class PriceOptimizer:
    """Price optimization engine"""
    
    def optimize_price(self, product: Product, competitor_prices: List[float], 
                      market_data: Optional[Dict[str, float]] = None) -> Dict:
        """Calculate optimal price based on multiple factors"""
        
        current_price = product.current_price
        cost_price = product.cost_price
        current_margin = ((current_price - cost_price) / current_price) * 100 if current_price > 0 else 0
        
        # Filter out invalid competitor prices before calculating statistics
        # Remove prices that are clearly wrong (too far from current price)
        if competitor_prices and current_price > 0:
            min_reasonable = current_price * 0.1
            max_reasonable = current_price * 5.0
            filtered_prices = [
                p for p in competitor_prices 
                if min_reasonable <= p <= max_reasonable
            ]
            if filtered_prices:
                competitor_prices = filtered_prices
                print(f'[Price Optimizer] Filtered competitor prices: {len(competitor_prices)} valid prices')
            else:
                print(f'[Price Optimizer] All competitor prices filtered out as invalid, using fallback')
        
        # Calculate market statistics
        avg_competitor_price = (sum(competitor_prices) / len(competitor_prices)) if competitor_prices else current_price
        min_competitor_price = min(competitor_prices) if competitor_prices else current_price * 0.9
        max_competitor_price = max(competitor_prices) if competitor_prices else current_price * 1.15
        
        # When we have fresh market data (competitor_prices from recent scan),
        # prioritize matching the market average price
        # This ensures the optimized price matches the newly scraped price
        if competitor_prices and len(competitor_prices) > 0:
            # Use the average scraped price as the base suggested price
            suggested_price = avg_competitor_price
            strategy = 'Match Market'
            rationale = f'Price matched to market average from {len(competitor_prices)} scraped sources. Aligning with current market conditions.'
            confidence_score = 85
            risk_level = 'low'
            market_position = 'Competitive'
        else:
            # Fallback to current price if no market data
            suggested_price = current_price
            strategy = 'No Data'
            rationale = 'No recent market data available. Using current price.'
            confidence_score = 50
            risk_level = 'medium'
            market_position = 'Unknown'
        
        # Price difference analysis (for display purposes)
        price_diff = avg_competitor_price - current_price
        price_diff_percent = (price_diff / current_price) * 100 if current_price > 0 else 0
        
        # Ensure minimum margin protection (20%) - but only if it's a small adjustment
        # If the market price is significantly below cost, we still want to show it
        # but flag it as high risk
        min_price = cost_price * 1.2
        if suggested_price < min_price:
            # Only adjust if the difference is small (within 10% of cost)
            # Otherwise, keep the market price but flag as high risk
            if suggested_price >= cost_price * 1.1:
                suggested_price = min_price
                rationale += ' Adjusted to maintain minimum 20% margin.'
                risk_level = 'medium'
            else:
                rationale += ' WARNING: Market price is below recommended minimum margin. Consider reviewing cost structure.'
                risk_level = 'high'
        
        # Calculate predicted margin
        predicted_margin = ((suggested_price - cost_price) / suggested_price) * 100 if suggested_price > 0 else 0
        
        # Calculate revenue impact (monthly estimate)
        price_change = suggested_price - current_price
        revenue_impact = product.sales_velocity * price_change * 4  # Weekly to monthly
        
        # Determine implementation timing
        if risk_level == 'high' or abs(price_change) > current_price * 0.1:
            implementation_timing = 'Phased - Monitor closely'
        elif price_change > 0 and current_margin < 30:
            implementation_timing = 'Immediate - High opportunity'
        else:
            implementation_timing = 'Immediate'
        
        return {
            'suggestedPrice': round(suggested_price, 2),
            'predictedMargin': round(predicted_margin, 1),
            'confidenceScore': confidence_score,
            'rationale': rationale,
            'riskLevel': risk_level,
            'strategy': strategy,
            'marketPosition': market_position,
            'implementationTiming': implementation_timing,
            'revenueImpact': round(revenue_impact),
            'competitorMinPrice': round(min_competitor_price, 2),
            'competitorMaxPrice': round(max_competitor_price, 2),
        }
    
    def _estimate_elasticity(self, product: Product, current_margin: float) -> float:
        """Estimate price elasticity (simplified model)"""
        elasticity = 1.5  # Base elasticity
        
        # Category adjustments
        luxury_categories = ['Shapewear', 'Loungewear']
        if product.category in luxury_categories:
            elasticity -= 0.3
        
        # Margin adjustments
        if current_margin > 50:
            elasticity -= 0.5
        elif current_margin < 30:
            elasticity += 0.3
        
        # Sales velocity adjustments
        if product.sales_velocity > 50:
            elasticity += 0.2
        
        return max(0.5, min(3.0, elasticity))
    
    def calculate_elasticity_curve(self, product: Product, current_price: float, 
                                   suggested_price: float, base_demand: float = 100.0) -> List[Dict]:
        """
        Calculate elasticity curve data points showing price vs demand relationship.
        
        Args:
            product: Product object
            current_price: Current product price
            suggested_price: Suggested price from recommendation
            base_demand: Base demand at current price (default 100 for percentage)
        
        Returns:
            List of dicts with 'price' and 'demand' keys for curve visualization
        """
        current_margin = ((current_price - product.cost_price) / current_price) * 100 if current_price > 0 else 0
        elasticity = self._estimate_elasticity(product, current_margin)
        
        # Calculate price range for the curve (±50% from current price, but within reasonable bounds)
        min_price = max(product.cost_price * 0.8, current_price * 0.5)
        max_price = min(current_price * 2.0, current_price * 1.5)
        
        # Generate 20 data points for smooth curve
        num_points = 20
        price_points = []
        demand_points = []
        
        for i in range(num_points):
            # Price at this point
            price = min_price + (max_price - min_price) * (i / (num_points - 1))
            
            # Calculate demand using price elasticity formula: Q2 = Q1 * (P1/P2)^elasticity
            # Where Q1 is base demand at current price P1
            price_ratio = current_price / price if price > 0 else 1
            demand = base_demand * (price_ratio ** elasticity)
            
            # Ensure demand doesn't go negative or too high
            demand = max(0, min(demand, base_demand * 3))
            
            price_points.append(round(price, 2))
            demand_points.append(round(demand, 1))
        
        # Create curve data points
        curve_data = [
            {'price': price, 'demand': demand}
            for price, demand in zip(price_points, demand_points)
        ]
        
        return curve_data


# Singleton instance
price_optimizer = PriceOptimizer()
