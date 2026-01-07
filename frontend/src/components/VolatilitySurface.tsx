import { useState, useEffect } from 'react';
import axios from 'axios';
import Plot from 'react-plotly.js';

interface VolatilitySurfaceProps {
    ticker: string;
}

interface SurfaceData {
    strikes: number[];
    expirations: string[];
    iv_matrix: number[][];
}

export default function VolatilitySurface({ ticker }: VolatilitySurfaceProps) {
    const [surface, setSurface] = useState<SurfaceData | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchSurface = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await axios.get(`/api/volatility/surface/${ticker}`);
                setSurface(response.data.surface);
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Failed to load IV surface');
            } finally {
                setLoading(false);
            }
        };

        if (ticker) {
            fetchSurface();
        }
    }, [ticker]);

    if (loading) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4 h-full flex items-center justify-center">
                <div className="text-gray-400">Loading IV Surface...</div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4 h-full flex items-center justify-center">
                <div className="text-red-400">{error}</div>
            </div>
        );
    }

    if (!surface) {
        return null;
    }

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4 h-full">
            <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                🌐 3D Volatility Surface
            </h3>

            <Plot
                data={[
                    {
                        type: 'surface',
                        x: surface.strikes,
                        y: surface.expirations,
                        z: surface.iv_matrix,
                        colorscale: [
                            [0, '#00E676'],      // Low IV - Green (Cheap)
                            [0.5, '#FFD700'],    // Medium IV - Yellow
                            [1, '#FF1744']       // High IV - Red (Expensive)
                        ],
                        colorbar: {
                            title: 'IV %',
                            titlefont: { color: '#fff' },
                            tickfont: { color: '#fff' }
                        }
                    }
                ]}
                layout={{
                    autosize: true,
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0)',
                    margin: { l: 60, r: 30, t: 30, b: 60 },
                    scene: {
                        xaxis: {
                            title: 'Strike',
                            color: '#fff',
                            gridcolor: 'rgba(255,255,255,0.1)'
                        },
                        yaxis: {
                            title: 'Expiration',
                            color: '#fff',
                            gridcolor: 'rgba(255,255,255,0.1)'
                        },
                        zaxis: {
                            title: 'IV %',
                            color: '#fff',
                            gridcolor: 'rgba(255,255,255,0.1)'
                        },
                        bgcolor: 'rgba(0,0,0,0)'
                    }
                }}
                config={{ responsive: true }}
                style={{ width: '100%', height: '350px' }}
            />

            <div className="mt-2 text-xs text-gray-400 text-center">
                🟢 Low IV (Cheap) → 🟡 Medium → 🔴 High IV (Expensive)
            </div>
        </div>
    );
}
