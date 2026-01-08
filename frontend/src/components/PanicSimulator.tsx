import { useState, useMemo } from 'react';

interface PanicSimulatorProps {
    currentPrice: number;
    portfolioValue: number;
}

interface Scenario {
    name: string;
    priceMove: number;
    volSpike: number;
    description: string;
}

const SCENARIOS: Scenario[] = [
    { name: 'Flash Crash', priceMove: -0.10, volSpike: 1.5, description: 'Sudden 10% drop, VIX spikes 150%' },
    { name: 'Black Monday', priceMove: -0.22, volSpike: 2.0, description: '22% crash like 1987' },
    { name: 'COVID Crash', priceMove: -0.35, volSpike: 3.0, description: '35% drop over 2 weeks, VIX to 80' },
    { name: 'Tech Bubble', priceMove: -0.50, volSpike: 2.5, description: '50% drawdown like 2000-2002' },
    { name: 'Mild Correction', priceMove: -0.05, volSpike: 0.5, description: 'Normal 5% pullback' },
    { name: 'Bear Market', priceMove: -0.20, volSpike: 1.0, description: 'Sustained 20% decline' },
];

export default function PanicSimulator({ currentPrice, portfolioValue }: PanicSimulatorProps) {
    const [selectedScenario, setSelectedScenario] = useState<Scenario>(SCENARIOS[0]);
    const [leverage, setLeverage] = useState(1.0);
    const [hedgeRatio, setHedgeRatio] = useState(0);

    const simulationResults = useMemo(() => {
        const priceChange = selectedScenario.priceMove;
        const newPrice = currentPrice * (1 + priceChange);

        // Portfolio impact
        const baseImpact = portfolioValue * priceChange;
        const leveragedImpact = baseImpact * leverage;

        // Hedge protection (simplified - assumes protective puts)
        const hedgeProtection = Math.abs(leveragedImpact) * hedgeRatio * 0.8; // 80% effective
        const netImpact = leveragedImpact + hedgeProtection;

        // Margin call check
        const marginCallLevel = portfolioValue * 0.3; // 30% equity
        const finalEquity = portfolioValue + netImpact;
        const marginCall = finalEquity < marginCallLevel * leverage;

        // Options impact (simplified)
        const callImpact = priceChange < 0 ? -100 : 50; // Lose 100% on puts if crash
        const putImpact = priceChange < 0 ? 200 : -80; // Gain 200% on puts if crash

        // VIX spike impact
        const vixChange = selectedScenario.volSpike;
        const volDragCost = portfolioValue * 0.02 * vixChange; // 2% drag per 100% VIX spike

        // Recovery time estimate (simplified model)
        const recoveryMonths = Math.abs(priceChange) * 24; // ~24 months per 100% drop

        return {
            newPrice,
            priceChange,
            baseImpact,
            leveragedImpact,
            hedgeProtection,
            netImpact,
            marginCall,
            finalEquity,
            callImpact,
            putImpact,
            vixChange,
            volDragCost,
            recoveryMonths,
            drawdownPct: (netImpact / portfolioValue) * 100,
        };
    }, [selectedScenario, currentPrice, portfolioValue, leverage, hedgeRatio]);

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                🚨 Panic Simulator
                <span className="text-xs text-gray-400">Stress Test Your Portfolio</span>
            </h3>

            {/* Scenario Selector */}
            <div className="grid grid-cols-3 gap-2 mb-4">
                {SCENARIOS.map((scenario) => (
                    <button
                        key={scenario.name}
                        onClick={() => setSelectedScenario(scenario)}
                        className={`p-2 rounded-lg text-xs text-left transition ${selectedScenario.name === scenario.name
                            ? 'bg-red-600/30 border border-red-500'
                            : 'bg-[#252b3b] border border-transparent hover:border-white/20'
                            }`}
                    >
                        <p className="font-semibold">{scenario.name}</p>
                        <p className="text-red-400">{(scenario.priceMove * 100).toFixed(0)}%</p>
                    </button>
                ))}
            </div>

            {/* Parameters */}
            <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                    <label className="block text-xs text-gray-400 mb-1">
                        Leverage: {leverage.toFixed(1)}x
                    </label>
                    <input
                        type="range"
                        min="0.5"
                        max="4"
                        step="0.5"
                        value={leverage}
                        onChange={(e) => setLeverage(Number(e.target.value))}
                        className="w-full"
                    />
                </div>
                <div>
                    <label className="block text-xs text-gray-400 mb-1">
                        Hedge Ratio: {(hedgeRatio * 100).toFixed(0)}%
                    </label>
                    <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={hedgeRatio}
                        onChange={(e) => setHedgeRatio(Number(e.target.value))}
                        className="w-full"
                    />
                </div>
            </div>

            {/* Scenario Description */}
            <div className="bg-[#252b3b] rounded-lg p-3 mb-4">
                <p className="text-sm font-semibold">{selectedScenario.name}</p>
                <p className="text-xs text-gray-400">{selectedScenario.description}</p>
            </div>

            {/* Results */}
            <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="bg-[#252b3b] rounded-lg p-3">
                    <p className="text-xs text-gray-400">New Price</p>
                    <p className="text-xl font-mono text-white">
                        ${simulationResults.newPrice.toFixed(2)}
                    </p>
                    <p className="text-xs text-red-400">
                        {(simulationResults.priceChange * 100).toFixed(0)}%
                    </p>
                </div>
                <div className="bg-[#252b3b] rounded-lg p-3">
                    <p className="text-xs text-gray-400">Portfolio Impact</p>
                    <p className={`text-xl font-mono ${simulationResults.netImpact >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${simulationResults.netImpact.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </p>
                    <p className="text-xs text-gray-400">
                        {simulationResults.drawdownPct.toFixed(1)}% drawdown
                    </p>
                </div>
            </div>

            {/* Breakdown */}
            <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Base Impact</span>
                    <span className="text-red-400 font-mono">
                        ${simulationResults.baseImpact.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Leverage Effect ({leverage}x)</span>
                    <span className="text-orange-400 font-mono">
                        ${(simulationResults.leveragedImpact - simulationResults.baseImpact).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Hedge Protection ({(hedgeRatio * 100).toFixed(0)}%)</span>
                    <span className="text-green-400 font-mono">
                        +${simulationResults.hedgeProtection.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                </div>
                <div className="flex justify-between text-sm">
                    <span className="text-gray-400">VIX Spike Cost</span>
                    <span className="text-red-400 font-mono">
                        -${simulationResults.volDragCost.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                    </span>
                </div>
            </div>

            {/* Warnings */}
            {simulationResults.marginCall && (
                <div className="bg-red-900/50 border border-red-500 rounded-lg p-3 mb-4">
                    <div className="flex items-center gap-2">
                        <span className="text-2xl">⚠️</span>
                        <div>
                            <p className="font-semibold text-red-300">MARGIN CALL WARNING</p>
                            <p className="text-xs text-red-200">
                                Your account would fall below maintenance margin requirements
                            </p>
                        </div>
                    </div>
                </div>
            )}

            {/* Recovery Estimate */}
            <div className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 rounded-lg p-3">
                <div className="flex justify-between items-center">
                    <div>
                        <p className="text-xs text-gray-400">Estimated Recovery Time</p>
                        <p className="text-lg font-mono">
                            {simulationResults.recoveryMonths.toFixed(0)} months
                        </p>
                    </div>
                    <div className="text-right">
                        <p className="text-xs text-gray-400">Final Equity</p>
                        <p className={`text-lg font-mono ${simulationResults.finalEquity > 0 ? 'text-white' : 'text-red-400'}`}>
                            ${simulationResults.finalEquity.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                        </p>
                    </div>
                </div>
            </div>

            {/* Recommendations */}
            <div className="mt-4 text-xs text-gray-400">
                <p className="font-semibold mb-1">🛡️ Protection Recommendations:</p>
                <ul className="list-disc list-inside space-y-1">
                    {hedgeRatio < 0.2 && <li>Consider adding portfolio puts (SPY or index protection)</li>}
                    {leverage > 2 && <li>Reduce leverage before high-risk events</li>}
                    {simulationResults.marginCall && <li>Add capital or reduce positions to avoid margin call</li>}
                </ul>
            </div>
        </div>
    );
}
