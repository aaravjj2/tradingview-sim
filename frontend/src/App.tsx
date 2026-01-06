import { useState, useEffect } from 'react';
import CandleChart from './components/CandleChart';
import Supergraph from './components/Supergraph';
import GreeksPanel from './components/GreeksPanel';
import { useMarketData, useGreeks } from './hooks/useMarketData';

// Mock legs for demo
const DEMO_LEGS = [
  { option_type: 'call', position: 'long', strike: 500, premium: 7.50, quantity: 1 }
];

function App() {
  const [ticker, setTicker] = useState('SPY');
  const [paperMode, setPaperMode] = useState(true);
  const [hoveredPrice, setHoveredPrice] = useState<number | undefined>();

  const { price, candles, loading, error } = useMarketData(ticker);
  const greeks = useGreeks(ticker, price?.price ?? 500);

  const handleCandleHover = (price: number, timestamp: string) => {
    setHoveredPrice(price);
  };

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

          <div className="flex items-center gap-4">
            {/* Ticker Input */}
            <input
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
              className="bg-[#1a1f2e] border border-white/20 rounded-lg px-3 py-2 text-sm w-24 focus:outline-none focus:border-blue-500"
              placeholder="Ticker"
            />

            {/* Price Display */}
            {price && (
              <div className="bg-[#1a1f2e] rounded-lg px-4 py-2">
                <span className="text-gray-400 text-sm">Price: </span>
                <span className="text-white font-mono font-bold">${price.price.toFixed(2)}</span>
              </div>
            )}

            {/* Paper/Live Toggle */}
            <button
              onClick={() => setPaperMode(!paperMode)}
              className={`px-4 py-2 rounded-full text-sm font-semibold transition-all ${paperMode
                  ? 'bg-gradient-to-r from-yellow-500 to-orange-500 text-black'
                  : 'bg-gradient-to-r from-green-500 to-emerald-500 text-white animate-pulse'
                }`}
            >
              {paperMode ? '📝 PAPER' : '🔴 LIVE'}
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="p-6">
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
            {/* Chart Grid - Split Layout */}
            <div className="grid grid-cols-2 gap-6 mb-6">
              {/* Candle Chart */}
              <CandleChart
                ticker={ticker}
                data={candles}
                breakevens={[Math.round((price?.price ?? 500) * 0.97)]}
                onHover={handleCandleHover}
              />

              {/* Supergraph */}
              <Supergraph
                currentPrice={price?.price ?? 500}
                legs={DEMO_LEGS}
                hoveredPrice={hoveredPrice}
              />
            </div>

            {/* Greeks Panel */}
            <GreeksPanel
              delta={greeks.delta}
              gamma={greeks.gamma}
              theta={greeks.theta}
              vega={greeks.vega}
              netDelta={greeks.delta * 100}
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
        Supergraph Pro • {paperMode ? 'Paper Trading' : 'Live Trading'} • React + FastAPI
      </footer>
    </div>
  );
}

export default App;
