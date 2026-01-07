import { useState, useEffect, useMemo } from 'react';

interface ContextSidebarProps {
    activeContext: 'chart' | 'supergraph' | 'analytics' | 'none';
    ticker: string;
    currentPrice: number;
    onIVChange?: (iv: number) => void;
    onDaysChange?: (days: number) => void;
}

export default function ContextSidebar({
    activeContext,
    ticker,
    currentPrice,
    onIVChange,
    onDaysChange,
}: ContextSidebarProps) {
    const [isCollapsed, setIsCollapsed] = useState(false);

    // Chart context state
    const [showSMA, setShowSMA] = useState(true);
    const [showEMA, setShowEMA] = useState(false);
    const [showBollingerBands, setShowBollingerBands] = useState(false);
    const [showRSI, setShowRSI] = useState(false);
    const [showMACD, setShowMACD] = useState(false);
    const [smaLength, setSmaLength] = useState(20);
    const [emaLength, setEmaLength] = useState(12);

    // Supergraph context state
    const [ivSlider, setIvSlider] = useState(25);
    const [daysSlider, setDaysSlider] = useState(30);
    const [showBreakevens, setShowBreakevens] = useState(true);
    const [showGhosts, setShowGhosts] = useState(false);

    // Propagate changes
    useEffect(() => {
        onIVChange?.(ivSlider / 100);
    }, [ivSlider, onIVChange]);

    useEffect(() => {
        onDaysChange?.(daysSlider);
    }, [daysSlider, onDaysChange]);

    const contextTitle = useMemo(() => {
        switch (activeContext) {
            case 'chart': return '📊 Chart Settings';
            case 'supergraph': return '📈 Supergraph Settings';
            case 'analytics': return '🔬 Analytics Settings';
            default: return '⚙️ Settings';
        }
    }, [activeContext]);

    if (isCollapsed) {
        return (
            <button
                onClick={() => setIsCollapsed(false)}
                className="fixed right-0 top-1/2 -translate-y-1/2 bg-[#1a1f2e] border border-white/20 rounded-l-lg p-2 hover:bg-[#252b3b] transition z-40"
            >
                ◀
            </button>
        );
    }

    return (
        <div className="fixed right-0 top-20 bottom-4 w-64 bg-[#1a1f2e] border-l border-white/10 z-40 flex flex-col">
            {/* Header */}
            <div className="flex items-center justify-between p-3 border-b border-white/10">
                <h3 className="text-sm font-semibold text-white">{contextTitle}</h3>
                <button
                    onClick={() => setIsCollapsed(true)}
                    className="p-1 hover:bg-white/10 rounded text-gray-400"
                >
                    ▶
                </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-3 space-y-4">
                {activeContext === 'chart' && (
                    <>
                        {/* Technical Indicators */}
                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-gray-400 uppercase">Indicators</h4>

                            <label className="flex items-center justify-between">
                                <span className="text-sm text-white">SMA</span>
                                <input
                                    type="checkbox"
                                    checked={showSMA}
                                    onChange={(e) => setShowSMA(e.target.checked)}
                                    className="w-4 h-4 rounded bg-[#252b3b]"
                                />
                            </label>
                            {showSMA && (
                                <input
                                    type="range"
                                    min="5"
                                    max="200"
                                    value={smaLength}
                                    onChange={(e) => setSmaLength(Number(e.target.value))}
                                    className="w-full"
                                />
                            )}

                            <label className="flex items-center justify-between">
                                <span className="text-sm text-white">EMA</span>
                                <input
                                    type="checkbox"
                                    checked={showEMA}
                                    onChange={(e) => setShowEMA(e.target.checked)}
                                    className="w-4 h-4 rounded bg-[#252b3b]"
                                />
                            </label>
                            {showEMA && (
                                <input
                                    type="range"
                                    min="5"
                                    max="200"
                                    value={emaLength}
                                    onChange={(e) => setEmaLength(Number(e.target.value))}
                                    className="w-full"
                                />
                            )}

                            <label className="flex items-center justify-between">
                                <span className="text-sm text-white">Bollinger Bands</span>
                                <input
                                    type="checkbox"
                                    checked={showBollingerBands}
                                    onChange={(e) => setShowBollingerBands(e.target.checked)}
                                    className="w-4 h-4 rounded bg-[#252b3b]"
                                />
                            </label>

                            <label className="flex items-center justify-between">
                                <span className="text-sm text-white">RSI</span>
                                <input
                                    type="checkbox"
                                    checked={showRSI}
                                    onChange={(e) => setShowRSI(e.target.checked)}
                                    className="w-4 h-4 rounded bg-[#252b3b]"
                                />
                            </label>

                            <label className="flex items-center justify-between">
                                <span className="text-sm text-white">MACD</span>
                                <input
                                    type="checkbox"
                                    checked={showMACD}
                                    onChange={(e) => setShowMACD(e.target.checked)}
                                    className="w-4 h-4 rounded bg-[#252b3b]"
                                />
                            </label>
                        </div>

                        {/* Price Levels */}
                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-gray-400 uppercase">Price Levels</h4>
                            <div className="bg-[#252b3b] rounded p-2 text-center">
                                <p className="text-xs text-gray-400">Current Price</p>
                                <p className="text-lg font-mono text-white">${currentPrice.toFixed(2)}</p>
                            </div>
                        </div>
                    </>
                )}

                {activeContext === 'supergraph' && (
                    <>
                        {/* IV Slider */}
                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <span className="text-sm text-white">Implied Volatility</span>
                                <span className="text-sm text-blue-400">{ivSlider}%</span>
                            </div>
                            <input
                                type="range"
                                min="5"
                                max="150"
                                value={ivSlider}
                                onChange={(e) => setIvSlider(Number(e.target.value))}
                                className="w-full"
                            />
                        </div>

                        {/* Days to Expiry */}
                        <div className="space-y-2">
                            <div className="flex justify-between">
                                <span className="text-sm text-white">Days to Expiry</span>
                                <span className="text-sm text-purple-400">{daysSlider} DTE</span>
                            </div>
                            <input
                                type="range"
                                min="1"
                                max="365"
                                value={daysSlider}
                                onChange={(e) => setDaysSlider(Number(e.target.value))}
                                className="w-full"
                            />
                        </div>

                        {/* Display Options */}
                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-gray-400 uppercase">Display</h4>

                            <label className="flex items-center justify-between">
                                <span className="text-sm text-white">Breakeven Lines</span>
                                <input
                                    type="checkbox"
                                    checked={showBreakevens}
                                    onChange={(e) => setShowBreakevens(e.target.checked)}
                                    className="w-4 h-4 rounded"
                                />
                            </label>

                            <label className="flex items-center justify-between">
                                <span className="text-sm text-white">Ghost Overlays</span>
                                <input
                                    type="checkbox"
                                    checked={showGhosts}
                                    onChange={(e) => setShowGhosts(e.target.checked)}
                                    className="w-4 h-4 rounded"
                                />
                            </label>
                        </div>

                        {/* Quick Strikes */}
                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-gray-400 uppercase">Quick Strikes</h4>
                            <div className="grid grid-cols-3 gap-1">
                                {[-10, -5, 0, 5, 10, 15].map((offset) => (
                                    <button
                                        key={offset}
                                        className="bg-[#252b3b] hover:bg-blue-600/30 rounded px-2 py-1 text-xs text-white transition"
                                    >
                                        ${(currentPrice + offset).toFixed(0)}
                                    </button>
                                ))}
                            </div>
                        </div>
                    </>
                )}

                {activeContext === 'analytics' && (
                    <>
                        <div className="space-y-2">
                            <h4 className="text-xs font-semibold text-gray-400 uppercase">Analytics Options</h4>
                            <p className="text-sm text-gray-500">
                                Click on a chart element to see context-specific controls here.
                            </p>
                        </div>

                        {/* Ticker Info */}
                        <div className="bg-[#252b3b] rounded p-3 space-y-1">
                            <p className="text-xs text-gray-400">Ticker</p>
                            <p className="text-lg font-bold text-white">{ticker}</p>
                            <p className="text-sm text-green-400">${currentPrice.toFixed(2)}</p>
                        </div>
                    </>
                )}

                {activeContext === 'none' && (
                    <div className="text-center text-gray-500 py-8">
                        <p className="text-3xl mb-2">👆</p>
                        <p className="text-sm">Click on a panel to see its settings here</p>
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-3 border-t border-white/10 text-xs text-gray-500 text-center">
                Context: {activeContext}
            </div>
        </div>
    );
}
