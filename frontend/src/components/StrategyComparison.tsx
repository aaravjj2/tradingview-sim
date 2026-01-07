import { useState, useMemo } from 'react';

interface OptionLeg {
    option_type: 'call' | 'put' | 'stock';
    position: 'long' | 'short';
    strike: number;
    premium: number;
    quantity: number;
}

interface Props {
    currentPrice: number;
}

// Preset strategies for comparison
const PRESET_STRATEGIES: Record<string, OptionLeg[]> = {
    'Long Call': [
        { option_type: 'call', position: 'long', strike: 500, premium: 7.50, quantity: 1 }
    ],
    'Long Put': [
        { option_type: 'put', position: 'long', strike: 500, premium: 6.00, quantity: 1 }
    ],
    'Covered Call': [
        { option_type: 'stock', position: 'long', strike: 500, premium: 0, quantity: 100 },
        { option_type: 'call', position: 'short', strike: 510, premium: 3.50, quantity: 1 }
    ],
    'Iron Condor': [
        { option_type: 'put', position: 'short', strike: 480, premium: 2.00, quantity: 1 },
        { option_type: 'put', position: 'long', strike: 470, premium: 1.00, quantity: 1 },
        { option_type: 'call', position: 'short', strike: 520, premium: 2.00, quantity: 1 },
        { option_type: 'call', position: 'long', strike: 530, premium: 1.00, quantity: 1 }
    ],
    'Straddle': [
        { option_type: 'call', position: 'long', strike: 500, premium: 7.50, quantity: 1 },
        { option_type: 'put', position: 'long', strike: 500, premium: 6.00, quantity: 1 }
    ],
    'Strangle': [
        { option_type: 'call', position: 'long', strike: 510, premium: 4.00, quantity: 1 },
        { option_type: 'put', position: 'long', strike: 490, premium: 3.50, quantity: 1 }
    ],
    'Bull Call Spread': [
        { option_type: 'call', position: 'long', strike: 495, premium: 8.00, quantity: 1 },
        { option_type: 'call', position: 'short', strike: 510, premium: 3.00, quantity: 1 }
    ],
    'Bear Put Spread': [
        { option_type: 'put', position: 'long', strike: 505, premium: 7.00, quantity: 1 },
        { option_type: 'put', position: 'short', strike: 490, premium: 2.50, quantity: 1 }
    ]
};

const STRATEGY_COLORS: Record<string, string> = {
    'Long Call': '#00ff88',
    'Long Put': '#ff6b6b',
    'Covered Call': '#4ecdc4',
    'Iron Condor': '#ffe66d',
    'Straddle': '#a855f7',
    'Strangle': '#f472b6',
    'Bull Call Spread': '#22c55e',
    'Bear Put Spread': '#ef4444'
};

function calculatePayoff(legs: OptionLeg[], spotPrice: number): number {
    let payoff = 0;

    for (const leg of legs) {
        const multiplier = leg.position === 'long' ? 1 : -1;
        const premiumCost = multiplier * leg.premium * 100 * leg.quantity;

        if (leg.option_type === 'stock') {
            payoff += multiplier * (spotPrice - leg.strike) * leg.quantity;
        } else if (leg.option_type === 'call') {
            const intrinsic = Math.max(0, spotPrice - leg.strike);
            payoff += (multiplier * intrinsic - leg.premium) * 100 * leg.quantity;
        } else if (leg.option_type === 'put') {
            const intrinsic = Math.max(0, leg.strike - spotPrice);
            payoff += (multiplier * intrinsic - leg.premium) * 100 * leg.quantity;
        }
    }

    return payoff;
}

