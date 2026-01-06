import { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';

interface CandleChartProps {
    ticker: string;
    data: CandleData[];
    breakevens?: number[];
    onHover?: (price: number, timestamp: string) => void;
}

interface CandleData {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

export default function CandleChart({ ticker, data, breakevens = [], onHover }: CandleChartProps) {
    const chartContainerRef = useRef<HTMLDivElement>(null);
    const [currentPrice, setCurrentPrice] = useState<number>(0);
    const [chartError, setChartError] = useState<string | null>(null);

    useEffect(() => {
        if (!chartContainerRef.current) return;

        try {
            // Create chart
            const chart = createChart(chartContainerRef.current, {
                layout: {
                    background: { color: '#0f1117' },
                    textColor: 'rgba(255, 255, 255, 0.7)',
                },
                grid: {
                    vertLines: { color: 'rgba(255, 255, 255, 0.05)' },
                    horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
                },
                width: chartContainerRef.current.clientWidth,
                height: 350,
            });

            // Try to add candlestick series with v5 API
            let candleSeries: any;
            try {
                // v5+ API
                candleSeries = chart.addCandlestickSeries({
                    upColor: '#00C853',
                    downColor: '#FF1744',
                    borderUpColor: '#00C853',
                    borderDownColor: '#FF1744',
                    wickUpColor: '#00C853',
                    wickDownColor: '#FF1744',
                });
            } catch {
                // Fallback - just use line series if candlestick fails
                candleSeries = chart.addLineSeries({
                    color: '#00BCD4',
                    lineWidth: 2,
                });
            }

            // Set data if available
            if (data.length > 0) {
                const chartData = data.map(d => ({
                    time: d.timestamp.split('T')[0],
                    open: d.open,
                    high: d.high,
                    low: d.low,
                    close: d.close,
                }));

                try {
                    candleSeries.setData(chartData);
                } catch {
                    // If candlestick data fails, try line data
                    const lineData = data.map(d => ({
                        time: d.timestamp.split('T')[0],
                        value: d.close,
                    }));
                    candleSeries.setData(lineData);
                }

                setCurrentPrice(data[data.length - 1].close);
                chart.timeScale().fitContent();
            }

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
        } catch (err: any) {
            setChartError(err.message || 'Failed to create chart');
        }
    }, [data]);

    if (chartError) {
        return (
            <div className="bg-[#1a1f2e] rounded-xl p-4 h-full">
                <div className="flex justify-between items-center mb-3">
                    <h3 className="text-lg font-semibold text-white">📊 {ticker} Price Chart</h3>
                </div>
                <div className="flex items-center justify-center h-[350px] text-red-400">
                    Chart Error: {chartError}
                </div>
            </div>
        );
    }

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4 h-full">
            <div className="flex justify-between items-center mb-3">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    📊 {ticker} Price Chart
                </h3>
                <div className="text-sm text-gray-400">
                    Current: <span className="text-white font-mono">${currentPrice.toFixed(2)}</span>
                </div>
            </div>
            <div
                ref={chartContainerRef}
                className="w-full h-[350px]"
            />
        </div>
    );
}
