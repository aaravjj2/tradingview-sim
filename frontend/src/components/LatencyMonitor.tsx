interface LatencyMonitorProps {
    latency: number;  // -1 = error, 0 = no data yet
    refreshCount: number;
    lastUpdate: Date | null;
}

export default function LatencyMonitor({ latency, refreshCount, lastUpdate }: LatencyMonitorProps) {
    const getLatencyColor = () => {
        if (latency < 0) return 'text-red-400';
        if (latency < 100) return 'text-green-400';
        if (latency < 300) return 'text-yellow-400';
        return 'text-orange-400';
    };

    const getLatencyLabel = () => {
        if (latency < 0) return 'Error';
        if (latency < 100) return 'Fast';
        if (latency < 300) return 'Normal';
        return 'Slow';
    };

    return (
        <div className="flex items-center gap-3 text-xs">
            {/* Latency */}
            <div className="flex items-center gap-1">
                <span className="text-gray-500">API:</span>
                <span className={getLatencyColor()}>
                    {latency < 0 ? '❌' : `${latency}ms`}
                </span>
                <span className={`${getLatencyColor()} opacity-50`}>
                    ({getLatencyLabel()})
                </span>
            </div>

            {/* Refresh count */}
            <div className="flex items-center gap-1">
                <span className="text-gray-500">Polls:</span>
                <span className="text-gray-400">{refreshCount}</span>
            </div>

            {/* Last update */}
            {lastUpdate && (
                <div className="flex items-center gap-1">
                    <span className="text-gray-500">Updated:</span>
                    <span className="text-gray-400">
                        {lastUpdate.toLocaleTimeString()}
                    </span>
                </div>
            )}

            {/* Live indicator */}
            <div className="flex items-center gap-1">
                <span className={`inline-block w-2 h-2 rounded-full ${latency < 0 ? 'bg-red-500' :
                        latency > 0 ? 'bg-green-500 animate-pulse' :
                            'bg-gray-500'
                    }`} />
                <span className="text-gray-400">
                    {latency < 0 ? 'Disconnected' : latency > 0 ? 'Live' : 'Connecting...'}
                </span>
            </div>
        </div>
    );
}