export default function StrategyComparison({ currentPrice }: Props) {
    const [strategy1, setStrategy1] = useState<string>('Iron Condor');
    const [strategy2, setStrategy2] = useState<string>('Straddle');

    const priceRange = useMemo(() => {
        const range: number[] = [];
        const min = currentPrice * 0.85;
        const max = currentPrice * 1.15;
        const step = (max - min) / 100;
        for (let p = min; p <= max; p += step) {
            range.push(p);
        }
        return range;
    }, [currentPrice]);

    const payoffs1 = useMemo(() => {
        const legs = PRESET_STRATEGIES[strategy1] || [];
        return priceRange.map(p => calculatePayoff(legs, p));
    }, [strategy1, priceRange]);

    const payoffs2 = useMemo(() => {
        const legs = PRESET_STRATEGIES[strategy2] || [];
        return priceRange.map(p => calculatePayoff(legs, p));
    }, [strategy2, priceRange]);

    const maxPayoff = Math.max(...payoffs1, ...payoffs2);
    const minPayoff = Math.min(...payoffs1, ...payoffs2);
    const range = maxPayoff - minPayoff || 1;

    // SVG dimensions
    const width = 500;
    const height = 200;
    const padding = 30;

    const xScale = (i: number) => padding + (i / priceRange.length) * (width - 2 * padding);
    const yScale = (val: number) => height - padding - ((val - minPayoff) / range) * (height - 2 * padding);

    const path1 = payoffs1.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p)}`).join(' ');
    const path2 = payoffs2.map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i)} ${yScale(p)}`).join(' ');

    // Find breakevens
    const findBreakevens = (payoffs: number[]) => {
        const breakevens: number[] = [];
        for (let i = 1; i < payoffs.length; i++) {
            if ((payoffs[i - 1] < 0 && payoffs[i] >= 0) || (payoffs[i - 1] >= 0 && payoffs[i] < 0)) {
                breakevens.push(priceRange[i]);
            }
        }
        return breakevens;
    };

    const breakevens1 = findBreakevens(payoffs1);
    const breakevens2 = findBreakevens(payoffs2);

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                🔀 Strategy Comparison
            </h3>

            {/* Strategy Selectors */}
            <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label className="text-xs text-gray-400 block mb-1">Strategy 1</label>
                    <select
                        value={strategy1}
                        onChange={(e) => setStrategy1(e.target.value)}
                        className="w-full bg-[#0f1117] border border-white/20 rounded px-2 py-1 text-sm text-white"
                    >
                        {Object.keys(PRESET_STRATEGIES).map(name => (
                            <option key={name} value={name}>{name}</option>
                        ))}
                    </select>
                </div>
                <div>
                    <label className="text-xs text-gray-400 block mb-1">Strategy 2</label>
                    <select
                        value={strategy2}
                        onChange={(e) => setStrategy2(e.target.value)}
                        className="w-full bg-[#0f1117] border border-white/20 rounded px-2 py-1 text-sm text-white"
                    >
                        {Object.keys(PRESET_STRATEGIES).map(name => (
                            <option key={name} value={name}>{name}</option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Chart */}
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-48">
                {/* Zero line */}
                <line
                    x1={padding}
                    y1={yScale(0)}
                    x2={width - padding}
                    y2={yScale(0)}
                    stroke="#4a5568"
                    strokeWidth="1"
                    strokeDasharray="4"
                />

                {/* Current price line */}
                <line
                    x1={xScale(priceRange.length / 2)}
                    y1={padding}
                    x2={xScale(priceRange.length / 2)}
                    y2={height - padding}
                    stroke="#3b82f6"
                    strokeWidth="1"
                    strokeDasharray="4"
                />

                {/* Strategy 1 */}
                <path
                    d={path1}
                    fill="none"
                    stroke={STRATEGY_COLORS[strategy1]}
                    strokeWidth="2"
                />

                {/* Strategy 2 */}
                <path
                    d={path2}
                    fill="none"
                    stroke={STRATEGY_COLORS[strategy2]}
                    strokeWidth="2"
                />

                {/* Axis labels */}
                <text x={padding} y={height - 5} fill="#9ca3af" fontSize="10">
                    ${priceRange[0]?.toFixed(0)}
                </text>
                <text x={width - padding - 30} y={height - 5} fill="#9ca3af" fontSize="10">
                    ${priceRange[priceRange.length - 1]?.toFixed(0)}
                </text>
            </svg>

            {/* Legend & Stats */}
            <div className="grid grid-cols-2 gap-4 mt-3 text-xs">
                <div className="bg-[#0f1117] rounded p-2">
                    <div className="flex items-center gap-2 mb-1">
                        <span
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: STRATEGY_COLORS[strategy1] }}
                        />
                        <span className="text-white font-semibold">{strategy1}</span>
                    </div>
                    <div className="text-gray-400">
                        Breakeven: {breakevens1.map(b => `$${b.toFixed(0)}`).join(', ') || 'N/A'}
                    </div>
                    <div className="text-gray-400">
                        Max Profit: ${Math.max(...payoffs1).toFixed(0)}
                    </div>
                    <div className="text-gray-400">
                        Max Loss: ${Math.min(...payoffs1).toFixed(0)}
                    </div>
                </div>
                <div className="bg-[#0f1117] rounded p-2">
                    <div className="flex items-center gap-2 mb-1">
                        <span
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: STRATEGY_COLORS[strategy2] }}
                        />
                        <span className="text-white font-semibold">{strategy2}</span>
                    </div>
                    <div className="text-gray-400">
                        Breakeven: {breakevens2.map(b => `$${b.toFixed(0)}`).join(', ') || 'N/A'}
                    </div>
                    <div className="text-gray-400">
                        Max Profit: ${Math.max(...payoffs2).toFixed(0)}
                    </div>
                    <div className="text-gray-400">
                        Max Loss: ${Math.min(...payoffs2).toFixed(0)}
                    </div>
                </div>
            </div>
        </div>
    );
}
