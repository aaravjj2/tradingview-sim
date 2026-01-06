interface GreeksPanelProps {
    delta: number;
    gamma: number;
    theta: number;
    vega: number;
    netDelta?: number;
    heartbeatStatus?: 'live' | 'stale' | 'disconnected';
}

export default function GreeksPanel({
    delta,
    gamma,
    theta,
    vega,
    netDelta,
    heartbeatStatus = 'live'
}: GreeksPanelProps) {
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

    const getHeartbeatIndicator = () => {
        switch (heartbeatStatus) {
            case 'live':
                return <span className="inline-block w-2 h-2 rounded-full bg-green-500 animate-pulse mr-2" title="Live data" />;
            case 'stale':
                return <span className="inline-block w-2 h-2 rounded-full bg-yellow-500 mr-2" title="Stale data" />;
            case 'disconnected':
                return <span className="inline-block w-2 h-2 rounded-full bg-red-500 mr-2" title="Disconnected" />;
        }
    };

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    📐 Position Greeks
                </h3>
                <div className="flex items-center text-sm text-gray-400">
                    {getHeartbeatIndicator()}
                    {heartbeatStatus === 'live' ? 'Live' : heartbeatStatus === 'stale' ? 'Updating...' : 'Disconnected'}
                </div>
            </div>

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
                    <div className="text-xs text-gray-500 mt-1">per $1 move</div>
                </div>

                {/* Gamma */}
                <div className="text-center">
                    <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">Gamma (Γ)</div>
                    <div className="text-2xl font-bold text-blue-400">
                        {gamma.toFixed(4)}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">delta change</div>
                </div>

                {/* Theta */}
                <div className="text-center">
                    <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">Theta (Θ)</div>
                    <div className={`text-2xl font-bold ${theta >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        ${theta.toFixed(2)}/day
                    </div>
                    <div className="text-xs text-gray-500 mt-1">time decay</div>
                </div>

                {/* Vega */}
                <div className="text-center">
                    <div className="text-gray-400 text-xs uppercase tracking-wider mb-1">Vega (ν)</div>
                    <div className="text-2xl font-bold text-purple-400">
                        ${vega.toFixed(2)}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">per 1% IV</div>
                </div>
            </div>
        </div>
    );
}
