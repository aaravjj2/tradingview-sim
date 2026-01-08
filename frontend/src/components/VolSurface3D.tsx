import { useState, useRef } from 'react';

interface VolSurfaceData {
    strikes: number[];
    expirations: string[];
    ivMatrix: number[][];
}

const DEMO_SURFACE: VolSurfaceData = {
    strikes: [480, 490, 500, 510, 520, 530, 540, 550, 560, 570, 580, 590, 600],
    expirations: ['1W', '2W', '1M', '2M', '3M', '6M', '1Y'],
    ivMatrix: [
        // Each row is an expiration, each column is a strike
        [0.35, 0.32, 0.28, 0.22, 0.18, 0.20, 0.24, 0.28, 0.32, 0.36, 0.40, 0.44, 0.48],
        [0.33, 0.30, 0.26, 0.21, 0.18, 0.19, 0.22, 0.26, 0.30, 0.34, 0.38, 0.42, 0.46],
        [0.31, 0.28, 0.24, 0.20, 0.17, 0.18, 0.21, 0.24, 0.28, 0.32, 0.36, 0.40, 0.44],
        [0.29, 0.26, 0.23, 0.19, 0.16, 0.17, 0.20, 0.23, 0.27, 0.30, 0.34, 0.38, 0.42],
        [0.28, 0.25, 0.22, 0.18, 0.16, 0.17, 0.19, 0.22, 0.26, 0.29, 0.33, 0.37, 0.40],
        [0.27, 0.24, 0.21, 0.18, 0.15, 0.16, 0.18, 0.21, 0.24, 0.28, 0.32, 0.35, 0.38],
        [0.26, 0.23, 0.20, 0.17, 0.15, 0.16, 0.18, 0.20, 0.23, 0.27, 0.30, 0.33, 0.36],
    ]
};

function getColor(iv: number): string {
    // Color scale from blue (low IV) to red (high IV)
    const normalized = Math.min(1, Math.max(0, (iv - 0.15) / 0.30));
    const r = Math.round(normalized * 255);
    const b = Math.round((1 - normalized) * 255);
    const g = Math.round((1 - Math.abs(normalized - 0.5) * 2) * 100);
    return `rgb(${r}, ${g}, ${b})`;
}

