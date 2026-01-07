import { useState, useEffect } from 'react';
import axios from 'axios';

interface GEXData {
    strike: number;
    gex: number;
}

interface GEXProfile {
    ticker: string;
    current_price: number;
    profile: GEXData[];
    total_gex: number;
    zero_gamma_level: number;
    regime: string;
    regime_description: string;
}

interface Props {
    ticker: string;
    currentPrice: number;
}

export default function GEXProfile({ ticker, currentPrice }: Props) {
    const [data, setData] = useState<GEXProfile | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchGEX = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`/api/market/gex/${ticker}`);
                setData(response.data);
            } catch (err) {
                console.error('Error fetching GEX data:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchGEX();
    }, [ticker]);

    if (loading) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-2">⚡ Gamma Exposure (GEX)</h3>
                <div className="animate-pulse h-48 bg-gray-700 rounded"></div>
            </div>
        );
    }

    if (!data || data.profile.length === 0) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-2">⚡ Gamma Exposure (GEX)</h3>
                <p className="text-gray-400 text-sm">No GEX data available for {ticker}</p>
            </div>
        );
    }

    // Calculate max GEX for scaling
    const maxGEX = Math.max(...data.profile.map(p => Math.abs(p.gex)));

    // Filter to show strikes around current price
    const relevantStrikes = data.profile.filter(
        p => Math.abs(p.strike - currentPrice) / currentPrice < 0.1
    );

    const isPositiveRegime = data.regime === 'positive';

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    ⚡ Gamma Exposure (GEX)
                </h3>
                <div className={`text-xs px-2 py-1 rounded ${isPositiveRegime
                        ? 'bg-green-500/20 text-green-400'
                        : 'bg-red-500/20 text-red-400'
                    }`}>
                    {isPositiveRegime ? '🟢 Positive γ' : '🔴 Negative γ'}
                </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-3 gap-2 mb-4 text-xs">
                <div className="bg-[#0f1117] rounded p-2">
                    <span className="text-gray-400">Total GEX:</span>
                    <span className={`font-mono ml-1 ${data.total_gex > 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                        {(data.total_gex / 1e9).toFixed(2)}B
                    </span>
                </div>
                <div className="bg-[#0f1117] rounded p-2">
                    <span className="text-gray-400">Flip Point:</span>
                    <span className="text-yellow-400 font-mono ml-1">${data.zero_gamma_level}</span>
                </div>
                <div className="bg-[#0f1117] rounded p-2">
                    <span className="text-gray-400">Regime:</span>
                    <span className={`ml-1 ${isPositiveRegime ? 'text-green-400' : 'text-red-400'
                        }`}>
                        {data.regime_description}
                    </span>
                </div>
            </div>

            {/* GEX Bar Chart */}
            <div className="space-y-1 max-h-48 overflow-y-auto">
                {relevantStrikes.map((item) => {
                    const isCurrentStrike = Math.abs(item.strike - currentPrice) < 1;
                    const barWidth = Math.abs(item.gex) / maxGEX * 100;
                    const isPositive = item.gex > 0;

                    return (
                        <div
                            key={item.strike}
                            className={`flex items-center gap-2 text-xs ${isCurrentStrike ? 'bg-blue-900/30 rounded' : ''
                                }`}
                        >
                            {/* Strike Price */}
                            <div className={`w-16 text-right font-mono ${isCurrentStrike ? 'text-blue-400 font-bold' : 'text-gray-300'
                                }`}>
                                ${item.strike}
                            </div>

                            {/* GEX Bar */}
                            <div className="flex-1 flex items-center h-4">
                                <div className="w-1/2 flex justify-end">
                                    {!isPositive && (
                                        <div
                                            className="h-3 bg-red-500/70 rounded-l"
                                            style={{ width: `${barWidth}%` }}
                                        />
                                    )}
                                </div>
                                <div className="w-px h-4 bg-gray-600" />
                                <div className="w-1/2">
                                    {isPositive && (
                                        <div
                                            className="h-3 bg-green-500/70 rounded-r"
                                            style={{ width: `${barWidth}%` }}
                                        />
                                    )}
                                </div>
                            </div>

                            {/* GEX Value */}
                            <div className={`w-16 text-right font-mono ${isPositive ? 'text-green-400' : 'text-red-400'
                                }`}>
                                {(item.gex / 1e6).toFixed(1)}M
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* Explanation */}
            <div className="mt-3 p-2 bg-[#0f1117] rounded text-xs text-gray-400">
                <strong className="text-gray-300">💡 What is GEX?</strong>
                <p className="mt-1">
                    Gamma Exposure measures dealer hedging pressure.
                    <span className="text-green-400"> Positive GEX</span> = dealers buy dips/sell rallies (stabilizing).
                    <span className="text-red-400"> Negative GEX</span> = dealers amplify moves (volatile).
                </p>
            </div>
        </div>
    );
}
