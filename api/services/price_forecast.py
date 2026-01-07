"""
Price Forecasting with Monte Carlo Simulation
Advanced simulation for forecasting against specific target prices
"""

from typing import Dict, List, Tuple
import math
import random
from datetime import datetime, timedelta


class PriceForecaster:
    """
    Advanced Price Forecaster
    
    Uses Monte Carlo simulation with:
    - GBM (Geometric Brownian Motion) base model
    - Mean reversion component
    - Jump diffusion for tail events
    - Target price probability analysis
    """
    
    def __init__(
        self,
        current_price: float,
        annual_vol: float = 0.25,
        drift: float = 0.08,  # Expected annual return
        mean_reversion_speed: float = 0.1,
        long_term_mean: float = None,
        jump_intensity: float = 0.5,
        jump_mean: float = -0.03,
        jump_std: float = 0.05
    ):
        self.current_price = current_price
        self.annual_vol = annual_vol
        self.drift = drift
        self.mean_reversion_speed = mean_reversion_speed
        self.long_term_mean = long_term_mean or current_price
        self.jump_intensity = jump_intensity
        self.jump_mean = jump_mean
        self.jump_std = jump_std
    
    def simulate_path(
        self,
        days: int,
        steps_per_day: int = 1
    ) -> List[float]:
        """Simulate a single price path"""
        dt = 1.0 / (252 * steps_per_day)  # Time step in years
        sqrt_dt = math.sqrt(dt)
        
        daily_drift = self.drift * dt
        daily_vol = self.annual_vol * sqrt_dt
        
        path = [self.current_price]
        price = self.current_price
        
        for _ in range(days * steps_per_day):
            # Random components
            dW = random.gauss(0, 1)  # Brownian motion
            
            # Mean reversion component
            mean_rev = self.mean_reversion_speed * (math.log(self.long_term_mean) - math.log(price)) * dt
            
            # Jump component (Poisson process)
            jump = 0
            if random.random() < self.jump_intensity * dt:
                jump = random.gauss(self.jump_mean, self.jump_std)
            
            # Price evolution
            log_return = daily_drift + mean_rev + daily_vol * dW + jump
            price = price * math.exp(log_return)
            
            path.append(price)
        
        return path
    
    def run_simulation(
        self,
        days: int,
        num_paths: int = 1000,
        steps_per_day: int = 1
    ) -> Dict:
        """Run Monte Carlo simulation"""
        all_paths = []
        final_prices = []
        
        for _ in range(num_paths):
            path = self.simulate_path(days, steps_per_day)
            all_paths.append(path)
            final_prices.append(path[-1])
        
        # Calculate statistics
        final_prices.sort()
        mean_price = sum(final_prices) / len(final_prices)
        
        # Percentiles
        def percentile(data, p):
            idx = int(len(data) * p / 100)
            return data[min(idx, len(data) - 1)]
        
        return {
            "days": days,
            "num_paths": num_paths,
            "current_price": self.current_price,
            "mean_final": round(mean_price, 2),
            "median_final": round(percentile(final_prices, 50), 2),
            "percentile_5": round(percentile(final_prices, 5), 2),
            "percentile_25": round(percentile(final_prices, 25), 2),
            "percentile_75": round(percentile(final_prices, 75), 2),
            "percentile_95": round(percentile(final_prices, 95), 2),
            "min_price": round(min(final_prices), 2),
            "max_price": round(max(final_prices), 2),
            "expected_return_pct": round((mean_price / self.current_price - 1) * 100, 2),
            "paths_sample": all_paths[:10]  # First 10 paths for visualization
        }
    
    def probability_of_target(
        self,
        target_price: float,
        days: int,
        direction: str = "above",  # "above" or "below"
        num_paths: int = 5000
    ) -> Dict:
        """Calculate probability of reaching target price"""
        hits = 0
        hit_days = []
        final_prices = []
        max_prices = []
        min_prices = []
        
        for _ in range(num_paths):
            path = self.simulate_path(days)
            final_prices.append(path[-1])
            max_prices.append(max(path))
            min_prices.append(min(path))
            
            # Check if target was hit at any point
            if direction == "above":
                if max(path) >= target_price:
                    hits += 1
                    # Find first day target was hit
                    for i, p in enumerate(path):
                        if p >= target_price:
                            hit_days.append(i)
                            break
            else:  # below
                if min(path) <= target_price:
                    hits += 1
                    for i, p in enumerate(path):
                        if p <= target_price:
                            hit_days.append(i)
                            break
        
        probability = hits / num_paths
        avg_hit_day = sum(hit_days) / len(hit_days) if hit_days else None
        
        # Final price probability
        if direction == "above":
            final_prob = len([p for p in final_prices if p >= target_price]) / num_paths
        else:
            final_prob = len([p for p in final_prices if p <= target_price]) / num_paths
        
        return {
            "target_price": target_price,
            "current_price": self.current_price,
            "days": days,
            "direction": direction,
            "touch_probability": round(probability * 100, 2),
            "finish_probability": round(final_prob * 100, 2),
            "avg_days_to_hit": round(avg_hit_day, 1) if avg_hit_day else None,
            "paths_simulated": num_paths,
            "move_required_pct": round((target_price / self.current_price - 1) * 100, 2)
        }
    
    def forecast_with_targets(
        self,
        days: int,
        targets: List[float],
        num_paths: int = 5000
    ) -> Dict:
        """Comprehensive forecast with multiple price targets"""
        # Run base simulation
        sim_results = self.run_simulation(days, num_paths)
        
        # Analyze each target
        target_analysis = []
        for target in targets:
            direction = "above" if target > self.current_price else "below"
            analysis = self.probability_of_target(target, days, direction, num_paths)
            target_analysis.append(analysis)
        
        # Distribution buckets
        final_prices = []
        for _ in range(num_paths):
            path = self.simulate_path(days)
            final_prices.append(path[-1])
        
        # Create distribution
        bucket_size = self.current_price * 0.05  # 5% buckets
        min_bucket = int(min(final_prices) / bucket_size) * bucket_size
        max_bucket = int(max(final_prices) / bucket_size + 1) * bucket_size
        
        distribution = {}
        price = min_bucket
        while price <= max_bucket:
            count = len([p for p in final_prices if price <= p < price + bucket_size])
            distribution[f"${price:.0f}-${price + bucket_size:.0f}"] = round(count / num_paths * 100, 1)
            price += bucket_size
        
        return {
            "forecast_date": (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d"),
            "days_ahead": days,
            "simulation": sim_results,
            "targets": target_analysis,
            "price_distribution": distribution,
            "model_params": {
                "volatility": self.annual_vol,
                "drift": self.drift,
                "mean_reversion": self.mean_reversion_speed,
                "jump_intensity": self.jump_intensity
            }
        }


async def forecast_price(
    ticker: str,
    current_price: float,
    target_prices: List[float],
    days: int = 30,
    volatility: float = 0.25,
    num_simulations: int = 5000
) -> Dict:
    """API helper for price forecasting"""
    forecaster = PriceForecaster(
        current_price=current_price,
        annual_vol=volatility,
        drift=0.08
    )
    
    result = forecaster.forecast_with_targets(days, target_prices, num_simulations)
    result["ticker"] = ticker
    
    return result


async def quick_probability(
    current_price: float,
    target_price: float,
    days: int = 30,
    volatility: float = 0.25
) -> Dict:
    """Quick probability calculation"""
    forecaster = PriceForecaster(current_price=current_price, annual_vol=volatility)
    direction = "above" if target_price > current_price else "below"
    return forecaster.probability_of_target(target_price, days, direction)
