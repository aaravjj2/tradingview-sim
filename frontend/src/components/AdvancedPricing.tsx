import { useState, useEffect } from 'react';
import axios from 'axios';

interface PricingResult {
    spot: number;
    strike: number;
    expiry_days: number;
    iv: number;
    black_scholes: number;
    local_vol: number;
    jump_diffusion: number;
    local_vol_diff: number;
    jump_premium: number;
}

interface Props {
    ticker: string;
    currentPrice: number;
}

export default function AdvancedPricing({ ticker, currentPrice }: Props) {
    const [strike, setStrike] = useState<number>(Math.round(currentPrice));
    const [expiryDays, setExpiryDays] = useState<number>(30);
    const [results, setResults] = useState<{ call: PricingResult; put: PricingResult } | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setStrike(Math.round(currentPrice));
    }, [currentPrice]);

    const fetchPricing = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await axios.get(`/api/market/pricing/compare/${ticker}`, {
                params: { strike, expiry_days: expiryDays }
            });
            setResults(response.data);
        } catch (err) {
            console.error('Error fetching pricing:', err);
            setError('Failed to fetch pricing data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (strike > 0 && expiryDays > 0) {
            const timer = setTimeout(fetchPricing, 500);
            return () => clearTimeout(timer);
        }
    }, [strike, expiryDays, ticker]);

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                🧮 Advanced Pricing Models
            </h3>

            {/* Input Controls */}
            <div className="grid grid-cols-3 gap-4 mb-4">
                <div>
                    <label className="text-xs text-gray-400 block mb-1">Strike</label>
                    <input
                        type="number"
                        value={strike}
                        onChange={(e) => setStrike(parseFloat(e.target.value) || 0)}
                        className="w-full bg-[#0f1117] border border-white/20 rounded px-2 py-1 text-sm text-white"
                    />
                </div>
                <div>
                    <label className="text-xs text-gray-400 block mb-1">Expiry (Days)</label>
                    <input
                        type="number"
                        value={expiryDays}
                        onChange={(e) => setExpiryDays(parseInt(e.target.value) || 30)}
                        className="w-full bg-[#0f1117] border border-white/20 rounded px-2 py-1 text-sm text-white"
                    />
                </div>
                <div className="flex items-end">
                    <button
                        onClick={fetchPricing}
                        disabled={loading}
                        className="w-full bg-blue-600 hover:bg-blue-500 rounded px-3 py-1 text-sm text-white disabled:opacity-50"
                    >
                        {loading ? '...' : '🔄 Calculate'}
                    </button>
                </div>
            </div>

            {error && (
                <div className="text-red-400 text-sm mb-4">{error}</div>
            )}

            {results && (
                <div className="space-y-4">
                    {/* Model Comparison Table */}
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="text-gray-400 border-b border-white/10">
                                    <th className="text-left py-2">Model</th>
                                    <th className="text-right py-2">Call Price</th>
                                    <th className="text-right py-2">Put Price</th>
                                    <th className="text-right py-2">Δ from BS</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr className="border-b border-white/5">
                                    <td className="py-2 text-white flex items-center gap-2">
                                        📊 Black-Scholes
                                        <span className="text-xs text-gray-500">(baseline)</span>
                                    </td>
                                    <td className="py-2 text-right font-mono text-gray-300">
                                        ${results.call.black_scholes.toFixed(2)}
                                    </td>
                                    <td className="py-2 text-right font-mono text-gray-300">
                                        ${results.put.black_scholes.toFixed(2)}
                                    </td>
                                    <td className="py-2 text-right text-gray-500">—</td>
                                </tr>
                                <tr className="border-b border-white/5">
                                    <td className="py-2 text-white flex items-center gap-2">
                                        📈 Local Volatility
                                        <span className="text-xs text-blue-400">(Dupire)</span>
                                    </td>
                                    <td className="py-2 text-right font-mono text-blue-400">
                                        ${results.call.local_vol.toFixed(2)}
                                    </td>
                                    <td className="py-2 text-right font-mono text-blue-400">
                                        ${results.put.local_vol.toFixed(2)}
                                    </td>
                                    <td className={`py-2 text-right font-mono ${results.call.local_vol_diff > 0 ? 'text-green-400' : 'text-red-400'
                                        }`}>
                                        {results.call.local_vol_diff > 0 ? '+' : ''}
                                        ${results.call.local_vol_diff.toFixed(2)}
                                    </td>
                                </tr>
                                <tr className="border-b border-white/5">
                                    <td className="py-2 text-white flex items-center gap-2">
                                        ⚡ Jump-Diffusion
                                        <span className="text-xs text-purple-400">(Merton)</span>
                                    </td>
                                    <td className="py-2 text-right font-mono text-purple-400">
                                        ${results.call.jump_diffusion.toFixed(2)}
                                    </td>
                                    <td className="py-2 text-right font-mono text-purple-400">
                                        ${results.put.jump_diffusion.toFixed(2)}
                                    </td>
                                    <td className={`py-2 text-right font-mono ${results.call.jump_premium > 0 ? 'text-green-400' : 'text-red-400'
                                        }`}>
                                        {results.call.jump_premium > 0 ? '+' : ''}
                                        ${results.call.jump_premium.toFixed(2)}
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>

                    {/* Key Metrics */}
                    <div className="grid grid-cols-4 gap-2 text-xs">
                        <div className="bg-[#0f1117] rounded p-2 text-center">
                            <span className="text-gray-400 block">Spot</span>
                            <span className="text-white font-mono">${results.call.spot.toFixed(2)}</span>
                        </div>
                        <div className="bg-[#0f1117] rounded p-2 text-center">
                            <span className="text-gray-400 block">IV</span>
                            <span className="text-yellow-400 font-mono">{(results.call.iv * 100).toFixed(1)}%</span>
                        </div>
                        <div className="bg-[#0f1117] rounded p-2 text-center">
                            <span className="text-gray-400 block">Moneyness</span>
                            <span className="text-white font-mono">
                                {((results.call.spot / results.call.strike) * 100).toFixed(1)}%
                            </span>
                        </div>
                        <div className="bg-[#0f1117] rounded p-2 text-center">
                            <span className="text-gray-400 block">DTE</span>
                            <span className="text-white font-mono">{results.call.expiry_days}d</span>
                        </div>
                    </div>

                    {/* Explanation */}
                    <div className="mt-3 p-2 bg-[#0f1117] rounded text-xs text-gray-400">
                        <strong className="text-gray-300">💡 Model Differences:</strong>
                        <ul className="mt-1 space-y-1 list-disc list-inside">
                            <li><span className="text-blue-400">Local Vol</span>: Accounts for volatility skew, better for ATM options</li>
                            <li><span className="text-purple-400">Jump-Diffusion</span>: Adds tail risk premium, better for OTM options</li>
                        </ul>
                    </div>
                </div>
            )}

            {!results && !loading && (
                <div className="text-center text-gray-500 py-8">
                    Enter strike and expiry to compare pricing models
                </div>
            )}
        </div>
    );
}
