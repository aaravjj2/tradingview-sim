import { useMemo } from 'react';

interface OptionLeg {
    option_type: string;
    position: string;
    strike: number;
    premium: number;
    quantity: number;
}

interface SupergraphProps {
    currentPrice: number;
    legs: OptionLeg[];
    hoveredPrice?: number;
    priceRange?: number; // percentage from current price
}

export default function Supergraph({
    currentPrice,
    legs,
    hoveredPrice,
    priceRange = 0.2
}: SupergraphProps) {

    // Generate price points
    const pricePoints = useMemo(() => {
        const prices: number[] = [];
        const min = currentPrice * (1 - priceRange);
        const max = currentPrice * (1 + priceRange);
        const step = (max - min) / 100;

        for (let p = min; p <= max; p += step) {
            prices.push(p);
        }
        return prices;
    }, [currentPrice, priceRange]);

    // Calculate payoff at each price point
    const payoffData = useMemo(() => {
        return pricePoints.map(price => {
            let payoff = 0;

            legs.forEach(leg => {
                const sign = leg.position === 'long' ? 1 : -1;
                const qty = leg.quantity;

                if (leg.option_type === 'call') {
                    const intrinsic = Math.max(0, price - leg.strike);
                    payoff += sign * qty * 100 * (intrinsic - leg.premium);
                } else if (leg.option_type === 'put') {
                    const intrinsic = Math.max(0, leg.strike - price);
                    payoff += sign * qty * 100 * (intrinsic - leg.premium);
                } else if (leg.option_type === 'stock') {
                    payoff += sign * qty * (price - leg.strike);
                }
            });

            return { price, payoff };
        });
    }, [pricePoints, legs]);

    // Find breakevens
    const breakevens = useMemo(() => {
        const bes: number[] = [];
        for (let i = 1; i < payoffData.length; i++) {
            if ((payoffData[i - 1].payoff < 0 && payoffData[i].payoff >= 0) ||
                (payoffData[i - 1].payoff >= 0 && payoffData[i].payoff < 0)) {
                bes.push(payoffData[i].price);
            }
        }
        return bes;
    }, [payoffData]);

    // Calculate max/min for scaling
    const maxPayoff = Math.max(...payoffData.map(d => d.payoff));
    const minPayoff = Math.min(...payoffData.map(d => d.payoff));
    const range = maxPayoff - minPayoff || 1;

    // SVG dimensions
    const width = 500;
    const height = 300;
    const padding = 40;

    // Scale functions
    const xScale = (price: number) => {
        const min = pricePoints[0];
        const max = pricePoints[pricePoints.length - 1];
        return padding + ((price - min) / (max - min)) * (width - 2 * padding);
    };

    const yScale = (payoff: number) => {
        return height - padding - ((payoff - minPayoff) / range) * (height - 2 * padding);
    };

    // Generate path
    const pathD = payoffData.map((d, i) => {
        const x = xScale(d.price);
        const y = yScale(d.payoff);
        return i === 0 ? `M ${x} ${y}` : `L ${x} ${y}`;
    }).join(' ');

    // Zero line y position
    const zeroY = yScale(0);

    // Hovered price position
    const hoveredX = hoveredPrice ? xScale(hoveredPrice) : null;
    const hoveredPayoff = hoveredPrice
        ? payoffData.find(d => Math.abs(d.price - hoveredPrice) < 1)?.payoff ?? 0
        : null;

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4 h-full">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    📈 P/L Supergraph
                </h3>
                <div className="flex gap-4 text-sm">
                    {breakevens.map((be, i) => (
                        <span key={i} className="text-orange-400">
                            BE: ${be.toFixed(2)}
                        </span>
                    ))}
                </div>
            </div>

            <svg width="100%" viewBox={`0 0 ${width} ${height}`} className="overflow-visible">
                {/* Grid lines */}
                <line x1={padding} y1={zeroY} x2={width - padding} y2={zeroY}
                    stroke="rgba(255,255,255,0.2)" strokeWidth="1" />

                {/* Current price line */}
                <line x1={xScale(currentPrice)} y1={padding} x2={xScale(currentPrice)} y2={height - padding}
                    stroke="rgba(33, 150, 243, 0.5)" strokeWidth="1" strokeDasharray="4" />

                {/* Payoff curve */}
                <path d={pathD} fill="none" stroke="#FFD700" strokeWidth="3" />

                {/* Fill area */}
                <path
                    d={`${pathD} L ${xScale(pricePoints[pricePoints.length - 1])} ${zeroY} L ${xScale(pricePoints[0])} ${zeroY} Z`}
                    fill="url(#payoffGradient)"
                    opacity="0.3"
                />

                {/* Gradient definition */}
                <defs>
                    <linearGradient id="payoffGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" stopColor="#00C853" />
                        <stop offset="50%" stopColor="transparent" />
                        <stop offset="100%" stopColor="#FF1744" />
                    </linearGradient>
                </defs>

                {/* Breakeven markers */}
                {breakevens.map((be, i) => (
                    <g key={i}>
                        <circle cx={xScale(be)} cy={zeroY} r="6" fill="#FF9800" />
                        <text x={xScale(be)} y={zeroY - 12} textAnchor="middle" fill="#FF9800" fontSize="10">
                            ${be.toFixed(0)}
                        </text>
                    </g>
                ))}

                {/* Hovered line */}
                {hoveredX && hoveredPayoff !== null && (
                    <g>
                        <line x1={hoveredX} y1={padding} x2={hoveredX} y2={height - padding}
                            stroke="rgba(156, 39, 176, 0.7)" strokeWidth="2" strokeDasharray="4" />
                        <circle cx={hoveredX} cy={yScale(hoveredPayoff)} r="6" fill="#9C27B0" />
                        <text x={hoveredX + 10} y={yScale(hoveredPayoff)} fill="#fff" fontSize="12">
                            ${hoveredPayoff.toFixed(2)}
                        </text>
                    </g>
                )}

                {/* Axes labels */}
                <text x={width / 2} y={height - 5} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="11">
                    Stock Price ($)
                </text>
                <text x={12} y={height / 2} textAnchor="middle" fill="rgba(255,255,255,0.5)" fontSize="11"
                    transform={`rotate(-90, 12, ${height / 2})`}>
                    P/L ($)
                </text>
            </svg>
        </div>
    );
}
