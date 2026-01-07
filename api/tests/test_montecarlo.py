"""
Tests for Monte Carlo simulation
Validates simulation accuracy and convergence
"""

import pytest
import sys
sys.path.insert(0, '..')

from services.montecarlo import (
    simulate_gbm_paths,
    calculate_strategy_payoff,
    monte_carlo_pop,
    price_distribution
)


class TestGBMSimulation:
    """Tests for Geometric Brownian Motion price paths"""
    
    def test_paths_start_at_spot(self):
        """All paths should start at the spot price"""
        paths = simulate_gbm_paths(
            spot=100,
            drift=0.05,
            volatility=0.20,
            days=30,
            num_paths=100,
            seed=42
        )
        
        for path in paths:
            assert path[0] == 100
    
    def test_correct_number_of_paths(self):
        """Should generate requested number of paths"""
        paths = simulate_gbm_paths(
            spot=100,
            drift=0.05,
            volatility=0.20,
            days=30,
            num_paths=500,
            seed=42
        )
        
        assert len(paths) == 500
    
    def test_correct_path_length(self):
        """Each path should have days + 1 points"""
        paths = simulate_gbm_paths(
            spot=100,
            drift=0.05,
            volatility=0.20,
            days=30,
            num_paths=10,
            seed=42
        )
        
        for path in paths:
            assert len(path) == 31  # 30 days + starting point
    
    def test_reproducibility_with_seed(self):
        """Same seed should produce same paths"""
        paths1 = simulate_gbm_paths(
            spot=100, drift=0.05, volatility=0.20,
            days=10, num_paths=5, seed=42
        )
        paths2 = simulate_gbm_paths(
            spot=100, drift=0.05, volatility=0.20,
            days=10, num_paths=5, seed=42
        )
        
        for p1, p2 in zip(paths1, paths2):
            for v1, v2 in zip(p1, p2):
                assert v1 == v2
    
    def test_prices_stay_positive(self):
        """GBM should never produce negative prices"""
        paths = simulate_gbm_paths(
            spot=100,
            drift=0.05,
            volatility=0.50,  # High vol
            days=252,  # 1 year
            num_paths=1000,
            seed=42
        )
        
        for path in paths:
            for price in path:
                assert price > 0


class TestPayoffCalculation:
    """Tests for strategy payoff calculation"""
    
    def test_long_call_payoff_itm(self):
        """Long call should profit when price > strike + premium"""
        legs = [{
            "option_type": "call",
            "position": "long",
            "strike": 100,
            "premium": 5,
            "quantity": 1
        }]
        
        # Price = 110, Strike = 100, Premium = 5
        # Payoff = (110 - 100 - 5) * 100 = 500
        payoff = calculate_strategy_payoff(110, legs)
        assert payoff == 500
    
    def test_long_call_payoff_otm(self):
        """Long call should lose premium when OTM"""
        legs = [{
            "option_type": "call",
            "position": "long",
            "strike": 100,
            "premium": 5,
            "quantity": 1
        }]
        
        # Price = 90, Strike = 100, Premium = 5
        # Payoff = (0 - 5) * 100 = -500
        payoff = calculate_strategy_payoff(90, legs)
        assert payoff == -500
    
    def test_long_put_payoff_itm(self):
        """Long put should profit when price < strike - premium"""
        legs = [{
            "option_type": "put",
            "position": "long",
            "strike": 100,
            "premium": 5,
            "quantity": 1
        }]
        
        # Price = 90, Strike = 100, Premium = 5
        # Payoff = (100 - 90 - 5) * 100 = 500
        payoff = calculate_strategy_payoff(90, legs)
        assert payoff == 500
    
    def test_short_call_payoff(self):
        """Short call should profit from premium when OTM"""
        legs = [{
            "option_type": "call",
            "position": "short",
            "strike": 100,
            "premium": 5,
            "quantity": 1
        }]
        
        # Price = 90 (OTM), collect premium
        # Payoff = -(0 - 5) * 100 = 500
        payoff = calculate_strategy_payoff(90, legs)
        assert payoff == 500
    
    def test_spread_payoff(self):
        """Bull call spread should have limited profit/loss"""
        legs = [
            {"option_type": "call", "position": "long", "strike": 100, "premium": 5, "quantity": 1},
            {"option_type": "call", "position": "short", "strike": 110, "premium": 2, "quantity": 1}
        ]
        
        # Net debit = 5 - 2 = 3
        # Max profit at 110+ = (110-100) - 3 = 7 per share, *100 = 700
        payoff_high = calculate_strategy_payoff(120, legs)
        assert payoff_high == 700
        
        # Max loss below 100 = -3 * 100 = -300
        payoff_low = calculate_strategy_payoff(90, legs)
        assert payoff_low == -300


class TestMonteCarloPoP:
    """Tests for probability of profit calculation"""
    
    def test_pop_returns_valid_percentage(self):
        """PoP should be between 0 and 100"""
        result = monte_carlo_pop(
            spot=100,
            volatility=0.25,
            days=30,
            legs=[{
                "option_type": "call",
                "position": "long",
                "strike": 100,
                "premium": 5,
                "quantity": 1
            }],
            num_simulations=100
        )
        
        assert 0 <= result.pop <= 100
    
    def test_deep_itm_high_pop(self):
        """Deep ITM option should have high PoP"""
        result = monte_carlo_pop(
            spot=150,  # Far above strike
            volatility=0.10,  # Low vol
            days=5,  # Short time
            legs=[{
                "option_type": "call",
                "position": "long",
                "strike": 100,
                "premium": 5,
                "quantity": 1
            }],
            num_simulations=1000
        )
        
        # Should be very likely to profit
        assert result.pop > 90
    
    def test_deep_otm_low_pop(self):
        """Deep OTM option should have low PoP"""
        result = monte_carlo_pop(
            spot=50,  # Far below strike
            volatility=0.10,
            days=5,
            legs=[{
                "option_type": "call",
                "position": "long",
                "strike": 100,
                "premium": 5,
                "quantity": 1
            }],
            num_simulations=1000
        )
        
        # Very unlikely to profit
        assert result.pop < 10


class TestPriceDistribution:
    """Tests for price distribution histogram"""
    
    def test_distribution_has_histogram(self):
        """Distribution should return histogram data"""
        final_prices = [100 + i for i in range(100)]
        dist = price_distribution(final_prices, bins=10)
        
        assert "histogram" in dist
        assert len(dist["histogram"]) == 10
    
    def test_distribution_frequencies_sum_to_one(self):
        """Histogram frequencies should sum to approximately 1"""
        final_prices = [100 + i for i in range(100)]
        dist = price_distribution(final_prices, bins=10)
        
        total_freq = sum(b["frequency"] for b in dist["histogram"])
        assert 0.99 < total_freq <= 1.01


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
