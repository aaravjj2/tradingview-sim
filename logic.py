"""
Logic Module for Options Supergraph Dashboard
Contains Black-Scholes pricing, Greeks calculations, and P/L computations
"""

import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from config import DEFAULT_RISK_FREE_RATE, NUM_PRICE_POINTS, PRICE_RANGE_PERCENT


@dataclass
class OptionLeg:
    """Represents a single option leg in a strategy"""
    option_type: str  # 'call', 'put', or 'stock'
    position: str  # 'long' or 'short'
    strike: float
    premium: float
    quantity: int
    expiration_days: int
    iv: float = 0.30
    
    @property
    def sign(self) -> int:
        """Returns +1 for long positions, -1 for short positions"""
        return 1 if self.position == "long" else -1


class BlackScholes:
    """Black-Scholes Option Pricing Model"""
    
    @staticmethod
    def d1(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d1 parameter"""
        if T <= 0 or sigma <= 0:
            return 0.0
        return (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    
    @staticmethod
    def d2(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d2 parameter"""
        if T <= 0 or sigma <= 0:
            return 0.0
        return BlackScholes.d1(S, K, T, r, sigma) - sigma * np.sqrt(T)
    
    @staticmethod
    def call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Black-Scholes call option price
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration in years
            r: Risk-free interest rate
            sigma: Implied volatility
            
        Returns:
            Theoretical call option price
        """
        if T <= 0:
            return max(0, S - K)  # Intrinsic value at expiration
        
        d1 = BlackScholes.d1(S, K, T, r, sigma)
        d2 = BlackScholes.d2(S, K, T, r, sigma)
        
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    
    @staticmethod
    def put_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """
        Calculate Black-Scholes put option price
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration in years
            r: Risk-free interest rate
            sigma: Implied volatility
            
        Returns:
            Theoretical put option price
        """
        if T <= 0:
            return max(0, K - S)  # Intrinsic value at expiration
        
        d1 = BlackScholes.d1(S, K, T, r, sigma)
        d2 = BlackScholes.d2(S, K, T, r, sigma)
        
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    @staticmethod
    def delta(S: float, K: float, T: float, r: float, sigma: float, 
              option_type: str) -> float:
        """Calculate option Delta (rate of change of option price vs stock price)"""
        if T <= 0:
            if option_type == "call":
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0
        
        d1 = BlackScholes.d1(S, K, T, r, sigma)
        if option_type == "call":
            return norm.cdf(d1)
        else:
            return norm.cdf(d1) - 1
    
    @staticmethod
    def gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate option Gamma (rate of change of Delta)"""
        if T <= 0 or sigma <= 0:
            return 0.0
        
        d1 = BlackScholes.d1(S, K, T, r, sigma)
        return norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    @staticmethod
    def theta(S: float, K: float, T: float, r: float, sigma: float,
              option_type: str) -> float:
        """Calculate option Theta (time decay per day)"""
        if T <= 0:
            return 0.0
        
        d1 = BlackScholes.d1(S, K, T, r, sigma)
        d2 = BlackScholes.d2(S, K, T, r, sigma)
        
        common = -(S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T))
        
        if option_type == "call":
            theta = common - r * K * np.exp(-r * T) * norm.cdf(d2)
        else:
            theta = common + r * K * np.exp(-r * T) * norm.cdf(-d2)
        
        return theta / 365  # Convert to daily theta
    
    @staticmethod
    def vega(S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate option Vega (sensitivity to volatility, per 1% IV change)"""
        if T <= 0:
            return 0.0
        
        d1 = BlackScholes.d1(S, K, T, r, sigma)
        return S * np.sqrt(T) * norm.pdf(d1) / 100  # Per 1% change
    
    @staticmethod
    def rho(S: float, K: float, T: float, r: float, sigma: float,
            option_type: str) -> float:
        """Calculate option Rho (sensitivity to interest rate)"""
        if T <= 0:
            return 0.0
        
        d2 = BlackScholes.d2(S, K, T, r, sigma)
        
        if option_type == "call":
            return K * T * np.exp(-r * T) * norm.cdf(d2) / 100
        else:
            return -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100


def calculate_option_price(S: float, K: float, T_days: float, r: float, 
                          sigma: float, option_type: str) -> float:
    """
    Calculate theoretical option price
    
    Args:
        S: Current stock price
        K: Strike price
        T_days: Days to expiration
        r: Risk-free rate (annual)
        sigma: Implied volatility
        option_type: 'call' or 'put'
        
    Returns:
        Theoretical option price
    """
    T = T_days / 365.0  # Convert to years
    
    if option_type == "call":
        return BlackScholes.call_price(S, K, T, r, sigma)
    else:
        return BlackScholes.put_price(S, K, T, r, sigma)


def calculate_greeks(S: float, K: float, T_days: float, r: float,
                    sigma: float, option_type: str) -> Dict[str, float]:
    """
    Calculate all Greeks for an option
    
    Returns:
        Dictionary with Delta, Gamma, Theta, Vega, Rho
    """
    T = T_days / 365.0
    
    return {
        "delta": BlackScholes.delta(S, K, T, r, sigma, option_type),
        "gamma": BlackScholes.gamma(S, K, T, r, sigma),
        "theta": BlackScholes.theta(S, K, T, r, sigma, option_type),
        "vega": BlackScholes.vega(S, K, T, r, sigma),
        "rho": BlackScholes.rho(S, K, T, r, sigma, option_type)
    }


def calculate_expiration_payoff(legs: List[OptionLeg], 
                                 price_range: np.ndarray) -> np.ndarray:
    """
    Calculate P/L at expiration for a multi-leg position
    
    This produces the sharp, angular "hockey stick" lines.
    
    Args:
        legs: List of OptionLeg objects
        price_range: Array of stock prices to evaluate
        
    Returns:
        Array of P/L values at each price point
    """
    payoff = np.zeros_like(price_range)
    
    for leg in legs:
        if leg.option_type == "stock":
            # Stock position: P/L = (final_price - entry_price) * quantity
            # Assume entry at current price (which we'll adjust later)
            leg_payoff = (price_range - leg.strike) * leg.quantity * leg.sign
        elif leg.option_type == "call":
            # Call payoff at expiration: max(0, S - K) - premium
            intrinsic = np.maximum(0, price_range - leg.strike)
            leg_payoff = (intrinsic - leg.premium) * 100 * leg.quantity * leg.sign
        else:  # put
            # Put payoff at expiration: max(0, K - S) - premium
            intrinsic = np.maximum(0, leg.strike - price_range)
            leg_payoff = (intrinsic - leg.premium) * 100 * leg.quantity * leg.sign
        
        payoff += leg_payoff
    
    return payoff


def calculate_theoretical_payoff(legs: List[OptionLeg], price_range: np.ndarray,
                                  days_remaining: float, iv_adjustment: float = 0.0,
                                  r: float = DEFAULT_RISK_FREE_RATE) -> np.ndarray:
    """
    Calculate theoretical P/L using Black-Scholes (the curved T+0 line)
    
    This is the "smooth curve" that shows current theoretical value.
    
    Args:
        legs: List of OptionLeg objects
        price_range: Array of stock prices to evaluate
        days_remaining: Days until expiration
        iv_adjustment: Adjustment to IV (e.g., -0.10 for 10% IV crush)
        r: Risk-free rate
        
    Returns:
        Array of theoretical P/L values
    """
    payoff = np.zeros_like(price_range)
    
    for leg in legs:
        if leg.option_type == "stock":
            # Stock position value
            leg_payoff = (price_range - leg.strike) * leg.quantity * leg.sign
        else:
            # Option theoretical value
            adjusted_iv = max(0.01, leg.iv + iv_adjustment)  # Minimum 1% IV
            
            theoretical_values = np.array([
                calculate_option_price(S, leg.strike, days_remaining, r, 
                                       adjusted_iv, leg.option_type)
                for S in price_range
            ])
            
            # P/L = (current value - entry premium) * quantity * direction
            leg_payoff = (theoretical_values - leg.premium) * 100 * leg.quantity * leg.sign
        
        payoff += leg_payoff
    
    return payoff


def calculate_position_greeks(legs: List[OptionLeg], current_price: float,
                              days_remaining: float, 
                              r: float = DEFAULT_RISK_FREE_RATE) -> Dict[str, float]:
    """
    Calculate aggregate Greeks for a multi-leg position
    
    Args:
        legs: List of OptionLeg objects
        current_price: Current stock price
        days_remaining: Days until expiration
        r: Risk-free rate
        
    Returns:
        Dictionary with net Delta, Gamma, Theta, Vega
    """
    total_greeks = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0, "rho": 0.0}
    
    for leg in legs:
        if leg.option_type == "stock":
            # Stock has delta of 1 per share
            total_greeks["delta"] += leg.quantity * leg.sign
        else:
            greeks = calculate_greeks(
                current_price, leg.strike, days_remaining,
                r, leg.iv, leg.option_type
            )
            
            multiplier = 100 * leg.quantity * leg.sign
            for key in total_greeks:
                total_greeks[key] += greeks[key] * multiplier
    
    return total_greeks


def find_breakeven_points(legs: List[OptionLeg], 
                          price_range: np.ndarray) -> List[float]:
    """
    Find breakeven points where P/L crosses zero at expiration
    
    Returns:
        List of stock prices where P/L = 0
    """
    payoff = calculate_expiration_payoff(legs, price_range)
    
    breakevens = []
    for i in range(len(payoff) - 1):
        if payoff[i] * payoff[i + 1] < 0:  # Sign change
            # Linear interpolation to find exact crossing
            x0, x1 = price_range[i], price_range[i + 1]
            y0, y1 = payoff[i], payoff[i + 1]
            breakeven = x0 - y0 * (x1 - x0) / (y1 - y0)
            breakevens.append(round(breakeven, 2))
    
    return breakevens


def calculate_max_profit_loss(legs: List[OptionLeg], 
                              price_range: np.ndarray) -> Tuple[float, float]:
    """
    Calculate maximum profit and maximum loss at expiration
    
    Returns:
        Tuple of (max_profit, max_loss)
    """
    payoff = calculate_expiration_payoff(legs, price_range)
    
    max_profit = np.max(payoff)
    max_loss = np.min(payoff)
    
    return max_profit, max_loss


def calculate_probability_of_profit(legs: List[OptionLeg], current_price: float,
                                    days_remaining: float, iv: float) -> float:
    """
    Estimate probability of profit using lognormal distribution
    
    This is a simplified calculation based on the assumption that
    stock returns are lognormally distributed.
    
    Returns:
        Probability of profit as a percentage (0-100)
    """
    # Generate price range
    price_range = generate_price_range(current_price)
    
    # Calculate payoff at expiration
    payoff = calculate_expiration_payoff(legs, price_range)
    
    # Find profitable region
    profitable = payoff > 0
    
    if not np.any(profitable):
        return 0.0
    if np.all(profitable):
        return 100.0
    
    # Use lognormal CDF to calculate probability
    T = days_remaining / 365.0
    if T <= 0:
        T = 1 / 365.0  # Minimum 1 day
    
    sigma_t = iv * np.sqrt(T)
    mu = np.log(current_price) - 0.5 * sigma_t ** 2
    
    # Find breakeven points
    breakevens = find_breakeven_points(legs, price_range)
    
    if not breakevens:
        # Check if always profitable or always losing
        if payoff[len(payoff) // 2] > 0:
            return 100.0
        return 0.0
    
    # Sum probability of being in profitable zones
    prob = 0.0
    
    # Sort breakevens
    breakevens = sorted(breakevens)
    
    # Determine if center is profitable (to know which regions are profit)
    center_idx = len(price_range) // 2
    center_profitable = payoff[center_idx] > 0
    
    if len(breakevens) == 1:
        be = breakevens[0]
        if center_profitable:
            # Profitable below breakeven (e.g., long put)
            if payoff[0] > 0:
                prob = norm.cdf((np.log(be) - mu) / sigma_t)
            else:
                # Profitable above breakeven (e.g., long call)
                prob = 1 - norm.cdf((np.log(be) - mu) / sigma_t)
        else:
            if payoff[0] > 0:
                prob = norm.cdf((np.log(be) - mu) / sigma_t)
            else:
                prob = 1 - norm.cdf((np.log(be) - mu) / sigma_t)
    elif len(breakevens) == 2:
        be_low, be_high = breakevens[0], breakevens[1]
        p_low = norm.cdf((np.log(be_low) - mu) / sigma_t)
        p_high = norm.cdf((np.log(be_high) - mu) / sigma_t)
        
        if center_profitable:
            # Profitable between breakevens (e.g., short straddle, iron condor)
            prob = p_high - p_low
        else:
            # Profitable outside breakevens (e.g., long straddle)
            prob = p_low + (1 - p_high)
    else:
        # Multiple breakeven points - approximate
        prob = 50.0  # Default to 50% for complex cases
    
    return min(100, max(0, prob * 100))


def generate_price_range(current_price: float, 
                         range_percent: float = PRICE_RANGE_PERCENT,
                         num_points: int = NUM_PRICE_POINTS) -> np.ndarray:
    """
    Generate array of stock prices centered on current price
    
    Args:
        current_price: Current stock price
        range_percent: How far to extend (+/- percentage)
        num_points: Number of price points
        
    Returns:
        Array of stock prices
    """
    low = current_price * (1 - range_percent)
    high = current_price * (1 + range_percent)
    return np.linspace(low, high, num_points)


def build_strategy_legs(strategy_template: List[Dict], current_price: float,
                        strike_interval: float, base_iv: float,
                        days_to_expiration: int,
                        option_prices: Dict = None) -> List[OptionLeg]:
    """
    Build OptionLeg objects from a strategy template
    
    Args:
        strategy_template: List of leg definitions from config
        current_price: Current stock price
        strike_interval: Distance between strikes
        base_iv: Base implied volatility
        days_to_expiration: Days until expiration
        option_prices: Optional dict of actual option prices
        
    Returns:
        List of OptionLeg objects
    """
    legs = []
    
    # Round current price to nearest strike
    atm_strike = round(current_price / strike_interval) * strike_interval
    
    for leg_def in strategy_template:
        leg_type = leg_def["type"]
        position = leg_def["position"]
        quantity = leg_def["quantity"]
        strike_offset = leg_def.get("strike_offset", 0)
        
        if leg_type == "stock":
            leg = OptionLeg(
                option_type="stock",
                position=position,
                strike=current_price,  # Entry price
                premium=0,
                quantity=quantity,
                expiration_days=days_to_expiration,
                iv=0
            )
        else:
            strike = atm_strike + (strike_offset * strike_interval)
            
            # Calculate theoretical premium if not provided
            premium = calculate_option_price(
                current_price, strike, days_to_expiration,
                DEFAULT_RISK_FREE_RATE, base_iv, leg_type
            )
            
            leg = OptionLeg(
                option_type=leg_type,
                position=position,
                strike=strike,
                premium=premium,
                quantity=quantity,
                expiration_days=days_to_expiration,
                iv=base_iv
            )
        
        legs.append(leg)
    
    return legs


# =============================================================================
# Technical Indicators
# =============================================================================

def calculate_sma(prices: List[float], period: int) -> List[float]:
    """
    Calculate Simple Moving Average
    
    Args:
        prices: List of closing prices
        period: Number of periods for SMA
        
    Returns:
        List of SMA values (NaN for first period-1 values)
    """
    if len(prices) < period:
        return [np.nan] * len(prices)
    
    sma = []
    for i in range(len(prices)):
        if i < period - 1:
            sma.append(np.nan)
        else:
            sma.append(np.mean(prices[i - period + 1:i + 1]))
    
    return sma


def calculate_ema(prices: List[float], period: int) -> List[float]:
    """
    Calculate Exponential Moving Average
    
    Args:
        prices: List of closing prices
        period: Number of periods for EMA
        
    Returns:
        List of EMA values
    """
    if len(prices) < period:
        return [np.nan] * len(prices)
    
    multiplier = 2 / (period + 1)
    ema = [np.nan] * (period - 1)
    
    # First EMA is SMA
    ema.append(np.mean(prices[:period]))
    
    # Calculate subsequent EMAs
    for i in range(period, len(prices)):
        ema.append((prices[i] - ema[-1]) * multiplier + ema[-1])
    
    return ema


def calculate_rsi(prices: List[float], period: int = 14) -> List[float]:
    """
    Calculate Relative Strength Index
    
    Args:
        prices: List of closing prices
        period: RSI period (typically 14)
        
    Returns:
        List of RSI values (0-100)
    """
    if len(prices) < period + 1:
        return [np.nan] * len(prices)
    
    # Calculate price changes
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    
    gains = [d if d > 0 else 0 for d in deltas]
    losses = [-d if d < 0 else 0 for d in deltas]
    
    rsi = [np.nan] * period
    
    # First average
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
        if avg_loss == 0:
            rsi.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi.append(100 - (100 / (1 + rs)))
    
    # Pad to match original length
    rsi = [np.nan] + rsi
    
    return rsi


def calculate_bollinger_bands(prices: List[float], period: int = 20, 
                               std_dev: float = 2.0) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate Bollinger Bands
    
    Args:
        prices: List of closing prices
        period: SMA period (typically 20)
        std_dev: Number of standard deviations
        
    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    middle = calculate_sma(prices, period)
    
    upper = []
    lower = []
    
    for i in range(len(prices)):
        if i < period - 1:
            upper.append(np.nan)
            lower.append(np.nan)
        else:
            std = np.std(prices[i - period + 1:i + 1])
            upper.append(middle[i] + std_dev * std)
            lower.append(middle[i] - std_dev * std)
    
    return upper, middle, lower


def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, 
                   signal: int = 9) -> Tuple[List[float], List[float], List[float]]:
    """
    Calculate MACD (Moving Average Convergence Divergence)
    
    Args:
        prices: List of closing prices
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
        
    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    
    # MACD line
    macd_line = [f - s if not (np.isnan(f) or np.isnan(s)) else np.nan 
                 for f, s in zip(ema_fast, ema_slow)]
    
    # Signal line (EMA of MACD)
    valid_macd = [m for m in macd_line if not np.isnan(m)]
    signal_ema = calculate_ema(valid_macd, signal) if len(valid_macd) >= signal else []
    
    # Pad signal line
    nan_count = len(macd_line) - len(signal_ema)
    signal_line = [np.nan] * nan_count + signal_ema
    
    # Histogram
    histogram = [m - s if not (np.isnan(m) or np.isnan(s)) else np.nan 
                 for m, s in zip(macd_line, signal_line)]
    
    return macd_line, signal_line, histogram


# =============================================================================
# IV Surface Calculations
# =============================================================================

def calculate_iv_surface(options_data: List[Dict], current_price: float,
                        risk_free_rate: float = DEFAULT_RISK_FREE_RATE) -> Dict:
    """
    Calculate IV surface data for 3D/heatmap visualization
    
    Args:
        options_data: List of option dicts with 'strike', 'expiration', 'iv', 'type'
        current_price: Current stock price
        risk_free_rate: Risk-free rate
        
    Returns:
        Dict with 'strikes', 'expirations', 'ivs' (2D array)
    """
    if not options_data:
        return {"strikes": [], "expirations": [], "ivs": []}
    
    # Extract unique strikes and expirations
    strikes = sorted(set(opt.get("strike", 0) for opt in options_data))
    expirations = sorted(set(opt.get("expiration", "") for opt in options_data))
    
    # Build IV matrix
    iv_matrix = np.full((len(expirations), len(strikes)), np.nan)
    
    for opt in options_data:
        strike = opt.get("strike", 0)
        exp = opt.get("expiration", "")
        iv = opt.get("iv", 0)
        
        if strike in strikes and exp in expirations and iv > 0:
            strike_idx = strikes.index(strike)
            exp_idx = expirations.index(exp)
            iv_matrix[exp_idx, strike_idx] = iv * 100  # Convert to percentage
    
    return {
        "strikes": strikes,
        "expirations": expirations,
        "ivs": iv_matrix.tolist(),
        "current_price": current_price
    }


def calculate_iv_smile(options_data: List[Dict], expiration: str, 
                       current_price: float) -> Tuple[List[float], List[float]]:
    """
    Calculate IV smile for a specific expiration
    
    Args:
        options_data: List of option dicts
        expiration: Target expiration date
        current_price: Current stock price
        
    Returns:
        Tuple of (strikes, ivs) where strikes are expressed as % moneyness
    """
    filtered = [opt for opt in options_data 
                if opt.get("expiration") == expiration and opt.get("iv", 0) > 0]
    
    if not filtered:
        return [], []
    
    # Sort by strike
    filtered.sort(key=lambda x: x.get("strike", 0))
    
    strikes = []
    ivs = []
    
    for opt in filtered:
        strike = opt.get("strike", 0)
        iv = opt.get("iv", 0)
        
        # Express as moneyness (% from ATM)
        moneyness = ((strike / current_price) - 1) * 100
        strikes.append(moneyness)
        ivs.append(iv * 100)  # Convert to percentage
    
    return strikes, ivs


def calculate_term_structure(options_data: List[Dict], strike: float = None,
                             current_price: float = None) -> Tuple[List[int], List[float]]:
    """
    Calculate IV term structure (IV vs. time to expiration)
    
    Args:
        options_data: List of option dicts
        strike: Target strike (uses ATM if None)
        current_price: Current price for ATM strike selection
        
    Returns:
        Tuple of (days_to_expiration, ivs)
    """
    from datetime import datetime
    
    if strike is None and current_price:
        # Use ATM options
        atm_options = [opt for opt in options_data 
                       if abs(opt.get("strike", 0) - current_price) / current_price < 0.02]
    else:
        atm_options = [opt for opt in options_data 
                       if abs(opt.get("strike", 0) - (strike or 0)) < 0.01]
    
    if not atm_options:
        return [], []
    
    # Calculate DTE for each option
    today = datetime.now()
    term_data = []
    
    for opt in atm_options:
        exp_str = opt.get("expiration", "")
        iv = opt.get("iv", 0)
        
        if iv <= 0:
            continue
            
        try:
            exp_date = datetime.strptime(exp_str, "%Y-%m-%d")
            dte = (exp_date - today).days
            if dte > 0:
                term_data.append((dte, iv * 100))
        except:
            continue
    
    # Sort by DTE
    term_data.sort(key=lambda x: x[0])
    
    dtes = [t[0] for t in term_data]
    ivs = [t[1] for t in term_data]
    
    return dtes, ivs


# =============================================================================
# Dynamic Crosshair Calculations
# =============================================================================

def calculate_pnl_at_price(legs: List[OptionLeg], target_price: float,
                           days_remaining: float, iv_adjustment: float = 0.0,
                           r: float = DEFAULT_RISK_FREE_RATE) -> Dict[str, float]:
    """
    Calculate detailed P/L and Greeks at a specific price point
    
    Args:
        legs: List of OptionLeg objects
        target_price: Stock price to calculate at
        days_remaining: Days until expiration
        iv_adjustment: IV adjustment
        r: Risk-free rate
        
    Returns:
        Dict with P/L, Greeks, and other metrics at that price
    """
    # Calculate P/L at expiration
    price_array = np.array([target_price])
    expiry_pnl = calculate_expiration_payoff(legs, price_array)[0]
    
    # Calculate theoretical P/L now
    current_pnl = calculate_theoretical_payoff(
        legs, price_array, days_remaining, iv_adjustment, r
    )[0]
    
    # Calculate Greeks at this price
    greeks = {"delta": 0.0, "gamma": 0.0, "theta": 0.0, "vega": 0.0}
    
    for leg in legs:
        if leg.option_type == "stock":
            greeks["delta"] += leg.quantity * leg.sign
        else:
            adjusted_iv = max(0.01, leg.iv + iv_adjustment)
            leg_greeks = calculate_greeks(
                target_price, leg.strike, days_remaining,
                r, adjusted_iv, leg.option_type
            )
            
            multiplier = 100 * leg.quantity * leg.sign
            for key in greeks:
                greeks[key] += leg_greeks[key] * multiplier
    
    return {
        "price": target_price,
        "theoretical_pnl": current_pnl,
        "expiry_pnl": expiry_pnl,
        "time_value": current_pnl - expiry_pnl if days_remaining > 0 else 0,
        "delta": greeks["delta"],
        "gamma": greeks["gamma"],
        "theta": greeks["theta"],
        "vega": greeks["vega"]
    }
