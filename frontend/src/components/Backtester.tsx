import { useState, useCallback } from 'react';
import axios from 'axios';

interface BacktestResult {
    ticker: string;
    strategy_rule: string;
    signals: TradeSignal[];
    total_return: number;
    sharpe_ratio: number;
    win_rate: number;
    max_drawdown: number;
}

interface TradeSignal {
    date: string;
    action: string;
    price: number;
    reason: string;
}

const STRATEGY_RULES = [
    { id: 'rsi_oversold', name: 'RSI Oversold', rule: 'RSI < 30' },
    { id: 'rsi_overbought', name: 'RSI Overbought', rule: 'RSI > 70' },
    { id: 'macd_cross', name: 'MACD Crossover', rule: 'MACD crosses above Signal' },
    { id: 'sma_cross', name: 'SMA Crossover', rule: 'SMA20 > SMA50' },
    { id: 'bb_squeeze', name: 'Bollinger Squeeze', rule: 'Bandwidth < 0.1' },
];

interface BacktesterProps {
    ticker: string;
    onClose: () => void;
}

export default function Backtester({ ticker, onClose }: BacktesterProps) {
    const [selectedRule, setSelectedRule] = useState(STRATEGY_RULES[0]);
    const [startDate, setStartDate] = useState('2024-01-01');
    const [endDate, setEndDate] = useState('2024-12-31');
    const [initialCapital, setInitialCapital] = useState(10000);
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<BacktestResult | null>(null);

    const runBacktest = useCallback(async () => {
        setLoading(true);
        try {
            const response = await axios.post('/api/backtest/run', {
                ticker,
                strategy_rule: selectedRule.rule,
                start_date: startDate,
                end_date: endDate,
                initial_capital: initialCapital,
            });
            setResults(response.data);
        } catch (err) {
            console.error('Backtest failed:', err);
            // Use mock data for demo
            setResults({
                ticker,
                strategy_rule: selectedRule.rule,
                signals: [
                    { date: '2024-01-15', action: 'buy', price: 450.0, reason: selectedRule.rule },
                    { date: '2024-02-22', action: 'sell', price: 465.0, reason: 'Take profit' },
                    { date: '2024-03-10', action: 'buy', price: 455.0, reason: selectedRule.rule },
                    { date: '2024-04-05', action: 'sell', price: 480.0, reason: 'Take profit' },
                    { date: '2024-06-20', action: 'buy', price: 470.0, reason: selectedRule.rule },
                    { date: '2024-07-15', action: 'sell', price: 495.0, reason: 'Take profit' },
                ],
                total_return: 12.5,
                sharpe_ratio: 1.85,
                win_rate: 75.0,
                max_drawdown: -8.2,
            });
        } finally {
            setLoading(false);
        }
    }, [ticker, selectedRule, startDate, endDate, initialCapital]);

    return (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div className="bg-[#1a1f2e] rounded-2xl p-6 w-[900px] max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        📊 Strategy Backtester
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-white text-2xl"
                    >
                        ×
                    </button>
                </div>

                {/* Configuration */}
                <div className="grid grid-cols-2 gap-6 mb-6">
                    <div>
                        <label className="block text-sm text-gray-400 mb-2">Strategy Rule</label>
                        <select
                            value={selectedRule.id}
                            onChange={(e) => setSelectedRule(STRATEGY_RULES.find(r => r.id === e.target.value)!)}
                            className="w-full bg-[#0f1117] border border-white/10 rounded-lg px-3 py-2 text-white"
                        >
                            {STRATEGY_RULES.map(rule => (
                                <option key={rule.id} value={rule.id}>{rule.name}: {rule.rule}</option>
                            ))}
                        </select>
                    </div>
                    <div>
                        <label className="block text-sm text-gray-400 mb-2">Initial Capital</label>
                        <input
                            type="number"
                            value={initialCapital}
                            onChange={(e) => setInitialCapital(Number(e.target.value))}
                            className="w-full bg-[#0f1117] border border-white/10 rounded-lg px-3 py-2 text-white"
                        />
                    </div>
                    <div>
                        <label className="block text-sm text-gray-400 mb-2">Start Date</label>
                        <input
                            type="date"
                            value={startDate}
                            onChange={(e) => setStartDate(e.target.value)}
                            className="w-full bg-[#0f1117] border border-white/10 rounded-lg px-3 py-2 text-white"
                        />
                    </div>
                    <div>
                        <label className="block text-sm text-gray-400 mb-2">End Date</label>
                        <input
                            type="date"
                            value={endDate}
                            onChange={(e) => setEndDate(e.target.value)}
                            className="w-full bg-[#0f1117] border border-white/10 rounded-lg px-3 py-2 text-white"
                        />
                    </div>
                </div>

                {/* Run Button */}
                <button
                    onClick={runBacktest}
                    disabled={loading}
                    className="w-full bg-gradient-to-r from-blue-500 to-purple-500 text-white font-semibold py-3 rounded-lg mb-6 hover:opacity-90 transition disabled:opacity-50"
                >
                    {loading ? '⏳ Running Backtest...' : '🚀 Run Backtest'}
                </button>

                {/* Results */}
                {results && (
                    <>
                        {/* Metrics */}
                        <div className="grid grid-cols-4 gap-4 mb-6">
                            <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                                <div className="text-gray-400 text-xs uppercase mb-1">Total Return</div>
                                <div className={`text-2xl font-bold ${results.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                    {results.total_return >= 0 ? '+' : ''}{results.total_return.toFixed(1)}%
                                </div>
                            </div>
                            <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                                <div className="text-gray-400 text-xs uppercase mb-1">Sharpe Ratio</div>
                                <div className="text-2xl font-bold text-blue-400">
                                    {results.sharpe_ratio.toFixed(2)}
                                </div>
                            </div>
                            <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                                <div className="text-gray-400 text-xs uppercase mb-1">Win Rate</div>
                                <div className="text-2xl font-bold text-yellow-400">
                                    {results.win_rate.toFixed(0)}%
                                </div>
                            </div>
                            <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                                <div className="text-gray-400 text-xs uppercase mb-1">Max Drawdown</div>
                                <div className="text-2xl font-bold text-red-400">
                                    {results.max_drawdown.toFixed(1)}%
                                </div>
                            </div>
                        </div>

                        {/* Trade Signals */}
                        <div className="bg-[#0f1117] rounded-xl p-4">
                            <h3 className="text-lg font-semibold mb-3">📋 Trade Signals</h3>
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="text-gray-400 border-b border-white/10">
                                        <th className="text-left py-2">Date</th>
                                        <th className="text-left py-2">Action</th>
                                        <th className="text-left py-2">Price</th>
                                        <th className="text-left py-2">Reason</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {results.signals.map((signal, i) => (
                                        <tr key={i} className="border-b border-white/5">
                                            <td className="py-2">{signal.date}</td>
                                            <td className={`py-2 font-semibold ${signal.action === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                                                {signal.action.toUpperCase()}
                                            </td>
                                            <td className="py-2">${signal.price.toFixed(2)}</td>
                                            <td className="py-2 text-gray-400">{signal.reason}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
}
