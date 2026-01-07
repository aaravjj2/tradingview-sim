"""
Natural Language Strategy Parser
Converts natural language commands to structured option strategies
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ParsedStrategy:
    """Represents a parsed strategy from natural language"""
    strategy_name: str
    ticker: str
    legs: List[Dict]
    confidence: float
    original_input: str


class NLPStrategyParser:
    """
    Parses natural language trading commands into structured strategies
    
    Examples:
    - "Buy a protective collar on AAPL"
    - "Sell an iron condor on SPY"
    - "Long straddle on NVDA"
    - "Buy 5 AAPL 180 calls"
    """
    
    def __init__(self):
        # Strategy patterns (regex + structure)
        self.strategy_patterns = {
            'protective_collar': {
                'patterns': [
                    r'(?:buy|create|enter)\s+(?:a\s+)?protective\s+collar\s+(?:on\s+)?(\w+)',
                    r'collar\s+(?:on\s+)?(\w+)',
                ],
                'legs': lambda ticker, price: [
                    {'option_type': 'stock', 'position': 'long', 'strike': None, 'quantity': 100},
                    {'option_type': 'put', 'position': 'long', 'strike': round(price * 0.95, 2), 'quantity': 1},
                    {'option_type': 'call', 'position': 'short', 'strike': round(price * 1.05, 2), 'quantity': 1},
                ]
            },
            'iron_condor': {
                'patterns': [
                    r'(?:sell|write|enter)\s+(?:an?\s+)?iron\s+condor\s+(?:on\s+)?(\w+)',
                    r'ic\s+(?:on\s+)?(\w+)',
                ],
                'legs': lambda ticker, price: [
                    {'option_type': 'put', 'position': 'long', 'strike': round(price * 0.92, 2), 'quantity': 1},
                    {'option_type': 'put', 'position': 'short', 'strike': round(price * 0.95, 2), 'quantity': 1},
                    {'option_type': 'call', 'position': 'short', 'strike': round(price * 1.05, 2), 'quantity': 1},
                    {'option_type': 'call', 'position': 'long', 'strike': round(price * 1.08, 2), 'quantity': 1},
                ]
            },
            'straddle': {
                'patterns': [
                    r'(?:buy|long)\s+(?:a\s+)?straddle\s+(?:on\s+)?(\w+)',
                    r'straddle\s+(\w+)',
                ],
                'legs': lambda ticker, price: [
                    {'option_type': 'call', 'position': 'long', 'strike': round(price, 2), 'quantity': 1},
                    {'option_type': 'put', 'position': 'long', 'strike': round(price, 2), 'quantity': 1},
                ]
            },
            'strangle': {
                'patterns': [
                    r'(?:buy|long|sell|short)\s+(?:a\s+)?strangle\s+(?:on\s+)?(\w+)',
                ],
                'legs': lambda ticker, price: [
                    {'option_type': 'call', 'position': 'long', 'strike': round(price * 1.05, 2), 'quantity': 1},
                    {'option_type': 'put', 'position': 'long', 'strike': round(price * 0.95, 2), 'quantity': 1},
                ]
            },
            'covered_call': {
                'patterns': [
                    r'(?:sell|write)\s+(?:a\s+)?covered\s+call\s+(?:on\s+)?(\w+)',
                    r'cc\s+(?:on\s+)?(\w+)',
                ],
                'legs': lambda ticker, price: [
                    {'option_type': 'stock', 'position': 'long', 'strike': None, 'quantity': 100},
                    {'option_type': 'call', 'position': 'short', 'strike': round(price * 1.05, 2), 'quantity': 1},
                ]
            },
            'cash_secured_put': {
                'patterns': [
                    r'(?:sell|write)\s+(?:a\s+)?(?:cash[- ]secured\s+)?put\s+(?:on\s+)?(\w+)',
                    r'csp\s+(?:on\s+)?(\w+)',
                ],
                'legs': lambda ticker, price: [
                    {'option_type': 'put', 'position': 'short', 'strike': round(price * 0.95, 2), 'quantity': 1},
                ]
            },
            'bull_call_spread': {
                'patterns': [
                    r'bull\s+call\s+(?:spread\s+)?(?:on\s+)?(\w+)',
                    r'(?:buy|long)\s+call\s+spread\s+(?:on\s+)?(\w+)',
                ],
                'legs': lambda ticker, price: [
                    {'option_type': 'call', 'position': 'long', 'strike': round(price, 2), 'quantity': 1},
                    {'option_type': 'call', 'position': 'short', 'strike': round(price * 1.05, 2), 'quantity': 1},
                ]
            },
            'bear_put_spread': {
                'patterns': [
                    r'bear\s+put\s+(?:spread\s+)?(?:on\s+)?(\w+)',
                    r'(?:buy|long)\s+put\s+spread\s+(?:on\s+)?(\w+)',
                ],
                'legs': lambda ticker, price: [
                    {'option_type': 'put', 'position': 'long', 'strike': round(price, 2), 'quantity': 1},
                    {'option_type': 'put', 'position': 'short', 'strike': round(price * 0.95, 2), 'quantity': 1},
                ]
            },
            'butterfly': {
                'patterns': [
                    r'(?:buy|long)\s+(?:a\s+)?butterfly\s+(?:on\s+)?(\w+)',
                ],
                'legs': lambda ticker, price: [
                    {'option_type': 'call', 'position': 'long', 'strike': round(price * 0.95, 2), 'quantity': 1},
                    {'option_type': 'call', 'position': 'short', 'strike': round(price, 2), 'quantity': 2},
                    {'option_type': 'call', 'position': 'long', 'strike': round(price * 1.05, 2), 'quantity': 1},
                ]
            },
            'calendar_spread': {
                'patterns': [
                    r'calendar\s+(?:spread\s+)?(?:on\s+)?(\w+)',
                    r'time\s+spread\s+(?:on\s+)?(\w+)',
                ],
                'legs': lambda ticker, price: [
                    {'option_type': 'call', 'position': 'short', 'strike': round(price, 2), 'quantity': 1, 'dte': 30},
                    {'option_type': 'call', 'position': 'long', 'strike': round(price, 2), 'quantity': 1, 'dte': 60},
                ]
            },
        }
        
        # Simple option patterns
        self.simple_option_pattern = re.compile(
            r'(?:buy|sell|long|short)\s+(\d+)?\s*(\w+)\s+\$?(\d+(?:\.\d+)?)\s+(call|put)s?',
            re.IGNORECASE
        )
    
    def parse(
        self, 
        command: str, 
        current_price: float = 100.0
    ) -> Optional[ParsedStrategy]:
        """
        Parse a natural language command into a structured strategy
        
        Args:
            command: Natural language trading command
            current_price: Current price of the underlying
        
        Returns:
            ParsedStrategy or None if parsing fails
        """
        command = command.lower().strip()
        
        # Try named strategies first
        for strategy_name, config in self.strategy_patterns.items():
            for pattern in config['patterns']:
                match = re.search(pattern, command, re.IGNORECASE)
                if match:
                    ticker = match.group(1).upper()
                    legs = config['legs'](ticker, current_price)
                    
                    return ParsedStrategy(
                        strategy_name=strategy_name,
                        ticker=ticker,
                        legs=legs,
                        confidence=0.9,
                        original_input=command
                    )
        
        # Try simple option pattern
        match = self.simple_option_pattern.search(command)
        if match:
            quantity = int(match.group(1)) if match.group(1) else 1
            ticker = match.group(2).upper()
            strike = float(match.group(3))
            option_type = match.group(4).lower()
            
            # Determine position (buy = long, sell = short)
            position = 'long' if command.startswith(('buy', 'long')) else 'short'
            
            return ParsedStrategy(
                strategy_name='single_option',
                ticker=ticker,
                legs=[{
                    'option_type': option_type,
                    'position': position,
                    'strike': strike,
                    'quantity': quantity
                }],
                confidence=0.95,
                original_input=command
            )
        
        # Try to extract just a ticker for a simple long call
        ticker_match = re.search(r'\b([A-Z]{1,5})\b', command.upper())
        if ticker_match and any(word in command for word in ['buy', 'call', 'long']):
            ticker = ticker_match.group(1)
            return ParsedStrategy(
                strategy_name='long_call',
                ticker=ticker,
                legs=[{
                    'option_type': 'call',
                    'position': 'long',
                    'strike': round(current_price * 1.02, 2),
                    'quantity': 1
                }],
                confidence=0.5,
                original_input=command
            )
        
        return None
    
    def get_suggestions(self, partial_command: str) -> List[str]:
        """
        Get auto-complete suggestions for partial commands
        """
        suggestions = []
        partial = partial_command.lower()
        
        # Strategy name suggestions
        strategy_keywords = [
            'protective collar', 'iron condor', 'straddle', 'strangle',
            'covered call', 'cash secured put', 'bull call spread',
            'bear put spread', 'butterfly', 'calendar spread'
        ]
        
        for kw in strategy_keywords:
            if kw.startswith(partial) or partial in kw:
                suggestions.append(f"Buy a {kw} on SPY")
        
        # Action suggestions
        if partial.startswith('buy'):
            suggestions.extend([
                'Buy a protective collar on AAPL',
                'Buy a straddle on SPY',
                'Buy 5 NVDA 500 calls'
            ])
        elif partial.startswith('sell'):
            suggestions.extend([
                'Sell an iron condor on SPY',
                'Sell a covered call on AAPL',
                'Sell a cash secured put on QQQ'
            ])
        
        return suggestions[:5]
    
    def describe_strategy(self, strategy: ParsedStrategy) -> str:
        """
        Generate a human-readable description of a parsed strategy
        """
        descriptions = {
            'protective_collar': f"Protective Collar on {strategy.ticker}: Own stock, buy put for protection, sell call for income",
            'iron_condor': f"Iron Condor on {strategy.ticker}: Sell OTM put spread and call spread for premium",
            'straddle': f"Long Straddle on {strategy.ticker}: Buy ATM call and put, profit from big moves",
            'strangle': f"Strangle on {strategy.ticker}: Buy OTM call and put for directional play",
            'covered_call': f"Covered Call on {strategy.ticker}: Own stock, sell call for income",
            'cash_secured_put': f"Cash Secured Put on {strategy.ticker}: Sell put to potentially buy stock at discount",
            'bull_call_spread': f"Bull Call Spread on {strategy.ticker}: Bullish debit spread",
            'bear_put_spread': f"Bear Put Spread on {strategy.ticker}: Bearish debit spread",
            'butterfly': f"Butterfly on {strategy.ticker}: Profit from low volatility around strike",
            'calendar_spread': f"Calendar Spread on {strategy.ticker}: Profit from time decay difference",
            'single_option': f"Single Option on {strategy.ticker}",
            'long_call': f"Long Call on {strategy.ticker}",
        }
        
        return descriptions.get(strategy.strategy_name, f"Strategy on {strategy.ticker}")
