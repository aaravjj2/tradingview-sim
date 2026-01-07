import { useState, useRef, useCallback } from 'react';

interface Block {
    id: string;
    type: 'call' | 'put' | 'stock';
    position: 'long' | 'short';
    strike?: number;
    premium?: number;
}

interface StrategyLegosProps {
    ticker: string;
    currentPrice: number;
    onStrategyChange?: (blocks: Block[]) => void;
}

// Draggable lego block component
function LegoBlock({
    block,
    onRemove
}: {
    block: Block;
    onRemove: (id: string) => void
}) {
    const colors = {
        'long-call': 'from-green-600 to-green-500',
        'short-call': 'from-red-600 to-red-500',
        'long-put': 'from-blue-600 to-blue-500',
        'short-put': 'from-orange-600 to-orange-500',
        'long-stock': 'from-purple-600 to-purple-500',
        'short-stock': 'from-pink-600 to-pink-500',
    };

    const colorKey = `${block.position}-${block.type}` as keyof typeof colors;

    return (
        <div
            className={`relative p-3 rounded-lg bg-gradient-to-r ${colors[colorKey]} cursor-move shadow-lg`}
            draggable
        >
            <button
                onClick={() => onRemove(block.id)}
                className="absolute -top-1 -right-1 w-5 h-5 bg-red-500 rounded-full text-xs flex items-center justify-center hover:bg-red-400"
            >
                ×
            </button>
            <div className="flex items-center gap-2">
                <span className="text-xl">
                    {block.type === 'call' ? '📈' : block.type === 'put' ? '📉' : '📊'}
                </span>
                <div>
                    <p className="font-semibold text-sm">
                        {block.position === 'long' ? '+' : '-'} {block.type.toUpperCase()}
                    </p>
                    {block.strike && (
                        <p className="text-xs opacity-80">${block.strike.toFixed(0)}</p>
                    )}
                </div>
            </div>
        </div>
    );
}

