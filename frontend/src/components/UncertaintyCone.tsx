import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';

interface UncertaintyConeProps {
    ticker: string;
    currentPrice: number;
    days?: number;
}

interface ForecastData {
    current_price: number;
    days: number;
    p10: number[];
    p25: number[];
    p50: number[];
    p75: number[];
    p90: number[];
    trend_forecast?: number[];  // Legacy
    lstm_forecast?: number[];   // New v2
    garch_volatility: number[];
    event_dates: string[];
    regime?: string;
    weights?: Record<string, number>;
}

export default function UncertaintyCone({ ticker, currentPrice, days = 30 }: UncertaintyConeProps) {
    const [forecast, setForecast] = useState<ForecastData | null>(null);
    const [loading, setLoading] = useState(false);
    const [showBands, setShowBands] = useState({ p90: true, p75: true, p50: true });

    useEffect(() => {
        const fetchForecast = async () => {
            if (!ticker || !currentPrice) return;

            setLoading(true);
            try {
                const response = await axios.get(`/api/forecast/ensemble/${ticker}`, {
                    params: { days, current_price: currentPrice }
                });
                setForecast(response.data);
            } catch (err) {
                console.error('Failed to fetch forecast:', err);
                // Generate mock data
                setForecast(generateMockForecast(currentPrice, days));
            } finally {
                setLoading(false);
            }
        };

        fetchForecast();
    }, [ticker, currentPrice, days]);

    const chartData = useMemo(() => {
        if (!forecast) return null;

        const width = 600;
        const height = 200;
        const padding = { top: 20, right: 20, bottom: 30, left: 50 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        // Find min/max across all bands - with null safety
        const allValues = [
            ...(forecast.p10 || []),
            ...(forecast.p90 || []),
            currentPrice
        ].filter(v => typeof v === 'number' && !isNaN(v));

        if (allValues.length === 0) return null;

        const minPrice = Math.min(...allValues) * 0.98;
        const maxPrice = Math.max(...allValues) * 1.02;

        const xScale = (i: number) => padding.left + (i / (forecast.days)) * chartWidth;
        const yScale = (price: number) =>
            padding.top + chartHeight - ((price - minPrice) / (maxPrice - minPrice)) * chartHeight;

        // Generate path strings for bands
        const createAreaPath = (upper: number[], lower: number[]) => {
            const upperPath = upper.map((p, i) => `${xScale(i)},${yScale(p)}`).join(' L');
            const lowerPath = lower.slice().reverse().map((p, i) =>
                `${xScale(lower.length - 1 - i)},${yScale(p)}`
            ).join(' L');
            return `M${upperPath} L${lowerPath} Z`;
        };

        const createLinePath = (values: number[]) => {
            return values.map((p, i) => `${i === 0 ? 'M' : 'L'}${xScale(i)},${yScale(p)}`).join(' ');
        };

        // Trend line (support both old and new formats)
        const trendData = forecast.lstm_forecast || forecast.trend_forecast || forecast.p50;

        return {
            width,
            height,
            padding,
            minPrice,
            maxPrice,
            xScale,
            yScale,
            p90Band: createAreaPath(forecast.p90 || [], forecast.p10 || []),
            p75Band: createAreaPath(forecast.p75 || [], forecast.p25 || []),
            p50Line: createLinePath(forecast.p50 || []),
            trendLine: trendData ? createLinePath(trendData) : '',
            currentPriceY: yScale(currentPrice)
        };
    }, [forecast, currentPrice]);

    if (loading) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4">
                <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
                    🎯 Uncertainty Cone
                    <span className="animate-pulse text-gray-400">Loading...</span>
                </h3>
                <div className="h-48 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-blue-500"></div>
                </div>
            </div>
        );
    }

    if (!forecast || !chartData) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4">
                <h3 className="text-sm font-semibold mb-2">🎯 Uncertainty Cone</h3>
                <p className="text-gray-400 text-sm">No forecast data available</p>
            </div>
        );
    }

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                    🎯 Uncertainty Cone
                    <span className="text-xs text-gray-400">{days} Day Forecast</span>
                </h3>

                {/* Band toggles */}
                <div className="flex items-center gap-2 text-xs">
                    <label className="flex items-center gap-1 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={showBands.p90}
                            onChange={() => setShowBands(b => ({ ...b, p90: !b.p90 }))}
                            className="w-3 h-3"
                        />
                        <span className="text-purple-400">P10-90</span>
                    </label>
                    <label className="flex items-center gap-1 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={showBands.p75}
                            onChange={() => setShowBands(b => ({ ...b, p75: !b.p75 }))}
                            className="w-3 h-3"
                        />
                        <span className="text-blue-400">P25-75</span>
                    </label>
                    <label className="flex items-center gap-1 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={showBands.p50}
                            onChange={() => setShowBands(b => ({ ...b, p50: !b.p50 }))}
                            className="w-3 h-3"
                        />
                        <span className="text-green-400">Median</span>
                    </label>
                </div>
            </div>

            {/* Chart */}
            <svg viewBox={`0 0 ${chartData.width} ${chartData.height}`} className="w-full h-48">
                {/* P90 Band (widest) */}
                {showBands.p90 && (
                    <path
                        d={chartData.p90Band}
                        fill="rgba(168, 85, 247, 0.15)"
                        stroke="rgba(168, 85, 247, 0.3)"
                        strokeWidth="1"
                    />
                )}

                {/* P75 Band */}
                {showBands.p75 && (
                    <path
                        d={chartData.p75Band}
                        fill="rgba(59, 130, 246, 0.2)"
                        stroke="rgba(59, 130, 246, 0.4)"
                        strokeWidth="1"
                    />
                )}

                {/* Median Line (P50) */}
                {showBands.p50 && (
                    <path
                        d={chartData.p50Line}
                        fill="none"
                        stroke="#22c55e"
                        strokeWidth="2"
                    />
                )}

                {/* Trend Line */}
                <path
                    d={chartData.trendLine}
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth="1"
                    strokeDasharray="4 2"
                />

                {/* Current Price Line */}
                <line
                    x1={chartData.padding.left}
                    y1={chartData.currentPriceY}
                    x2={chartData.width - chartData.padding.right}
                    y2={chartData.currentPriceY}
                    stroke="#fff"
                    strokeWidth="1"
                    strokeDasharray="2 2"
                    opacity="0.5"
                />

                {/* Current Price Marker */}
                <circle
                    cx={chartData.padding.left}
                    cy={chartData.currentPriceY}
                    r="4"
                    fill="#fff"
                />

                {/* Y-axis labels */}
                <text x="45" y={chartData.padding.top + 5} fill="#9ca3af" fontSize="10" textAnchor="end">
                    ${chartData.maxPrice.toFixed(0)}
                </text>
                <text x="45" y={chartData.height - chartData.padding.bottom} fill="#9ca3af" fontSize="10" textAnchor="end">
                    ${chartData.minPrice.toFixed(0)}
                </text>

                {/* X-axis labels */}
                <text x={chartData.padding.left} y={chartData.height - 5} fill="#9ca3af" fontSize="10">
                    Today
                </text>
                <text x={chartData.width - chartData.padding.right} y={chartData.height - 5} fill="#9ca3af" fontSize="10" textAnchor="end">
                    +{days}d
                </text>
            </svg>

            {/* Stats */}
            <div className="grid grid-cols-4 gap-2 mt-3 text-xs">
                <div className="bg-[#252b3b] rounded p-2 text-center">
                    <p className="text-gray-400">P10 (Bear)</p>
                    <p className="text-red-400 font-mono">${forecast.p10[forecast.p10.length - 1]?.toFixed(2)}</p>
                </div>
                <div className="bg-[#252b3b] rounded p-2 text-center">
                    <p className="text-gray-400">P50 (Mid)</p>
                    <p className="text-green-400 font-mono">${forecast.p50[forecast.p50.length - 1]?.toFixed(2)}</p>
                </div>
                <div className="bg-[#252b3b] rounded p-2 text-center">
                    <p className="text-gray-400">P90 (Bull)</p>
                    <p className="text-purple-400 font-mono">${forecast.p90[forecast.p90.length - 1]?.toFixed(2)}</p>
                </div>
                <div className="bg-[#252b3b] rounded p-2 text-center">
                    <p className="text-gray-400">GARCH σ</p>
                    <p className="text-blue-400 font-mono">{(forecast.garch_volatility[0] * 100).toFixed(1)}%</p>
                </div>
            </div>
        </div>
    );
}

// Mock data generator for when API is unavailable
function generateMockForecast(currentPrice: number, days: number): ForecastData {
    const vol = 0.25;
    const dt = 1 / 252;

    const p10: number[] = [currentPrice];
    const p25: number[] = [currentPrice];
    const p50: number[] = [currentPrice];
    const p75: number[] = [currentPrice];
    const p90: number[] = [currentPrice];
    const trend: number[] = [currentPrice];

    for (let i = 1; i <= days; i++) {
        const t = i * dt;
        const sqrtT = Math.sqrt(t);

        p10.push(currentPrice * Math.exp(-1.28 * vol * sqrtT));
        p25.push(currentPrice * Math.exp(-0.67 * vol * sqrtT));
        p50.push(currentPrice * Math.exp(0.02 * t)); // Slight drift
        p75.push(currentPrice * Math.exp(0.67 * vol * sqrtT));
        p90.push(currentPrice * Math.exp(1.28 * vol * sqrtT));
        trend.push(currentPrice * (1 + 0.001 * i)); // Linear trend
    }

    return {
        current_price: currentPrice,
        days,
        p10,
        p25,
        p50,
        p75,
        p90,
        trend_forecast: trend,
        garch_volatility: Array(days).fill(vol),
        event_dates: []
    };
}
