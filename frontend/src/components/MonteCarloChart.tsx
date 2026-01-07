import { useState } from 'react';
import axios from 'axios';

interface MonteCarloChartProps {
    ticker: string;
    currentPrice: number;
    iv: number;
    legs: {
        option_type: string;
        position: string;
        strike: number;
        premium: number;
        quantity: number;
    }[];
    daysToExpiry?: number;
}

interface SimulationResult {
    pop: number;
    expected_return: number;
    max_profit: number;
    max_loss: number;
    percentiles: {
        "5th": number;
        "25th": number;
        "50th": number;
        "75th": number;
        "95th": number;
    };
}

export default function MonteCarloChart({
    ticker,
    currentPrice,
    iv,
    legs,
    daysToExpiry = 30
}: MonteCarloChartProps) {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<SimulationResult | null>(null);
    const [paths, setPaths] = useState<number[][]>([]);
    const [simCount, setSimCount] = useState(1000);

    const runSimulation = async () => {
        setLoading(true);
        try {
            const response = await axios.post('/api/backtest/monte-carlo', {
                spot: currentPrice,
                volatility: iv,
                days: daysToExpiry,
                legs: legs,
                num_simulations: simCount
            });

            setResult(response.data.results);
            setPaths(response.data.sample_paths || []);
        } catch (err) {
            console.error('Monte Carlo simulation failed:', err);
        } finally {
            setLoading(false);
        }
    };

    const getPopColor = (pop: number) => {
        if (pop >= 70) return 'text-green-400';
        if (pop >= 50) return 'text-yellow-400';
        return 'text-red-400';
    };

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    🎲 Monte Carlo Simulation
                </h3>
                <div className="flex items-center gap-2">
                    <select
                        value={simCount}
                        onChange={(e) => setSimCount(Number(e.target.value))}
                        className="bg-[#0f1117] text-white text-xs px-2 py-1 rounded border border-white/10"
                    >
                        <option value={100}>100 sims</option>
                        <option value={500}>500 sims</option>
                        <option value={1000}>1,000 sims</option>
                        <option value={5000}>5,000 sims</option>
                    </select>
                    <button
                        onClick={runSimulation}
                        disabled={loading}
                        className="bg-gradient-to-r from-purple-600 to-pink-600 text-white text-xs px-3 py-1 rounded hover:opacity-90 disabled:opacity-50"
                    >
                        {loading ? '⏳ Running...' : '▶️ Run'}
                    </button>
                </div>
            </div>

            {!result && !loading && (
                <div className="text-center py-8 text-gray-400">
                    <div className="text-3xl mb-2">🎲</div>
                    <p>Click "Run" to simulate {simCount.toLocaleString()} price paths</p>
                    <p className="text-xs mt-1">Uses Geometric Brownian Motion with IV = {(iv * 100).toFixed(1)}%</p>
                </div>
            )}

            {loading && (
                <div className="text-center py-8">
                    <div className="text-3xl mb-2 animate-bounce">⏳</div>
                    <p className="text-gray-400">Simulating {simCount.toLocaleString()} paths...</p>
                </div>
            )}

            {result && !loading && (
                <div className="space-y-4">
                    {/* Key Metrics */}
                    <div className="grid grid-cols-4 gap-3">
                        <div className="bg-[#0f1117] rounded-lg p-3 text-center">
                            <div className="text-xs text-gray-400 mb-1">Prob. of Profit</div>
                            <div className={`text-2xl font-bold ${getPopColor(result.pop)}`}>
                                {result.pop}%
                            </div>
                        </div>
                        <div className="bg-[#0f1117] rounded-lg p-3 text-center">
                            <div className="text-xs text-gray-400 mb-1">Expected Return</div>
                            <div className={`text-2xl font-bold ${result.expected_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                ${result.expected_return.toFixed(0)}
                            </div>
                        </div>
                        <div className="bg-[#0f1117] rounded-lg p-3 text-center">
                            <div className="text-xs text-gray-400 mb-1">Max Profit</div>
                            <div className="text-2xl font-bold text-green-400">
                                ${result.max_profit.toFixed(0)}
                            </div>
                        </div>
                        <div className="bg-[#0f1117] rounded-lg p-3 text-center">
                            <div className="text-xs text-gray-400 mb-1">Max Loss</div>
                            <div className="text-2xl font-bold text-red-400">
                                ${result.max_loss.toFixed(0)}
                            </div>
                        </div>
                    </div>

                    {/* Price Paths Visualization */}
                    <div className="bg-[#0f1117] rounded-lg p-3">
                        <div className="text-xs text-gray-400 mb-2">Sample Price Paths ({paths.length})</div>
                        <svg viewBox="0 0 400 150" className="w-full h-32">
                            {paths.slice(0, 20).map((path, pathIdx) => {
                                const minP = Math.min(...paths.flat()) * 0.98;
                                const maxP = Math.max(...paths.flat()) * 1.02;
                                const range = maxP - minP;

                                return (
                                    <path
                                        key={pathIdx}
                                        d={path.map((p, i) => {
                                            const x = (i / (path.length - 1)) * 400;
                                            const y = 150 - ((p - minP) / range) * 150;
                                            return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
                                        }).join(' ')}
                                        fill="none"
                                        stroke={`hsla(${(pathIdx * 18) % 360}, 70%, 60%, 0.3)`}
                                        strokeWidth="1"
                                    />
                                );
                            })}
                            {/* Current price line */}
                            <line
                                x1="0"
                                y1="75"
                                x2="400"
                                y2="75"
                                stroke="rgba(255,255,255,0.2)"
                                strokeDasharray="4"
                            />
                        </svg>
                    </div>

                    {/* Percentiles */}
                    <div className="bg-[#0f1117] rounded-lg p-3">
                        <div className="text-xs text-gray-400 mb-2">P/L Distribution (Percentiles)</div>
                        <div className="flex justify-between text-xs">
                            <div className="text-center">
                                <div className="text-gray-500">5th</div>
                                <div className="text-red-400">${result.percentiles["5th"].toFixed(0)}</div>
                            </div>
                            <div className="text-center">
                                <div className="text-gray-500">25th</div>
                                <div className="text-orange-400">${result.percentiles["25th"].toFixed(0)}</div>
                            </div>
                            <div className="text-center">
                                <div className="text-gray-500">50th</div>
                                <div className="text-yellow-400 font-bold">${result.percentiles["50th"].toFixed(0)}</div>
                            </div>
                            <div className="text-center">
                                <div className="text-gray-500">75th</div>
                                <div className="text-lime-400">${result.percentiles["75th"].toFixed(0)}</div>
                            </div>
                            <div className="text-center">
                                <div className="text-gray-500">95th</div>
                                <div className="text-green-400">${result.percentiles["95th"].toFixed(0)}</div>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