export default function StrategyLegos({ ticker, currentPrice, onStrategyChange }: StrategyLegosProps) {
    const [blocks, setBlocks] = useState<Block[]>([]);
    const [draggedType, setDraggedType] = useState<string | null>(null);
    const dropZoneRef = useRef<HTMLDivElement>(null);

    // Available block types to drag
    const availableBlocks = [
        { type: 'call', position: 'long', label: 'Buy Call', icon: '📈', color: 'bg-green-600' },
        { type: 'call', position: 'short', label: 'Sell Call', icon: '📈', color: 'bg-red-600' },
        { type: 'put', position: 'long', label: 'Buy Put', icon: '📉', color: 'bg-blue-600' },
        { type: 'put', position: 'short', label: 'Sell Put', icon: '📉', color: 'bg-orange-600' },
        { type: 'stock', position: 'long', label: 'Buy Stock', icon: '📊', color: 'bg-purple-600' },
    ];

    // Handle drag start
    const handleDragStart = (type: string, position: string) => {
        setDraggedType(`${position}-${type}`);
    };

    // Handle drop
    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        if (!draggedType) return;

        const [position, type] = draggedType.split('-');
        const newBlock: Block = {
            id: `block-${Date.now()}`,
            type: type as 'call' | 'put' | 'stock',
            position: position as 'long' | 'short',
            strike: type !== 'stock' ? currentPrice : undefined,
            premium: type !== 'stock' ? 2.5 : undefined,
        };

        const newBlocks = [...blocks, newBlock];
        setBlocks(newBlocks);
        onStrategyChange?.(newBlocks);
        setDraggedType(null);
    };

    // Handle drag over
    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
    };

    // Remove block
    const handleRemoveBlock = (id: string) => {
        const newBlocks = blocks.filter(b => b.id !== id);
        setBlocks(newBlocks);
        onStrategyChange?.(newBlocks);
    };

    // Update block strike
    const handleUpdateStrike = (id: string, strike: number) => {
        const newBlocks = blocks.map(b =>
            b.id === id ? { ...b, strike } : b
        );
        setBlocks(newBlocks);
        onStrategyChange?.(newBlocks);
    };

    // Calculate strategy metrics
    const calculateMetrics = useCallback(() => {
        if (blocks.length === 0) return null;

        let netPremium = 0;
        let maxProfit = 0;
        let maxLoss = 0;

        blocks.forEach(block => {
            const premium = (block.premium || 0) * 100;
            if (block.position === 'long') {
                netPremium -= premium;
            } else {
                netPremium += premium;
            }
        });

        // Simplified max profit/loss (would need proper calculation)
        if (netPremium > 0) {
            maxProfit = netPremium;
            maxLoss = -500; // Placeholder
        } else {
            maxProfit = 500; // Placeholder
            maxLoss = netPremium;
        }

        return {
            netPremium,
            maxProfit,
            maxLoss,
            legsCount: blocks.length
        };
    }, [blocks]);

    const metrics = calculateMetrics();

    // Preset strategies
    const applyPreset = (preset: string) => {
        let newBlocks: Block[] = [];

        switch (preset) {
            case 'iron_condor':
                newBlocks = [
                    { id: 'ic-1', type: 'put', position: 'long', strike: currentPrice * 0.92, premium: 0.5 },
                    { id: 'ic-2', type: 'put', position: 'short', strike: currentPrice * 0.95, premium: 1.5 },
                    { id: 'ic-3', type: 'call', position: 'short', strike: currentPrice * 1.05, premium: 1.5 },
                    { id: 'ic-4', type: 'call', position: 'long', strike: currentPrice * 1.08, premium: 0.5 },
                ];
                break;
            case 'straddle':
                newBlocks = [
                    { id: 'str-1', type: 'call', position: 'long', strike: currentPrice, premium: 5.0 },
                    { id: 'str-2', type: 'put', position: 'long', strike: currentPrice, premium: 5.0 },
                ];
                break;
            case 'covered_call':
                newBlocks = [
                    { id: 'cc-1', type: 'stock', position: 'long', premium: 0 },
                    { id: 'cc-2', type: 'call', position: 'short', strike: currentPrice * 1.05, premium: 2.0 },
                ];
                break;
        }

        setBlocks(newBlocks);
        onStrategyChange?.(newBlocks);
    };

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                🧱 Strategy Builder (Drag & Drop)
                <span className="text-xs text-gray-400">{ticker} @ ${currentPrice.toFixed(2)}</span>
            </h3>

            {/* Preset Buttons */}
            <div className="flex gap-2 mb-4">
                <button
                    onClick={() => applyPreset('iron_condor')}
                    className="px-3 py-1 bg-[#252b3b] rounded text-xs hover:bg-[#2d3548] transition"
                >
                    Iron Condor
                </button>
                <button
                    onClick={() => applyPreset('straddle')}
                    className="px-3 py-1 bg-[#252b3b] rounded text-xs hover:bg-[#2d3548] transition"
                >
                    Straddle
                </button>
                <button
                    onClick={() => applyPreset('covered_call')}
                    className="px-3 py-1 bg-[#252b3b] rounded text-xs hover:bg-[#2d3548] transition"
                >
                    Covered Call
                </button>
                <button
                    onClick={() => { setBlocks([]); onStrategyChange?.([]); }}
                    className="px-3 py-1 bg-red-900/30 text-red-400 rounded text-xs hover:bg-red-900/50 transition ml-auto"
                >
                    Clear
                </button>
            </div>

            <div className="flex gap-4">
                {/* Available Blocks */}
                <div className="w-32 space-y-2">
                    <p className="text-xs text-gray-400 mb-2">Drag to build:</p>
                    {availableBlocks.map((block) => (
                        <div
                            key={`${block.position}-${block.type}`}
                            draggable
                            onDragStart={() => handleDragStart(block.type, block.position)}
                            className={`p-2 ${block.color} rounded-lg cursor-grab active:cursor-grabbing text-center shadow-md hover:scale-105 transition`}
                        >
                            <p className="text-lg">{block.icon}</p>
                            <p className="text-xs font-medium">{block.label}</p>
                        </div>
                    ))}
                </div>

                {/* Drop Zone */}
                <div
                    ref={dropZoneRef}
                    onDrop={handleDrop}
                    onDragOver={handleDragOver}
                    className={`flex-1 min-h-[200px] border-2 border-dashed rounded-xl p-4 transition ${draggedType
                            ? 'border-blue-500 bg-blue-500/10'
                            : 'border-white/20 bg-[#252b3b]/50'
                        }`}
                >
                    {blocks.length === 0 ? (
                        <div className="h-full flex items-center justify-center text-gray-500">
                            <p>Drop blocks here to build your strategy</p>
                        </div>
                    ) : (
                        <div className="flex flex-wrap gap-3">
                            {blocks.map((block) => (
                                <LegoBlock
                                    key={block.id}
                                    block={block}
                                    onRemove={handleRemoveBlock}
                                />
                            ))}
                        </div>
                    )}
                </div>
            </div>

            {/* Metrics */}
            {metrics && metrics.legsCount > 0 && (
                <div className="mt-4 grid grid-cols-4 gap-2">
                    <div className="bg-[#252b3b] rounded p-2 text-center">
                        <p className="text-xs text-gray-400">Legs</p>
                        <p className="text-lg font-mono">{metrics.legsCount}</p>
                    </div>
                    <div className="bg-[#252b3b] rounded p-2 text-center">
                        <p className="text-xs text-gray-400">Net Premium</p>
                        <p className={`text-lg font-mono ${metrics.netPremium >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            ${metrics.netPremium.toFixed(0)}
                        </p>
                    </div>
                    <div className="bg-[#252b3b] rounded p-2 text-center">
                        <p className="text-xs text-gray-400">Max Profit</p>
                        <p className="text-lg font-mono text-green-400">${metrics.maxProfit.toFixed(0)}</p>
                    </div>
                    <div className="bg-[#252b3b] rounded p-2 text-center">
                        <p className="text-xs text-gray-400">Max Loss</p>
                        <p className="text-lg font-mono text-red-400">${Math.abs(metrics.maxLoss).toFixed(0)}</p>
                    </div>
                </div>
            )}
        </div>
    );
}
