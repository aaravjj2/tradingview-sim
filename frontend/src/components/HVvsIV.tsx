import { useState, useEffect } from 'react';
import axios from 'axios';

interface HVvsIVProps {
    ticker: string;
}

interface VolData {
    historical_volatility: number;
    implied_volatility: number;
    iv_hv_ratio: number;
    signal: 'expensive' | 'cheap' | 'fair';
}

export default function HVvsIV({ ticker }: HVvsIVProps) {
    const [data, setData] = useState<VolData | null>(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                const response = await axios.get(`/api/volatility/hv/${ticker}`);
                setData(response.data);
            } catch (err) {
                console.error('Failed to load HV vs IV:', err);
            } finally {
                setLoading(false);
            }
        };

        if (ticker) {
            fetchData();
        }
    }, [ticker]);

    if (loading || !data) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-3">📉 HV vs IV</h3>
                <div className="text-gray-400 text-center py-4">Loading...</div>
            </div>
        );
    }

    const hv = data.historical_volatility * 100;
    const iv = data.implied_volatility * 100;
    const maxVol = Math.max(hv, iv, 1) * 1.2;

    const signalColors = {
        expensive: { bg: 'bg-red-500/20', text: 'text-red-400', label: '🔴 Options Expensive' },
        cheap: { bg: 'bg-green-500/20', text: 'text-green-400', label: '🟢 Options Cheap' },
        fair: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', label: '🟡 Fair Value' }
    };

    const signal = signalColors[data.signal];

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white">📉 HV vs IV</h3>
                <span className={`text-xs px-2 py-1 rounded ${signal.bg} ${signal.text}`}>
                    {signal.label}
                </span>
            </div>

            {/* Bar Chart */}
            <div className="space-y-3 mt-4">
                {/* HV Bar */}
                <div>
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                        <span>Historical Volatility (20d)</span>
                        <span>{hv.toFixed(1)}%</span>
                    </div>
                    <div className="h-6 bg-[#0f1117] rounded-full overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full transition-all duration-500"
                            style={{ width: `${(hv / maxVol) * 100}%` }}
                        />
                    </div>
                </div>

                {/* IV Bar */}
                <div>
                    <div className="flex justify-between text-xs text-gray-400 mb-1">
                        <span>Implied Volatility</span>
                        <span>{iv.toFixed(1)}%</span>
                    </div>
                    <div className="h-6 bg-[#0f1117] rounded-full overflow-hidden">
                        <div
                            className="h-full bg-gradient-to-r from-purple-600 to-purple-400 rounded-full transition-all duration-500"
                            style={{ width: `${(iv / maxVol) * 100}%` }}
                        />
                    </div>
                </div>
            </div>

            {/* Ratio */}
            <div className="mt-4 text-center">
                <span className="text-gray-400 text-sm">IV/HV Ratio: </span>
                <span className={`text-lg font-bold ${data.iv_hv_ratio > 1.2 ? 'text-red-400' :
                        data.iv_hv_ratio < 0.8 ? 'text-green-400' :
                            'text-yellow-400'
                    }`}>
                    {data.iv_hv_ratio.toFixed(2)}x
                </span>
            </div>

            {/* Interpretation */}
            <div className="mt-3 text-xs text-gray-500 text-center">
                {data.signal === 'expensive' && 'Consider selling premium (credit spreads)'}
                {data.signal === 'cheap' && 'Consider buying options (long strategies)'}
                {data.signal === 'fair' && 'Volatility priced at historical levels'}
            </div>
        </div>
    );
}
