import { useState } from 'react';
import axios from 'axios';

interface PanicButtonProps {
    onClose?: () => void;
}

export default function PanicButton({ onClose }: PanicButtonProps) {
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<string | null>(null);
    const [confirmed, setConfirmed] = useState(false);

    const executeCloseAll = async () => {
        if (!confirmed) {
            setConfirmed(true);
            return;
        }

        setLoading(true);
        setResult(null);

        try {
            const response = await axios.post('/api/strategy/close-all');
            setResult(`✅ Closed ${response.data.closed_count || 0} positions`);
        } catch (err: any) {
            setResult(`❌ Error: ${err.response?.data?.detail || 'Failed to close positions'}`);
        } finally {
            setLoading(false);
            setConfirmed(false);
        }
    };

    const cancel = () => {
        setConfirmed(false);
        setResult(null);
        onClose?.();
    };

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
            <div className="bg-[#1a1f2e] rounded-2xl p-6 w-[400px] border-2 border-red-500">
                {/* Header */}
                <div className="text-center mb-6">
                    <div className="text-6xl mb-4">🚨</div>
                    <h2 className="text-2xl font-bold text-red-400">
                        PANIC CLOSE ALL
                    </h2>
                    <p className="text-sm text-gray-400 mt-2">
                        This will send MARKET SELL orders for ALL open positions
                    </p>
                </div>

                {/* Warning */}
                <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 mb-6">
                    <div className="text-sm text-red-300">
                        ⚠️ <strong>Warning:</strong> This action cannot be undone.
                        All positions will be closed at current market price.
                    </div>
                </div>

                {/* Result */}
                {result && (
                    <div className={`mb-4 p-3 rounded-lg text-center ${result.startsWith('✅') ? 'bg-green-900/30 text-green-300' : 'bg-red-900/30 text-red-300'
                        }`}>
                        {result}
                    </div>
                )}

                {/* Buttons */}
                <div className="flex gap-3">
                    <button
                        onClick={cancel}
                        className="flex-1 py-3 rounded-lg bg-gray-700 text-white hover:bg-gray-600 transition-colors"
                    >
                        Cancel
                    </button>
                    <button
                        onClick={executeCloseAll}
                        disabled={loading}
                        className={`flex-1 py-3 rounded-lg font-bold transition-all ${confirmed
                                ? 'bg-red-600 text-white animate-pulse hover:bg-red-500'
                                : 'bg-red-900 text-red-300 hover:bg-red-800'
                            }`}
                    >
                        {loading ? '⏳ Closing...' : confirmed ? '⚡ CONFIRM CLOSE ALL' : '🛑 Close All Positions'}
                    </button>
                </div>

                {confirmed && !loading && (
                    <div className="mt-4 text-center text-xs text-red-400 animate-pulse">
                        Click again to confirm emergency close
                    </div>
                )}
            </div>
        </div>
    );
}
