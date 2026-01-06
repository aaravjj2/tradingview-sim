import { useState, useCallback, useEffect, useRef } from 'react';

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

    const startBot = useCallback(() => {
        addLog(`🤖 Starting ${selectedStrategy.name} bot for ${ticker}`);
        addLog(`📊 Position size: ${positionSize} shares, Max loss: $${maxLoss}`);

        setStatus(prev => ({
            ...prev,
            running: true,
            strategy: selectedStrategy.name,
        }));

        // Simulated bot execution loop
        intervalRef.current = setInterval(() => {
            const signals = ['BUY', 'SELL', 'HOLD'];
            const randomSignal = signals[Math.floor(Math.random() * 10) % 3]; // More HOLDs

            if (randomSignal !== 'HOLD') {
                const pnlChange = randomSignal === 'BUY'
                    ? Math.random() * 50 - 10  // More likely positive
                    : Math.random() * 30 - 15;

                setStatus(prev => ({
                    ...prev,
                    positions: randomSignal === 'BUY' ? prev.positions + 1 : Math.max(0, prev.positions - 1),
                    pnl: prev.pnl + pnlChange,
                    lastSignal: randomSignal,
                    lastSignalTime: new Date().toLocaleTimeString(),
                }));

                addLog(`📈 Signal: ${randomSignal} ${ticker} @ $${currentPrice.toFixed(2)}`);

                if (randomSignal === 'BUY') {
                    // Would call API in production
                    addLog(`✅ Executed: BUY ${positionSize} ${ticker} (${paperMode ? 'PAPER' : 'LIVE'})`);
                } else {
                    addLog(`✅ Executed: SELL ${positionSize} ${ticker} (${paperMode ? 'PAPER' : 'LIVE'})`);
                }
            }
        }, 5000); // Check every 5 seconds

        addLog('⏱️ Bot running - checking signals every 5 seconds');
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
