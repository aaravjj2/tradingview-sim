import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

interface ActivityEntry {
    timestamp: string;
    source: string;
    message: string;
    level: string;
    ticker?: string;
}

interface AutoPilotStatusData {
    state: string;
    started_at: string | null;
    last_scan: string | null;
    scan_count: number;
    trade_count: number;
    paused_reason: string | null;
    activity_log: ActivityEntry[];
}

const SOURCE_ICONS: Record<string, string> = {
    scanner: '🔍',
    analyst: '🧠',
    executor: '✅',
    risk: '⚠️',
    system: '⚙️'
};

const LEVEL_COLORS: Record<string, string> = {
    info: 'text-gray-400',
    warning: 'text-yellow-400',
    error: 'text-red-400',
    success: 'text-green-400'
};

export default function ActivityFeed() {
    const [status, setStatus] = useState<AutoPilotStatusData | null>(null);
    const [isRunning, setIsRunning] = useState(false);
    const [paperMode, setPaperMode] = useState(true);
    const feedRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 3000);
        return () => clearInterval(interval);
    }, []);

    useEffect(() => {
        // Auto-scroll to bottom when new entries arrive
        if (feedRef.current) {
            feedRef.current.scrollTop = feedRef.current.scrollHeight;
        }
    }, [status?.activity_log]);

    const fetchStatus = async () => {
        try {
            const response = await axios.get('/api/autopilot/status');
            setStatus(response.data);
            setIsRunning(response.data.state === 'running' || response.data.state === 'scanning' ||
                response.data.state === 'analyzing' || response.data.state === 'executing');
        } catch (err) {
            console.error('Failed to fetch AutoPilot status:', err);
        }
    };

    const handleStart = async () => {
        try {
            await axios.post(`/api/autopilot/start?paper_mode=${paperMode}`);
            fetchStatus();
        } catch (err) {
            console.error('Failed to start AutoPilot:', err);
        }
    };

    const handleStop = async () => {
        try {
            await axios.post('/api/autopilot/stop');
            fetchStatus();
        } catch (err) {
            console.error('Failed to stop AutoPilot:', err);
        }
    };

    const handlePause = async () => {
        try {
            await axios.post('/api/autopilot/pause?reason=Manual%20pause');
            fetchStatus();
        } catch (err) {
            console.error('Failed to pause AutoPilot:', err);
        }
    };

    const handleResume = async () => {
        try {
            await axios.post('/api/autopilot/resume');
            fetchStatus();
        } catch (err) {
            console.error('Failed to resume AutoPilot:', err);
        }
    };

    const formatTime = (timestamp: string) => {
        return new Date(timestamp).toLocaleTimeString();
    };

    return (
        <div className="bg-[#0f1117] rounded-xl p-4 h-full flex flex-col">
            {/* Header */}
            <div className="flex justify-between items-center mb-4">
                <div className="flex items-center gap-3">
                    <h3 className="text-lg font-semibold">🤖 AutoPilot</h3>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${status?.state === 'running' ? 'bg-green-500/20 text-green-400' :
                            status?.state === 'paused' ? 'bg-yellow-500/20 text-yellow-400' :
                                status?.state === 'scanning' ? 'bg-blue-500/20 text-blue-400' :
                                    status?.state === 'analyzing' ? 'bg-purple-500/20 text-purple-400' :
                                        'bg-gray-500/20 text-gray-400'
                        }`}>
                        {status?.state?.toUpperCase() || 'STOPPED'}
                    </span>
                </div>

                <div className="flex items-center gap-2">
                    {/* Paper Mode Toggle */}
                    <label className="flex items-center gap-2 text-xs text-gray-400">
                        <input
                            type="checkbox"
                            checked={paperMode}
                            onChange={(e) => setPaperMode(e.target.checked)}
                            disabled={isRunning}
                            className="rounded"
                        />
                        Paper Mode
                    </label>

                    {/* Control Buttons */}
                    {!isRunning ? (
                        <button
                            onClick={handleStart}
                            className="bg-green-500 hover:bg-green-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium"
                        >
                            ▶️ Start
                        </button>
                    ) : (
                        <>
                            {status?.state === 'paused' ? (
                                <button
                                    onClick={handleResume}
                                    className="bg-yellow-500 hover:bg-yellow-600 text-black px-4 py-1.5 rounded-lg text-sm font-medium"
                                >
                                    ⏯️ Resume
                                </button>
                            ) : (
                                <button
                                    onClick={handlePause}
                                    className="bg-yellow-500 hover:bg-yellow-600 text-black px-4 py-1.5 rounded-lg text-sm font-medium"
                                >
                                    ⏸️ Pause
                                </button>
                            )}
                            <button
                                onClick={handleStop}
                                className="bg-red-500 hover:bg-red-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium"
                            >
                                ⏹️ Stop
                            </button>
                        </>
                    )}
                </div>
            </div>

            {/* Stats Bar */}
            <div className="grid grid-cols-4 gap-2 mb-4 text-xs">
                <div className="bg-[#1a1f2e] rounded-lg p-2 text-center">
                    <div className="text-gray-400">Scans</div>
                    <div className="text-lg font-bold text-blue-400">{status?.scan_count || 0}</div>
                </div>
                <div className="bg-[#1a1f2e] rounded-lg p-2 text-center">
                    <div className="text-gray-400">Trades</div>
                    <div className="text-lg font-bold text-green-400">{status?.trade_count || 0}</div>
                </div>
                <div className="bg-[#1a1f2e] rounded-lg p-2 text-center">
                    <div className="text-gray-400">Last Scan</div>
                    <div className="text-sm font-medium text-gray-300">
                        {status?.last_scan ? formatTime(status.last_scan) : '-'}
                    </div>
                </div>
                <div className="bg-[#1a1f2e] rounded-lg p-2 text-center">
                    <div className="text-gray-400">Mode</div>
                    <div className={`text-sm font-medium ${paperMode ? 'text-cyan-400' : 'text-red-400'}`}>
                        {paperMode ? '📝 Paper' : '🔴 Live'}
                    </div>
                </div>
            </div>

            {/* Paused Warning */}
            {status?.state === 'paused' && status?.paused_reason && (
                <div className="bg-yellow-500/20 border border-yellow-500/50 rounded-lg p-3 mb-4 text-sm">
                    <span className="text-yellow-400 font-medium">⚠️ CIRCUIT BREAKER:</span>{' '}
                    <span className="text-yellow-200">{status.paused_reason}</span>
                </div>
            )}

            {/* Activity Feed */}
            <div className="flex-1 overflow-hidden">
                <h4 className="text-sm font-medium text-gray-400 mb-2">Activity Feed</h4>
                <div
                    ref={feedRef}
                    className="h-[300px] overflow-y-auto space-y-1 font-mono text-xs"
                >
                    {!status?.activity_log?.length ? (
                        <p className="text-gray-500 italic">No activity yet. Start AutoPilot to see the feed.</p>
                    ) : (
                        status.activity_log.map((entry, i) => (
                            <div
                                key={i}
                                className={`py-1.5 px-2 rounded ${entry.level === 'success' ? 'bg-green-500/10' :
                                        entry.level === 'warning' ? 'bg-yellow-500/10' :
                                            entry.level === 'error' ? 'bg-red-500/10' :
                                                'bg-white/5'
                                    }`}
                            >
                                <span className="text-gray-500">{formatTime(entry.timestamp)}</span>
                                {' '}
                                <span>{SOURCE_ICONS[entry.source] || '📌'}</span>
                                {' '}
                                <span className="text-gray-400">[{entry.source.toUpperCase()}]</span>
                                {' '}
                                {entry.ticker && (
                                    <span className="text-cyan-400 font-medium">${entry.ticker}</span>
                                )}
                                {' '}
                                <span className={LEVEL_COLORS[entry.level] || 'text-gray-300'}>
                                    {entry.message}
                                </span>
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
