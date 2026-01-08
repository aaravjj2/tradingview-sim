import { useState, useEffect } from 'react';

interface StrategyCardData {
    id: string;
    name: string;
    ticker: string;
    status: 'running' | 'stopped' | 'paused';
    pnl: number;
    pnlHistory: number[];
    entryPrice: number;
    currentPrice: number;
    stopLoss: number;
    takeProfit: number;
    openedAt: string;
}

const DEMO_STRATEGIES: StrategyCardData[] = [
    {
        id: 'theta1',
        name: 'Theta Eater',
        ticker: 'SPY',
        status: 'running',
        pnl: 245.50,
        pnlHistory: [0, 50, 80, 120, 180, 220, 245],
        entryPrice: 580,
        currentPrice: 582.50,
        stopLoss: 575,
        takeProfit: 590,
        openedAt: '2024-01-07T10:30:00'
    },
    {
        id: 'gamma1',
        name: 'Gamma Scalper',
        ticker: 'QQQ',
        status: 'running',
        pnl: -62.00,
        pnlHistory: [0, 20, -10, -30, -45, -62],
        entryPrice: 500,
        currentPrice: 498.20,
        stopLoss: 495,
        takeProfit: 510,
        openedAt: '2024-01-07T11:15:00'
    },
    {
        id: 'vega1',
        name: 'Vega Arb',
        ticker: 'AAPL',
        status: 'paused',
        pnl: 88.25,
        pnlHistory: [0, 30, 50, 70, 88],
        entryPrice: 185,
        currentPrice: 186.50,
        stopLoss: 182,
        takeProfit: 192,
        openedAt: '2024-01-07T09:45:00'
    }
];

function MiniSparkline({ data, positive }: { data: number[], positive: boolean }) {
    const height = 30;
    const width = 80;

    if (!data.length) return null;

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const points = data.map((val, i) => {
        const x = (i / (data.length - 1)) * width;
        const y = height - ((val - min) / range) * height;
        return `${x},${y}`;
    }).join(' ');

    return (
        <svg width={width} height={height} className="inline-block">
            <polyline
                points={points}
                fill="none"
                stroke={positive ? '#22c55e' : '#ef4444'}
                strokeWidth="1.5"
            />
        </svg>
    );
}

function HealthBar({ current, stopLoss, takeProfit }: { current: number, stopLoss: number, takeProfit: number }) {
    const totalRange = takeProfit - stopLoss;
    const position = ((current - stopLoss) / totalRange) * 100;
    const clampedPosition = Math.max(0, Math.min(100, position));

    // Color zones
    const dangerZone = 20; // First 20% is danger (red)
    const safeZone = 80;   // Last 20% is profit zone (green)

    return (
        <div className="relative h-2 bg-gray-700 rounded-full overflow-hidden">
            {/* Danger zone (red) */}
            <div
                className="absolute left-0 top-0 h-full bg-red-500/30"
                style={{ width: `${dangerZone}%` }}
            />
            {/* Safe zone (green) */}
            <div
                className="absolute right-0 top-0 h-full bg-green-500/30"
                style={{ width: `${100 - safeZone}%` }}
            />
            {/* Current position indicator */}
            <div
                className={`absolute top-0 h-full w-1 ${clampedPosition < dangerZone ? 'bg-red-500' :
                    clampedPosition > safeZone ? 'bg-green-500' :
                        'bg-yellow-400'
                    }`}
                style={{ left: `${clampedPosition}%`, transform: 'translateX(-50%)' }}
            />
        </div>
    );
}

export default function StrategyCards() {
    const [strategies, setStrategies] = useState<StrategyCardData[]>(DEMO_STRATEGIES);

    useEffect(() => {
        // Simulate real-time P&L updates
        const interval = setInterval(() => {
            setStrategies(prev => prev.map(s => {
                if (s.status !== 'running') return s;

                const change = (Math.random() - 0.5) * 20;
                const newPnl = s.pnl + change;

                return {
                    ...s,
                    pnl: newPnl,
                    pnlHistory: [...s.pnlHistory.slice(-9), newPnl],
                    currentPrice: s.currentPrice + (Math.random() - 0.5) * 0.5
                };
            }));
        }, 3000);

        return () => clearInterval(interval);
    }, []);

    const handleToggle = (id: string) => {
        setStrategies(prev => prev.map(s => {
            if (s.id !== id) return s;
            return {
                ...s,
                status: s.status === 'running' ? 'stopped' : 'running'
            };
        }));
    };

    return (
        <div className="bg-[#0f1117] rounded-xl p-4">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                🎴 Active Strategies
                <span className="text-xs text-gray-500">
                    {strategies.filter(s => s.status === 'running').length} running
                </span>
            </h3>

            <div className="grid grid-cols-3 gap-4">
                {strategies.map(strategy => (
                    <div
                        key={strategy.id}
                        className={`bg-[#1a1f2e] rounded-xl p-4 border ${strategy.status === 'running' ? 'border-green-500/30' :
                            strategy.status === 'paused' ? 'border-yellow-500/30' :
                                'border-gray-600/30'
                            }`}
                    >
                        {/* Header */}
                        <div className="flex justify-between items-start mb-3">
                            <div>
                                <h4 className="font-semibold text-white">{strategy.name}</h4>
                                <span className="text-xs text-gray-400">{strategy.ticker}</span>
                            </div>
                            <button
                                onClick={() => handleToggle(strategy.id)}
                                className={`px-2 py-1 rounded text-xs font-medium ${strategy.status === 'running'
                                    ? 'bg-green-500/20 text-green-400'
                                    : 'bg-gray-500/20 text-gray-400'
                                    }`}
                            >
                                {strategy.status === 'running' ? '● Running' : '○ Stopped'}
                            </button>
                        </div>

                        {/* P&L with Sparkline */}
                        <div className="flex items-center justify-between mb-3">
                            <div className={`text-2xl font-bold ${strategy.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {strategy.pnl >= 0 ? '+' : ''}${strategy.pnl.toFixed(2)}
                            </div>
                            <MiniSparkline data={strategy.pnlHistory} positive={strategy.pnl >= 0} />
                        </div>

                        {/* Health Bar */}
                        <div className="mb-2">
                            <div className="flex justify-between text-xs text-gray-500 mb-1">
                                <span>SL: ${strategy.stopLoss}</span>
                                <span>Price: ${strategy.currentPrice.toFixed(2)}</span>
                                <span>TP: ${strategy.takeProfit}</span>
                            </div>
                            <HealthBar
                                current={strategy.currentPrice}
                                stopLoss={strategy.stopLoss}
                                takeProfit={strategy.takeProfit}
                            />
                        </div>

                        {/* Footer */}
                        <div className="text-xs text-gray-500 mt-2">
                            Opened: {new Date(strategy.openedAt).toLocaleTimeString()}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}
