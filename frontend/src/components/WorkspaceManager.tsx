import { useState, useCallback } from 'react';

interface WorkspacePreset {
    name: string;
    icon: string;
    gridTemplate: string;
    gridAreas: string;
}

interface WorkspaceManagerProps {
    children: React.ReactNode;
    focusMode: boolean;
}

// Default layouts using CSS Grid
const PRESETS: WorkspacePreset[] = [
    {
        name: 'Default',
        icon: '📊',
        gridTemplate: '"chart supergraph" 1fr "greeks greeks" auto / 1fr 1fr',
        gridAreas: 'chart supergraph greeks',
    },
    {
        name: 'Trading Focus',
        icon: '🎯',
        gridTemplate: '"chart sidebar" 1fr / 2fr 1fr',
        gridAreas: 'chart sidebar',
    },
    {
        name: 'Analytics',
        icon: '🔬',
        gridTemplate: '"a b c" 1fr "d d d" auto / 1fr 1fr 1fr',
        gridAreas: 'a b c d',
    },
    {
        name: 'Single',
        icon: '🖥️',
        gridTemplate: '"main" 1fr / 1fr',
        gridAreas: 'main',
    },
];

const PRESET_KEY = 'supergraph-workspace-preset';

export default function WorkspaceManager({ children, focusMode }: WorkspaceManagerProps) {
    const [activePreset, setActivePreset] = useState(() => {
        return localStorage.getItem(PRESET_KEY) || 'Default';
    });

    const [showPresetMenu, setShowPresetMenu] = useState(false);

    const applyPreset = useCallback((preset: WorkspacePreset) => {
        setActivePreset(preset.name);
        localStorage.setItem(PRESET_KEY, preset.name);
        setShowPresetMenu(false);
    }, []);

    const resetToDefault = useCallback(() => {
        applyPreset(PRESETS[0]);
    }, [applyPreset]);

    if (focusMode) {
        return <div className="focus-mode-container h-full">{children}</div>;
    }

    return (
        <div className="workspace-manager relative">
            {/* Workspace Controls */}
            <div className="absolute top-2 right-2 z-10 flex items-center gap-2 workspace-controls">
                {/* Preset Selector */}
                <div className="relative">
                    <button
                        onClick={() => setShowPresetMenu(!showPresetMenu)}
                        className="bg-[#1a1f2e] border border-white/20 rounded-lg px-3 py-1.5 text-sm flex items-center gap-2 hover:border-blue-500 transition"
                    >
                        <span>{PRESETS.find(p => p.name === activePreset)?.icon || '📊'}</span>
                        <span>{activePreset}</span>
                        <span className="text-gray-400">▼</span>
                    </button>

                    {showPresetMenu && (
                        <div className="absolute top-full right-0 mt-1 w-48 bg-[#1a1f2e] border border-white/20 rounded-lg shadow-xl overflow-hidden z-50">
                            {PRESETS.map((preset) => (
                                <button
                                    key={preset.name}
                                    onClick={() => applyPreset(preset)}
                                    className={`w-full flex items-center gap-2 px-3 py-2 text-sm text-left transition ${activePreset === preset.name
                                        ? 'bg-blue-600/30 text-blue-400'
                                        : 'hover:bg-white/5 text-white'
                                        }`}
                                >
                                    <span>{preset.icon}</span>
                                    <span>{preset.name}</span>
                                </button>
                            ))}
                            <div className="border-t border-white/10">
                                <button
                                    onClick={resetToDefault}
                                    className="w-full flex items-center gap-2 px-3 py-2 text-sm text-left text-gray-400 hover:bg-white/5"
                                >
                                    <span>🔄</span>
                                    <span>Reset Layout</span>
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Grid Layout - Using CSS Grid for simplicity */}
            <div className="workspace-grid">
                {children}
            </div>
        </div>
    );
}

// Wrapper component for panels
interface DockablePanelProps {
    id: string;
    title: string;
    icon?: string;
    children: React.ReactNode;
    className?: string;
}

export function DockablePanel({ id, title, icon, children, className = '' }: DockablePanelProps) {
    const [isMaximized, setIsMaximized] = useState(false);

    const handleDetach = () => {
        console.log(`Panel ${id} detached - would open in new window`);
    };

    return (
        <div
            className={`bg-[#1a1f2e] rounded-xl border border-white/10 flex flex-col overflow-hidden ${className} ${isMaximized ? 'fixed inset-4 z-50' : ''
                }`}
        >
            {/* Panel Header - Drag Handle */}
            <div className="panel-drag-handle flex items-center justify-between px-3 py-2 bg-[#252b3b] border-b border-white/10">
                <div className="flex items-center gap-2">
                    {icon && <span>{icon}</span>}
                    <span className="text-sm font-medium text-white">{title}</span>
                </div>
                <div className="flex items-center gap-1">
                    <button
                        onClick={handleDetach}
                        className="p-1 hover:bg-white/10 rounded text-gray-400 hover:text-white transition"
                        title="Pop out"
                    >
                        ↗
                    </button>
                    <button
                        onClick={() => setIsMaximized(!isMaximized)}
                        className="p-1 hover:bg-white/10 rounded text-gray-400 hover:text-white transition"
                        title={isMaximized ? 'Restore' : 'Maximize'}
                    >
                        {isMaximized ? '⊙' : '⊡'}
                    </button>
                </div>
            </div>

            {/* Panel Content */}
            <div className="flex-1 overflow-auto p-3">
                {children}
            </div>
        </div>
    );
}
