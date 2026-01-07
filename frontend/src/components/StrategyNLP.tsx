import { useState, useCallback, useRef } from 'react';

interface StrategyLeg {
    id: string;
    optionType: 'call' | 'put';
    position: 'long' | 'short';
    strike: number;
    quantity: number;
    premium: number;
}

interface StrategyNLPProps {
    ticker: string;
    currentPrice: number;
    onStrategyCreated?: (legs: StrategyLeg[]) => void;
}

// Suggestions for autocomplete
const SUGGESTIONS = [
    'Buy a protective collar on',
    'Sell an iron condor on',
    'Buy a straddle on',
    'Sell a covered call on',
    'Buy a bull call spread on',
    'Sell a cash secured put on',
    'Long butterfly on',
    'Calendar spread on',
];

export default function StrategyNLP({ ticker, currentPrice, onStrategyCreated }: StrategyNLPProps) {
    const [input, setInput] = useState('');
    const [parsedStrategy, setParsedStrategy] = useState<any>(null);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState(false);
    const [showSuggestions, setShowSuggestions] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);

    // Parse input locally (simplified - would call backend in production)
    const parseStrategy = useCallback((command: string) => {
        const cmd = command.toLowerCase();

        // Pattern matching
        const strategies: Record<string, any> = {
            'iron condor': {
                name: 'Iron Condor',
                legs: [
                    { optionType: 'put', position: 'long', strike: currentPrice * 0.92, quantity: 1, premium: 0.5 },
                    { optionType: 'put', position: 'short', strike: currentPrice * 0.95, quantity: 1, premium: 1.5 },
                    { optionType: 'call', position: 'short', strike: currentPrice * 1.05, quantity: 1, premium: 1.5 },
                    { optionType: 'call', position: 'long', strike: currentPrice * 1.08, quantity: 1, premium: 0.5 },
                ],
                maxProfit: 2.0,
                maxLoss: 3.0,
                outlook: 'Neutral - Profit from low volatility'
            },
            'straddle': {
                name: 'Long Straddle',
                legs: [
                    { optionType: 'call', position: 'long', strike: currentPrice, quantity: 1, premium: 5.0 },
                    { optionType: 'put', position: 'long', strike: currentPrice, quantity: 1, premium: 5.0 },
                ],
                maxProfit: 'Unlimited',
                maxLoss: 10.0,
                outlook: 'Expecting big move in either direction'
            },
            'covered call': {
                name: 'Covered Call',
                legs: [
                    { optionType: 'call', position: 'short', strike: currentPrice * 1.05, quantity: 1, premium: 2.0 },
                ],
                maxProfit: 2.0 + (currentPrice * 0.05),
                maxLoss: currentPrice,
                outlook: 'Neutral to slightly bullish'
            },
            'bull call spread': {
                name: 'Bull Call Spread',
                legs: [
                    { optionType: 'call', position: 'long', strike: currentPrice, quantity: 1, premium: 5.0 },
                    { optionType: 'call', position: 'short', strike: currentPrice * 1.05, quantity: 1, premium: 2.0 },
                ],
                maxProfit: currentPrice * 0.05 - 3.0,
                maxLoss: 3.0,
                outlook: 'Moderately bullish'
            },
            'protective collar': {
                name: 'Protective Collar',
                legs: [
                    { optionType: 'put', position: 'long', strike: currentPrice * 0.95, quantity: 1, premium: 2.0 },
                    { optionType: 'call', position: 'short', strike: currentPrice * 1.05, quantity: 1, premium: 2.0 },
                ],
                maxProfit: currentPrice * 0.05,
                maxLoss: currentPrice * 0.05,
                outlook: 'Protective - limits both upside and downside'
            },
            'cash secured put': {
                name: 'Cash Secured Put',
                legs: [
                    { optionType: 'put', position: 'short', strike: currentPrice * 0.95, quantity: 1, premium: 2.5 },
                ],
                maxProfit: 250,
                maxLoss: currentPrice * 0.95 * 100,
                outlook: 'Slightly bullish - willing to buy at lower price'
            },
        };

        for (const [key, value] of Object.entries(strategies)) {
            if (cmd.includes(key)) {
                return value;
            }
        }

        return null;
    }, [currentPrice]);

    // Handle input change
    const handleInputChange = (value: string) => {
        setInput(value);

        // Filter suggestions
        if (value.length > 0) {
            const filtered = SUGGESTIONS
                .filter(s => s.toLowerCase().includes(value.toLowerCase()))
                .map(s => `${s} ${ticker}`);
            setSuggestions(filtered);
            setShowSuggestions(true);
        } else {
            setShowSuggestions(false);
        }
    };

    // Handle submit
    const handleSubmit = async () => {
        if (!input.trim()) return;

        setIsLoading(true);

        // Simulate API call delay
        await new Promise(resolve => setTimeout(resolve, 500));

        const parsed = parseStrategy(input);
        setParsedStrategy(parsed);

        if (parsed && onStrategyCreated) {
            onStrategyCreated(parsed.legs.map((leg: any, i: number) => ({
                ...leg,
                id: `leg-${i}`,
                strike: Math.round(leg.strike * 100) / 100
            })));
        }

        setIsLoading(false);
        setShowSuggestions(false);
    };

    // Handle suggestion click
    const handleSuggestionClick = (suggestion: string) => {
        setInput(suggestion);
        setShowSuggestions(false);
        inputRef.current?.focus();
    };

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                🗣️ Natural Language Strategy Builder
                <span className="text-xs text-gray-400">Type in plain English</span>
            </h3>

            {/* Input Area */}
            <div className="relative mb-4">
                <div className="flex gap-2">
                    <input
                        ref={inputRef}
                        type="text"
                        value={input}
                        onChange={(e) => handleInputChange(e.target.value)}
                        onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
                        placeholder={`Try "Sell an iron condor on ${ticker}"...`}
                        className="flex-1 bg-[#252b3b] border border-white/20 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
                    />
                    <button
                        onClick={handleSubmit}
                        disabled={isLoading}
                        className="px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 rounded-lg font-medium hover:opacity-90 transition disabled:opacity-50"
                    >
                        {isLoading ? '...' : 'Parse'}
                    </button>
                </div>

                {/* Suggestions Dropdown */}
                {showSuggestions && suggestions.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-[#252b3b] border border-white/20 rounded-lg shadow-xl z-10 overflow-hidden">
                        {suggestions.map((suggestion, i) => (
                            <button
                                key={i}
                                onClick={() => handleSuggestionClick(suggestion)}
                                className="w-full text-left px-4 py-2 hover:bg-white/10 text-sm transition"
                            >
                                {suggestion}
                            </button>
                        ))}
                    </div>
                )}
            </div>

            {/* Quick Actions */}
            <div className="flex flex-wrap gap-2 mb-4">
                {['Iron Condor', 'Straddle', 'Covered Call', 'Bull Call Spread'].map((strategy) => (
                    <button
                        key={strategy}
                        onClick={() => handleInputChange(`Buy a ${strategy.toLowerCase()} on ${ticker}`)}
                        className="px-3 py-1 bg-[#252b3b] border border-white/10 rounded-lg text-xs hover:border-blue-500 transition"
                    >
                        {strategy}
                    </button>
                ))}
            </div>

            {/* Parsed Result */}
            {parsedStrategy && (
                <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 border border-purple-500/30 rounded-lg p-4">
                    <div className="flex justify-between items-start mb-3">
                        <div>
                            <h4 className="font-semibold text-lg">{parsedStrategy.name}</h4>
                            <p className="text-sm text-gray-400">{parsedStrategy.outlook}</p>
                        </div>
                        <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded">
                            ✓ Parsed
                        </span>
                    </div>

                    {/* Legs Table */}
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-gray-400 border-b border-white/10">
                                    <th className="text-left py-2">Leg</th>
                                    <th className="text-left py-2">Type</th>
                                    <th className="text-right py-2">Strike</th>
                                    <th className="text-right py-2">Premium</th>
                                </tr>
                            </thead>
                            <tbody>
                                {parsedStrategy.legs.map((leg: any, i: number) => (
                                    <tr key={i} className="border-b border-white/5">
                                        <td className="py-2">{i + 1}</td>
                                        <td className={`py-2 ${leg.position === 'long' ? 'text-green-400' : 'text-red-400'}`}>
                                            {leg.position === 'long' ? '+' : '-'}{leg.optionType.toUpperCase()}
                                        </td>
                                        <td className="py-2 text-right font-mono">${leg.strike.toFixed(2)}</td>
                                        <td className="py-2 text-right font-mono">${leg.premium.toFixed(2)}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    {/* Risk/Reward */}
                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <div className="bg-[#1a1f2e] rounded p-2 text-center">
                            <p className="text-xs text-gray-400">Max Profit</p>
                            <p className="text-green-400 font-mono">
                                {typeof parsedStrategy.maxProfit === 'number'
                                    ? `$${parsedStrategy.maxProfit.toFixed(2)}`
                                    : parsedStrategy.maxProfit}
                            </p>
                        </div>
                        <div className="bg-[#1a1f2e] rounded p-2 text-center">
                            <p className="text-xs text-gray-400">Max Loss</p>
                            <p className="text-red-400 font-mono">${parsedStrategy.maxLoss.toFixed(2)}</p>
                        </div>
                    </div>

                    {/* Execute Button */}
                    <button className="w-full mt-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 rounded-lg font-medium hover:opacity-90 transition">
                        Execute Strategy
                    </button>
                </div>
            )}
        </div>
    );
}
