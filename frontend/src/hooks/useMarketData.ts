import { useState, useEffect, useCallback } from 'react';
import axios from 'axios';

interface CandleData {
    timestamp: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
}

interface PriceData {
    ticker: string;
    price: number;
    bid: number;
    ask: number;
    timestamp: string;
}

interface MarketDataOptions {
    refreshInterval?: number;  // in milliseconds, default 5000
    autoRefresh?: boolean;     // default true
}

export function useMarketData(ticker: string, options: MarketDataOptions = {}) {
    const { refreshInterval = 5000, autoRefresh = true } = options;

    const [price, setPrice] = useState<PriceData | null>(null);
    const [candles, setCandles] = useState<CandleData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
    const [latency, setLatency] = useState<number>(0);
    const [refreshCount, setRefreshCount] = useState(0);

    // Fetch current price with latency tracking
    const fetchPrice = useCallback(async () => {
        const startTime = performance.now();
        try {
            const response = await axios.get(`/api/market/price/${ticker}`);
            const endTime = performance.now();

            setPrice(response.data);
            setLastUpdate(new Date());
            setLatency(Math.round(endTime - startTime));
            setRefreshCount(prev => prev + 1);
        } catch (err) {
            console.error('Error fetching price:', err);
            setLatency(-1); // Indicates error
        }
    }, [ticker]);

    // Fetch candles (uses backend caching)
    const fetchCandles = useCallback(async () => {
        try {
            setLoading(true);
            const response = await axios.get(`/api/market/candles/${ticker}?limit=100`);

            // Normalize dates to current year (Alpaca free tier returns older data)
            const rawCandles = response.data as CandleData[];
            if (rawCandles.length > 0) {
                const lastDate = new Date(rawCandles[rawCandles.length - 1].timestamp);
                const today = new Date();
                const daysDiff = Math.floor((today.getTime() - lastDate.getTime()) / (1000 * 60 * 60 * 24));

                const normalizedCandles = rawCandles.map((candle: CandleData) => {
                    const originalDate = new Date(candle.timestamp);
                    originalDate.setDate(originalDate.getDate() + daysDiff);
                    return {
                        ...candle,
                        timestamp: originalDate.toISOString(),
                    };
                });
                setCandles(normalizedCandles);
            } else {
                setCandles(rawCandles);
            }
            setError(null);
        } catch (err) {
            setError('Failed to fetch candle data');
            console.error('Error fetching candles:', err);
        } finally {
            setLoading(false);
        }
    }, [ticker]);

    // Initial fetch
    useEffect(() => {
        fetchPrice();
        fetchCandles();
    }, [fetchPrice, fetchCandles]);

    // Configurable auto-refresh (heartbeat polling)
    useEffect(() => {
        if (!autoRefresh) return;

        const interval = setInterval(fetchPrice, refreshInterval);
        return () => clearInterval(interval);
    }, [fetchPrice, refreshInterval, autoRefresh]);

    return {
        price,
        candles,
        loading,
        error,
        lastUpdate,
        latency,
        refreshCount,
        refetch: fetchCandles,
        refreshPrice: fetchPrice
    };
}

