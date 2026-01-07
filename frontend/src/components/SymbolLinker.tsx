import { useState, createContext, useContext, useCallback } from 'react';

// Link group colors
const LINK_COLORS = {
    blue: { bg: 'bg-blue-500', text: 'text-blue-400', border: 'border-blue-500' },
    red: { bg: 'bg-red-500', text: 'text-red-400', border: 'border-red-500' },
    green: { bg: 'bg-green-500', text: 'text-green-400', border: 'border-green-500' },
    yellow: { bg: 'bg-yellow-500', text: 'text-yellow-400', border: 'border-yellow-500' },
    purple: { bg: 'bg-purple-500', text: 'text-purple-400', border: 'border-purple-500' },
    none: { bg: 'bg-gray-500', text: 'text-gray-400', border: 'border-gray-500' },
};

type LinkColor = keyof typeof LINK_COLORS;

interface LinkedWidget {
    id: string;
    name: string;
    color: LinkColor;
}

interface SymbolLinkContextType {
    linkedWidgets: LinkedWidget[];
    activeTicker: string;
    setTicker: (ticker: string, sourceColor?: LinkColor) => void;
    registerWidget: (id: string, name: string, color: LinkColor) => void;
    unregisterWidget: (id: string) => void;
    setWidgetColor: (id: string, color: LinkColor) => void;
}

const SymbolLinkContext = createContext<SymbolLinkContextType | null>(null);

export function useSymbolLink() {
    const context = useContext(SymbolLinkContext);
    if (!context) {
        throw new Error('useSymbolLink must be used within a SymbolLinkProvider');
    }
    return context;
}

interface SymbolLinkProviderProps {
    children: React.ReactNode;
    initialTicker?: string;
    onTickerChange?: (ticker: string) => void;
}

export function SymbolLinkProvider({ children, initialTicker = 'SPY', onTickerChange }: SymbolLinkProviderProps) {
    const [linkedWidgets, setLinkedWidgets] = useState<LinkedWidget[]>([]);
    const [activeTicker, setActiveTicker] = useState(initialTicker);

    const setTicker = useCallback((ticker: string, sourceColor?: LinkColor) => {
        setActiveTicker(ticker);
        onTickerChange?.(ticker);

        // If source color is specified, only update widgets with matching color
        // If no source color, update all linked widgets
        console.log(`Symbol link: ${ticker} from ${sourceColor || 'all'}`);
    }, [onTickerChange]);

    const registerWidget = useCallback((id: string, name: string, color: LinkColor) => {
        setLinkedWidgets(prev => {
            if (prev.find(w => w.id === id)) {
                return prev.map(w => w.id === id ? { ...w, name, color } : w);
            }
            return [...prev, { id, name, color }];
        });
    }, []);

    const unregisterWidget = useCallback((id: string) => {
        setLinkedWidgets(prev => prev.filter(w => w.id !== id));
    }, []);

    const setWidgetColor = useCallback((id: string, color: LinkColor) => {
        setLinkedWidgets(prev =>
            prev.map(w => w.id === id ? { ...w, color } : w)
        );
    }, []);

    return (
        <SymbolLinkContext.Provider value={{
            linkedWidgets,
            activeTicker,
            setTicker,
            registerWidget,
            unregisterWidget,
            setWidgetColor,
        }}>
            {children}
        </SymbolLinkContext.Provider>
    );
}

// Link indicator component for widgets
interface LinkIndicatorProps {
    widgetId: string;
    widgetName: string;
    onTickerChange?: (ticker: string) => void;
}

export function LinkIndicator({ widgetId, widgetName }: LinkIndicatorProps) {
    const { registerWidget, unregisterWidget, setWidgetColor, linkedWidgets } = useSymbolLink();
    const [showMenu, setShowMenu] = useState(false);

    const widget = linkedWidgets.find(w => w.id === widgetId);
    const currentColor = widget?.color || 'none';

    // Register on mount
    useState(() => {
        registerWidget(widgetId, widgetName, 'blue');
        return () => unregisterWidget(widgetId);
    });

    const colors = LINK_COLORS[currentColor];

    return (
        <div className="relative">
            <button
                onClick={() => setShowMenu(!showMenu)}
                className={`w-3 h-3 rounded-full ${colors.bg} transition hover:scale-125`}
                title={`Link group: ${currentColor}`}
            />

            {showMenu && (
                <div className="absolute top-full left-0 mt-1 bg-[#1a1f2e] border border-white/20 rounded-lg shadow-xl z-50 p-2">
                    <p className="text-xs text-gray-400 mb-2 px-1">Link Group</p>
                    <div className="flex gap-1">
                        {(Object.keys(LINK_COLORS) as LinkColor[]).map((color) => (
                            <button
                                key={color}
                                onClick={() => {
                                    setWidgetColor(widgetId, color);
                                    setShowMenu(false);
                                }}
                                className={`w-5 h-5 rounded-full ${LINK_COLORS[color].bg} transition hover:scale-110 ${currentColor === color ? 'ring-2 ring-white' : ''
                                    }`}
                                title={color}
                            />
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
}

// Watchlist component with linking
interface WatchlistItem {
    ticker: string;
    price: number;
    change: number;
    changePercent: number;
}

interface SymbolWatchlistProps {
    items: WatchlistItem[];
    linkColor?: LinkColor;
}

export function SymbolWatchlist({ items, linkColor = 'blue' }: SymbolWatchlistProps) {
    const { setTicker, activeTicker } = useSymbolLink();

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-3">
            <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-white">📋 Watchlist</h3>
                <div className={`w-3 h-3 rounded-full ${LINK_COLORS[linkColor].bg}`} title={`Linked: ${linkColor}`} />
            </div>

            <div className="space-y-1">
                {items.map((item) => (
                    <button
                        key={item.ticker}
                        onClick={() => setTicker(item.ticker, linkColor)}
                        className={`w-full flex items-center justify-between p-2 rounded transition ${activeTicker === item.ticker
                            ? `bg-${linkColor}-600/20 border border-${linkColor}-500/50`
                            : 'hover:bg-white/5'
                            }`}
                    >
                        <span className="font-mono text-sm text-white">{item.ticker}</span>
                        <div className="text-right">
                            <p className="text-sm text-white">${item.price.toFixed(2)}</p>
                            <p className={`text-xs ${item.change >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {item.change >= 0 ? '+' : ''}{item.changePercent.toFixed(2)}%
                            </p>
                        </div>
                    </button>
                ))}
            </div>
        </div>
    );
}
