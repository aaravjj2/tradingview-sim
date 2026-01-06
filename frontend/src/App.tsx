import { useState, useCallback } from 'react';
import CandleChart from './components/CandleChart';
import Supergraph from './components/Supergraph';
import GreeksPanel from './components/GreeksPanel';
import Backtester from './components/Backtester';
import TradeJournal from './components/TradeJournal';
import TradingBot from './components/TradingBot';
import LiveModeToggle from './components/LiveModeToggle';
import { useMarketData, useGreeks, useHeartbeatStatus } from './hooks/useMarketData';

// Demo legs for testing
const DEMO_LEGS = [
  { option_type: 'call', position: 'long', strike: 500, premium: 7.50, quantity: 1, expiration_days: 30, iv: 0.25 }
];

function App() {
  const [ticker, setTicker] = useState('SPY');
  const [paperMode, setPaperMode] = useState(true);
  const [hoveredPrice, setHoveredPrice] = useState<number | undefined>();
  const [hoveredTimestamp, setHoveredTimestamp] = useState<string | undefined>();
  const [showBacktester, setShowBacktester] = useState(false);
  const [showJournal, setShowJournal] = useState(false);
  const [showBot, setShowBot] = useState(false);

  const { price, candles, loading, error, lastUpdate, refetch } = useMarketData(ticker);
  const greeks = useGreeks(ticker, price?.price ?? 500, DEMO_LEGS);
  const heartbeatStatus = useHeartbeatStatus(lastUpdate);

  // Cursor sync handler
  const handleCandleHover = useCallback((price: number, timestamp: string) => {
    setHoveredPrice(price);
    setHoveredTimestamp(timestamp);
  }, []);

  // Calculate breakevens dynamically
  const breakevens = DEMO_LEGS.map(leg => {
    if (leg.option_type === 'call') {
      return leg.strike + leg.premium;
    } else if (leg.option_type === 'put') {
      return leg.strike - leg.premium;
    }
    return leg.strike;
  });

  return (
    <div className="min-h-screen bg-[#0f1117] text-white">
      {/* Header */}
      <header className="bg-gradient-to-r from-[#1a1f2e] to-[#252b3b] border-b border-white/10 px-6 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              📈 Supergraph Pro
            </h1>
            <p className="text-sm text-gray-400 mt-1">
              Professional Options Visualizer • React + FastAPI
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Ticker Input */}
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="bg-[#1a1f2e] border border-white/20 rounded-lg px-3 py-2 text-sm w-20 focus:outline-none focus:border-blue-500"
              placeholder="Ticker"
            />

            {/* Price Display with Heartbeat */}
            {price && (
              <div className="bg-[#1a1f2e] rounded-lg px-3 py-2 flex items-center gap-2">
                <span className={`inline-block w-2 h-2 rounded-full ${heartbeatStatus === 'live' ? 'bg-green-500 animate-pulse' :
                    heartbeatStatus === 'stale' ? 'bg-yellow-500' : 'bg-red-500'
                  }`} />
                <span className="text-white font-mono font-bold text-sm">${price.price.toFixed(2)}</span>
              </div>
            )}

            {/* Refresh Button */}
            <button
              onClick={() => refetch()}
              className="bg-[#1a1f2e] border border-white/20 rounded-lg p-2 text-sm hover:border-blue-500 transition"
              title="Refresh Data"
            >
              🔄
            </button>

            {/* Bot Button */}
            <button
              onClick={() => setShowBot(true)}
              className="bg-gradient-to-r from-purple-600 to-indigo-600 rounded-lg px-3 py-2 text-sm font-semibold hover:opacity-90 transition"
            >
              🤖 Bot
            </button>

            {/* Backtester Button */}
            <button
              onClick={() => setShowBacktester(true)}
              className="bg-[#1a1f2e] border border-white/20 rounded-lg px-3 py-2 text-sm hover:border-blue-500 transition"
            >
              📊 Backtest
            </button>

            {/* Journal Button */}
            <button
              onClick={() => setShowJournal(true)}
              className="bg-[#1a1f2e] border border-white/20 rounded-lg px-3 py-2 text-sm hover:border-green-500 transition"
            >
              📓 Journal
            </button>

            {/* Paper/Live Toggle */}
            <LiveModeToggle
              paperMode={paperMode}
              onToggle={setPaperMode}
            />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6">
        {/* Live Mode Warning */}
        {!paperMode && (
          <div className="mb-6 bg-red-900/50 border border-red-500 rounded-lg p-4 flex items-center gap-3">
            <span className="text-2xl">⚠️</span>
            <div>
              <p className="font-semibold text-red-300">LIVE TRADING MODE ACTIVE</p>
              <p className="text-sm text-red-200/70">All orders will be executed with real money on your connected broker account.</p>
            </div>
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center h-96">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : error ? (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 text-center">
            {error}
          </div>
        ) : (
          <>
            {/* Chart Grid - Split Layout with Synced Cursors */}
            <div className="grid grid-cols-2 gap-6 mb-6">
              {/* Candle Chart */}
              <CandleChart
                ticker={ticker}
                data={candles}
                breakevens={breakevens}
                onHover={handleCandleHover}
                hoveredTimestamp={hoveredTimestamp}
              />

              {/* Supergraph with cursor sync */}
              <Supergraph
                currentPrice={price?.price ?? 500}
                legs={DEMO_LEGS}
                hoveredPrice={hoveredPrice}
              />
            </div>

            {/* Greeks Panel with Heartbeat */}
            <GreeksPanel
              delta={greeks.delta}
              gamma={greeks.gamma}
              theta={greeks.theta}
              vega={greeks.vega}
              netDelta={greeks.delta * 100}
              heartbeatStatus={heartbeatStatus}
            />

            {/* Strategy Info */}
            <div className="mt-6 bg-[#1a1f2e] rounded-xl p-4">
              <h3 className="text-lg font-semibold mb-3">📋 Strategy: Long Call</h3>
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-400 border-b border-white/10">
                    <th className="text-left py-2">Leg</th>
                    <th className="text-left py-2">Type</th>
                    <th className="text-left py-2">Strike</th>
                    <th className="text-left py-2">Premium</th>
                    <th className="text-left py-2">Qty</th>
                    <th className="text-left py-2">Breakeven</th>
                  </tr>
                </thead>
                <tbody>
                  {DEMO_LEGS.map((leg, i) => (
                    <tr key={i} className="border-b border-white/5">
                      <td className="py-2">{i + 1}</td>
                      <td className="py-2 capitalize">{leg.position} {leg.option_type}</td>
                      <td className="py-2">${leg.strike}</td>
                      <td className="py-2">${leg.premium.toFixed(2)}</td>
                      <td className="py-2">{leg.quantity}</td>
                      <td className="py-2 text-orange-400">${breakevens[i].toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="text-center py-4 text-gray-500 text-sm">
        Supergraph Pro • {paperMode ? 'Paper Trading' : '🔴 LIVE Trading'} • React + FastAPI
      </footer>

      {/* Modals */}
      {showBacktester && (
        <Backtester ticker={ticker} onClose={() => setShowBacktester(false)} />
      )}
      {showJournal && (
        <TradeJournal onClose={() => setShowJournal(false)} />
      )}
      {showBot && (
        <TradingBot
          ticker={ticker}
          currentPrice={price?.price ?? 500}
          paperMode={paperMode}
          onClose={() => setShowBot(false)}
        />
      )}
    </div>
  );
}

export default App;
