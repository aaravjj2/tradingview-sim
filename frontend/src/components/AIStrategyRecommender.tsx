import { useState, useEffect } from 'react';
import axios from 'axios';

interface Strategy {
    name: string;
    score: number;
    grade: string;
    reasons: string[];
    warnings: string[];
    best_for: string;
}

interface Recommendation {
    ticker: string;
    current_price: number;
    market_conditions: {
        trend: string;
        iv_level: string;
        vol_premium: string;
        regime: string;
    };
    top_strategies: Strategy[];
    best_pick: {
        strategy: string;
        score: number;
        grade: string;
        reasoning: string[];
    };
}

interface Props {
    ticker: string;
    currentPrice: number;
}

export default function AIStrategyRecommender({ ticker, currentPrice }: Props) {
    const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
    const [loading, setLoading] = useState(false);
    const [ivRank, setIvRank] = useState(50);
    const [daysToExpiry, setDaysToExpiry] = useState(30);
    const [riskTolerance, setRiskTolerance] = useState<'conservative' | 'moderate' | 'aggressive'>('moderate');

    const fetchRecommendation = async () => {
        try {
            setLoading(true);
            const response = await axios.get(`/api/strategy/recommend/${ticker}`, {
                params: {
                    current_price: currentPrice,
                    iv_rank: ivRank,
                    days_to_expiry: daysToExpiry,
                    risk_tolerance: riskTolerance
                }
            });
            setRecommendation(response.data);
        } catch (err) {
            console.error('Error fetching recommendation:', err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        if (ticker && currentPrice > 0) {
            fetchRecommendation();
        }
    }, [ticker, currentPrice, ivRank, daysToExpiry, riskTolerance]);

    const gradeColors: Record<string, string> = {
        'A': 'bg-green-500 text-white',
        'B': 'bg-blue-500 text-white',
        'C': 'bg-yellow-500 text-black',
        'D': 'bg-orange-500 text-white',
        'F': 'bg-red-500 text-white'
    };

    const trendIcons: Record<string, string> = {
        'strong_bullish': '🚀',
        'bullish': '📈',
        'neutral': '➡️',
        'bearish': '📉',
        'strong_bearish': '💥'
    };

    return (
        <div className="bg-[#1a1f2e] rounded-xl p-4">
            <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                    🤖 AI Strategy Recommender
                </h3>
                <button
                    onClick={fetchRecommendation}
                    disabled={loading}
                    className="text-xs px-3 py-1 bg-purple-600 hover:bg-purple-500 rounded text-white disabled:opacity-50"
                >
                    {loading ? '⏳' : '🔄 Refresh'}
                </button>
            </div>

            {/* Input Controls */}
            <div className="grid grid-cols-3 gap-3 mb-4">
                <div>
                    <label className="text-xs text-gray-400 block mb-1">IV Rank (0-100)</label>
                    <input
                        type="range"
                        min="0"
                        max="100"
                        value={ivRank}
                        onChange={(e) => setIvRank(parseInt(e.target.value))}
                        className="w-full"
                    />
                    <div className="text-center text-xs text-white">{ivRank}%</div>
                </div>
                <div>
                    <label className="text-xs text-gray-400 block mb-1">Days to Expiry</label>
                    <select
                        value={daysToExpiry}
                        onChange={(e) => setDaysToExpiry(parseInt(e.target.value))}
                        className="w-full bg-[#0f1117] text-white text-sm rounded px-2 py-1 border border-white/20"
                    >
                        <option value={7}>7 days</option>
                        <option value={14}>14 days</option>
                        <option value={30}>30 days</option>
                        <option value={45}>45 days</option>
                        <option value={60}>60 days</option>
                    </select>
                </div>
                <div>
                    <label className="text-xs text-gray-400 block mb-1">Risk Tolerance</label>
                    <select
                        value={riskTolerance}
                        onChange={(e) => setRiskTolerance(e.target.value as typeof riskTolerance)}
                        className="w-full bg-[#0f1117] text-white text-sm rounded px-2 py-1 border border-white/20"
                    >
                        <option value="conservative">Conservative</option>
                        <option value="moderate">Moderate</option>
                        <option value="aggressive">Aggressive</option>
                    </select>
                </div>
            </div>

            {recommendation && (
                <>
                    {/* Market Conditions */}
                    <div className="grid grid-cols-4 gap-2 mb-4 text-xs">
                        <div className="bg-[#0f1117] rounded p-2 text-center">
                            <span className="text-gray-400 block">Trend</span>
                            <span className="text-white">
                                {trendIcons[recommendation.market_conditions.trend]} {recommendation.market_conditions.trend.replace('_', ' ')}
                            </span>
                        </div>
                        <div className="bg-[#0f1117] rounded p-2 text-center">
                            <span className="text-gray-400 block">IV Level</span>
                            <span className={`${recommendation.market_conditions.iv_level === 'high' ? 'text-red-400' :
                                    recommendation.market_conditions.iv_level === 'low' ? 'text-green-400' : 'text-yellow-400'
                                }`}>{recommendation.market_conditions.iv_level}</span>
                        </div>
                        <div className="bg-[#0f1117] rounded p-2 text-center">
                            <span className="text-gray-400 block">Vol Premium</span>
                            <span className="text-white">{recommendation.market_conditions.vol_premium}</span>
                        </div>
                        <div className="bg-[#0f1117] rounded p-2 text-center">
                            <span className="text-gray-400 block">Regime</span>
                            <span className="text-white">{recommendation.market_conditions.regime}</span>
                        </div>
                    </div>

                    {/* Best Pick */}
                    <div className="bg-gradient-to-r from-purple-900/30 to-blue-900/30 rounded-lg p-3 mb-4 border border-purple-500/30">
                        <div className="flex justify-between items-center">
                            <div>
                                <span className="text-xs text-purple-400">🏆 TOP RECOMMENDATION</span>
                                <h4 className="text-xl font-bold text-white">{recommendation.best_pick.strategy}</h4>
                            </div>
                            <div className={`text-3xl font-bold px-3 py-1 rounded ${gradeColors[recommendation.best_pick.grade]}`}>
                                {recommendation.best_pick.grade}
                            </div>
                        </div>
                        <div className="mt-2 text-xs text-gray-300">
                            {recommendation.best_pick.reasoning.map((r, i) => (
                                <div key={i}>{r}</div>
                            ))}
                        </div>
                    </div>

                    {/* All Strategies */}
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                        <div className="text-xs text-gray-400 mb-1">All Strategies Ranked:</div>
                        {recommendation.top_strategies.map((strategy, i) => (
                            <div
                                key={i}
                                className={`flex items-center justify-between p-2 rounded ${i === 0 ? 'bg-purple-900/20 border border-purple-500/30' : 'bg-[#0f1117]'
                                    }`}
                            >
                                <div className="flex items-center gap-2">
                                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${gradeColors[strategy.grade]}`}>
                                        {strategy.grade}
                                    </span>
                                    <span className="text-white text-sm">{strategy.name}</span>
                                </div>
                                <div className="flex items-center gap-2">
                                    <div className="w-16 h-2 bg-gray-700 rounded overflow-hidden">
                                        <div
                                            className="h-full bg-gradient-to-r from-purple-500 to-blue-500"
                                            style={{ width: `${strategy.score}%` }}
                                        />
                                    </div>
                                    <span className="text-xs text-gray-400 w-8">{strategy.score}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            )}

            {loading && (
                <div className="text-center py-8 text-gray-400">
                    <div className="animate-spin text-2xl mb-2">⚙️</div>
                    Analyzing market conditions...
                </div>
            )}
        </div>
    );
}