export default function VolSurface3D({ ticker = 'SPY', currentPrice = 540 }: { ticker?: string, currentPrice?: number }) {
    const [surface, setSurface] = useState<VolSurfaceData>(DEMO_SURFACE);
    const [rotation, setRotation] = useState({ x: 25, y: -30 });
    const [isDragging, setIsDragging] = useState(false);
    const [lastMouse, setLastMouse] = useState({ x: 0, y: 0 });
    const containerRef = useRef<HTMLDivElement>(null);

    // Transform 3D point to 2D with perspective
    const project = (x: number, y: number, z: number): { x: number, y: number } => {
        const radX = (rotation.x * Math.PI) / 180;
        const radY = (rotation.y * Math.PI) / 180;

        // Rotate around Y axis
        const x1 = x * Math.cos(radY) - z * Math.sin(radY);
        const z1 = x * Math.sin(radY) + z * Math.cos(radY);

        // Rotate around X axis
        const y1 = y * Math.cos(radX) - z1 * Math.sin(radX);
        const z2 = y * Math.sin(radX) + z1 * Math.cos(radX);

        // Perspective projection
        const perspective = 500;
        const scale = perspective / (perspective + z2 + 200);

        return {
            x: 250 + x1 * scale * 1.5,
            y: 200 - y1 * scale * 1.5
        };
    };

    const handleMouseDown = (e: React.MouseEvent) => {
        setIsDragging(true);
        setLastMouse({ x: e.clientX, y: e.clientY });
    };

    const handleMouseMove = (e: React.MouseEvent) => {
        if (!isDragging) return;

        const dx = e.clientX - lastMouse.x;
        const dy = e.clientY - lastMouse.y;

        setRotation(prev => ({
            x: Math.max(-60, Math.min(60, prev.x + dy * 0.5)),
            y: prev.y + dx * 0.5
        }));

        setLastMouse({ x: e.clientX, y: e.clientY });
    };

    const handleMouseUp = () => {
        setIsDragging(false);
    };

    // Build surface mesh
    const renderSurface = () => {
        const elements: JSX.Element[] = [];
        const { strikes, expirations, ivMatrix } = surface;

        // Normalize coordinates
        const xScale = 150 / strikes.length;
        const zScale = 100 / expirations.length;
        const yScale = 300;

        // Draw surface as grid of quads
        for (let i = 0; i < expirations.length - 1; i++) {
            for (let j = 0; j < strikes.length - 1; j++) {
                const iv00 = ivMatrix[i][j];
                const iv01 = ivMatrix[i][j + 1];
                const iv10 = ivMatrix[i + 1][j];
                const iv11 = ivMatrix[i + 1][j + 1];

                const avgIv = (iv00 + iv01 + iv10 + iv11) / 4;

                const p00 = project(j * xScale - 75, iv00 * yScale - 50, i * zScale - 50);
                const p01 = project((j + 1) * xScale - 75, iv01 * yScale - 50, i * zScale - 50);
                const p10 = project(j * xScale - 75, iv10 * yScale - 50, (i + 1) * zScale - 50);
                const p11 = project((j + 1) * xScale - 75, iv11 * yScale - 50, (i + 1) * zScale - 50);

                elements.push(
                    <polygon
                        key={`quad-${i}-${j}`}
                        points={`${p00.x},${p00.y} ${p01.x},${p01.y} ${p11.x},${p11.y} ${p10.x},${p10.y}`}
                        fill={getColor(avgIv)}
                        fillOpacity={0.7}
                        stroke="rgba(255,255,255,0.1)"
                        strokeWidth={0.5}
                    />
                );
            }
        }

        // Draw grid lines
        for (let i = 0; i < expirations.length; i++) {
            const points = strikes.map((_, j) => {
                const p = project(j * xScale - 75, ivMatrix[i][j] * yScale - 50, i * zScale - 50);
                return `${p.x},${p.y}`;
            }).join(' ');

            elements.push(
                <polyline
                    key={`line-exp-${i}`}
                    points={points}
                    fill="none"
                    stroke="rgba(255,255,255,0.3)"
                    strokeWidth={1}
                />
            );
        }

        return elements;
    };

    // Render axes
    const renderAxes = () => {
        const origin = project(0, -50, 0);
        const xEnd = project(80, -50, 0);
        const yEnd = project(0, 50, 0);
        const zEnd = project(0, -50, 60);

        return (
            <>
                {/* X axis - Strike */}
                <line x1={origin.x} y1={origin.y} x2={xEnd.x} y2={xEnd.y} stroke="#ef4444" strokeWidth={2} />
                <text x={xEnd.x + 10} y={xEnd.y} fill="#ef4444" fontSize="12">Strike</text>

                {/* Y axis - IV */}
                <line x1={origin.x} y1={origin.y} x2={yEnd.x} y2={yEnd.y} stroke="#22c55e" strokeWidth={2} />
                <text x={yEnd.x + 10} y={yEnd.y} fill="#22c55e" fontSize="12">IV</text>

                {/* Z axis - Expiration */}
                <line x1={origin.x} y1={origin.y} x2={zEnd.x} y2={zEnd.y} stroke="#3b82f6" strokeWidth={2} />
                <text x={zEnd.x + 10} y={zEnd.y} fill="#3b82f6" fontSize="12">Expiry</text>
            </>
        );
    };

    return (
        <div className="bg-[#0f1117] rounded-xl p-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold flex items-center gap-2">
                    🌋 3D Volatility Surface
                    <span className="text-xs text-gray-500">{ticker}</span>
                </h3>
                <div className="text-xs text-gray-400">
                    Drag to rotate
                </div>
            </div>

            <div
                ref={containerRef}
                className="bg-[#1a1f2e] rounded-lg cursor-grab active:cursor-grabbing"
                onMouseDown={handleMouseDown}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
            >
                <svg width="100%" height="400" viewBox="0 0 500 400">
                    {/* Background gradient */}
                    <defs>
                        <radialGradient id="surfaceBg" cx="50%" cy="50%" r="50%">
                            <stop offset="0%" stopColor="#1a1f2e" />
                            <stop offset="100%" stopColor="#0f1117" />
                        </radialGradient>
                    </defs>
                    <rect width="500" height="400" fill="url(#surfaceBg)" />

                    {/* Surface mesh */}
                    <g>{renderSurface()}</g>

                    {/* Axes */}
                    {renderAxes()}
                </svg>
            </div>

            {/* Color legend */}
            <div className="mt-3 flex items-center justify-center gap-2 text-xs">
                <span className="text-gray-400">Low IV</span>
                <div className="w-32 h-3 rounded" style={{
                    background: 'linear-gradient(to right, rgb(0,100,255), rgb(100,100,0), rgb(255,0,0))'
                }} />
                <span className="text-gray-400">High IV</span>
            </div>

            {/* Stats */}
            <div className="mt-3 grid grid-cols-4 gap-2 text-center text-xs">
                <div className="bg-[#1a1f2e] rounded p-2">
                    <div className="text-gray-400">ATM IV</div>
                    <div className="text-white font-medium">18.5%</div>
                </div>
                <div className="bg-[#1a1f2e] rounded p-2">
                    <div className="text-gray-400">Skew</div>
                    <div className="text-yellow-400 font-medium">-2.3</div>
                </div>
                <div className="bg-[#1a1f2e] rounded p-2">
                    <div className="text-gray-400">Term</div>
                    <div className="text-blue-400 font-medium">Contango</div>
                </div>
                <div className="bg-[#1a1f2e] rounded p-2">
                    <div className="text-gray-400">Spot</div>
                    <div className="text-green-400 font-medium">${currentPrice}</div>
                </div>
            </div>
        </div>
    );
}
