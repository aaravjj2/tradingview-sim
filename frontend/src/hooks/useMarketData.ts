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

export function useMarketData(ticker: string) {
    const [price, setPrice] = useState<PriceData | null>(null);
    const [candles, setCandles] = useState<CandleData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Fetch current price
    const fetchPrice = useCallback(async () => {
        try {
            const response = await axios.get(`/api/market/price/${ticker}`);
            setPrice(response.data);
        } catch (err) {
            console.error('Error fetching price:', err);
        }
    }, [ticker]);

    // Fetch candles
    const fetchCandles = useCallback(async () => {
        try {
            setLoading(true);
            const response = await axios.get(`/api/market/candles/${ticker}?limit=100`);
            setCandles(response.data);
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

    // Heartbeat polling (every 5 seconds)
    useEffect(() => {
        const interval = setInterval(fetchPrice, 5000);
        return () => clearInterval(interval);
    }, [fetchPrice]);

    return { price, candles, loading, error, refetch: fetchCandles };
}

export function useGreeks(ticker: string, currentPrice: number) {
    const [greeks, setGreeks] = useState({
        delta: 0,
        gamma: 0,
        theta: 0,
        vega: 0,
    });

    // Placeholder - would be calculated from strategy
    useEffect(() => {
        // Mock greeks calculation
        setGreeks({
            delta: 0.55,
            gamma: 0.023,
            theta: -15.50,
            vega: 22.30,
        });
    }, [ticker, currentPrice]);

    return greeks;
}
