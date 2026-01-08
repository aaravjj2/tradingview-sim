import { useState, useEffect } from 'react';
import axios from 'axios';

interface RegimeData {
    regime: string;
    confidence: number;
    adx: number;
    vix: number;
    rsi: number;
    price_range_pct: number;
    trend_direction: string | null;
    recommended_strategy: string;
    reasoning: string;
}

interface BotStatus {
    active_positions_count: number;
    total_pnl: number;
    running_strategies: string[];
}

interface DashboardProps {
    ticker: string;
}

export default function Dashboard({ ticker }: DashboardProps) {
    const [regime, setRegime] = useState<RegimeData | null>(null);
    const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
    const [portfolioDelta, setPortfolioDelta] = useState(0);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchData();
        const interval = setInterval(fetchData, 5000);
        return () => clearInterval(interval);
    }, [ticker]);

    const fetchData = async () => {
        try {
            const [regimeRes, botRes] = await Promise.all([
                axios.get('/api/autopilot/regime'),
                axios.get('/api/analytics/bot/status')
            ]);

            setRegime(regimeRes.data);
            setBotStatus(botRes.data);

            // Mock portfolio delta (would come from real portfolio service)
            setPortfolioDelta(Math.sin(Date.now() / 10000) * 200);

            setLoading(false);
        } catch (err) {
            console.error('Dashboard fetch error:', err);
            setLoading(false);
        }
    };

    const getRegimeColor = (regimeType: string) => {
        switch (regimeType?.toLowerCase()) {
            case 'trending': return 'from-green-500 to-emerald-600';
            case 'choppy': return 'from-yellow-500 to-orange-500';
            case 'crash': return 'from-red-600 to-red-800';
            default: return 'from-gray-500 to-gray-600';
        }
    };

    const getRegimeIcon = (regimeType: string) => {
        switch (regimeType?.toLowerCase()) {
            case 'trending': return '📈';
            case 'choppy': return '📊';
            case 'crash': return '🔥';
            default: return '❓';
        }
    };

    const getDeltaColor = () => {
        if (portfolioDelta > 300) return 'text-red-400';
        if (portfolioDelta < -300) return 'text-red-400';
        if (Math.abs(portfolioDelta) < 100) return 'text-green-400';
        return 'text-yellow-400';
    };

    const getDeltaNeedle = () => {
        // Normalize delta to -100 to 100 for gauge
        const normalized = Math.max(-100, Math.min(100, portfolioDelta / 5));
        const rotation = normalized * 0.9; // -90 to 90 degrees
        return rotation;
    };

    if (loading) {
        return (
            <div className="bg-[#0f1117] rounded-xl p-6 animate-pulse">
                <div className="h-8 bg-gray-700 rounded w-1/3 mb-4"></div>
                <div className="grid grid-cols-3 gap-4">
                    <div className="h-32 bg-gray-700 rounded"></div>
                    <div className="h-32 bg-gray-700 rounded"></div>
                    <div className="h-32 bg-gray-700 rounded"></div>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-[#0f1117] rounded-xl p-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                🎛️ Glass Cockpit
                <span className="text-xs text-gray-500">Live Market Intelligence</span>
            </h3>

            <div className="grid grid-cols-3 gap-4">
                {/* Market Regime Card */}
                <div className={`relative overflow-hidden rounded-xl p-4 bg-gradient-to-br ${getRegimeColor(regime?.regime || '')}`}>
                    <div className="absolute top-0 right-0 text-6xl opacity-20 -mt-2 -mr-2">
                        {getRegimeIcon(regime?.regime || '')}
                    </div>
                    <div className="relative z-10">
                        <div className="text-xs uppercase tracking-wider opacity-80">Market Regime</div>
                        <div className="text-2xl font-bold mt-1">
                            {regime?.regime?.toUpperCase() || 'UNKNOWN'}
                        </div>
                        <div className="text-sm mt-2 opacity-90">
                            {regime?.recommended_strategy || 'Calculating...'}
                        </div>
                        <div className="mt-3 flex gap-4 text-xs opacity-80">
                            <span>ADX: {regime?.adx?.toFixed(1)}</span>
                            <span>VIX: {regime?.vix?.toFixed(1)}</span>
                            <span>RSI: {regime?.rsi?.toFixed(1)}</span>
                        </div>
                    </div>
                </div>

                {/* Portfolio Delta Gauge */}
                <div className="bg-[#1a1f2e] rounded-xl p-4">
                    <div className="text-xs uppercase tracking-wider text-gray-400">Portfolio Delta</div>

                    {/* SVG Gauge */}
                    <div className="flex justify-center mt-2">
                        <svg width="120" height="80" viewBox="0 0 120 80">
                            {/* Background arc */}
                            <path
                                d="M 10 70 A 50 50 0 0 1 110 70"
                                fill="none"
                                stroke="#374151"
                                strokeWidth="8"
                                strokeLinecap="round"
                            />

                            {/* Danger zones */}
                            <path
                                d="M 10 70 A 50 50 0 0 1 30 35"
                                fill="none"
                                stroke="#ef4444"
                                strokeWidth="4"
                                strokeLinecap="round"
                                opacity="0.5"
                            />
                            <path
                                d="M 90 35 A 50 50 0 0 1 110 70"
                                fill="none"
                                stroke="#ef4444"
                                strokeWidth="4"
                                strokeLinecap="round"
                                opacity="0.5"
                            />

                            {/* Safe zone */}
                            <path
                                d="M 45 25 A 50 50 0 0 1 75 25"
                                fill="none"
                                stroke="#22c55e"
                                strokeWidth="4"
                                strokeLinecap="round"
                                opacity="0.5"
                            />

                            {/* Needle */}
                            <line
                                x1="60"
                                y1="70"
                                x2="60"
                                y2="30"
                                stroke="#fff"
                                strokeWidth="2"
                                strokeLinecap="round"
                                transform={`rotate(${getDeltaNeedle()}, 60, 70)`}
                            />

                            {/* Center dot */}
                            <circle cx="60" cy="70" r="5" fill="#fff" />
                        </svg>
                    </div>

                    <div className={`text-center text-2xl font-bold ${getDeltaColor()}`}>
                        {portfolioDelta > 0 ? '+' : ''}{portfolioDelta.toFixed(0)}
                    </div>
                    <div className="text-center text-xs text-gray-500 mt-1">
                        {Math.abs(portfolioDelta) < 100 ? '✅ Neutral' :
                            Math.abs(portfolioDelta) < 300 ? '⚠️ Moderate' : '🔴 High Exposure'}
                    </div>
                </div>

                {/* P&L Summary */}
                <div className="bg-[#1a1f2e] rounded-xl p-4">
                    <div className="text-xs uppercase tracking-wider text-gray-400">Session P&L</div>
                    <div className={`text-3xl font-bold mt-2 ${(botStatus?.total_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'
                        }`}>
                        ${(botStatus?.total_pnl || 0).toFixed(2)}
                    </div>

                    <div className="mt-3 space-y-1">
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-400">Active Positions</span>
                            <span className="text-white">{botStatus?.active_positions_count || 0}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                            <span className="text-gray-400">Strategies</span>
                            <span className="text-cyan-400">
                                {botStatus?.running_strategies?.length || 0}
                            </span>
                        </div>
                    </div>

                    {/* Mini strategy list */}
                    {botStatus?.running_strategies && botStatus.running_strategies.length > 0 && (
                        <div className="mt-3 pt-3 border-t border-white/10">
                            <div className="text-xs text-gray-500">Active:</div>
                            <div className="flex flex-wrap gap-1 mt-1">
                                {botStatus.running_strategies.map((s, i) => (
                                    <span key={i} className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">
                                        {s}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Regime Reasoning Footer */}
            {regime?.reasoning && (
                <div className="mt-4 p-3 bg-[#1a1f2e] rounded-lg text-sm text-gray-400">
                    <span className="text-gray-500">📝 Analysis: </span>
                    {regime.reasoning}
                </div>
            )}
        </div>
    );
}
