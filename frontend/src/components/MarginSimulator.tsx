import { useState, useMemo } from 'react';

interface MarginSimulatorProps {
    ticker: string;
    currentPrice: number;
}

interface Position {
    type: 'stock' | 'call' | 'put';
    position: 'long' | 'short';
    strike?: number;
    quantity: number;
}

export default function MarginSimulator({ currentPrice }: MarginSimulatorProps) {
    const [strategy, setStrategy] = useState<string>('iron_condor');
    const [quantity, setQuantity] = useState(1);

    // Calculate margins for the selected strategy
    const marginData = useMemo(() => {
        const positions: Position[] = [];

        switch (strategy) {
            case 'covered_call':
                positions.push(
                    { type: 'stock', position: 'long', quantity: quantity * 100 },
                    { type: 'call', position: 'short', strike: currentPrice * 1.05, quantity }
                );
                break;
            case 'iron_condor':
                positions.push(
                    { type: 'put', position: 'long', strike: currentPrice * 0.92, quantity },
                    { type: 'put', position: 'short', strike: currentPrice * 0.95, quantity },
                    { type: 'call', position: 'short', strike: currentPrice * 1.05, quantity },
                    { type: 'call', position: 'long', strike: currentPrice * 1.08, quantity }
                );
                break;
            case 'naked_put':
                positions.push(
                    { type: 'put', position: 'short', strike: currentPrice * 0.95, quantity }
                );
                break;
            case 'straddle':
                positions.push(
                    { type: 'call', position: 'long', strike: currentPrice, quantity },
                    { type: 'put', position: 'long', strike: currentPrice, quantity }
                );
                break;
        }

        // Calculate Reg-T margin (simplified)
        let regTMargin = 0;
        positions.forEach(pos => {
            if (pos.type === 'stock') {
                regTMargin += pos.quantity * currentPrice * 0.5; // 50% margin
            } else if (pos.position === 'short') {
                if (pos.strike) {
                    // Naked option: 20% of underlying + OTM amount
                    regTMargin += pos.quantity * 100 * currentPrice * 0.20;
                }
            }
        });

        // Adjust for spreads (max loss)
        if (strategy === 'iron_condor') {
            // Max loss is width of spread ($5) - credit received (~$2)
            regTMargin = quantity * (5 - 2) * 100;
        }

        // Calculate Portfolio Margin (simplified - typically 4-5x more efficient)
        // PM uses stress testing, so hedged positions get much lower requirements
        let portfolioMargin = 0;

        // Stress scenarios
        const scenarios = [
            { move: -0.15, name: 'Down 15%' },
            { move: -0.10, name: 'Down 10%' },
            { move: -0.05, name: 'Down 5%' },
            { move: 0, name: 'Unchanged' },
            { move: 0.05, name: 'Up 5%' },
            { move: 0.10, name: 'Up 10%' },
            { move: 0.15, name: 'Up 15%' },
        ];

        const scenarioResults = scenarios.map(scenario => {
            const newPrice = currentPrice * (1 + scenario.move);
            let pnl = 0;

            positions.forEach(pos => {
                if (pos.type === 'stock') {
                    pnl += pos.position === 'long'
                        ? (newPrice - currentPrice) * pos.quantity
                        : (currentPrice - newPrice) * pos.quantity;
                } else if (pos.strike) {
                    // Option P/L at expiration (simplified)
                    let intrinsicValue = 0;
                    if (pos.type === 'call') {
                        intrinsicValue = Math.max(0, newPrice - pos.strike);
                    } else {
                        intrinsicValue = Math.max(0, pos.strike - newPrice);
                    }

                    pnl += pos.position === 'long'
                        ? (intrinsicValue - 2.5) * pos.quantity * 100
                        : (2.5 - intrinsicValue) * pos.quantity * 100;
                }
            });

            return { ...scenario, pnl };
        });

        // Portfolio margin = worst-case loss + buffer
        const worstCase = Math.min(...scenarioResults.map(s => s.pnl));
        portfolioMargin = Math.abs(worstCase) * 1.15; // 15% buffer
        portfolioMargin = Math.max(portfolioMargin, currentPrice * quantity * 100 * 0.05); // 5% minimum

        // Calculate efficiency
        const efficiency = regTMargin / portfolioMargin;
        const savings = regTMargin - portfolioMargin;
        const savingsPct = (savings / regTMargin) * 100;

        return {
            regT: {
                margin: regTMargin,
                capitalRequired: regTMargin,
            },
            portfolio: {
                margin: portfolioMargin,
                capitalRequired: portfolioMargin,
                scenarios: scenarioResults,
                worstCase: worstCase,
            },
            comparison: {
                efficiency,
                savings,
                savingsPct,
                recommendation: efficiency > 1.5 ? 'Portfolio Margin' : 'Either'
            }
        };
    }, [strategy, quantity, currentPrice]);

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                💰 Margin Simulator
                <span className="text-xs text-gray-400">Reg-T vs Portfolio Margin</span>
            </h3>

            {/* Controls */}
            <div className="flex gap-4 mb-4">
                <div className="flex-1">
                    <label className="block text-xs text-gray-400 mb-1">Strategy</label>
                    <select
                        value={strategy}
                        onChange={(e) => setStrategy(e.target.value)}
                        className="w-full bg-[#252b3b] border border-white/20 rounded-lg px-3 py-2 text-sm"
                    >
                        <option value="iron_condor">Iron Condor</option>
                        <option value="covered_call">Covered Call</option>
                        <option value="naked_put">Naked Put</option>
                        <option value="straddle">Long Straddle</option>
                    </select>
                </div>
                <div className="w-24">
                    <label className="block text-xs text-gray-400 mb-1">Quantity</label>
                    <input
                        type="number"
                        value={quantity}
                        onChange={(e) => setQuantity(Number(e.target.value))}
                        min={1}
                        max={100}
                        className="w-full bg-[#252b3b] border border-white/20 rounded-lg px-3 py-2 text-sm"
                    />
                </div>
            </div>

            {/* Comparison Cards */}
            <div className="grid grid-cols-2 gap-4 mb-4">
                {/* Reg-T Card */}
                <div className="bg-[#252b3b] rounded-lg p-4 border border-white/10">
                    <div className="flex items-center gap-2 mb-3">
                        <span className="text-lg">🏦</span>
                        <h4 className="font-semibold">Reg-T Margin</h4>
                    </div>
                    <p className="text-2xl font-mono text-orange-400">
                        ${marginData.regT.margin.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">Strategy-based calculation</p>
                </div>

                {/* Portfolio Margin Card */}
                <div className="bg-gradient-to-br from-green-900/30 to-blue-900/30 rounded-lg p-4 border border-green-500/30">
                    <div className="flex items-center gap-2 mb-3">
                        <span className="text-lg">💎</span>
                        <h4 className="font-semibold">Portfolio Margin</h4>
                    </div>
                    <p className="text-2xl font-mono text-green-400">
                        ${marginData.portfolio.margin.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">Risk-based (stress tested)</p>
                </div>
            </div>

            {/* Efficiency Stats */}
            <div className="bg-[#252b3b] rounded-lg p-4 mb-4">
                <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                        <p className="text-xs text-gray-400">Efficiency Ratio</p>
                        <p className="text-xl font-mono text-blue-400">
                            {marginData.comparison.efficiency.toFixed(1)}x
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-400">Capital Savings</p>
                        <p className="text-xl font-mono text-green-400">
                            ${marginData.comparison.savings.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </p>
                    </div>
                    <div>
                        <p className="text-xs text-gray-400">Savings %</p>
                        <p className="text-xl font-mono text-purple-400">
                            {marginData.comparison.savingsPct.toFixed(0)}%
                        </p>
                    </div>
                </div>
            </div>

            {/* Stress Scenarios */}
            <div className="overflow-x-auto">
                <table className="w-full text-xs">
                    <thead>
                        <tr className="text-gray-400 border-b border-white/10">
                            <th className="text-left py-2">Scenario</th>
                            <th className="text-right py-2">New Price</th>
                            <th className="text-right py-2">P/L</th>
                        </tr>
                    </thead>
                    <tbody>
                        {marginData.portfolio.scenarios.map((scenario, i) => (
                            <tr key={i} className="border-b border-white/5">
                                <td className="py-1">{scenario.name}</td>
                                <td className="py-1 text-right font-mono">
                                    ${(currentPrice * (1 + scenario.move)).toFixed(2)}
                                </td>
                                <td className={`py-1 text-right font-mono ${scenario.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    ${scenario.pnl.toFixed(0)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Recommendation */}
            <div className="mt-4 p-3 bg-gradient-to-r from-blue-900/30 to-purple-900/30 rounded-lg text-center">
                <p className="text-xs text-gray-400">Recommendation</p>
                <p className="font-semibold text-lg">
                    {marginData.comparison.recommendation === 'Portfolio Margin' ? (
                        <span className="text-green-400">✓ Use Portfolio Margin</span>
                    ) : (
                        <span className="text-gray-300">Either margin type acceptable</span>
                    )}
                </p>
                {marginData.comparison.efficiency > 1.5 && (
                    <p className="text-xs text-gray-400 mt-1">
                        PM saves {marginData.comparison.savingsPct.toFixed(0)}% capital for this strategy
                    </p>
                )}
            </div>
        </div>
    );
}
