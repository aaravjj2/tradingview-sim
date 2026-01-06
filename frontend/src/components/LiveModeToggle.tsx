import { useState, useCallback } from 'react';

interface LiveModeToggleProps {
    paperMode: boolean;
    onToggle: (isPaper: boolean) => void;
}

const LIVE_PASSWORD = 'LIVE_TRADE_2024';

export default function LiveModeToggle({ paperMode, onToggle }: LiveModeToggleProps) {
    const [showPasswordModal, setShowPasswordModal] = useState(false);
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');

    const handleToggle = useCallback(() => {
        if (paperMode) {
            // Switching to LIVE - require password
            setShowPasswordModal(true);
            setPassword('');
            setError('');
        } else {
            // Switching back to PAPER - no password needed
            onToggle(true);
        }
    }, [paperMode, onToggle]);

    const handlePasswordSubmit = useCallback(() => {
        if (password === LIVE_PASSWORD) {
            onToggle(false);
            setShowPasswordModal(false);
            setPassword('');
            setError('');
        } else {
            setError('Invalid password');
        }
    }, [password, onToggle]);

    return (
        <>
            {/* Toggle Button */}
            <button
                onClick={handleToggle}
                className={`px-4 py-2 rounded-full text-sm font-semibold transition-all ${paperMode
                        ? 'bg-gradient-to-r from-yellow-500 to-orange-500 text-black hover:opacity-90'
                        : 'bg-gradient-to-r from-red-500 to-red-700 text-white animate-pulse'
                    }`}
            >
                {paperMode ? '📝 PAPER' : '🔴 LIVE'}
            </button>

            {/* Password Modal */}
            {showPasswordModal && (
                <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
                    <div className="bg-[#1a1f2e] rounded-2xl p-6 w-[400px]">
                        <div className="text-center mb-6">
                            <div className="text-4xl mb-3">⚠️</div>
                            <h2 className="text-xl font-bold text-white mb-2">
                                Enable Live Trading
                            </h2>
                            <p className="text-gray-400 text-sm">
                                You are about to switch to LIVE trading mode.
                                Real money will be at risk.
                            </p>
                        </div>

                        <div className="mb-4">
                            <label className="block text-sm text-gray-400 mb-2">
                                Enter Password
                            </label>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                onKeyDown={(e) => e.key === 'Enter' && handlePasswordSubmit()}
                                placeholder="••••••••"
                                className="w-full bg-[#0f1117] border border-white/10 rounded-lg px-4 py-3 text-white text-center text-lg tracking-widest focus:outline-none focus:border-red-500"
                                autoFocus
                            />
                            {error && (
                                <p className="text-red-400 text-sm mt-2 text-center">{error}</p>
                            )}
                        </div>

                        <div className="flex gap-3">
                            <button
                                onClick={() => setShowPasswordModal(false)}
                                className="flex-1 bg-gray-700 text-white font-semibold py-3 rounded-lg hover:bg-gray-600"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handlePasswordSubmit}
                                className="flex-1 bg-gradient-to-r from-red-500 to-red-700 text-white font-semibold py-3 rounded-lg hover:opacity-90"
                            >
                                Enable LIVE Mode
                            </button>
                        </div>

                        <p className="text-xs text-gray-500 text-center mt-4">
                            💡 Hint: Default password is LIVE_TRADE_2024
                        </p>
                    </div>
                </div>
            )}
        </>
    );
}
