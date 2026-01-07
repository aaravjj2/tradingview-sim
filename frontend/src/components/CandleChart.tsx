import { useEffect, useRef, useState, useCallback } from 'react';
import { createChart, CandlestickSeries, LineSeries, AreaSeries } from 'lightweight-charts';

interface CandleChartProps {
    ticker: string;
    data: CandleData[];
    breakevens?: number[];
    probabilityCone?: {
        upper_1sigma: number;
        lower_1sigma: number;
        upper_2sigma: number;
        lower_2sigma: number;
        days: number;
    };
    onHover?: (price: number, timestamp: string) => void;
    hoveredTimestamp?: string;
    currentPrice?: number;
}

interface CandleData {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

export default function CandleChart({
    ticker,
    data,
    breakevens = [],
    probabilityCone,
    onHover,
    hoveredTimestamp,
    currentPrice: livePrice
}: CandleChartProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const chartRef = useRef<ReturnType<typeof createChart> | null>(null);
    const seriesRef = useRef<any>(null);
    const coneSeriesRefs = useRef<any[]>([]);
    const [currentPrice, setCurrentPrice] = useState<number>(0);
    const [showCone, setShowCone] = useState(true);

    // Initialize chart
    useEffect(() => {
        if (!chartContainerRef.current) return;

        const chart = createChart(chartContainerRef.current, {
            layout: {
                background: { color: '#0f1117' },
                textColor: 'rgba(255, 255, 255, 0.7)',
            },
            grid: {
                vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
            },
            crosshair: {
                mode: 1,
                vertLine: {
                    color: 'rgba(255, 255, 255, 0.3)',
                    width: 1,
                    style: 2,
                    labelBackgroundColor: '#1a1f2e',
                },
                horzLine: {
                    color: 'rgba(255, 255, 255, 0.3)',
                    width: 1,
                    style: 2,
                    labelBackgroundColor: '#1a1f2e',
                },
            },
            rightPriceScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
            },
            timeScale: {
                borderColor: 'rgba(255, 255, 255, 0.1)',
                timeVisible: true,
                secondsVisible: false,
            },
            width: chartContainerRef.current.clientWidth,
            height: 350,
        });

        chartRef.current = chart;

        // Add candlestick series using v5 API
        const candleSeries = chart.addSeries(CandlestickSeries, {
            upColor: '#00C853',
            downColor: '#FF1744',
            borderUpColor: '#00C853',
            borderDownColor: '#FF1744',
            wickUpColor: '#00C853',
            wickDownColor: '#FF1744',
        });

        seriesRef.current = candleSeries;

        // Handle crosshair move for sync
        chart.subscribeCrosshairMove((param) => {
            if (param.point && param.time && onHover) {
                const data = param.seriesData.get(candleSeries);
                if (data && 'close' in data) {
                    onHover((data as any).close, param.time as string);
                }
            }
        });

        // Handle resize
        const handleResize = () => {
            if (chartContainerRef.current) {
                chart.applyOptions({ width: chartContainerRef.current.clientWidth });
            }
        };

        window.addEventListener('resize', handleResize);

        return () => {
            window.removeEventListener('resize', handleResize);
            chart.remove();
        };
    }, [onHover]);

    // Update data
    useEffect(() => {
        if (!seriesRef.current || data.length === 0) return;

        const chartData = data.map(d => ({
            time: d.timestamp.split('T')[0] as string,
            open: d.open,
            high: d.high,
            low: d.low,
            close: d.close,
        }));

        seriesRef.current.setData(chartData);

        if (livePrice) {
            setCurrentPrice(livePrice);
        } else if (data.length > 0) {
            setCurrentPrice(data[data.length - 1].close);
        }

        chartRef.current?.timeScale().fitContent();
    }, [data, livePrice]);

    // Update display price when external price changes
    useEffect(() => {
        if (livePrice) {
            setCurrentPrice(livePrice);
        }
    }, [livePrice]);

    // Add breakeven lines
    useEffect(() => {
        if (!seriesRef.current || !chartRef.current) return;

        // Create price lines for breakevens
        breakevens.forEach((be, index) => {
            try {
                seriesRef.current.createPriceLine({
                    price: be,
                    color: '#FF9800',
                    lineWidth: 2,
                    lineStyle: 2,
                    axisLabelVisible: true,
                    title: `BE ${index + 1}`,
                });
            } catch (err) {
                console.warn('Could not create price line:', err);
            }
        });
    }, [breakevens, data]);

    // Add probability cone visualization
    useEffect(() => {
        if (!chartRef.current || !probabilityCone || !showCone || data.length === 0) return;

        const lastDate = new Date(data[data.length - 1].timestamp);

        // Create future dates for cone projection
        const futureData1Sigma: { time: string; value: number }[] = [];
        const futureData2Sigma: { time: string; value: number }[] = []; // Unused but kept for structure

        for (let i = 0; i <= probabilityCone.days; i++) {
            const futureDate = new Date(lastDate);
            futureDate.setDate(futureDate.getDate() + i);
            const dateStr = futureDate.toISOString().split('T')[0];

            // Linear interpolation for cone expansion
            const ratio = i / probabilityCone.days;
            const upper1 = currentPrice + (probabilityCone.upper_1sigma - currentPrice) * ratio;
            const lower1 = currentPrice + (probabilityCone.lower_1sigma - currentPrice) * ratio;

            futureData1Sigma.push({ time: dateStr, value: upper1 });
        }

        try {
            const upperSeries = chartRef.current.addSeries(LineSeries, {
                color: 'rgba(100, 181, 246, 0.5)',
                lineWidth: 1,
                lineStyle: 2,
            });
            upperSeries.setData(futureData1Sigma);
            coneSeriesRefs.current.push(upperSeries);
        } catch (err) {
            console.warn('Could not add cone series:', err);
        }
    }, [probabilityCone, showCone, data, currentPrice]);

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4 h-full">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    📊 {ticker} Price Chart
                </h3>
                <div className="flex items-center gap-4">
                    {probabilityCone && (
                        <button
                            onClick={() => setShowCone(!showCone)}
                            className={`text-xs px-2 py-1 rounded ${showCone ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-700 text-gray-400'
                                }`}
                        >
                            📐 Cone
                        </button>
                    )}
                    <div className="text-sm text-gray-400">
                        Current: <span className="text-white font-mono">${currentPrice.toFixed(2)}</span>
                    </div>
                </div>
            </div>

            {probabilityCone && showCone && (
                <div className="flex gap-4 text-xs text-gray-400 mb-2">
                    <span>1σ: ${probabilityCone.lower_1sigma.toFixed(2)} - ${probabilityCone.upper_1sigma.toFixed(2)}</span>
                    <span>2σ: ${probabilityCone.lower_2sigma.toFixed(2)} - ${probabilityCone.upper_2sigma.toFixed(2)}</span>
                </div>
            )}

            <div
                ref={chartContainerRef}
                className="w-full h-[350px]"
            />
        </div>
    );
}

