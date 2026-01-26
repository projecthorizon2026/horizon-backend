import React, { useEffect, useRef, useState } from 'react';
import { createChart } from 'lightweight-charts';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8080';

/**
 * TradingView-style chart with live GEX level overlays
 * Fetches GEX data from Project Horizon API and displays on chart
 */
const TradingViewGEX = ({ symbol = 'GC', interval = '5m', height = 600 }) => {
  const chartContainerRef = useRef(null);
  const chartRef = useRef(null);
  const candleSeriesRef = useRef(null);
  const gexLinesRef = useRef({});
  const [gexData, setGexData] = useState(null);
  const [lastPrice, setLastPrice] = useState(null);

  // GEX level colors
  const GEX_COLORS = {
    call_wall: { color: '#ef4444', label: 'CALL WALL', dash: false },
    put_wall: { color: '#22c55e', label: 'PUT WALL', dash: false },
    gamma_flip: { color: '#facc15', label: 'GAMMA FLIP', dash: true },
    hvl: { color: '#a855f7', label: 'HVL', dash: true },
    max_pain: { color: '#f97316', label: 'MAX PAIN', dash: true },
  };

  // Initialize chart
  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { type: 'solid', color: '#0f0f23' },
        textColor: '#d1d5db',
      },
      grid: {
        vertLines: { color: '#1f2937' },
        horzLines: { color: '#1f2937' },
      },
      crosshair: {
        mode: 0,
        vertLine: { color: '#6b7280', width: 1, style: 2 },
        horzLine: { color: '#6b7280', width: 1, style: 2 },
      },
      rightPriceScale: {
        borderColor: '#374151',
        scaleMargins: { top: 0.1, bottom: 0.1 },
      },
      timeScale: {
        borderColor: '#374151',
        timeVisible: true,
        secondsVisible: false,
      },
    });

    // Add candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#22c55e',
      downColor: '#ef4444',
      borderUpColor: '#22c55e',
      borderDownColor: '#ef4444',
      wickUpColor: '#22c55e',
      wickDownColor: '#ef4444',
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current && chartRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [height]);

  // Fetch GEX data from API
  useEffect(() => {
    const fetchGEXData = async () => {
      try {
        const response = await fetch(API_BASE);
        const data = await response.json();
        setGexData(data);
        if (data.price || data.last_price || data.current_price) {
          setLastPrice(data.price || data.last_price || data.current_price);
        }
      } catch (error) {
        console.error('Error fetching GEX data:', error);
      }
    };

    fetchGEXData();
    const interval = setInterval(fetchGEXData, 500); // Poll every 500ms

    return () => clearInterval(interval);
  }, []);

  // Update GEX price lines
  useEffect(() => {
    if (!chartRef.current || !candleSeriesRef.current || !gexData) return;

    const series = candleSeriesRef.current;

    // Remove old price lines
    Object.values(gexLinesRef.current).forEach(line => {
      if (line) {
        series.removePriceLine(line);
      }
    });
    gexLinesRef.current = {};

    // Add new price lines for each GEX level
    Object.entries(GEX_COLORS).forEach(([key, config]) => {
      const price = gexData[key];
      if (price && price > 0) {
        const priceLine = series.createPriceLine({
          price: price,
          color: config.color,
          lineWidth: 2,
          lineStyle: config.dash ? 2 : 0, // 0 = solid, 2 = dashed
          axisLabelVisible: true,
          title: config.label,
        });
        gexLinesRef.current[key] = priceLine;
      }
    });
  }, [gexData]);

  // Generate sample candle data (replace with real data feed)
  useEffect(() => {
    if (!candleSeriesRef.current || !lastPrice) return;

    // Generate historical candles around the last price
    const now = Math.floor(Date.now() / 1000);
    const candles = [];
    let price = lastPrice;

    for (let i = 200; i >= 0; i--) {
      const time = now - i * 300; // 5-minute candles
      const volatility = price * 0.002;
      const open = price + (Math.random() - 0.5) * volatility;
      const close = open + (Math.random() - 0.5) * volatility;
      const high = Math.max(open, close) + Math.random() * volatility * 0.5;
      const low = Math.min(open, close) - Math.random() * volatility * 0.5;

      candles.push({ time, open, high, low, close });
      price = close;
    }

    candleSeriesRef.current.setData(candles);
    chartRef.current.timeScale().fitContent();
  }, [lastPrice]);

  return (
    <div className="relative w-full bg-[#0f0f23] rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#1a1a2e] border-b border-gray-700">
        <div className="flex items-center gap-4">
          <span className="text-white font-bold text-lg">{symbol}</span>
          <span className="text-gray-400 text-sm">{interval}</span>
          {lastPrice && (
            <span className="text-white font-mono text-lg">
              ${lastPrice.toFixed(2)}
            </span>
          )}
        </div>

        {/* GEX Regime Badge */}
        {gexData?.gamma_regime && (
          <div className={`px-3 py-1 rounded-full text-sm font-bold ${
            gexData.gamma_regime === 'POSITIVE'
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }`}>
            {gexData.gamma_regime} GAMMA
          </div>
        )}
      </div>

      {/* Chart */}
      <div ref={chartContainerRef} className="w-full" />

      {/* GEX Levels Legend */}
      <div className="absolute bottom-4 left-4 bg-black/70 rounded-lg p-3 backdrop-blur-sm">
        <div className="text-xs text-gray-400 mb-2 font-semibold">GEX LEVELS</div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1">
          {Object.entries(GEX_COLORS).map(([key, config]) => {
            const price = gexData?.[key];
            return (
              <div key={key} className="flex items-center gap-2 text-xs">
                <div
                  className="w-3 h-0.5"
                  style={{
                    backgroundColor: config.color,
                    borderStyle: config.dash ? 'dashed' : 'solid'
                  }}
                />
                <span className="text-gray-300">{config.label}:</span>
                <span className="text-white font-mono">
                  {price ? `$${price.toFixed(0)}` : '-'}
                </span>
              </div>
            );
          })}
        </div>

        {/* Total GEX */}
        {gexData?.total_gex !== undefined && (
          <div className="mt-2 pt-2 border-t border-gray-600">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-400">NET GEX:</span>
              <span className={`font-mono font-bold ${
                gexData.total_gex >= 0 ? 'text-green-400' : 'text-red-400'
              }`}>
                {gexData.total_gex >= 0 ? '+' : ''}{gexData.total_gex.toFixed(3)}B
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default TradingViewGEX;
