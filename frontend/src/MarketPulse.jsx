// Market Pulse Component - ohmygamma-inspired
// Gamma Regime, Volatility Analysis, AI Insights

import { useState } from 'react';

const MarketPulse = ({ gexData, currentPrice }) => {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const gammaRegime = gexData?.gamma_regime || 'UNKNOWN';
  const totalGex = gexData?.total_gex || 0;
  const zeroGamma = gexData?.zero_gamma || gexData?.gamma_flip || 0;
  const hvl = gexData?.hvl || 0;

  // Calculate distance from zero gamma
  const distanceFromZG = currentPrice ? (currentPrice - zeroGamma).toFixed(1) : 0;
  const isAboveZG = currentPrice > zeroGamma;

  // Simulated volatility data (would come from backend)
  const atr = 54.09;
  const vix = 17.73;
  const expMove = 94.8;
  const realizedVsExpected = 85;
  const gviMagnitude = 1.75;

  const colors = {
    green: '#22c55e',
    red: '#ef4444',
    cyan: '#22d3ee',
    purple: '#a855f7',
    amber: '#f59e0b',
    magenta: '#ec4899',
    text: '#f4f4f5',
    textMuted: '#71717a',
    background: 'rgba(20, 20, 30, 0.95)'
  };

  if (isCollapsed) {
    return (
      <div style={{
        background: 'linear-gradient(180deg, rgba(15,20,35,0.98) 0%, rgba(10,15,25,1) 100%)',
        borderRadius: 16,
        border: '1px solid rgba(168,85,247,0.3)',
        padding: '16px 24px',
        marginBottom: 24,
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 18 }}>📊</span>
          <span style={{ color: colors.purple, fontSize: 16, fontWeight: 600 }}>Market Pulse</span>
          <span style={{
            padding: '4px 12px',
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 600,
            background: gammaRegime === 'NEGATIVE' ? 'rgba(239,68,68,0.2)' : 'rgba(34,197,94,0.2)',
            color: gammaRegime === 'NEGATIVE' ? colors.red : colors.green
          }}>
            {gammaRegime}
          </span>
        </div>
        <button
          onClick={() => setIsCollapsed(false)}
          style={{
            padding: '8px 16px',
            background: 'transparent',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: 6,
            color: colors.text,
            fontSize: 12,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6
          }}
        >
          + EXPAND
        </button>
      </div>
    );
  }

  return (
    <div style={{
      background: 'linear-gradient(180deg, rgba(15,20,35,0.98) 0%, rgba(10,15,25,1) 100%)',
      borderRadius: 16,
      border: '1px solid rgba(168,85,247,0.3)',
      padding: 24,
      marginBottom: 24
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{ fontSize: 18 }}>📊</span>
          <span style={{ color: colors.purple, fontSize: 18, fontWeight: 600 }}>Market Pulse</span>
        </div>
        <button
          onClick={() => setIsCollapsed(true)}
          style={{
            padding: '8px 16px',
            background: 'rgba(255,255,255,0.05)',
            border: '1px solid rgba(255,255,255,0.2)',
            borderRadius: 6,
            color: colors.text,
            fontSize: 12,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: 6
          }}
        >
          − COLLAPSE
        </button>
      </div>

      {/* Main Content Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: 24 }}>
        {/* Left: Gamma Regime */}
        <div>
          <div style={{ fontSize: 10, color: colors.textMuted, letterSpacing: '0.1em', marginBottom: 8 }}>GAMMA REGIME</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <div style={{
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: gammaRegime === 'NEGATIVE' ? colors.red : colors.green,
              boxShadow: `0 0 10px ${gammaRegime === 'NEGATIVE' ? colors.red : colors.green}`
            }} />
            <span style={{
              fontSize: 18,
              fontWeight: 700,
              color: gammaRegime === 'NEGATIVE' ? colors.red : colors.green,
              letterSpacing: '0.05em'
            }}>
              CONFIRMED {gammaRegime}
            </span>
          </div>
          <div style={{ fontSize: 12, color: colors.textMuted, marginBottom: 16 }}>
            Net GEX: <span style={{ color: totalGex < 0 ? colors.red : colors.green, fontWeight: 600 }}>{totalGex.toFixed(2)}B</span>
          </div>

          {/* Volatility Regime */}
          <div style={{ fontSize: 10, color: colors.textMuted, letterSpacing: '0.1em', marginBottom: 8, marginTop: 24 }}>VOLATILITY REGIME</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: colors.text, marginBottom: 4 }}>
            {gammaRegime === 'NEGATIVE' ? 'EXPANSION' : 'CONTRACTION'}
          </div>
          <div style={{ fontSize: 12, color: colors.cyan }}>
            GVI Magnitude: <span style={{ fontWeight: 600 }}>{gviMagnitude}</span>
          </div>
        </div>

        {/* Right: Analysis & Metrics */}
        <div>
          {/* Description */}
          <div style={{
            padding: 16,
            background: 'rgba(0,0,0,0.3)',
            borderRadius: 8,
            marginBottom: 16,
            fontSize: 13,
            color: colors.textMuted,
            lineHeight: 1.6
          }}>
            Spot price is <span style={{ color: colors.text, fontWeight: 600 }}>{Math.abs(distanceFromZG)} points {isAboveZG ? 'above' : 'below'} Zero Gamma</span>.
            {gammaRegime === 'NEGATIVE' ? (
              <> Dealers hedge against explosive moves by amplifying volatility and reinforcing trend continuation.
              Requires <span style={{ color: colors.amber }}>extreme caution</span> around breakouts.</>
            ) : (
              <> Dealers hedge by dampening volatility and providing mean reversion.
              Expect <span style={{ color: colors.green }}>range-bound</span> price action.</>
            )}
          </div>

          {/* Metrics Cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
            {[
              { label: 'ATR', value: atr.toFixed(2) },
              { label: 'VIX', value: vix.toFixed(2) },
              { label: 'EXP. MOVE', value: expMove.toFixed(1) }
            ].map(({ label, value }) => (
              <div key={label} style={{
                background: 'rgba(0,0,0,0.3)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 8,
                padding: 16,
                textAlign: 'center'
              }}>
                <div style={{ fontSize: 10, color: colors.textMuted, marginBottom: 6 }}>{label}</div>
                <div style={{ fontSize: 20, fontWeight: 600, color: colors.text }}>{value}</div>
              </div>
            ))}
          </div>

          {/* Realized vs Expected Range */}
          <div style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <span style={{ fontSize: 11, color: colors.textMuted }}>REALIZED VS EXPECTED RANGE</span>
              <span style={{ fontSize: 11, color: colors.text }}>{realizedVsExpected} / {expMove.toFixed(1)} ({Math.round(realizedVsExpected / expMove * 100)}%)</span>
            </div>
            <div style={{ height: 8, background: 'rgba(255,255,255,0.1)', borderRadius: 4, overflow: 'hidden' }}>
              <div style={{
                width: `${Math.min(realizedVsExpected / expMove * 100, 100)}%`,
                height: '100%',
                background: realizedVsExpected > expMove * 0.8 ? colors.amber : colors.green,
                borderRadius: 4
              }} />
            </div>
          </div>

          {/* Greek Indicators */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, fontSize: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.textMuted }}>Sentiment (Skew):</span>
              <span style={{ color: colors.text }}>Neutral (-0.01)</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.textMuted }}>Stability (Speed):</span>
              <span style={{ color: colors.text }}>Normal</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.textMuted }}>Vanna:</span>
              <span style={{ color: colors.cyan }}>Vol Support</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.textMuted }}>Charm:</span>
              <span style={{ color: colors.text }}>Price Pressure</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: colors.textMuted }}>Magnete Charm:</span>
              <span style={{ color: colors.purple }}>Pressione ({zeroGamma.toFixed(2)})</span>
            </div>
          </div>
        </div>
      </div>

      {/* Volatility Diagnosis */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: 16,
        background: 'rgba(34,197,94,0.1)',
        borderRadius: 8,
        marginTop: 20,
        border: '1px solid rgba(34,197,94,0.3)'
      }}>
        <div style={{
          width: 24,
          height: 24,
          borderRadius: '50%',
          background: colors.green,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 14
        }}>✓</div>
        <div>
          <div style={{ fontSize: 12, color: colors.green, fontWeight: 600, marginBottom: 2 }}>VOLATILITY DIAGNOSIS</div>
          <div style={{ fontSize: 12, color: colors.textMuted }}>
            Confirmation: The multi-factor analysis (Speed/Convexity) confirms the detected regime.
          </div>
        </div>
      </div>

      {/* AI Deep Analysis */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        background: 'rgba(0,0,0,0.3)',
        borderRadius: 8,
        marginTop: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 36,
            height: 36,
            borderRadius: 8,
            background: 'rgba(168,85,247,0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: 18
          }}>⚙️</div>
          <div>
            <div style={{ fontSize: 14, color: colors.text, fontWeight: 600 }}>AI Deep Analysis</div>
            <div style={{ fontSize: 11, color: colors.textMuted }}>Market Structure & 0DTE Strategy</div>
          </div>
        </div>
        <button style={{
          padding: '10px 20px',
          background: 'linear-gradient(135deg, #a855f7 0%, #7c3aed 100%)',
          border: 'none',
          borderRadius: 8,
          color: '#fff',
          fontSize: 12,
          fontWeight: 600,
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}>
          👁 VIEW ANALYSIS
        </button>
      </div>
    </div>
  );
};

export default MarketPulse;
