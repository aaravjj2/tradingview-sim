import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';

interface Props {
    ticker: string;
    currentPrice: number;
}

interface VolData {
    date: string;
    rv: number;  // Realized Volatility
    iv: number;  // Implied Volatility
}

export default function IVRVCone({ ticker, currentPrice }: Props) {
    const [ivData, setIVData] = useState<number>(0.25);
    const [timeframes, setTimeframes] = useState<number[]>([7, 14, 30, 60, 90]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchIV = async () => {
            try {
                setLoading(true);
                const response = await axios.get(`/api/market/iv/${ticker}`);
                setIVData(response.data.iv);
            } catch (err) {
                console.error('Error fetching IV:', err);
            } finally {
                setLoading(false);
            }
        };

        fetchIV();
    }, [ticker]);

    // Simulate term structure (in production, fetch from API)
    const termStructure = useMemo(() => {
        const baseIV = ivData || 0.25;

        // Typically IV increases with time (contango) or decreases (backwardation)
        // Simulate slight contango structure
        return timeframes.map((days, i) => ({
            days,
            iv: baseIV * (1 + i * 0.02),  // IV increases slightly with time
            rv: baseIV * 0.8 * (1 + Math.random() * 0.2),  // RV typically lower
        }));
    }, [ivData, timeframes]);

    // Calculate cone boundaries based on IV
    const coneData = useMemo(() => {
        return termStructure.map(t => {
            const sqrtT = Math.sqrt(t.days / 365);
            const dailyVol = t.iv / Math.sqrt(252);

            return {
                days: t.days,
                iv: t.iv,
                rv: t.rv,
                upper1Sigma: currentPrice * Math.exp(t.iv * sqrtT),
                lower1Sigma: currentPrice * Math.exp(-t.iv * sqrtT),
                upper2Sigma: currentPrice * Math.exp(2 * t.iv * sqrtT),
                lower2Sigma: currentPrice * Math.exp(-2 * t.iv * sqrtT),
            };
        });
    }, [termStructure, currentPrice]);

    // SVG dimensions
    const width = 400;
    const height = 200;
    const padding = 40;

    const maxDays = Math.max(...timeframes);
    const xScale = (days: number) => padding + (days / maxDays) * (width - 2 * padding);

    const priceMin = Math.min(...coneData.map(c => c.lower2Sigma));
    const priceMax = Math.max(...coneData.map(c => c.upper2Sigma));
    const priceRange = priceMax - priceMin || 1;
    const yScale = (price: number) => height - padding - ((price - priceMin) / priceRange) * (height - 2 * padding);

    // Determine if IV is expensive or cheap relative to RV
    const avgIV = termStructure.reduce((s, t) => s + t.iv, 0) / termStructure.length;
    const avgRV = termStructure.reduce((s, t) => s + t.rv, 0) / termStructure.length;
    const ivPremium = ((avgIV / avgRV) - 1) * 100;
    const isExpensive = ivPremium > 10;

    if (loading) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-2">📈 IV vs RV Cone</h3>
                <div className="animate-pulse h-48 bg-gray-700 rounded"></div>
            </div>
        );
    }

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    📈 IV vs RV Cone
                </h3>
                <div className={`text-xs px-2 py-1 rounded ${isExpensive
                        ? 'bg-red-500/20 text-red-400'
                        : 'bg-green-500/20 text-green-400'
                    }`}>
                    {isExpensive ? '💰 Options Expensive' : '🎯 Options Cheap'}
                </div>
            </div>

            {/* Metrics */}
            <div className="grid grid-cols-3 gap-2 mb-4 text-xs">
                <div className="bg-[#0f1117] rounded p-2 text-center">
                    <span className="text-gray-400 block">Avg IV</span>
                    <span className="text-blue-400 font-mono">{(avgIV * 100).toFixed(1)}%</span>
                </div>
                <div className="bg-[#0f1117] rounded p-2 text-center">
                    <span className="text-gray-400 block">Avg RV</span>
                    <span className="text-green-400 font-mono">{(avgRV * 100).toFixed(1)}%</span>
                </div>
                <div className="bg-[#0f1117] rounded p-2 text-center">
                    <span className="text-gray-400 block">IV Premium</span>
                    <span className={`font-mono ${ivPremium > 0 ? 'text-red-400' : 'text-green-400'}`}>
                        {ivPremium > 0 ? '+' : ''}{ivPremium.toFixed(1)}%
                    </span>
                </div>
            </div>

            {/* Price Cone Chart */}
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-40">
                {/* 2-Sigma Cone (outer) */}
                <polygon
                    points={[
                        `${xScale(0)},${yScale(currentPrice)}`,
                        ...coneData.map(c => `${xScale(c.days)},${yScale(c.upper2Sigma)}`),
                        ...coneData.slice().reverse().map(c => `${xScale(c.days)},${yScale(c.lower2Sigma)}`),
                    ].join(' ')}
                    fill="rgba(168, 85, 247, 0.1)"
                    stroke="rgba(168, 85, 247, 0.3)"
                    strokeWidth="1"
                />

                {/* 1-Sigma Cone (inner) */}
                <polygon
                    points={[
                        `${xScale(0)},${yScale(currentPrice)}`,
                        ...coneData.map(c => `${xScale(c.days)},${yScale(c.upper1Sigma)}`),
                        ...coneData.slice().reverse().map(c => `${xScale(c.days)},${yScale(c.lower1Sigma)}`),
                    ].join(' ')}
                    fill="rgba(59, 130, 246, 0.2)"
                    stroke="rgba(59, 130, 246, 0.5)"
                    strokeWidth="1"
                />

                {/* Current price line */}
                <line
                    x1={xScale(0)}
                    y1={yScale(currentPrice)}
                    x2={xScale(maxDays)}
                    y2={yScale(currentPrice)}
                    stroke="#4a5568"
                    strokeWidth="1"
                    strokeDasharray="4"
                />

                {/* Axis labels */}
                <text x={padding} y={height - 5} fill="#9ca3af" fontSize="10">0d</text>
                <text x={width - padding - 20} y={height - 5} fill="#9ca3af" fontSize="10">{maxDays}d</text>
                <text x={5} y={yScale(currentPrice) + 4} fill="#9ca3af" fontSize="9">${currentPrice.toFixed(0)}</text>
            </svg>

            {/* Term Structure Table */}
            <div className="mt-3 overflow-x-auto">
                <table className="w-full text-xs">
                    <thead>
                        <tr className="text-gray-400 border-b border-white/10">
                            <th className="text-left py-1">DTE</th>
                            <th className="text-right py-1">IV</th>
                            <th className="text-right py-1">RV</th>
                            <th className="text-right py-1">1σ Range</th>
                        </tr>
                    </thead>
                    <tbody>
                        {coneData.map((c, i) => (
                            <tr key={i} className="border-b border-white/5">
                                <td className="py-1 text-white">{c.days}d</td>
                                <td className="py-1 text-right text-blue-400">{(c.iv * 100).toFixed(1)}%</td>
                                <td className="py-1 text-right text-green-400">{(c.rv * 100).toFixed(1)}%</td>
                                <td className="py-1 text-right text-gray-300">
                                    ${c.lower1Sigma.toFixed(0)} - ${c.upper1Sigma.toFixed(0)}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>

            {/* Legend */}
            <div className="flex justify-center gap-4 mt-2 text-xs text-gray-400">
                <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded bg-blue-500/30"></span> 1σ (68%)
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-3 h-3 rounded bg-purple-500/20"></span> 2σ (95%)
                </span>
            </div>
        </div>
    );
}
