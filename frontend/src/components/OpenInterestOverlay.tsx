import { useState, useEffect } from 'react';
import axios from 'axios';

interface OIData {
    strike: number;
    call_oi: number;
    put_oi: number;
    total_oi: number;
    net_gamma: number;
}

interface OIProfile {
    ticker: string;
    current_price: number;
    profile: OIData[];
    max_oi_strike: number;
    support_levels: number[];
    resistance_levels: number[];
}

interface Props {
    ticker: string;
    currentPrice: number;
}

export default function OpenInterestOverlay({ ticker, currentPrice }: Props) {
    const [data, setData] = useState<OIProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [showOverlay, setShowOverlay] = useState(true);

    useEffect(() => {
        const fetchOI = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`/api/market/oi/${ticker}`);
                setData(response.data);
            } catch (err) {
                console.error('Error fetching OI data:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchOI();
    }, [ticker]);

    if (loading) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-2">📊 Open Interest Walls</h3>
                <div className="animate-pulse h-48 bg-gray-700 rounded"></div>
            </div>
        );
    }

    if (!data || data.profile.length === 0) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-2">📊 Open Interest Walls</h3>
                <p className="text-gray-400 text-sm">No OI data available for {ticker}</p>
            </div>
        );
    }

    // Calculate max OI for scaling
    const maxOI = Math.max(...data.profile.map(p => p.total_oi));

    // Filter to show strikes around current price
    const relevantStrikes = data.profile.filter(
        p => Math.abs(p.strike - currentPrice) / currentPrice < 0.1
    );

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    📊 Open Interest Walls
                </h3>
                <button
                    onClick={() => setShowOverlay(!showOverlay)}
                    className={`text-xs px-2 py-1 rounded ${showOverlay ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-700 text-gray-400'
                        }`}
                >
                    {showOverlay ? '👁️ Hide' : '👁️ Show'}
                </button>
            </div>

            {/* Key Levels */}
            <div className="grid grid-cols-3 gap-2 mb-4 text-xs">
                <div className="bg-[#0f1117] rounded p-2">
                    <span className="text-gray-400">Max OI Pin:</span>
                    <span className="text-yellow-400 font-mono ml-1">${data.max_oi_strike}</span>
                </div>
                <div className="bg-[#0f1117] rounded p-2">
                    <span className="text-gray-400">Support:</span>
                    <span className="text-green-400 font-mono ml-1">
                        {data.support_levels[0] ? `$${data.support_levels[0]}` : 'N/A'}
                    </span>
                </div>
                <div className="bg-[#0f1117] rounded p-2">
                    <span className="text-gray-400">Resistance:</span>
                    <span className="text-red-400 font-mono ml-1">
                        {data.resistance_levels[0] ? `$${data.resistance_levels[0]}` : 'N/A'}
                    </span>
                </div>
            </div>

            {showOverlay && (
                <div className="space-y-1 max-h-64 overflow-y-auto">
                    {relevantStrikes.map((item) => {
                        const isCurrentStrike = Math.abs(item.strike - currentPrice) < 1;
                        const callWidth = (item.call_oi / maxOI) * 100;
                        const putWidth = (item.put_oi / maxOI) * 100;

                        return (
                            <div
                                key={item.strike}
                                className={`flex items-center gap-2 text-xs ${isCurrentStrike ? 'bg-blue-900/30 rounded' : ''
                                    }`}
                            >
                                {/* Put OI Bar (left) */}
                                <div className="w-24 flex justify-end">
                                    <div
                                        className="h-4 bg-red-500/60 rounded-l"
                                        style={{ width: `${putWidth}%` }}
                                    />
                                </div>

                                {/* Strike Price */}
                                <div className={`w-16 text-center font-mono ${isCurrentStrike ? 'text-blue-400 font-bold' : 'text-gray-300'
                                    }`}>
                                    ${item.strike}
                                </div>

                                {/* Call OI Bar (right) */}
                                <div className="w-24">
                                    <div
                                        className="h-4 bg-green-500/60 rounded-r"
                                        style={{ width: `${callWidth}%` }}
                                    />
                                </div>

                                {/* Gamma indicator */}
                                <div className={`w-8 text-right text-xs ${item.net_gamma > 0 ? 'text-green-400' : 'text-red-400'
                                    }`}>
                                    {item.net_gamma > 0 ? '+' : ''}{(item.net_gamma / 1000).toFixed(1)}k
                                </div>
                            </div>
                        );
                    })}
                </div>
            )}

            {/* Legend */}
            <div className="flex justify-center gap-4 mt-3 text-xs text-gray-400">
                <span className="flex items-center gap-1">
                    <span className="w-3 h-3 bg-red-500/60 rounded"></span> Puts
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-3 h-3 bg-green-500/60 rounded"></span> Calls
                </span>
            </div>
        </div>
    );
}
