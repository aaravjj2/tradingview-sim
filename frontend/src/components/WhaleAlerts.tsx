import { useState, useEffect } from 'react';
import axios from 'axios';

interface WhaleAlert {
    timestamp: string;
    ticker: string;
    type: string;
    details: string;
    premium: number;
    contracts: number;
    strike: number;
    expiration: string;
    option_type: string;
    sentiment: string;
    score: number;
    color: string;
}

interface WhaleAlertsProps {
    tickers?: string[];
}

export default function WhaleAlerts({ tickers = ['SPY', 'QQQ', 'AAPL', 'NVDA', 'TSLA'] }: WhaleAlertsProps) {
    const [alerts, setAlerts] = useState<WhaleAlert[]>([]);
    const [loading, setLoading] = useState(false);
    const [filter, setFilter] = useState<'all' | 'bullish' | 'bearish'>('all');

    useEffect(() => {
        const fetchAlerts = async () => {
            setLoading(true);
            try {
                const response = await axios.get('/api/whale/alerts', {
                    params: { tickers: tickers.join(',') }
                });
                setAlerts(response.data);
            } catch (err) {
                // Generate mock data
                setAlerts(generateMockAlerts(tickers));
            } finally {
                setLoading(false);
            }
        };

        fetchAlerts();
        // Auto-refresh every 60 seconds
        const interval = setInterval(fetchAlerts, 60000);
        return () => clearInterval(interval);
    }, [tickers]);

    const filteredAlerts = alerts.filter(alert => {
        if (filter === 'all') return true;
        return alert.sentiment === filter;
    });

    const formatPremium = (premium: number) => {
        if (premium >= 1000000) {
            return `$${(premium / 1000000).toFixed(1)}M`;
        } else if (premium >= 1000) {
            return `$${(premium / 1000).toFixed(0)}K`;
        }
        return `$${premium.toFixed(0)}`;
    };

    const formatTime = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = Math.floor((now.getTime() - date.getTime()) / 60000);

        if (diff < 1) return 'Just now';
        if (diff < 60) return `${diff}m ago`;
        return `${Math.floor(diff / 60)}h ago`;
    };

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                    🐋 Whale Alerts
                    {loading && <span className="animate-pulse text-gray-400 text-xs">Scanning...</span>}
                </h3>

                {/* Filter */}
                <div className="flex bg-[#252b3b] rounded-lg p-1">
                    {(['all', 'bullish', 'bearish'] as const).map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`px-2 py-1 rounded text-xs transition ${filter === f
                                    ? f === 'bullish' ? 'bg-green-600 text-white'
                                        : f === 'bearish' ? 'bg-red-600 text-white'
                                            : 'bg-blue-600 text-white'
                                    : 'text-gray-400 hover:text-white'
                                }`}
                        >
                            {f.charAt(0).toUpperCase() + f.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            {/* Alert List */}
            <div className="space-y-2 max-h-80 overflow-y-auto">
                {filteredAlerts.length === 0 ? (
                    <div className="text-center text-gray-500 py-8">
                        <p className="text-3xl mb-2">🔍</p>
                        <p className="text-sm">No whale activity detected</p>
                    </div>
                ) : (
                    filteredAlerts.map((alert, i) => (
                        <div
                            key={i}
                            className={`p-3 rounded-lg border transition hover:border-opacity-100 ${alert.sentiment === 'bullish'
                                    ? 'bg-green-900/20 border-green-500/30 hover:border-green-500'
                                    : alert.sentiment === 'bearish'
                                        ? 'bg-red-900/20 border-red-500/30 hover:border-red-500'
                                        : 'bg-gray-900/20 border-gray-500/30 hover:border-gray-500'
                                }`}
                        >
                            <div className="flex justify-between items-start mb-2">
                                <div className="flex items-center gap-2">
                                    <span className="font-bold text-lg">{alert.ticker}</span>
                                    <span className={`text-xs px-2 py-0.5 rounded ${alert.option_type === 'CALL' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                                        }`}>
                                        {alert.option_type}
                                    </span>
                                    <span className="text-xs text-gray-400">${alert.strike.toFixed(0)}</span>
                                </div>
                                <span className="text-xs text-gray-500">{formatTime(alert.timestamp)}</span>
                            </div>

                            <div className="flex justify-between items-center">
                                <div>
                                    <p className="text-sm text-gray-300">{alert.details}</p>
                                    <p className="text-xs text-gray-500 mt-1">Exp: {alert.expiration}</p>
                                </div>
                                <div className="text-right">
                                    <p className={`text-lg font-mono ${alert.sentiment === 'bullish' ? 'text-green-400' : 'text-red-400'
                                        }`}>
                                        {formatPremium(alert.premium)}
                                    </p>
                                    <p className="text-xs text-gray-500">{alert.contracts.toLocaleString()} contracts</p>
                                </div>
                            </div>

                            {/* Alert Type Badge */}
                            <div className="mt-2 flex items-center gap-2">
                                <span className={`text-xs px-2 py-0.5 rounded-full ${alert.type === 'large_block' ? 'bg-purple-500/20 text-purple-400' :
                                        alert.type === 'sweep' ? 'bg-yellow-500/20 text-yellow-400' :
                                            'bg-blue-500/20 text-blue-400'
                                    }`}>
                                    {alert.type.replace('_', ' ').toUpperCase()}
                                </span>
                                <div className="flex-1 bg-gray-700/50 rounded-full h-1">
                                    <div
                                        className={`h-full rounded-full ${alert.sentiment === 'bullish' ? 'bg-green-500' : 'bg-red-500'
                                            }`}
                                        style={{ width: `${Math.min(alert.score, 100)}%` }}
                                    />
                                </div>
                                <span className="text-xs text-gray-400">{alert.score.toFixed(0)}</span>
                            </div>
                        </div>
                    ))
                )}
            </div>

            {/* Summary */}
            {alerts.length > 0 && (
                <div className="mt-4 pt-4 border-t border-white/10 grid grid-cols-3 gap-2 text-xs text-center">
                    <div>
                        <p className="text-gray-400">Total Alerts</p>
                        <p className="text-lg font-mono">{alerts.length}</p>
                    </div>
                    <div>
                        <p className="text-gray-400">Bullish</p>
                        <p className="text-lg font-mono text-green-400">
                            {alerts.filter(a => a.sentiment === 'bullish').length}
                        </p>
                    </div>
                    <div>
                        <p className="text-gray-400">Bearish</p>
                        <p className="text-lg font-mono text-red-400">
                            {alerts.filter(a => a.sentiment === 'bearish').length}
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}

// Mock data generator
function generateMockAlerts(tickers: string[]): WhaleAlert[] {
    const alerts: WhaleAlert[] = [];

    tickers.forEach(ticker => {
        // 50% chance of having an alert
        if (Math.random() > 0.5) {
            const isCall = Math.random() > 0.5;
            const isBullish = isCall ? Math.random() > 0.3 : Math.random() < 0.3;

            alerts.push({
                timestamp: new Date(Date.now() - Math.random() * 3600000).toISOString(),
                ticker,
                type: ['large_block', 'unusual_volume', 'sweep'][Math.floor(Math.random() * 3)],
                details: `${(1000 + Math.random() * 5000).toFixed(0)} contracts (${(3 + Math.random() * 7).toFixed(1)}x avg)`,
                premium: 50000 + Math.random() * 250000,
                contracts: Math.floor(1000 + Math.random() * 5000),
                strike: Math.round((400 + Math.random() * 200) / 5) * 5,
                expiration: new Date(Date.now() + (7 + Math.random() * 30) * 86400000).toISOString().split('T')[0],
                option_type: isCall ? 'CALL' : 'PUT',
                sentiment: isBullish ? 'bullish' : 'bearish',
                score: 50 + Math.random() * 50,
                color: isBullish ? 'green' : 'red'
            });
        }
    });

    return alerts.sort((a, b) => b.score - a.score);
}
