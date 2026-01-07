import { useState, useEffect } from 'react';

interface KellyCalculatorProps {
    onClose?: () => void;
}

export default function KellyCalculator({ onClose }: KellyCalculatorProps) {
    const [winRate, setWinRate] = useState(55);
    const [rewardRisk, setRewardRisk] = useState(2);
    const [kellyPercent, setKellyPercent] = useState(0);
    const [halfKelly, setHalfKelly] = useState(0);
    const [quarterKelly, setQuarterKelly] = useState(0);

    useEffect(() => {
        // Kelly Formula: f* = (bp - q) / b
        // where b = reward/risk ratio, p = win probability, q = loss probability
        const p = winRate / 100;
        const q = 1 - p;
        const b = rewardRisk;

        const kelly = ((b * p) - q) / b;
        const kellyPct = Math.max(0, kelly * 100);

        setKellyPercent(kellyPct);
        setHalfKelly(kellyPct / 2);
        setQuarterKelly(kellyPct / 4);
    }, [winRate, rewardRisk]);

    return (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div className="bg-[#1a1f2e] rounded-2xl p-6 w-[500px] max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <div>
                        <h2 className="text-xl font-bold flex items-center gap-2">
                            🎯 Kelly Criterion Calculator
                        </h2>
                        <p className="text-sm text-gray-400">
                            Optimal position sizing based on edge
                        </p>
                    </div>
                    {onClose && (
                        <button
                            onClick={onClose}
                            className="text-gray-400 hover:text-white text-2xl"
                        >
                            ×
                        </button>
                    )}
                </div>

                {/* Inputs */}
                <div className="space-y-4 mb-6">
                    <div>
                        <label className="block text-sm text-gray-400 mb-2">
                            Win Rate: {winRate}%
                        </label>
                        <input
                            type="range"
                            min="0"
                            max="100"
                            value={winRate}
                            onChange={(e) => setWinRate(Number(e.target.value))}
                            className="w-full h-2 bg-[#0f1117] rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                            <span>0%</span>
                            <span>50%</span>
                            <span>100%</span>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm text-gray-400 mb-2">
                            Reward/Risk Ratio: {rewardRisk.toFixed(1)}
                        </label>
                        <input
                            type="range"
                            min="0.5"
                            max="5"
                            step="0.1"
                            value={rewardRisk}
                            onChange={(e) => setRewardRisk(Number(e.target.value))}
                            className="w-full h-2 bg-[#0f1117] rounded-lg appearance-none cursor-pointer"
                        />
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                            <span>0.5:1</span>
                            <span>2.5:1</span>
                            <span>5:1</span>
                        </div>
                    </div>
                </div>

                {/* Results */}
                <div className="bg-[#0f1117] rounded-xl p-4">
                    <h3 className="text-sm font-semibold text-gray-300 mb-3">
                        Recommended Position Size
                    </h3>

                    <div className="grid grid-cols-3 gap-4">
                        <div className="text-center">
                            <div className="text-xs text-gray-500 mb-1">Full Kelly</div>
                            <div className={`text-2xl font-bold ${kellyPercent > 25 ? 'text-red-400' : 'text-green-400'
                                }`}>
                                {kellyPercent.toFixed(1)}%
                            </div>
                            <div className="text-xs text-gray-500">⚠️ Aggressive</div>
                        </div>

                        <div className="text-center border-x border-white/10">
                            <div className="text-xs text-gray-500 mb-1">Half Kelly</div>
                            <div className="text-2xl font-bold text-yellow-400">
                                {halfKelly.toFixed(1)}%
                            </div>
                            <div className="text-xs text-gray-500">✓ Recommended</div>
                        </div>

                        <div className="text-center">
                            <div className="text-xs text-gray-500 mb-1">Quarter Kelly</div>
                            <div className="text-2xl font-bold text-blue-400">
                                {quarterKelly.toFixed(1)}%
                            </div>
                            <div className="text-xs text-gray-500">🛡️ Conservative</div>
                        </div>
                    </div>
                </div>

                {/* Explanation */}
                <div className="mt-4 p-3 bg-blue-900/20 border border-blue-500/30 rounded-lg">
                    <div className="text-xs text-blue-300">
                        <strong>Kelly Formula:</strong> f* = (bp - q) / b
                        <br />
                        <span className="text-blue-400">
                            where b = reward/risk, p = win rate, q = loss rate
                        </span>
                    </div>
                </div>

                {/* Warning */}
                {kellyPercent > 25 && (
                    <div className="mt-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
                        <div className="text-xs text-red-300">
                            ⚠️ <strong>Warning:</strong> Kelly suggests over 25% allocation.
                            Consider using Half or Quarter Kelly to reduce volatility.
                        </div>
                    </div>
                )}

                {kellyPercent <= 0 && (
                    <div className="mt-4 p-3 bg-yellow-900/20 border border-yellow-500/30 rounded-lg">
                        <div className="text-xs text-yellow-300">
                            ⚠️ <strong>No Edge:</strong> Your win rate and reward/risk suggest
                            no positive expectancy. Do not take this trade.
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
