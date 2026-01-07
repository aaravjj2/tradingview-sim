import { useState, useEffect, useRef, useCallback } from 'react';

interface OptionLeg {
    option_type: 'call' | 'put';
    position: 'long' | 'short';
    strike: number;
    premium: number;
    quantity: number;
}

interface Props {
    currentPrice: number;
    legs: OptionLeg[];
    onLegsChange?: (legs: OptionLeg[]) => void;
}

export default function DraggableSupergraph({ currentPrice, legs, onLegsChange }: Props) {
    const [activeLeg, setActiveLeg] = useState<number | null>(null);
    const [localLegs, setLocalLegs] = useState<OptionLeg[]>(legs);
    const svgRef = useRef<SVGSVGElement>(null);

    useEffect(() => {
        setLocalLegs(legs);
    }, [legs]);

    // SVG dimensions
    const width = 600;
    const height = 300;
    const padding = 40;

    // Price range (±15% from current)
    const minPrice = currentPrice * 0.85;
    const maxPrice = currentPrice * 1.15;

    const xScale = (price: number) => padding + ((price - minPrice) / (maxPrice - minPrice)) * (width - 2 * padding);
    const priceFromX = (x: number) => minPrice + ((x - padding) / (width - 2 * padding)) * (maxPrice - minPrice);
    const yScale = (val: number) => height / 2 - val;

    // Calculate payoff at a given price
    const calculatePayoff = useCallback((spotPrice: number): number => {
        let payoff = 0;
        for (const leg of localLegs) {
            const mult = leg.position === 'long' ? 1 : -1;
            const premium = leg.premium * leg.quantity * 100;

            if (leg.option_type === 'call') {
                const intrinsic = Math.max(0, spotPrice - leg.strike) * leg.quantity * 100;
                payoff += mult * intrinsic - mult * premium;
            } else {
                const intrinsic = Math.max(0, leg.strike - spotPrice) * leg.quantity * 100;
                payoff += mult * intrinsic - mult * premium;
            }
        }
        return payoff;
    }, [localLegs]);

    // Generate payoff curve points
    const payoffPoints = [];
    for (let p = minPrice; p <= maxPrice; p += (maxPrice - minPrice) / 100) {
        payoffPoints.push({ price: p, payoff: calculatePayoff(p) });
    }

    const maxPayoff = Math.max(...payoffPoints.map(p => Math.abs(p.payoff)), 100);
    const yScalePayoff = (val: number) => height / 2 - (val / maxPayoff) * (height / 2 - padding);

    // Handle drag
    const handleMouseDown = (legIndex: number) => {
        setActiveLeg(legIndex);
    };

    const handleMouseMove = useCallback((e: React.MouseEvent) => {
        if (activeLeg === null || !svgRef.current) return;

        const rect = svgRef.current.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const newStrike = Math.round(priceFromX(x));

        if (newStrike >= minPrice && newStrike <= maxPrice) {
            const newLegs = [...localLegs];
            newLegs[activeLeg] = { ...newLegs[activeLeg], strike: newStrike };
            setLocalLegs(newLegs);
        }
    }, [activeLeg, localLegs, minPrice, maxPrice]);

    const handleMouseUp = () => {
        if (activeLeg !== null && onLegsChange) {
            onLegsChange(localLegs);
        }
        setActiveLeg(null);
    };

    // Generate path
    const pathD = payoffPoints.map((p, i) => {
        const x = xScale(p.price);
        const y = yScalePayoff(p.payoff);
        return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
    }).join(' ');

    // Calculate breakeven points
    const breakevens: number[] = [];
    for (let i = 1; i < payoffPoints.length; i++) {
        const prev = payoffPoints[i - 1];
        const curr = payoffPoints[i];
        if ((prev.payoff < 0 && curr.payoff >= 0) || (prev.payoff >= 0 && curr.payoff < 0)) {
            breakevens.push(curr.price);
        }
    }

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    🎯 Draggable Strategy Builder
                </h3>
                <div className="text-xs text-gray-400">
                    Drag strikes to adjust
                </div>
            </div>

            <svg
                ref={svgRef}
                viewBox={`0 0 ${width} ${height}`}
                className="w-full h-64 cursor-crosshair"
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
            >
                {/* Grid */}
                <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="#4a5568" strokeWidth="1" />
                <line x1={xScale(currentPrice)} y1={padding} x2={xScale(currentPrice)} y2={height - padding} stroke="#3b82f6" strokeWidth="1" strokeDasharray="4" />

                {/* Zero line label */}
                <text x={padding - 5} y={height / 2 + 4} fill="#888" fontSize="10" textAnchor="end">$0</text>

                {/* Payoff curve - gradient fill */}
                <defs>
                    <linearGradient id="payoffGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#22c55e" stopOpacity="0.3" />
                        <stop offset="50%" stopColor="#22c55e" stopOpacity="0" />
                        <stop offset="50%" stopColor="#ef4444" stopOpacity="0" />
                        <stop offset="100%" stopColor="#ef4444" stopOpacity="0.3" />
                    </linearGradient>
                </defs>

                {/* Payoff curve */}
                <path
                    d={pathD}
                    fill="none"
                    stroke="url(#payoffGradient)"
                    strokeWidth="3"
                />
                <path
                    d={pathD}
                    fill="none"
                    stroke="#00ff88"
                    strokeWidth="2"
                />

                {/* Strike markers (draggable) */}
                {localLegs.map((leg, i) => {
                    const x = xScale(leg.strike);
                    const isActive = activeLeg === i;
                    const color = leg.position === 'long' ? '#22c55e' : '#ef4444';

                    return (
                        <g key={i}>
                            {/* Strike line */}
                            <line
                                x1={x}
                                y1={padding}
                                x2={x}
                                y2={height - padding}
                                stroke={color}
                                strokeWidth={isActive ? 3 : 2}
                                strokeDasharray={isActive ? "0" : "4"}
                                opacity={0.6}
                            />

                            {/* Draggable handle */}
                            <circle
                                cx={x}
                                cy={padding + 10}
                                r={isActive ? 12 : 8}
                                fill={color}
                                stroke="white"
                                strokeWidth="2"
                                className="cursor-grab active:cursor-grabbing"
                                onMouseDown={() => handleMouseDown(i)}
                            />

                            {/* Label */}
                            <text
                                x={x}
                                y={padding + 30}
                                fill="white"
                                fontSize="10"
                                textAnchor="middle"
                                fontWeight="bold"
                            >
                                {leg.position === 'long' ? '+' : '-'}{leg.option_type[0].toUpperCase()} ${leg.strike}
                            </text>
                        </g>
                    );
                })}

                {/* Breakeven markers */}
                {breakevens.map((be, i) => (
                    <g key={`be-${i}`}>
                        <circle cx={xScale(be)} cy={height / 2} r={4} fill="#fbbf24" />
                        <text x={xScale(be)} y={height / 2 + 15} fill="#fbbf24" fontSize="9" textAnchor="middle">
                            BE: ${be.toFixed(0)}
                        </text>
                    </g>
                ))}

                {/* Current price marker */}
                <circle cx={xScale(currentPrice)} cy={height - padding + 5} r={5} fill="#3b82f6" />
                <text x={xScale(currentPrice)} y={height - 10} fill="#3b82f6" fontSize="10" textAnchor="middle">
                    ${currentPrice.toFixed(0)}
                </text>

                {/* Axis labels */}
                <text x={padding} y={height - 5} fill="#888" fontSize="9">${minPrice.toFixed(0)}</text>
                <text x={width - padding} y={height - 5} fill="#888" fontSize="9" textAnchor="end">${maxPrice.toFixed(0)}</text>
            </svg>

            {/* Leg Editor */}
            <div className="mt-4 space-y-2">
                <div className="text-xs text-gray-400">Strategy Legs:</div>
                {localLegs.map((leg, i) => (
                    <div key={i} className="flex items-center gap-2 bg-[#0f1117] rounded p-2 text-sm">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${leg.position === 'long' ? 'bg-green-600' : 'bg-red-600'
                            }`}>
                            {leg.position === 'long' ? '+' : '-'}
                        </span>
                        <span className="text-white">{leg.quantity}x</span>
                        <span className={`px-2 py-0.5 rounded text-xs ${leg.option_type === 'call' ? 'bg-blue-900/50 text-blue-300' : 'bg-purple-900/50 text-purple-300'
                            }`}>
                            {leg.option_type.toUpperCase()}
                        </span>
                        <span className="text-white font-mono">${leg.strike}</span>
                        <span className="text-gray-400">@ ${leg.premium.toFixed(2)}</span>
                    </div>
                ))}
            </div>

            {/* Max Profit/Loss */}
            <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
                <div className="bg-green-900/20 rounded p-2 text-center">
                    <span className="text-gray-400">Max Profit:</span>
                    <span className="text-green-400 font-mono ml-1">
                        ${Math.max(...payoffPoints.map(p => p.payoff)).toFixed(0)}
                    </span>
                </div>
                <div className="bg-red-900/20 rounded p-2 text-center">
                    <span className="text-gray-400">Max Loss:</span>
                    <span className="text-red-400 font-mono ml-1">
                        ${Math.min(...payoffPoints.map(p => p.payoff)).toFixed(0)}
                    </span>
                </div>
            </div>
        </div>
    );
}
