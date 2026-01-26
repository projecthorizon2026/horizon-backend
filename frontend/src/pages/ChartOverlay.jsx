import React, { useEffect, useState } from 'react';
import TradingViewGEX from '../components/TradingViewGEX';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080';

/**
 * Full-page chart with GEX overlay
 * Access at /chart route
 */
const ChartOverlay = () => {
  const [gexData, setGexData] = useState(null);
  const [symbol, setSymbol] = useState('GC');
  const [timeframe, setTimeframe] = useState('5m');

  useEffect(() => {
    const fetchGEXData = async () => {
      try {
        const response = await fetch(API_BASE);
        const data = await response.json();
        setGexData(data);
      } catch (error) {
        console.error('Error fetching GEX data:', error);
      }
    };

    fetchGEXData();
    const interval = setInterval(fetchGEXData, 500);
    return () => clearInterval(interval);
  }, []);

  const timeframes = ['1m', '5m', '15m', '1h', '4h', '1D'];

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-white">
      {/* Top Bar */}
      <div className="flex items-center justify-between px-6 py-3 bg-[#12122a] border-b border-gray-800">
        <div className="flex items-center gap-6">
          <h1 className="text-xl font-bold text-cyan-400">
            PROJECT HORIZON
          </h1>
          <span className="text-gray-500">|</span>
          <span className="text-gray-300">Live GEX Chart</span>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-4">
          {/* Symbol Selector */}
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="bg-gray-800 text-white px-3 py-1.5 rounded border border-gray-700 focus:outline-none focus:border-cyan-500"
          >
            <option value="GC">Gold (GC)</option>
            <option value="ES">S&P 500 (ES)</option>
            <option value="NQ">Nasdaq (NQ)</option>
            <option value="SPX">SPX</option>
          </select>

          {/* Timeframe Selector */}
          <div className="flex gap-1">
            {timeframes.map((tf) => (
              <button
                key={tf}
                onClick={() => setTimeframe(tf)}
                className={`px-3 py-1.5 text-sm rounded transition-colors ${
                  timeframe === tf
                    ? 'bg-cyan-500 text-white'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
                }`}
              >
                {tf}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex">
        {/* Chart Area */}
        <div className="flex-1 p-4">
          <TradingViewGEX symbol={symbol} interval={timeframe} height={700} />
        </div>

        {/* Right Sidebar - GEX Panel */}
        <div className="w-80 bg-[#12122a] border-l border-gray-800 p-4">
          <h2 className="text-lg font-bold text-white mb-4">GEX Analysis</h2>

          {/* Gamma Regime */}
          {gexData?.gamma_regime && (
            <div className={`p-4 rounded-lg mb-4 ${
              gexData.gamma_regime === 'POSITIVE'
                ? 'bg-green-500/10 border border-green-500/30'
                : 'bg-red-500/10 border border-red-500/30'
            }`}>
              <div className="text-sm text-gray-400 mb-1">Gamma Regime</div>
              <div className={`text-2xl font-bold ${
                gexData.gamma_regime === 'POSITIVE' ? 'text-green-400' : 'text-red-400'
              }`}>
                {gexData.gamma_regime}
              </div>
              <div className="text-xs text-gray-500 mt-2">
                {gexData.gamma_regime === 'POSITIVE'
                  ? 'Dealers sell rallies, buy dips. Expect range-bound action.'
                  : 'Dealers buy rallies, sell dips. Expect trending moves.'}
              </div>
            </div>
          )}

          {/* Key Levels */}
          <div className="space-y-3">
            <div className="text-sm font-semibold text-gray-400 mb-2">KEY LEVELS</div>

            {/* Call Wall */}
            <LevelCard
              label="CALL WALL"
              emoji="🛡️"
              price={gexData?.call_wall}
              color="red"
              description="Major resistance - dealer short gamma"
            />

            {/* Gamma Flip */}
            <LevelCard
              label="GAMMA FLIP"
              emoji="⚡"
              price={gexData?.gamma_flip || gexData?.zero_gamma}
              color="yellow"
              description="Zero gamma pivot point"
            />

            {/* HVL */}
            <LevelCard
              label="HVL"
              emoji="📊"
              price={gexData?.hvl}
              color="purple"
              description="High volume level - price magnet"
            />

            {/* Put Wall */}
            <LevelCard
              label="PUT WALL"
              emoji="🛡️"
              price={gexData?.put_wall}
              color="green"
              description="Major support - dealer long gamma"
            />

            {/* Max Pain */}
            <LevelCard
              label="MAX PAIN"
              emoji="🎯"
              price={gexData?.max_pain}
              color="orange"
              description="Options expiry target"
            />
          </div>

          {/* Net GEX */}
          {gexData?.total_gex !== undefined && (
            <div className="mt-6 p-4 bg-gray-800/50 rounded-lg">
              <div className="text-sm text-gray-400 mb-1">Net GEX Exposure</div>
              <div className={`text-3xl font-bold font-mono ${
                gexData.total_gex >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {gexData.total_gex >= 0 ? '+' : ''}{gexData.total_gex.toFixed(3)}B
              </div>
            </div>
          )}

          {/* Last Update */}
          <div className="mt-4 text-xs text-gray-600 text-center">
            Data refreshes every 500ms
          </div>
        </div>
      </div>
    </div>
  );
};

// Level Card Component
const LevelCard = ({ label, emoji, price, color, description }) => {
  const colorClasses = {
    red: 'border-red-500/30 bg-red-500/5',
    green: 'border-green-500/30 bg-green-500/5',
    yellow: 'border-yellow-500/30 bg-yellow-500/5',
    purple: 'border-purple-500/30 bg-purple-500/5',
    orange: 'border-orange-500/30 bg-orange-500/5',
  };

  const textColors = {
    red: 'text-red-400',
    green: 'text-green-400',
    yellow: 'text-yellow-400',
    purple: 'text-purple-400',
    orange: 'text-orange-400',
  };

  return (
    <div className={`p-3 rounded-lg border ${colorClasses[color]}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span>{emoji}</span>
          <span className={`text-sm font-semibold ${textColors[color]}`}>{label}</span>
        </div>
        <span className="text-white font-mono font-bold">
          {price ? `$${price.toFixed(0)}` : '-'}
        </span>
      </div>
      <div className="text-xs text-gray-500 mt-1">{description}</div>
    </div>
  );
};

export default ChartOverlay;