// Black-Scholes Greeks calculation
function calculateGreeks(
    stockPrice: number,
    strikePrice: number,
    timeToExpiry: number, // in years
    riskFreeRate: number,
    volatility: number,
    optionType: 'call' | 'put'
) {
    // Standard normal distribution functions
    const normCdf = (x: number) => {
        const a1 = 0.254829592;
        const a2 = -0.284496736;
        const a3 = 1.421413741;
        const a4 = -1.453152027;
        const a5 = 1.061405429;
        const p = 0.3275911;
        const sign = x < 0 ? -1 : 1;
        const absX = Math.abs(x);
        const t = 1 / (1 + p * absX);
        const y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-absX * absX / 2);
        return 0.5 * (1 + sign * y);
    };

    const normPdf = (x: number) => {
        return Math.exp(-x * x / 2) / Math.sqrt(2 * Math.PI);
    };

    // Calculate d1 and d2
    const sqrtT = Math.sqrt(timeToExpiry);
    const d1 = (Math.log(stockPrice / strikePrice) + (riskFreeRate + volatility * volatility / 2) * timeToExpiry) / (volatility * sqrtT);
    const d2 = d1 - volatility * sqrtT;

    // Greeks
    const delta = optionType === 'call' ? normCdf(d1) : normCdf(d1) - 1;
    const gamma = normPdf(d1) / (stockPrice * volatility * sqrtT);
    const theta = optionType === 'call'
        ? (-stockPrice * normPdf(d1) * volatility / (2 * sqrtT) - riskFreeRate * strikePrice * Math.exp(-riskFreeRate * timeToExpiry) * normCdf(d2)) / 365
        : (-stockPrice * normPdf(d1) * volatility / (2 * sqrtT) + riskFreeRate * strikePrice * Math.exp(-riskFreeRate * timeToExpiry) * normCdf(-d2)) / 365;
    const vega = stockPrice * sqrtT * normPdf(d1) / 100; // per 1% change in volatility

    return { delta, gamma, theta, vega };
}

interface OptionLeg {
    option_type: string;
    position: string;
    strike: number;
    premium: number;
    quantity: number;
    expiration_days?: number;
    iv?: number;
}

export function useGreeks(
    ticker: string,
    currentPrice: number,
    legs: OptionLeg[] = []
) {
    const [greeks, setGreeks] = useState({
        delta: 0,
        gamma: 0,
        theta: 0,
        vega: 0,
    });

    useEffect(() => {
        if (!currentPrice || legs.length === 0) {
            // Default demo values
            setGreeks({
                delta: 0.55,
                gamma: 0.023,
                theta: -15.50,
                vega: 22.30,
            });
            return;
        }

        // Calculate aggregate Greeks from all legs
        let totalDelta = 0;
        let totalGamma = 0;
        let totalTheta = 0;
        let totalVega = 0;

        legs.forEach(leg => {
            if (leg.option_type === 'stock') {
                const sign = leg.position === 'long' ? 1 : -1;
                totalDelta += sign * leg.quantity;
                return;
            }

            const optionType = leg.option_type as 'call' | 'put';
            const timeToExpiry = (leg.expiration_days || 30) / 365;
            const iv = leg.iv || 0.25;
            const riskFreeRate = 0.05;

            const legGreeks = calculateGreeks(
                currentPrice,
                leg.strike,
                timeToExpiry,
                riskFreeRate,
                iv,
                optionType
            );

            const sign = leg.position === 'long' ? 1 : -1;
            const multiplier = leg.quantity * 100; // Options contract multiplier

            totalDelta += sign * legGreeks.delta * multiplier;
            totalGamma += sign * legGreeks.gamma * multiplier;
            totalTheta += sign * legGreeks.theta * multiplier;
            totalVega += sign * legGreeks.vega * multiplier;
        });

        setGreeks({
            delta: totalDelta / 100, // Normalize to per-share basis
            gamma: totalGamma / 100,
            theta: totalTheta,
            vega: totalVega,
        });
    }, [currentPrice, legs]);

    return greeks;
}

// Hook for last update indicator
export function useHeartbeatStatus(lastUpdate: Date | null) {
    const [status, setStatus] = useState<'live' | 'stale' | 'disconnected'>('disconnected');

    useEffect(() => {
        if (!lastUpdate) {
            setStatus('disconnected');
            return;
        }

        const checkStatus = () => {
            const now = new Date();
            const diff = now.getTime() - lastUpdate.getTime();

            if (diff < 10000) {
                setStatus('live');
            } else if (diff < 30000) {
                setStatus('stale');
            } else {
                setStatus('disconnected');
            }
        };

        checkStatus();
        const interval = setInterval(checkStatus, 1000);
        return () => clearInterval(interval);
    }, [lastUpdate]);

    return status;
}
