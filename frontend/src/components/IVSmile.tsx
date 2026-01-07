import { useState, useEffect } from 'react';
import axios from 'axios';

interface IVSmileProps {
    ticker: string;
    expiration?: string;
}

interface SmileData {
    expiration: string;
    calls: { strike: number; iv: number }[];
    puts: { strike: number; iv: number }[];
    skew: 'bullish' | 'bearish' | 'neutral';
}

// Generate realistic IV smile data
function generateMockSmile(currentPrice: number = 500): SmileData {
    const strikes: number[] = [];
    const atmStrike = Math.round(currentPrice / 5) * 5;

    for (let i = -10; i <= 10; i++) {
        strikes.push(atmStrike + i * 5);
    }

    // IV smile: OTM options have higher IV (smile shape)
    const atmIV = 25 + Math.random() * 10; // 25-35%

    const calls = strikes.map(strike => {
        const moneyness = (strike - currentPrice) / currentPrice;
        // Call skew: slightly higher IV for OTM calls
        const skewAdj = Math.abs(moneyness) * 15 + (moneyness > 0 ? moneyness * 5 : 0);
        return { strike, iv: atmIV + skewAdj + Math.random() * 2 };
    });

    const puts = strikes.map(strike => {
        const moneyness = (currentPrice - strike) / currentPrice;
        // Put skew: higher IV for OTM puts (fear premium)
        const skewAdj = Math.abs(moneyness) * 20 + (moneyness > 0 ? moneyness * 10 : 0);
        return { strike, iv: atmIV + skewAdj + Math.random() * 2 };
    });

    // Determine skew from relative IVs
    const avgCallIV = calls.reduce((s, c) => s + c.iv, 0) / calls.length;
    const avgPutIV = puts.reduce((s, p) => s + p.iv, 0) / puts.length;
    const skew: 'bullish' | 'bearish' | 'neutral' =
        avgPutIV > avgCallIV + 3 ? 'bearish' :
            avgCallIV > avgPutIV + 3 ? 'bullish' : 'neutral';

    return {
        expiration: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
        calls,
        puts,
        skew
    };
}

export default function IVSmile({ ticker, expiration }: IVSmileProps) {
    const [smile, setSmile] = useState<SmileData | null>(null);
    const [loading, setLoading] = useState(false);
    const [currentPrice, setCurrentPrice] = useState(500);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            try {
                // Try to get current price first
                const priceResp = await axios.get(`/api/market/price/${ticker}`);
                const price = priceResp.data?.price || 500;
                setCurrentPrice(price);

                // Try to get real smile data
                const url = expiration
                    ? `/api/volatility/smile/${ticker}?expiration=${expiration}`
                    : `/api/volatility/smile/${ticker}`;
                const response = await axios.get(url);
                setSmile(response.data);
            } catch {
                // Use mock data on error
                setSmile(generateMockSmile(currentPrice));
            } finally {
                setLoading(false);
            }
        };

        if (ticker) {
            fetchData();
        }
    }, [ticker, expiration, currentPrice]);

    // Generate mock on mount if no data
    useEffect(() => {
        if (!smile && !loading) {
            setSmile(generateMockSmile(currentPrice));
        }
    }, []);

    if (loading) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4">
                <h3 className="text-lg font-semibold text-white mb-3">📊 IV Smile</h3>
                <div className="text-gray-400 text-center py-8">Loading...</div>
            </div>
        );
    }

    if (!smile) {
        return null;
    }

    // Prepare chart data
    const allStrikes = [...new Set([
        ...smile.calls.map(c => c.strike),
        ...smile.puts.map(p => p.strike)
    ])].sort((a, b) => a - b);

    const maxIV = Math.max(
        ...smile.calls.map(c => c.iv),
        ...smile.puts.map(p => p.iv),
        1
    );

    const getCallIV = (strike: number) => {
        const call = smile.calls.find(c => c.strike === strike);
        return call?.iv || 0;
    };

    const getPutIV = (strike: number) => {
        const put = smile.puts.find(p => p.strike === strike);
        return put?.iv || 0;
    };

    const skewColors = {
        bullish: 'text-green-400',
        bearish: 'text-red-400',
        neutral: 'text-yellow-400'
    };

    const skewLabels = {
        bullish: '📈 Call Skew (Bullish)',
        bearish: '📉 Put Skew (Bearish)',
        neutral: '➡️ Neutral'
    };

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white">📊 IV Smile</h3>
                <span className={`text-sm ${skewColors[smile.skew]}`}>
                    {skewLabels[smile.skew]}
                </span>
            </div>

            <div className="text-xs text-gray-400 mb-2">
                Expiration: {smile.expiration}
            </div>

            {/* Chart */}
            <svg viewBox="0 0 400 200" className="w-full h-48">
                {/* Grid */}
                <line x1="50" y1="180" x2="380" y2="180" stroke="rgba(255,255,255,0.2)" />
                <line x1="50" y1="20" x2="50" y2="180" stroke="rgba(255,255,255,0.2)" />

                {/* Y-axis labels */}
                <text x="40" y="25" fontSize="10" fill="#888" textAnchor="end">{maxIV.toFixed(0)}%</text>
                <text x="40" y="100" fontSize="10" fill="#888" textAnchor="end">{(maxIV / 2).toFixed(0)}%</text>
                <text x="40" y="180" fontSize="10" fill="#888" textAnchor="end">0%</text>

                {/* Call IV Line (Green) */}
                <path
                    d={allStrikes.map((strike, i) => {
                        const x = 50 + (330 / (allStrikes.length - 1 || 1)) * i;
                        const iv = getCallIV(strike);
                        const y = 180 - (iv / maxIV) * 160;
                        return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
                    }).join(' ')}
                    fill="none"
                    stroke="#00E676"
                    strokeWidth="2"
                />

                {/* Put IV Line (Red) */}
                <path
                    d={allStrikes.map((strike, i) => {
                        const x = 50 + (330 / (allStrikes.length - 1 || 1)) * i;
                        const iv = getPutIV(strike);
                        const y = 180 - (iv / maxIV) * 160;
                        return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
                    }).join(' ')}
                    fill="none"
                    stroke="#FF1744"
                    strokeWidth="2"
                />

                {/* X-axis labels (strikes) */}
                {allStrikes.filter((_, i) => i % Math.ceil(allStrikes.length / 6) === 0).map((strike, i) => {
                    const x = 50 + (330 / (allStrikes.length - 1 || 1)) *
                        allStrikes.indexOf(strike);
                    return (
                        <text key={i} x={x} y="195" fontSize="9" fill="#888" textAnchor="middle">
                            ${strike}
                        </text>
                    );
                })}
            </svg>

            {/* Legend */}
            <div className="flex justify-center gap-6 mt-2 text-xs">
                <span className="flex items-center gap-1">
                    <span className="w-3 h-0.5 bg-green-500"></span>
                    <span className="text-gray-400">Call IV</span>
                </span>
                <span className="flex items-center gap-1">
                    <span className="w-3 h-0.5 bg-red-500"></span>
                    <span className="text-gray-400">Put IV</span>
                </span>
            </div>
        </div>
    );
}
