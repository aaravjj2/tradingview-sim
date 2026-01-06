import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

interface JournalEntry {
    id: number;
    trade_id: string;
    ticker: string;
    strategy: string;
    entry_price: number;
    exit_price: number;
    quantity: number;
    side: string;
    pnl: number;
    notes: string;
    tags: string;
    created_at: string;
}

interface TradeJournalProps {
    onClose: () => void;
}

export default function TradeJournal({ onClose }: TradeJournalProps) {
    const [entries, setEntries] = useState<JournalEntry[]>([]);
    const [newNote, setNewNote] = useState('');
    const [newTags, setNewTags] = useState('');
    const [selectedTicker, setSelectedTicker] = useState('SPY');
    const [loading, setLoading] = useState(true);

    // Fetch journal entries
    const fetchEntries = useCallback(async () => {
        setLoading(true);
        try {
            const response = await axios.get('/api/strategy/journal');
            setEntries(response.data);
        } catch (err) {
            // Use mock data for demo
            setEntries([
                {
                    id: 1,
                    trade_id: 'T001',
                    ticker: 'SPY',
                    strategy: 'Long Call',
                    entry_price: 450.00,
                    exit_price: 465.00,
                    quantity: 1,
                    side: 'buy',
                    pnl: 150.00,
                    notes: 'RSI was below 30, good entry point. Exited at resistance.',
                    tags: 'momentum,oversold',
                    created_at: '2024-01-15T10:30:00Z',
                },
                {
                    id: 2,
                    trade_id: 'T002',
                    ticker: 'AAPL',
                    strategy: 'Iron Condor',
                    entry_price: 180.00,
                    exit_price: 175.00,
                    quantity: 2,
                    side: 'sell',
                    pnl: -250.00,
                    notes: 'Earnings volatility was higher than expected. Should have reduced position size.',
                    tags: 'earnings,volatility',
                    created_at: '2024-01-20T14:15:00Z',
                },
                {
                    id: 3,
                    trade_id: 'T003',
                    ticker: 'SPY',
                    strategy: 'Bull Put Spread',
                    entry_price: 478.00,
                    exit_price: 485.00,
                    quantity: 3,
                    side: 'sell',
                    pnl: 420.00,
                    notes: 'Sold premium on pullback. Theta worked in our favor.',
                    tags: 'premium,theta',
                    created_at: '2024-02-05T09:00:00Z',
                },
            ]);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchEntries();
    }, [fetchEntries]);

    const handleAddNote = useCallback(async () => {
        if (!newNote.trim()) return;

        // In production, this would POST to the API
        const newEntry: JournalEntry = {
            id: entries.length + 1,
            trade_id: `T${String(entries.length + 1).padStart(3, '0')}`,
            ticker: selectedTicker,
            strategy: 'Manual Entry',
            entry_price: 0,
            exit_price: 0,
            quantity: 0,
            side: 'note',
            pnl: 0,
            notes: newNote,
            tags: newTags,
            created_at: new Date().toISOString(),
        };

        setEntries([newEntry, ...entries]);
        setNewNote('');
        setNewTags('');
    }, [newNote, newTags, selectedTicker, entries]);

    const totalPnL = entries.reduce((sum, e) => sum + e.pnl, 0);
    const winningTrades = entries.filter(e => e.pnl > 0).length;
    const losingTrades = entries.filter(e => e.pnl < 0).length;

    return (
        <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
            <div className="bg-[#1a1f2e] rounded-2xl p-6 w-[1000px] max-h-[90vh] overflow-y-auto">
                {/* Header */}
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-xl font-bold flex items-center gap-2">
                        📓 Trade Journal
                    </h2>
                    <button
                        onClick={onClose}
                        className="text-gray-400 hover:text-white text-2xl"
                    >
                        ×
                    </button>
                </div>

                {/* Stats */}
                <div className="grid grid-cols-4 gap-4 mb-6">
                    <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                        <div className="text-gray-400 text-xs uppercase mb-1">Total P/L</div>
                        <div className={`text-2xl font-bold ${totalPnL >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            ${totalPnL.toFixed(2)}
                        </div>
                    </div>
                    <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                        <div className="text-gray-400 text-xs uppercase mb-1">Total Trades</div>
                        <div className="text-2xl font-bold text-blue-400">
                            {entries.length}
                        </div>
                    </div>
                    <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                        <div className="text-gray-400 text-xs uppercase mb-1">Winners</div>
                        <div className="text-2xl font-bold text-green-400">
                            {winningTrades}
                        </div>
                    </div>
                    <div className="bg-[#0f1117] rounded-xl p-4 text-center">
                        <div className="text-gray-400 text-xs uppercase mb-1">Losers</div>
                        <div className="text-2xl font-bold text-red-400">
                            {losingTrades}
                        </div>
                    </div>
                </div>

                {/* Add Note Form */}
                <div className="bg-[#0f1117] rounded-xl p-4 mb-6">
                    <h3 className="text-sm font-semibold mb-3 text-gray-300">Add Note</h3>
                    <div className="grid grid-cols-4 gap-3">
                        <select
                            value={selectedTicker}
                            onChange={(e) => setSelectedTicker(e.target.value)}
                            className="bg-[#1a1f2e] border border-white/10 rounded-lg px-3 py-2 text-white"
                        >
                            <option value="SPY">SPY</option>
                            <option value="AAPL">AAPL</option>
                            <option value="TSLA">TSLA</option>
                            <option value="QQQ">QQQ</option>
                        </select>
                        <input
                            type="text"
                            value={newTags}
                            onChange={(e) => setNewTags(e.target.value)}
                            placeholder="Tags (comma-separated)"
                            className="bg-[#1a1f2e] border border-white/10 rounded-lg px-3 py-2 text-white"
                        />
                        <input
                            type="text"
                            value={newNote}
                            onChange={(e) => setNewNote(e.target.value)}
                            placeholder="Why did the bot buy here?"
                            className="col-span-2 bg-[#1a1f2e] border border-white/10 rounded-lg px-3 py-2 text-white"
                        />
                    </div>
                    <button
                        onClick={handleAddNote}
                        className="mt-3 bg-gradient-to-r from-green-500 to-emerald-500 text-white font-semibold px-4 py-2 rounded-lg hover:opacity-90"
                    >
                        ➕ Add Note
                    </button>
                </div>

                {/* Journal Entries */}
                <div className="space-y-3">
                    {loading ? (
                        <div className="text-center py-8 text-gray-400">Loading...</div>
                    ) : entries.length === 0 ? (
                        <div className="text-center py-8 text-gray-400">No journal entries yet</div>
                    ) : (
                        entries.map((entry) => (
                            <div key={entry.id} className="bg-[#0f1117] rounded-xl p-4">
                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex items-center gap-3">
                                        <span className="text-lg font-bold text-white">{entry.ticker}</span>
                                        <span className="text-sm text-gray-400">{entry.strategy}</span>
                                        {entry.pnl !== 0 && (
                                            <span className={`text-sm font-semibold ${entry.pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                {entry.pnl >= 0 ? '+' : ''}${entry.pnl.toFixed(2)}
                                            </span>
                                        )}
                                    </div>
                                    <span className="text-xs text-gray-500">
                                        {new Date(entry.created_at).toLocaleDateString()}
                                    </span>
                                </div>
                                <p className="text-gray-300 text-sm mb-2">{entry.notes}</p>
                                {entry.tags && (
                                    <div className="flex gap-2">
                                        {entry.tags.split(',').map((tag, i) => (
                                            <span key={i} className="text-xs bg-blue-900/50 text-blue-300 px-2 py-1 rounded-full">
                                                #{tag.trim()}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        ))
                    )}
                </div>
            </div>
        </div>
    );
}
