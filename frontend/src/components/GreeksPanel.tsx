interface GreeksPanelProps {
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
    netDelta?: number;
}

export default function GreeksPanel({ delta, gamma, theta, vega, netDelta }: GreeksPanelProps) {
    const getDeltaWarning = () => {
        if (netDelta === undefined) return null;
        const absDelta = Math.abs(netDelta);

        if (absDelta > 100) {
            return { level: 'danger', message: `⚠️ HIGH EXPOSURE: Net Delta ${netDelta > 0 ? '+' : ''}${netDelta.toFixed(0)}` };
        } else if (absDelta > 50) {
            return { level: 'warning', message: `⚡ Moderate exposure: Net Delta ${netDelta > 0 ? '+' : ''}${netDelta.toFixed(0)}` };
        }
        return { level: 'ok', message: `✅ Delta-neutral: ${netDelta.toFixed(2)}` };
    };

    const warning = getDeltaWarning();

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                📐 Position Greeks
            </h3>

            {/* Warning Banner */}
            {warning && (
                <div className={`mb-4 px-4 py-2 rounded-lg text-sm font-medium ${warning.level === 'danger' ? 'bg-red-900/50 text-red-300 border border-red-700' :
                        warning.level === 'warning' ? 'bg-yellow-900/50 text-yellow-300 border border-yellow-700' :
                            'bg-green-900/50 text-green-300 border border-green-700'
                    }`}>
                    {warning.message}
                </div>
            )}

            <div className="grid grid-cols-4 gap-4">
                {/* Delta */}
                <div className="text-center">
                    <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">Delta (Δ)</div>
                    <div className={`text-2xl font-bold ${delta >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {delta >= 0 ? '+' : ''}{delta.toFixed(2)}
                    </div>
                </div>

                {/* Gamma */}
                <div className="text-center">
                    <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">Gamma (Γ)</div>
                    <div className="text-2xl font-bold text-blue-400">
                        {gamma.toFixed(4)}
                    </div>
                </div>

                {/* Theta */}
                <div className="text-center">
                    <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">Theta (Θ)</div>
                    <div className={`text-2xl font-bold ${theta >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${theta.toFixed(2)}/day
                    </div>
                </div>

                {/* Vega */}
                <div className="text-center">
                    <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">Vega (ν)</div>
                    <div className="text-2xl font-bold text-purple-400">
                        ${vega.toFixed(2)}
                    </div>
                </div>
            </div>
        </div>
    );
}
