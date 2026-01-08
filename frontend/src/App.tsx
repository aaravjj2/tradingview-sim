import { useState, useCallback, useEffect } from 'react';
import CandleChart from './components/CandleChart';
import Supergraph from './components/Supergraph';
import GreeksPanel from './components/GreeksPanel';
import Backtester from './components/Backtester';
import TradeJournal from './components/TradeJournal';
import TradingBot from './components/TradingBot';
import LiveModeToggle from './components/LiveModeToggle';
import IVSmile from './components/IVSmile';
import HVvsIV from './components/HVvsIV';
import MaxPainIndicator from './components/MaxPainIndicator';
import MonteCarloChart from './components/MonteCarloChart';
import KellyCalculator from './components/KellyCalculator';
import PanicButton from './components/PanicButton';
import LatencyMonitor from './components/LatencyMonitor';
import QuickStart from './components/QuickStart';
import OpenInterestOverlay from './components/OpenInterestOverlay';
import GEXProfile from './components/GEXProfile';
import StrategyComparison from './components/StrategyComparison';
import IVRVCone from './components/IVRVCone';
import AIStrategyRecommender from './components/AIStrategyRecommender';
import DraggableSupergraph from './components/DraggableSupergraph';
import HistoricalPayoffReplay from './components/HistoricalPayoffReplay';
import CommandPalette from './components/CommandPalette';
// Phase 8-13 Components
import UncertaintyCone from './components/UncertaintyCone';
import StrategyNLP from './components/StrategyNLP';
import StrategyLegos from './components/StrategyLegos';
import MarginSimulator from './components/MarginSimulator';
import WhaleAlerts from './components/WhaleAlerts';
import PanicSimulator from './components/PanicSimulator';
// Phase 16-18: Manager's Suite Components
import ActivityFeed from './components/ActivityFeed';
import Dashboard from './components/Dashboard';
import StrategyCards from './components/StrategyCards';
import VolSurface3D from './components/VolSurface3D';
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
  const [showKelly, setShowKelly] = useState(false);
  const [showPanic, setShowPanic] = useState(false);
  const [activeTab, setActiveTab] = useState<'charts' | 'analytics'>('charts');
  const [showCommandPalette, setShowCommandPalette] = useState(false);
  const [focusMode, setFocusMode] = useState(false);
  const [analyticsTab, setAnalyticsTab] = useState<'market_intel' | 'strategy_lab' | 'risk_sim'>('market_intel');
  const [showQuickStart, setShowQuickStart] = useState(() => {
    return localStorage.getItem('supergraph-quickstart-dismissed') !== 'true';
  });

  const dismissQuickStart = () => {
    setShowQuickStart(false);
    localStorage.setItem('supergraph-quickstart-dismissed', 'true');
  };

  // Keyboard handler for Command Palette (Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setShowCommandPalette(prev => !prev);
      }
      // Focus mode toggle with F key (when not in input)
      if (e.key === 'f' && !['INPUT', 'TEXTAREA'].includes((e.target as HTMLElement).tagName)) {
        // Don't toggle if user is typing
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const { price, candles, loading, error, lastUpdate, latency, refreshCount, refetch } = useMarketData(ticker);
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
                <span className="text-white font-mono font-bold text-sm">${(price.price ?? 0).toFixed(2)}</span>
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

            {/* Tab Toggle */}
            <div className="flex bg-[#1a1f2e] rounded-lg p-1">
              <button
                onClick={() => setActiveTab('charts')}
                className={`px-3 py-1 rounded text-sm ${activeTab === 'charts' ? 'bg-blue-600 text-white' : 'text-gray-400'}`}
              >
                📊 Charts
              </button>
              <button
                onClick={() => setActiveTab('analytics')}
                className={`px-3 py-1 rounded text-sm ${activeTab === 'analytics' ? 'bg-purple-600 text-white' : 'text-gray-400'}`}
              >
                🔬 Analytics
              </button>
            </div>

            {/* Kelly Button */}
            <button
              onClick={() => setShowKelly(true)}
              className="bg-[#1a1f2e] border border-white/20 rounded-lg px-3 py-2 text-sm hover:border-yellow-500 transition"
              title="Kelly Criterion"
            >
              🎯 Kelly
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

            {/* Panic Button */}
            {!paperMode && (
              <button
                onClick={() => setShowPanic(true)}
                className="bg-red-600 hover:bg-red-500 rounded-lg px-3 py-2 text-sm font-bold transition animate-pulse"
              >
                🚨 PANIC
              </button>
            )}

            {/* Paper/Live Toggle */}
            <LiveModeToggle
              paperMode={paperMode}
              onToggle={setPaperMode}
            />
          </div>
        </div>

        {/* Latency Monitor Bar */}
        <div className="mt-2 flex justify-end">
          <LatencyMonitor
            latency={latency}
            refreshCount={refreshCount}
            lastUpdate={lastUpdate}
          />
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

        {/* Quick Start Guide for new users */}
        {showQuickStart && (
          <QuickStart onDismiss={dismissQuickStart} />
        )}

        {loading ? (
          <div className="flex items-center justify-center h-96">
            <div className="text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500 mx-auto mb-4"></div>
              <p className="text-gray-400">Loading market data...</p>
            </div>
          </div>
        ) : error ? (
          <div className="bg-red-900/50 border border-red-500 rounded-lg p-6 text-center">
            <span className="text-3xl mb-2 block">⚠️</span>
            <p className="font-semibold text-red-300">Failed to Load Data</p>
            <p className="text-sm text-red-200/70 mt-2">{error}</p>
            <button
              onClick={() => refetch()}
              className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-sm"
            >
              🔄 Retry
            </button>
          </div>
        ) : (
          <>
            {activeTab === 'charts' ? (
              <>
                {/* Charts Tab - Main Layout */}
                <div className="grid grid-cols-2 gap-6 mb-6">
                  {/* Candle Chart */}
                  <CandleChart
                    ticker={ticker}
                    data={candles}
                    currentPrice={price?.price}
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

                {/* Greeks Panel with Second-Order Greeks */}
                <GreeksPanel
                  delta={greeks.delta}
                  gamma={greeks.gamma}
                  theta={greeks.theta}
                  vega={greeks.vega}
                  vanna={0.0012}
                  charm={-0.0034}
                  betaWeightedDelta={greeks.delta * 100 * 1.2}
                  netDelta={greeks.delta * 100}
                  heartbeatStatus={heartbeatStatus}
                />

                {/* Strategy Comparison & IV/RV Cone */}
                <div className="grid grid-cols-2 gap-6 mt-6">
                  <StrategyComparison currentPrice={price?.price ?? 500} />
                  <IVRVCone ticker={ticker} currentPrice={price?.price ?? 500} />
                </div>

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
            ) : (
              /* Analytics Tab - New Components */
              <div className="flex flex-col h-full">
                {/* Analytics Sub-Tabs */}
                <div className="flex space-x-1 bg-[#0f1117] p-1 rounded-lg mb-4 w-fit">
                  {(['market_intel', 'strategy_lab', 'risk_sim'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setAnalyticsTab(tab)}
                      className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${analyticsTab === tab
                        ? 'bg-[#2a2e39] text-white shadow-sm'
                        : 'text-gray-400 hover:text-white hover:bg-[#1a1f2e]'
                        }`}
                    >
                      {tab === 'market_intel' && '📊 Market Intel'}
                      {tab === 'strategy_lab' && '🧪 Strategy Lab'}
                      {tab === 'risk_sim' && '⚡ Risk & Sim'}
                    </button>
                  ))}
                </div>

                {/* Market Intel Tab */}
                {analyticsTab === 'market_intel' && (
                  <>
                    <div className="grid grid-cols-3 gap-6 mb-6">
                      <IVSmile ticker={ticker} />
                      <HVvsIV ticker={ticker} />
                      <MaxPainIndicator ticker={ticker} currentPrice={price?.price ?? 500} />
                    </div>
                    <div className="grid grid-cols-2 gap-6 mb-6">
                      <OpenInterestOverlay ticker={ticker} currentPrice={price?.price ?? 500} />
                      <GEXProfile ticker={ticker} currentPrice={price?.price ?? 500} />
                    </div>
                    <div className="mt-6">
                      <WhaleAlerts tickers={['SPY', 'QQQ', ticker, 'NVDA', 'TSLA']} />
                    </div>
                    {/* Glass Cockpit Dashboard */}
                    <div className="mt-6">
                      <Dashboard ticker={ticker} />
                    </div>
                    {/* AutoPilot Activity Feed */}
                    <div className="mt-6">
                      <ActivityFeed />
                    </div>
                  </>
                )}

                {/* Strategy Lab Tab */}
                {analyticsTab === 'strategy_lab' && (
                  <>
                    <div className="mb-6">
                      <AIStrategyRecommender ticker={ticker} currentPrice={price?.price ?? 500} />
                    </div>
                    <div className="grid grid-cols-2 gap-6 mb-6">
                      <DraggableSupergraph currentPrice={price?.price ?? 500} legs={DEMO_LEGS as any} />
                      <HistoricalPayoffReplay ticker={ticker} currentPrice={price?.price ?? 500} legs={DEMO_LEGS as any} />
                    </div>
                    <div className="grid grid-cols-2 gap-6 mt-6">
                      <StrategyNLP ticker={ticker} currentPrice={price?.price ?? 500} />
                      <StrategyLegos ticker={ticker} currentPrice={price?.price ?? 500} />
                    </div>
                  </>
                )}

                {/* Risk & Sim Tab */}
                {analyticsTab === 'risk_sim' && (
                  <>
                    <div className="grid grid-cols-2 gap-6 mb-6">
                      <UncertaintyCone ticker={ticker} currentPrice={price?.price ?? 500} days={30} />
                      <MonteCarloChart
                        ticker={ticker}
                        currentPrice={price?.price ?? 500}
                        iv={DEMO_LEGS[0].iv}
                        legs={DEMO_LEGS}
                        daysToExpiry={DEMO_LEGS[0].expiration_days}
                      />
                    </div>
                    <div className="mb-6">
                      <GreeksPanel
                        delta={greeks.delta}
                        gamma={greeks.gamma}
                        theta={greeks.theta}
                        vega={greeks.vega}
                        vanna={0.0012}
                        charm={-0.0034}
                        betaWeightedDelta={greeks.delta * 100 * 1.2}
                        netDelta={greeks.delta * 100}
                        heartbeatStatus={heartbeatStatus}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-6 mt-6">
                      <MarginSimulator ticker={ticker} currentPrice={price?.price ?? 500} />
                      <PanicSimulator currentPrice={price?.price ?? 500} portfolioValue={100000} />
                    </div>
                    {/* Phase 17-19 Components */}
                    <div className="mt-6">
                      <StrategyCards />
                    </div>
                    <div className="mt-6">
                      <VolSurface3D ticker={ticker} currentPrice={price?.price ?? 540} />
                    </div>
                  </>
                )}
              </div>
            )}
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
      {showKelly && (
        <KellyCalculator onClose={() => setShowKelly(false)} />
      )}
      {showPanic && (
        <PanicButton onClose={() => setShowPanic(false)} />
      )}

      {/* Command Palette (Ctrl+K) */}
      <CommandPalette
        isOpen={showCommandPalette}
        onClose={() => setShowCommandPalette(false)}
        onTicker={(t) => setTicker(t)}
        onTogglePaperMode={() => setPaperMode(!paperMode)}
        onOpenBot={() => setShowBot(true)}
        onOpenBacktest={() => setShowBacktester(true)}
        onOpenJournal={() => setShowJournal(true)}
        onCloseAll={() => setShowPanic(true)}
        onToggleTab={(tab) => setActiveTab(tab)}
        onToggleFocusMode={() => setFocusMode(!focusMode)}
      />
    </div>
  );
}

export default App;

