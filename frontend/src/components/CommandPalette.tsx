import { useState, useEffect, useCallback, useRef } from 'react';

interface Command {
    id: string;
    label: string;
    shortcut?: string;
    category: 'navigation' | 'trading' | 'view' | 'system';
    action: () => void;
    icon: string;
}

interface CommandPaletteProps {
    isOpen: boolean;
    onClose: () => void;
    onTicker: (ticker: string) => void;
    onTogglePaperMode: () => void;
    onOpenBot: () => void;
    onOpenBacktest: () => void;
    onOpenJournal: () => void;
    onCloseAll: () => void;
    onToggleTab: (tab: 'charts' | 'analytics') => void;
    onToggleFocusMode: () => void;
}

export default function CommandPalette({
    isOpen,
    onClose,
    onTicker,
    onTogglePaperMode,
    onOpenBot,
    onOpenBacktest,
    onOpenJournal,
    onCloseAll,
    onToggleTab,
    onToggleFocusMode,
}: CommandPaletteProps) {
    const [query, setQuery] = useState('');
    const [selectedIndex, setSelectedIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);

    // Define all available commands
    const commands: Command[] = [
        // Navigation
        { id: 'goto-charts', label: 'Switch to Charts Tab', category: 'navigation', icon: '📊', action: () => onToggleTab('charts') },
        { id: 'goto-analytics', label: 'Switch to Analytics Tab', category: 'navigation', icon: '🔬', action: () => onToggleTab('analytics') },
        { id: 'focus-mode', label: 'Toggle Focus Mode', category: 'view', icon: '🎯', shortcut: 'F', action: onToggleFocusMode },

        // Trading
        { id: 'open-bot', label: 'Open Trading Bot', category: 'trading', icon: '🤖', action: onOpenBot },
        { id: 'open-backtest', label: 'Open Backtester', category: 'trading', icon: '📈', action: onOpenBacktest },
        { id: 'open-journal', label: 'Open Trade Journal', category: 'trading', icon: '📓', action: onOpenJournal },
        { id: 'close-all', label: 'Close All Positions (PANIC)', category: 'trading', icon: '🚨', action: onCloseAll },
        { id: 'toggle-paper', label: 'Toggle Paper/Live Mode', category: 'trading', icon: '🔄', action: onTogglePaperMode },

        // Quick Tickers
        { id: 'ticker-spy', label: 'Graph SPY', category: 'navigation', icon: '📈', action: () => onTicker('SPY') },
        { id: 'ticker-qqq', label: 'Graph QQQ', category: 'navigation', icon: '📈', action: () => onTicker('QQQ') },
        { id: 'ticker-aapl', label: 'Graph AAPL', category: 'navigation', icon: '📈', action: () => onTicker('AAPL') },
        { id: 'ticker-nvda', label: 'Graph NVDA', category: 'navigation', icon: '📈', action: () => onTicker('NVDA') },
        { id: 'ticker-tsla', label: 'Graph TSLA', category: 'navigation', icon: '📈', action: () => onTicker('TSLA') },
        { id: 'ticker-gc', label: 'Graph Gold (GC)', category: 'navigation', icon: '🥇', action: () => onTicker('GC') },
    ];

    // Filter commands based on query
    const filteredCommands = commands.filter(cmd => {
        const searchStr = `${cmd.label} ${cmd.category}`.toLowerCase();
        const queryLower = query.toLowerCase();

        // Check if it's a direct ticker command like "buy AAPL" or just "AAPL"
        if (queryLower.match(/^(buy|sell|graph)?\s*[a-z]{1,5}$/i)) {
            const ticker = queryLower.replace(/^(buy|sell|graph)\s*/i, '').toUpperCase();
            if (ticker.length >= 1) {
                return cmd.id.includes('ticker') || searchStr.includes(queryLower);
            }
        }

        return searchStr.includes(queryLower);
    });

    // Add dynamic ticker command if query looks like a ticker
    const dynamicCommands = [...filteredCommands];
    const tickerMatch = query.match(/^(graph\s+)?([A-Za-z]{1,5})$/i);
    if (tickerMatch && tickerMatch[2]) {
        const ticker = tickerMatch[2].toUpperCase();
        if (!commands.find(c => c.id === `ticker-${ticker.toLowerCase()}`)) {
            dynamicCommands.unshift({
                id: `ticker-dynamic-${ticker}`,
                label: `Graph ${ticker}`,
                category: 'navigation',
                icon: '📈',
                action: () => onTicker(ticker),
            });
        }
    }

    const executeCommand = useCallback((command: Command) => {
        command.action();
        setQuery('');
        onClose();
    }, [onClose]);

    // Keyboard navigation
    useEffect(() => {
        if (!isOpen) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            switch (e.key) {
                case 'ArrowDown':
                    e.preventDefault();
                    setSelectedIndex(i => Math.min(i + 1, dynamicCommands.length - 1));
                    break;
                case 'ArrowUp':
                    e.preventDefault();
                    setSelectedIndex(i => Math.max(i - 1, 0));
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (dynamicCommands[selectedIndex]) {
                        executeCommand(dynamicCommands[selectedIndex]);
                    }
                    break;
                case 'Escape':
                    e.preventDefault();
                    onClose();
                    break;
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, selectedIndex, dynamicCommands, executeCommand, onClose]);

    // Focus input when opened
    useEffect(() => {
        if (isOpen && inputRef.current) {
            inputRef.current.focus();
            setSelectedIndex(0);
        }
    }, [isOpen]);

    // Reset when query changes
    useEffect(() => {
        setSelectedIndex(0);
    }, [query]);

    if (!isOpen) return null;

    const categoryColors: Record<string, string> = {
        navigation: 'bg-blue-500/20 text-blue-400',
        trading: 'bg-green-500/20 text-green-400',
        view: 'bg-purple-500/20 text-purple-400',
        system: 'bg-gray-500/20 text-gray-400',
    };

    return (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Palette */}
            <div className="relative w-full max-w-xl bg-[#1a1f2e] rounded-xl border border-white/20 shadow-2xl overflow-hidden">
                {/* Search Input */}
                <div className="flex items-center gap-3 p-4 border-b border-white/10">
                    <span className="text-gray-400">🔍</span>
                    <input
                        ref={inputRef}
                        type="text"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        placeholder="Type a command or ticker... (e.g., 'Graph AAPL', 'Open Bot')"
                        className="flex-1 bg-transparent text-white placeholder-gray-500 outline-none text-lg"
                    />
                    <kbd className="px-2 py-1 bg-white/10 rounded text-xs text-gray-400">ESC</kbd>
                </div>

                {/* Results */}
                <div className="max-h-80 overflow-y-auto">
                    {dynamicCommands.length === 0 ? (
                        <div className="p-8 text-center text-gray-500">
                            No commands found. Try typing a ticker symbol.
                        </div>
                    ) : (
                        <div className="p-2">
                            {dynamicCommands.map((cmd, index) => (
                                <button
                                    key={cmd.id}
                                    onClick={() => executeCommand(cmd)}
                                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-left transition ${index === selectedIndex
                                            ? 'bg-blue-600/30 border border-blue-500/50'
                                            : 'hover:bg-white/5'
                                        }`}
                                >
                                    <span className="text-xl">{cmd.icon}</span>
                                    <div className="flex-1">
                                        <p className="text-white font-medium">{cmd.label}</p>
                                        <span className={`text-xs px-2 py-0.5 rounded ${categoryColors[cmd.category]}`}>
                                            {cmd.category}
                                        </span>
                                    </div>
                                    {cmd.shortcut && (
                                        <kbd className="px-2 py-1 bg-white/10 rounded text-xs text-gray-400">
                                            ⌘{cmd.shortcut}
                                        </kbd>
                                    )}
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer Hint */}
                <div className="p-3 border-t border-white/10 flex items-center justify-between text-xs text-gray-500">
                    <span>↑↓ Navigate • Enter Select • Esc Close</span>
                    <span>Ctrl+K to open</span>
                </div>
            </div>
        </div>
    );
}
