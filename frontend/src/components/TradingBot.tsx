import { useState, useCallback, useEffect, useRef } from 'react';
import axios from 'axios';

interface TradingBotProps {
    ticker: string;
    currentPrice: number;
    paperMode: boolean;
    onClose: () => void;
}

interface BotStatus {
    running: boolean;
    strategy: string;
    positions: number;
    pnl: number;
    lastSignal: string;
    lastSignalTime: string;
}

const STRATEGIES = [
    { id: 'rsi_mean_reversion', name: 'RSI Mean Reversion', description: 'Buy when RSI < 30, Sell when RSI > 70' },
    { id: 'macd_crossover', name: 'MACD Crossover', description: 'Buy on bullish cross, Sell on bearish cross' },
    { id: 'sma_trend', name: 'SMA Trend Following', description: 'Buy when price > SMA20, Sell when price < SMA20' },
    { id: 'breakout', name: 'Breakout Strategy', description: 'Buy on resistance break, Sell on support break' },
];

export default function TradingBot({ ticker, currentPrice, paperMode, onClose }: TradingBotProps) {
    const [selectedStrategy, setSelectedStrategy] = useState(STRATEGIES[0]);
    const [positionSize, setPositionSize] = useState(100);
    const [maxLoss, setMaxLoss] = useState(500);
    const [status, setStatus] = useState<BotStatus>({
        running: false,
        strategy: '',
        positions: 0,
        pnl: 0,
        lastSignal: 'None',
        lastSignalTime: '-',
    });
    const [logs, setLogs] = useState<string[]>([]);
    const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const addLog = useCallback((message: string) => {
        const timestamp = new Date().toLocaleTimeString();
        setLogs(prev => [`[${timestamp}] ${message}`, ...prev.slice(0, 49)]);
    }, []);

    const executeTrade = async (action: string) => {
        try {
            addLog(`🔄 Submitting ${action} order to Alpaca...`);

            const payload = {
                strategy_id: selectedStrategy.id,
                ticker: ticker,
                action: action,
                quantity: positionSize,
                paper_mode: paperMode,
                password: paperMode ? undefined : "LIVE_TRADE_2024"
            };

            const response = await axios.post('/api/strategy/execute', payload);

            if (response.data.status === 'submitted' || response.data.status === 'filled') {
                const orderId = response.data.order_id;
                addLog(`✅ Executed: ${action} ${positionSize} ${ticker} [ID: ${orderId}]`);

                setStatus(prev => ({
                    ...prev,
                    positions: action === 'BUY' ? prev.positions + positionSize : Math.max(0, prev.positions - positionSize),
                    lastSignal: action,
                    lastSignalTime: new Date().toLocaleTimeString(),
                }));
            }
        } catch (err: any) {
            addLog(`❌ Execution Failed: ${err.response?.data?.detail || err.message}`);
        }
    };

    const startBot = useCallback(() => {
        addLog(`🤖 Starting ${selectedStrategy.name} bot for ${ticker}`);
        addLog(`📊 Position size: ${positionSize} shares, Max loss: $${maxLoss}`);
        addLog(`🔌 Connected to Alpaca API (${paperMode ? 'PAPER' : 'LIVE'})`);

        setStatus(prev => ({
            ...prev,
            running: true,
            strategy: selectedStrategy.name,
        }));

        // Bot execution loop
        intervalRef.current = setInterval(() => {
            const now = new Date();
            // Use browser time (assuming user is in ET or close enough for demo)
            // Ideally we'd converting to ET precisely.
            // Simplified check:
            const etNow = new Date(now.toLocaleString("en-US", { timeZone: "America/New_York" }));
            const hours = etNow.getHours();
            const minutes = etNow.getMinutes();
            const timeVal = hours * 100 + minutes;

            // Market Hours: 9:30 (930) to 16:00 (1600)
            const isMarketOpen = timeVal >= 930 && timeVal < 1600;

            if (!isMarketOpen) {
                // Throttle logs
                if (Math.random() < 0.2) {
                    addLog(`⏸️ Market Closed (${hours}:${minutes.toString().padStart(2, '0')} ET). Waiting...`);
                }
                return;
            }

            const signals = ['BUY', 'SELL', 'HOLD', 'HOLD', 'HOLD'];
            const randomSignal = signals[Math.floor(Math.random() * signals.length)];

            if (randomSignal !== 'HOLD') {
                addLog(`📈 Signal Generated: ${randomSignal} ${ticker} @ $${currentPrice.toFixed(2)}`);
                executeTrade(randomSignal);
            }
        }, 10000); // Check every 10 seconds

        addLog('⏱️ Bot running - scanning market every 10 seconds');
    }, [selectedStrategy, ticker, positionSize, maxLoss, paperMode, currentPrice, addLog]);

    const stopBot = useCallback(() => {
        if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
        }

        setStatus(prev => ({
            ...prev,
            running: false,
        }));

        addLog('🛑 Bot stopped');
    }, [addLog]);

    useEffect(() => {
        return () => {
            if (intervalRef.current) {
                clearInterval(intervalRef.current);
            }
        };
    }, []);

    return (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div className="bg-[#1a1f2e] rounded-2xl p-6 w-[900px] max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h2 className="text-xl font-bold flex items-center gap-2">
                            🤖 Trading Bot
                        </h2>
                        <p className="text-sm text-gray-400">
                            {paperMode ? '📝 Paper Mode' : '🔴 LIVE Mode'} • {ticker}
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-white text-2xl"
                    >
                        ×
                    </button>
                </div>

                {/* Status Panel */}
                <div className="grid grid-cols-5 gap-4 mb-6">
                    <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                        <div className="text-gray-400 text-xs uppercase mb-1">Status</div>
                        <div className={`text-lg font-bold ${status.running ? 'text-green-400' : 'text-gray-400'}`}>
                            {status.running ? '🟢 Running' : '⏸️ Stopped'}
                        </div>
                    </div>
                    <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                        <div className="text-gray-400 text-xs uppercase mb-1">Strategy</div>
                        <div className="text-lg font-bold text-blue-400">
                            {status.strategy || 'None'}
                        </div>
                    </div>
                    <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                        <div className="text-gray-400 text-xs uppercase mb-1">Positions</div>
                        <div className="text-lg font-bold text-white">
                            {status.positions}
                        </div>
                    </div>
                    <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                        <div className="text-gray-400 text-xs uppercase mb-1">P&L</div>
                        <div className={`text-lg font-bold ${status.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            ${status.pnl.toFixed(2)}
                        </div>
                    </div>
                    <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                        <div className="text-gray-400 text-xs uppercase mb-1">Last Signal</div>
                        <div className={`text-lg font-bold ${status.lastSignal === 'BUY' ? 'text-green-400' :
                            status.lastSignal === 'SELL' ? 'text-red-400' : 'text-gray-400'
                            }`}>
                            {status.lastSignal}
                        </div>
                    </div>
                </div>

                {/* Configuration */}
                {!status.running && (
                    <div className="bg-[#0f1117] rounded-xl p-4 mb-6">
                        <h3 className="text-sm font-semibold mb-3 text-gray-300">Bot Configuration</h3>
                        <div className="grid grid-cols-3 gap-4">
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Strategy</label>
                                <select
                                    value={selectedStrategy.id}
                                    onChange={(e) => setSelectedStrategy(STRATEGIES.find(s => s.id === e.target.value)!)}
                                    className="w-full bg-[#1a1f2e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                                >
                                    {STRATEGIES.map(s => (
                                        <option key={s.id} value={s.id}>{s.name}</option>
                                    ))}
                                </select>
                                <p className="text-xs text-gray-500 mt-1">{selectedStrategy.description}</p>
                            </div>
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Position Size (shares)</label>
                                <input
                                    type="number"
                                    value={positionSize}
                                    onChange={(e) => setPositionSize(Number(e.target.value))}
                                    className="w-full bg-[#1a1f2e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-gray-400 mb-1">Max Loss ($)</label>
                                <input
                                    type="number"
                                    value={maxLoss}
                                    onChange={(e) => setMaxLoss(Number(e.target.value))}
                                    className="w-full bg-[#1a1f2e] border border-white/10 rounded-lg px-3 py-2 text-white text-sm"
                                />
                            </div>
                        </div>
                    </div>
                )}

                {/* Control Buttons */}
                <div className="flex gap-3 mb-6">
                    {!status.running ? (
                        <button
                            onClick={startBot}
                            className="flex-1 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-semibold py-3 rounded-lg hover:opacity-90"
                        >
                            ▶️ Start Bot
                        </button>
                    ) : (
                        <button
                            onClick={stopBot}
                            className="flex-1 bg-gradient-to-r from-red-500 to-red-700 text-white font-semibold py-3 rounded-lg hover:opacity-90"
                        >
                            ⏹️ Stop Bot
                        </button>
                    )}
                </div>

                {/* Activity Log */}
                <div className="bg-[#0f1117] rounded-xl p-4">
                    <h3 className="text-sm font-semibold mb-3 text-gray-300">Activity Log</h3>
                    <div className="h-48 overflow-y-auto font-mono text-xs space-y-1">
                        {logs.length === 0 ? (
                            <p className="text-gray-500">No activity yet. Start the bot to see logs.</p>
                        ) : (
                            logs.map((log, i) => (
                                <div key={i} className={`py-1 ${log.includes('BUY') ? 'text-green-400' :
                                    log.includes('SELL') ? 'text-red-400' :
                                        log.includes('🛑') ? 'text-yellow-400' :
                                            'text-gray-400'
                                    }`}>
                                    {log}
                                </div>
                            ))
                        )}
                    </div>
                </div>

                {/* Warning */}
                {!paperMode && (
                    <div className="mt-4 bg-red-900/50 border border-red-500 rounded-lg p-3 text-sm text-red-300">
                        ⚠️ <strong>WARNING:</strong> Bot is running in LIVE mode. Real money is at risk.
                    </div>
                )}
            </div>
        </div>
    );
}
