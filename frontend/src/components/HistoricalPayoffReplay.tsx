import { useState, useEffect, useRef } from 'react';

interface HistoricalData {
    date: string;
    price: number;
    iv: number;
}

interface OptionLeg {
    option_type: 'call' | 'put';
    position: 'long' | 'short';
    strike: number;
    premium: number;
    quantity: number;
    expiration_days: number;
}

interface Props {
    ticker: string;
    currentPrice: number;
    legs: OptionLeg[];
}

export default function HistoricalPayoffReplay({ ticker, currentPrice, legs }: Props) {
    const [isPlaying, setIsPlaying] = useState(false);
    const [currentDay, setCurrentDay] = useState(0);
    const [speed, setSpeed] = useState(100); // ms per frame
    const [historicalData, setHistoricalData] = useState<HistoricalData[]>([]);
    const animationRef = useRef<number | null>(null);

    // Generate simulated historical data
    useEffect(() => {
        const data: HistoricalData[] = [];
        let price = currentPrice * 0.9; // Start 10% lower
        let iv = 0.25;

        for (let i = 0; i < 60; i++) { // 60 days of history
            // Random walk
            const dailyReturn = (Math.random() - 0.48) * 0.03;
            price *= (1 + dailyReturn);

            // IV mean reverts around 0.25
            iv += (0.25 - iv) * 0.1 + (Math.random() - 0.5) * 0.02;
            iv = Math.max(0.10, Math.min(0.50, iv));

            const date = new Date();
            date.setDate(date.getDate() - (60 - i));

            data.push({
                date: date.toLocaleDateString(),
                price: price,
                iv: iv
            });
        }

        setHistoricalData(data);
    }, [currentPrice]);

    // Animation loop
    useEffect(() => {
        if (isPlaying && currentDay < historicalData.length - 1) {
            animationRef.current = window.setTimeout(() => {
                setCurrentDay(d => d + 1);
            }, speed);
        } else if (currentDay >= historicalData.length - 1) {
            setIsPlaying(false);
        }

        return () => {
            if (animationRef.current) {
                clearTimeout(animationRef.current);
            }
        };
    }, [isPlaying, currentDay, historicalData.length, speed]);

    // Calculate payoff at historical price
    const calculatePayoff = (spotPrice: number, daysElapsed: number): number => {
        let payoff = 0;
        for (const leg of legs) {
            const mult = leg.position === 'long' ? 1 : -1;
            const daysRemaining = Math.max(0, leg.expiration_days - daysElapsed);

            // Simple model: intrinsic + time decay approximation
            let value = 0;
            if (leg.option_type === 'call') {
                const intrinsic = Math.max(0, spotPrice - leg.strike);
                const timeValue = daysRemaining > 0 ? Math.sqrt(daysRemaining / leg.expiration_days) * leg.premium * 0.5 : 0;
                value = intrinsic + timeValue;
            } else {
                const intrinsic = Math.max(0, leg.strike - spotPrice);
                const timeValue = daysRemaining > 0 ? Math.sqrt(daysRemaining / leg.expiration_days) * leg.premium * 0.5 : 0;
                value = intrinsic + timeValue;
            }

            const cost = leg.premium;
            payoff += mult * (value - cost) * leg.quantity * 100;
        }
        return payoff;
    };

    const currentData = historicalData[currentDay] || { price: currentPrice, iv: 0.25, date: 'Today' };
    const currentPayoff = calculatePayoff(currentData.price, currentDay);

    // SVG dimensions
    const width = 500;
    const height = 200;
    const padding = 40;

    // Price chart scaling
    const prices = historicalData.map(d => d.price);
    const minPrice = Math.min(...prices, currentPrice * 0.85);
    const maxPrice = Math.max(...prices, currentPrice * 1.15);
    const priceRange = maxPrice - minPrice || 1;

    const xScale = (i: number) => padding + (i / (historicalData.length - 1)) * (width - 2 * padding);
    const yScale = (price: number) => height - padding - ((price - minPrice) / priceRange) * (height - 2 * padding);

    // Payoff values for each day
    const payoffs = historicalData.map((d, i) => calculatePayoff(d.price, i));
    const maxPayoff = Math.max(Math.abs(Math.min(...payoffs)), Math.abs(Math.max(...payoffs)), 100);

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    ⏱️ Historical Payoff Replay
                </h3>
                <div className="flex items-center gap-2">
                    <button
                        onClick={() => { setCurrentDay(0); setIsPlaying(false); }}
                        className="text-xs px-2 py-1 bg-gray-600 hover:bg-gray-500 rounded text-white"
                    >
                        ⏮️
                    </button>
                    <button
                        onClick={() => setIsPlaying(!isPlaying)}
                        className={`text-xs px-3 py-1 rounded text-white ${isPlaying ? 'bg-red-600 hover:bg-red-500' : 'bg-green-600 hover:bg-green-500'
                            }`}
                    >
                        {isPlaying ? '⏸️ Pause' : '▶️ Play'}
                    </button>
                    <select
                        value={speed}
                        onChange={(e) => setSpeed(parseInt(e.target.value))}
                        className="text-xs bg-[#0f1117] text-white rounded px-2 py-1 border border-white/20"
                    >
                        <option value={50}>Fast</option>
                        <option value={100}>Normal</option>
                        <option value={200}>Slow</option>
                    </select>
                </div>
            </div>

            {/* Current Stats */}
            <div className="grid grid-cols-4 gap-2 mb-4 text-xs">
                <div className="bg-[#0f1117] rounded p-2 text-center">
                    <span className="text-gray-400 block">Day</span>
                    <span className="text-white font-mono">{currentDay + 1} / {historicalData.length}</span>
                </div>
                <div className="bg-[#0f1117] rounded p-2 text-center">
                    <span className="text-gray-400 block">Price</span>
                    <span className="text-white font-mono">${currentData.price.toFixed(2)}</span>
                </div>
                <div className="bg-[#0f1117] rounded p-2 text-center">
                    <span className="text-gray-400 block">IV</span>
                    <span className="text-yellow-400 font-mono">{(currentData.iv * 100).toFixed(1)}%</span>
                </div>
                <div className={`rounded p-2 text-center ${currentPayoff >= 0 ? 'bg-green-900/20' : 'bg-red-900/20'}`}>
                    <span className="text-gray-400 block">P/L</span>
                    <span className={`font-mono ${currentPayoff >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {currentPayoff >= 0 ? '+' : ''}${currentPayoff.toFixed(0)}
                    </span>
                </div>
            </div>

            {/* Chart */}
            <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-48">
                {/* Grid */}
                <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#4a5568" />
                <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="#4a5568" />

                {/* Strike lines */}
                {legs.map((leg, i) => {
                    const y = yScale(leg.strike);
                    if (y >= padding && y <= height - padding) {
                        return (
                            <line
                                key={i}
                                x1={padding}
                                x2={width - padding}
                                y1={y}
                                y2={y}
                                stroke={leg.option_type === 'call' ? '#22c55e' : '#ef4444'}
                                strokeWidth="1"
                                strokeDasharray="4"
                                opacity="0.5"
                            />
                        );
                    }
                    return null;
                })}

                {/* Price path (up to current day) */}
                <path
                    d={historicalData.slice(0, currentDay + 1).map((d, i) => {
                        const x = xScale(i);
                        const y = yScale(d.price);
                        return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
                    }).join(' ')}
                    fill="none"
                    stroke="#3b82f6"
                    strokeWidth="2"
                />

                {/* Future path (faded) */}
                <path
                    d={historicalData.slice(currentDay).map((d, i) => {
                        const x = xScale(currentDay + i);
                        const y = yScale(d.price);
                        return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
                    }).join(' ')}
                    fill="none"
                    stroke="#3b82f6"
                    strokeWidth="1"
                    opacity="0.3"
                    strokeDasharray="4"
                />

                {/* Current position marker */}
                <circle
                    cx={xScale(currentDay)}
                    cy={yScale(currentData.price)}
                    r={6}
                    fill="#3b82f6"
                    stroke="white"
                    strokeWidth="2"
                />

                {/* P/L indicator */}
                <circle
                    cx={xScale(currentDay)}
                    cy={yScale(currentData.price) - 15}
                    r={4}
                    fill={currentPayoff >= 0 ? '#22c55e' : '#ef4444'}
                />
            </svg>

            {/* Timeline slider */}
            <div className="mt-3">
                <input
                    type="range"
                    min={0}
                    max={historicalData.length - 1}
                    value={currentDay}
                    onChange={(e) => { setCurrentDay(parseInt(e.target.value)); setIsPlaying(false); }}
                    className="w-full"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                    <span>{historicalData[0]?.date}</span>
                    <span>{currentData.date}</span>
                    <span>{historicalData[historicalData.length - 1]?.date}</span>
                </div>
            </div>
        </div>
    );
}
