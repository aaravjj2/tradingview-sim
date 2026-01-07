import { useState, useEffect } from 'react';
import axios from 'axios';

interface MaxPainIndicatorProps {
    ticker: string;
    currentPrice: number;
}

interface MaxPainData {
    max_pain: number;
    pain_by_strike: { strike: number; pain: number }[];
}

export default function MaxPainIndicator({ ticker, currentPrice }: MaxPainIndicatorProps) {
    const [data, setData] = useState<MaxPainData | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchMaxPain = async () => {
            setLoading(true);
            try {
                const response = await axios.get(`/api/volatility/maxpain/${ticker}`);
                setData(response.data);
            } catch (err) {
                console.error('Failed to load max pain:', err);
            } finally {
                setLoading(false);
            }
        };

        if (ticker) {
            fetchMaxPain();
        }
    }, [ticker]);

    if (loading || !data) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-3">💀 Max Pain</h3>
                <div className="text-gray-400 text-center py-4">Loading...</div>
            </div>
        );
    }

    const priceDiff = data.max_pain - currentPrice;
    const priceDiffPct = (priceDiff / currentPrice) * 100;
    const direction = priceDiff > 0 ? 'above' : 'below';
    const directionColor = priceDiff > 0 ? 'text-green-400' : 'text-red-400';

    // Prepare chart data - take top 10 strikes around max pain
    const sortedPain = [...data.pain_by_strike].sort((a, b) =>
        Math.abs(a.strike - data.max_pain) - Math.abs(b.strike - data.max_pain)
    ).slice(0, 10).sort((a, b) => a.strike - b.strike);

    const maxPainValue = Math.max(...sortedPain.map(p => p.pain), 1);

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white">💀 Max Pain</h3>
                <span className="text-sm text-gray-400">
                    Exp: Friday
                </span>
            </div>

            {/* Main Display */}
            <div className="text-center mb-4">
                <div className="text-3xl font-bold text-orange-400">
                    ${data.max_pain.toFixed(2)}
                </div>
                <div className={`text-sm ${directionColor}`}>
                    {Math.abs(priceDiffPct).toFixed(1)}% {direction} current price
                </div>
            </div>

            {/* Pain Chart */}
            <div className="space-y-2">
                {sortedPain.map((item) => (
                    <div key={item.strike} className="flex items-center gap-2">
                        <div className={`w-16 text-xs text-right ${item.strike === data.max_pain
                                ? 'text-orange-400 font-bold'
                                : 'text-gray-400'
                            }`}>
                            ${item.strike}
                        </div>
                        <div className="flex-1 h-4 bg-[#0f1117] rounded overflow-hidden">
                            <div
                                className={`h-full rounded transition-all duration-300 ${item.strike === data.max_pain
                                        ? 'bg-orange-500'
                                        : 'bg-gray-600'
                                    }`}
                                style={{ width: `${(item.pain / maxPainValue) * 100}%` }}
                            />
                        </div>
                    </div>
                ))}
            </div>

            {/* Interpretation */}
            <div className="mt-4 text-xs text-gray-500 text-center">
                Price tends to gravitate toward max pain at expiration
            </div>
        </div>
    );
}
