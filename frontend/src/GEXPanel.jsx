// GEX Panel Component - ohmygamma-inspired design
// Strategic Levels with 3 view modes: Table, Card, Quantum
// Enhanced tooltips and professional aesthetics

import { useState } from 'react';

const GEXPanel = ({ gexData, currentPrice }) => {
  const [viewMode, setViewMode] = useState('table'); // 'table', 'card', 'quantum'
  const [levelCount, setLevelCount] = useState(10);
  const [hoveredRow, setHoveredRow] = useState(null); // For "Click for Details" tooltip
  const [selectedLevel, setSelectedLevel] = useState(null); // For detail modal

  const profile = gexData?.gex_profile || [];
  const levels = gexData?.gex_levels || [];
  const gammaRegime = gexData?.gamma_regime || 'UNKNOWN';
  const totalGex = gexData?.total_gex || 0;
  const zeroGamma = gexData?.zero_gamma || gexData?.gamma_flip || 0;
  const maxPain = gexData?.max_pain || 0;
  const callWall = gexData?.call_wall || 0;
  const putWall = gexData?.put_wall || 0;
  const hvl = gexData?.hvl || 0;

  // Generate strategic levels from profile data
  const strategicLevels = profile
    .filter(p => Math.abs(p.gex) > 0.1)
    .sort((a, b) => b.strike - a.strike)
    .slice(0, levelCount)
    .map(p => {
      const isCall = p.gex < 0;  // Negative GEX = Call (dealers short calls), Positive = Put
      const distance = currentPrice ? Math.round(p.strike - currentPrice) : 0;
      const holdPct = Math.round(50 + (Math.abs(p.gex) * 10));
      const breakPct = 100 - holdPct;

      return {
        strike: p.strike,
        gex: p.gex,
        type: isCall ? 'CALL' : 'PUT',
        wallType: Math.abs(p.gex) > 0.5 ? 'WALL' : 'LEVEL',
        role: isCall
          ? (p.strike > currentPrice ? 'POT. RESISTANCE' : 'POT. RESISTANCE (EX-SUPP)')
          : (p.strike < currentPrice ? 'POT. SUPPORT' : 'POT. SUPPORT'),
        distance,
        holdPct: Math.min(holdPct, 85),
        breakPct: Math.max(breakPct, 15),
        callPct: isCall ? 70 + Math.random() * 20 : 10 + Math.random() * 20,
        putPct: isCall ? 30 - Math.random() * 20 : 80 + Math.random() * 10,
        mass: Math.abs(p.gex).toFixed(1),
        effective: Math.abs(p.gex * 0.9).toFixed(1),
        integrity: Math.round(85 + Math.random() * 15),
        fieldHigh: p.strike + 8,
        fieldLow: p.strike - 8,
        influence: Math.round(15 + Math.random() * 10)
      };
    });

  // Expected Move calculation (simplified)
  const emHigh = currentPrice ? currentPrice * 1.015 : 0;
  const emLow = currentPrice ? currentPrice * 0.985 : 0;
  const volBandHigh = currentPrice ? currentPrice * 1.012 : 0;
  const volBandLow = currentPrice ? currentPrice * 0.988 : 0;

  // Colors
  const colors = {
    cyan: '#22d3ee',
    green: '#22c55e',
    red: '#ef4444',
    amber: '#f59e0b',
    purple: '#a855f7',
    magenta: '#ec4899',
    background: 'rgba(10, 10, 15, 0.95)',
    cardBg: 'rgba(20, 20, 30, 0.8)',
    border: 'rgba(34, 211, 238, 0.2)',
    text: '#f4f4f5',
    textMuted: '#71717a'
  };

  // Find next/previous levels for structural context
  const getStructuralContext = (level) => {
    const idx = strategicLevels.findIndex(l => l.strike === level.strike);
    const nextLevel = strategicLevels[idx + 1];
    const prevLevel = strategicLevels[idx - 1];
    return { nextLevel, prevLevel };
  };

  // Level Detail Modal Component
  const LevelDetailModal = ({ level, onClose }) => {
    if (!level) return null;
    const { nextLevel, prevLevel } = getStructuralContext(level);
    const zgDistance = zeroGamma ? Math.round(level.strike - zeroGamma) : 0;
    const isNegativeGamma = level.gex < 0;
    const regimeReaction = isNegativeGamma
      ? (level.strike > currentPrice ? 'Continuation Short' : 'Reversal Long')
      : (level.strike < currentPrice ? 'Continuation Long' : 'Reversal Short');

    return (
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.7)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10000
      }} onClick={onClose}>
        <div style={{
          background: 'linear-gradient(180deg, rgba(20, 22, 35, 0.98) 0%, rgba(15, 17, 28, 0.99) 100%)',
          borderRadius: 16,
          width: 560,
          maxWidth: '90vw',
          maxHeight: '85vh',
          overflow: 'auto',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 25px 50px rgba(0,0,0,0.5)'
        }} onClick={e => e.stopPropagation()}>
          {/* Header */}
          <div style={{
            padding: '20px 24px',
            borderBottom: '1px solid rgba(255,255,255,0.08)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start'
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <span style={{
                  fontSize: 32,
                  fontWeight: 700,
                  color: level.type === 'PUT' ? colors.cyan : colors.magenta,
                  fontFamily: "'JetBrains Mono', monospace"
                }}>
                  {level.strike}
                </span>
                <span style={{
                  fontSize: 14,
                  fontWeight: 600,
                  color: level.type === 'PUT' ? colors.cyan : colors.magenta
                }}>
                  {level.type} {level.wallType}
                </span>
                <span style={{
                  padding: '4px 10px',
                  background: level.role.includes('SUPPORT') ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)',
                  border: `1px solid ${level.role.includes('SUPPORT') ? colors.green : colors.red}`,
                  borderRadius: 4,
                  fontSize: 10,
                  fontWeight: 600,
                  color: level.role.includes('SUPPORT') ? colors.green : colors.red
                }}>
                  {level.role.includes('SUPPORT') ? 'POTENTIAL SUPPORT' : 'POTENTIAL RESISTANCE'}
                </span>
              </div>
              <div style={{ fontSize: 11, color: colors.textMuted }}>
                <span style={{ color: isNegativeGamma ? colors.red : colors.green }}>
                  {isNegativeGamma ? 'NEGATIVE GAMMA' : 'POSITIVE GAMMA'}
                </span>
                <span style={{ margin: '0 8px' }}>|</span>
                ZG Dist: {zgDistance > 0 ? '+' : ''}{zgDistance}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: 10, color: colors.textMuted, marginBottom: 4 }}>DISTANCE FROM SPOT</div>
              <div style={{
                fontSize: 28,
                fontWeight: 600,
                color: level.distance > 0 ? colors.green : colors.red
              }}>
                {level.distance > 0 ? '+' : ''}{level.distance}
                <span style={{ fontSize: 14, color: colors.textMuted, marginLeft: 4 }}>pts</span>
              </div>
              <button
                onClick={onClose}
                style={{
                  position: 'absolute',
                  top: 16,
                  right: 16,
                  background: 'transparent',
                  border: 'none',
                  color: colors.textMuted,
                  fontSize: 24,
                  cursor: 'pointer',
                  padding: 4
                }}
              >×</button>
            </div>
          </div>

          {/* Body */}
          <div style={{ padding: 24 }}>
            {/* Γ Regime Expected Reaction */}
            <div style={{ textAlign: 'center', marginBottom: 24 }}>
              <div style={{ fontSize: 10, color: colors.textMuted, letterSpacing: '0.1em', marginBottom: 4 }}>
                Γ REGIME EXPECTED REACTION
              </div>
              <div style={{
                fontSize: 24,
                fontWeight: 600,
                color: regimeReaction.includes('Long') ? colors.cyan : colors.magenta,
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                {regimeReaction}
              </div>
            </div>

            {/* Dealer Positioning & Greeks */}
            <div style={{
              background: 'rgba(30, 32, 45, 0.6)',
              borderRadius: 12,
              padding: 20,
              marginBottom: 20,
              border: '1px solid rgba(255,255,255,0.05)'
            }}>
              <div style={{
                fontSize: 10,
                color: colors.cyan,
                letterSpacing: '0.1em',
                textAlign: 'center',
                marginBottom: 16
              }}>
                DEALER POSITIONING & GREEKS
              </div>

              {/* TOT GEX PROFILE bar */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                  <span style={{ fontSize: 11, color: colors.textMuted }}>TOT GEX PROFILE</span>
                  <span style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: level.gex < 0 ? colors.magenta : colors.cyan
                  }}>
                    {(level.gex * 1000).toFixed(1)}M
                  </span>
                </div>
                <div style={{
                  height: 8,
                  background: 'rgba(255,255,255,0.1)',
                  borderRadius: 4,
                  overflow: 'hidden',
                  position: 'relative'
                }}>
                  <div style={{
                    width: `${Math.min(Math.abs(level.gex) * 100, 90)}%`,
                    height: '100%',
                    background: level.gex < 0
                      ? 'linear-gradient(90deg, rgba(236,72,153,0.8), rgba(236,72,153,0.4))'
                      : 'linear-gradient(90deg, rgba(34,211,238,0.8), rgba(34,211,238,0.4))',
                    borderRadius: 4
                  }} />
                </div>
              </div>

              {/* Speed, Vanna, Charm */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr 1fr',
                gap: 16,
                borderTop: '1px solid rgba(255,255,255,0.05)',
                paddingTop: 16
              }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 9, color: colors.textMuted, marginBottom: 4 }}>SPEED</div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: colors.text }}>
                    {(Math.abs(level.gex) * 60).toFixed(1)}K
                  </div>
                </div>
                <div style={{ textAlign: 'center', borderLeft: '1px solid rgba(255,255,255,0.05)', borderRight: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ fontSize: 9, color: colors.textMuted, marginBottom: 4 }}>VANNA</div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: colors.cyan }}>
                    {(Math.abs(level.gex) * 25).toFixed(1)}M
                  </div>
                </div>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 9, color: colors.textMuted, marginBottom: 4 }}>CHARM</div>
                  <div style={{ fontSize: 16, fontWeight: 600, color: colors.magenta }}>
                    {(level.gex * -500).toFixed(1)}M
                  </div>
                </div>
              </div>
            </div>

            {/* Hold / Break Probabilities */}
            <div style={{
              background: 'rgba(30, 32, 45, 0.6)',
              borderRadius: 12,
              padding: 20,
              marginBottom: 20,
              border: '1px solid rgba(255,255,255,0.05)'
            }}>
              <div style={{
                fontSize: 10,
                color: colors.textMuted,
                letterSpacing: '0.1em',
                textAlign: 'center',
                marginBottom: 12
              }}>
                HOLD / BREAK PROBABILITIES
              </div>
              <div style={{
                display: 'flex',
                height: 28,
                borderRadius: 6,
                overflow: 'hidden',
                fontSize: 11,
                fontWeight: 600
              }}>
                <div style={{
                  width: `${level.holdPct}%`,
                  background: colors.green,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#000'
                }}>
                  Hold {level.holdPct}%
                </div>
                <div style={{
                  width: `${level.breakPct}%`,
                  background: colors.red,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#fff'
                }}>
                  Break {level.breakPct}%
                </div>
              </div>

              {/* Sensitivity description */}
              <div style={{
                marginTop: 16,
                padding: 12,
                background: 'rgba(0,0,0,0.3)',
                borderRadius: 8,
                borderLeft: `3px solid ${colors.amber}`
              }}>
                <div style={{ fontSize: 12, color: colors.text, marginBottom: 8 }}>
                  <strong>High Sensitivity.</strong> Dealer hedging activity increases rapidly here, creating potential for sharp reactions or rejection.
                </div>
                <span style={{
                  padding: '4px 8px',
                  background: 'rgba(245,158,11,0.2)',
                  border: `1px solid ${colors.amber}`,
                  borderRadius: 4,
                  fontSize: 9,
                  fontWeight: 600,
                  color: colors.amber
                }}>
                  REACTIVE ZONE
                </span>
              </div>
            </div>

            {/* Structural Context */}
            <div style={{
              background: 'rgba(30, 32, 45, 0.6)',
              borderRadius: 12,
              padding: 20,
              border: '1px solid rgba(255,255,255,0.05)'
            }}>
              <div style={{
                fontSize: 10,
                color: colors.textMuted,
                letterSpacing: '0.1em',
                marginBottom: 16
              }}>
                STRUCTURAL CONTEXT
              </div>

              {nextLevel && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                  <span style={{
                    padding: '4px 8px',
                    background: 'rgba(239,68,68,0.2)',
                    border: `1px solid ${colors.red}`,
                    borderRadius: 4,
                    fontSize: 9,
                    fontWeight: 600,
                    color: colors.red
                  }}>
                    IF BREAK
                  </span>
                  <span style={{ fontSize: 12, color: colors.text }}>
                    Next: {nextLevel.type} {nextLevel.wallType} (@ {nextLevel.strike})
                  </span>
                </div>
              )}

              {prevLevel && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{
                    padding: '4px 8px',
                    background: 'rgba(34,197,94,0.2)',
                    border: `1px solid ${colors.green}`,
                    borderRadius: 4,
                    fontSize: 9,
                    fontWeight: 600,
                    color: colors.green
                  }}>
                    IF HOLD
                  </span>
                  <span style={{ fontSize: 12, color: colors.text }}>
                    Target: {prevLevel.type} {prevLevel.wallType} (@ {prevLevel.strike})
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Key Market Level Row
  const MarketLevelRow = ({ label, value, color = colors.textMuted }) => (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      padding: '8px 16px',
      background: 'rgba(40, 40, 50, 0.4)',
      borderRadius: 6,
      marginBottom: 8
    }}>
      <span style={{
        fontSize: 12,
        color,
        fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: '0.1em'
      }}>
        ◆ {label}: {value} ◆
      </span>
    </div>
  );

  // Zero Gamma Flip Row (highlighted)
  const ZeroGammaRow = () => (
    <div style={{
      background: 'linear-gradient(90deg, rgba(34,211,238,0.1) 0%, rgba(34,211,238,0.2) 50%, rgba(34,211,238,0.1) 100%)',
      padding: '12px 20px',
      borderRadius: 8,
      margin: '16px 0',
      textAlign: 'center',
      border: '1px solid rgba(34,211,238,0.3)'
    }}>
      <span style={{
        fontSize: 14,
        fontWeight: 600,
        color: colors.cyan,
        fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: '0.15em'
      }}>
        ● ZERO GAMMA FLIP: {zeroGamma.toFixed(2)} ●
      </span>
      <div style={{ marginTop: 4 }}>
        <span style={{ fontSize: 10, color: colors.textMuted }}>
          Above: Dealers dampen volatility (<span style={{ color: colors.cyan }}>Reversal Playbook</span>)
        </span>
      </div>
      <div style={{ marginTop: 2 }}>
        <span style={{ fontSize: 10, color: colors.textMuted }}>
          Below: Dealers amplify volatility (<span style={{ color: colors.amber }}>Trend/Breakout Playbook</span>)
        </span>
      </div>
    </div>
  );

  // Current Spot Row (yellow)
  const CurrentSpotRow = () => (
    <div style={{
      background: 'linear-gradient(90deg, rgba(234,179,8,0.2) 0%, rgba(234,179,8,0.4) 50%, rgba(234,179,8,0.2) 100%)',
      padding: '12px 20px',
      borderRadius: 8,
      margin: '16px 0',
      textAlign: 'center',
      boxShadow: '0 0 20px rgba(234,179,8,0.3)'
    }}>
      <span style={{
        fontSize: 16,
        fontWeight: 700,
        color: '#eab308',
        fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: '0.15em'
      }}>
        ● CURRENT SPOT: {currentPrice?.toFixed(2) || '—'} ●
      </span>
    </div>
  );

  // Low Density Row
  const LowDensityRow = ({ pts }) => (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 12,
      padding: '8px 16px',
      background: 'rgba(0,0,0,0.4)',
      borderRadius: 6,
      margin: '8px 0'
    }}>
      <span style={{ fontSize: 14, color: colors.textMuted, letterSpacing: '0.15em' }}>LOW DENSITY</span>
      <span style={{ width: 60, height: 1, background: colors.textMuted }} />
      <span style={{ fontSize: 12, color: colors.textMuted }}>{pts} PTS</span>
      <span style={{ fontSize: 12, color: colors.amber, fontWeight: 600 }}>FAST LANE</span>
    </div>
  );

  // Hold/Break Probability Bar
  const HoldBreakBar = ({ holdPct, breakPct, size = 'normal' }) => (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
      <span style={{ fontSize: size === 'small' ? 9 : 11, color: colors.green }}>H:{holdPct}%</span>
      <div style={{
        flex: 1,
        height: size === 'small' ? 4 : 6,
        background: colors.red,
        borderRadius: 3,
        overflow: 'hidden',
        display: 'flex'
      }}>
        <div style={{
          width: `${holdPct}%`,
          height: '100%',
          background: colors.green
        }} />
      </div>
      <span style={{ fontSize: size === 'small' ? 9 : 11, color: colors.red }}>B:{breakPct}%</span>
    </div>
  );

  // Directional GEX Bar
  const DirectionalBar = ({ value, maxVal = 1000 }) => {
    const pct = Math.min(Math.abs(value) / maxVal * 100, 100);
    const isPositive = value > 0;
    return (
      <div style={{
        width: '100%',
        height: 6,
        background: 'rgba(255,255,255,0.1)',
        borderRadius: 3,
        overflow: 'hidden'
      }}>
        <div style={{
          width: `${pct}%`,
          height: '100%',
          background: isPositive
            ? 'linear-gradient(90deg, #22c55e, #4ade80)'
            : 'linear-gradient(90deg, #22d3ee, #67e8f9)',
          borderRadius: 3
        }} />
      </div>
    );
  };

  // TABLE VIEW
  const TableView = () => (
    <div style={{ overflowX: 'auto' }}>
      {/* Header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '80px 150px 140px 120px 100px 180px',
        gap: 8,
        padding: '12px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        marginBottom: 8
      }}>
        {['LEVEL', 'TOT. GEX PROFILE', 'ROLE', 'CONFLUENCES', 'WARNING', 'HOLD / BREAK PROB.'].map(h => (
          <span key={h} style={{ fontSize: 10, color: colors.textMuted, fontWeight: 600, letterSpacing: '0.05em' }}>{h}</span>
        ))}
      </div>

      {/* Market Levels */}
      <MarketLevelRow label="EM HIGH" value={emHigh.toFixed(2)} />
      <MarketLevelRow label="VOL BAND HIGH" value={volBandHigh.toFixed(2)} />

      {/* Levels above spot */}
      {strategicLevels.filter(l => l.strike > currentPrice).map((level, idx) => {
        const isHovered = hoveredRow === `above-${idx}`;
        return (
          <div
            key={idx}
            onMouseEnter={() => setHoveredRow(`above-${idx}`)}
            onMouseLeave={() => setHoveredRow(null)}
            onClick={() => setSelectedLevel(level)}
            style={{
              display: 'grid',
              gridTemplateColumns: '80px 150px 140px 120px 100px 180px',
              gap: 8,
              padding: '12px 16px',
              background: isHovered ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.02)',
              borderRadius: 8,
              marginBottom: 4,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              borderLeft: `3px solid ${level.type === 'CALL' ? colors.green : colors.magenta}`,
              transform: isHovered ? 'translateX(4px)' : 'none',
              boxShadow: isHovered ? '0 4px 12px rgba(0,0,0,0.3)' : 'none',
              position: 'relative'
            }}
          >
            {/* Click for Details tooltip */}
            {isHovered && (
              <div style={{
                position: 'absolute',
                top: '50%',
                right: 12,
                transform: 'translateY(-50%)',
                background: 'rgba(20, 22, 30, 0.95)',
                border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: 4,
                padding: '4px 10px',
                fontSize: 10,
                color: colors.textMuted,
                whiteSpace: 'nowrap',
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                zIndex: 10,
                fontFamily: "'Inter', sans-serif"
              }}>
                Click for Details
              </div>
            )}
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: level.type === 'CALL' ? colors.green : colors.magenta }}>{level.strike}</div>
              <div style={{ fontSize: 10, color: level.type === 'CALL' ? colors.green : colors.magenta }}>{level.type} WALL</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: colors.cyan, marginBottom: 4 }}>DIRECTIONAL</div>
              <div style={{ fontSize: 12, color: colors.text, marginBottom: 4 }}>{(level.gex * 1000).toFixed(1)}M</div>
              <DirectionalBar value={level.gex * 100} />
            </div>
            <div>
              <span style={{
                padding: '4px 8px',
                background: level.role.includes('SUPPORT') ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)',
                border: `1px solid ${level.role.includes('SUPPORT') ? colors.green : colors.red}`,
                borderRadius: 4,
                fontSize: 9,
                fontWeight: 600,
                color: level.role.includes('SUPPORT') ? colors.green : colors.red
              }}>
                {level.role}
              </span>
            </div>
            <div style={{ fontSize: 10, color: colors.textMuted }}>—</div>
            <div style={{
              fontSize: 10,
              padding: '2px 6px',
              background: 'rgba(245,158,11,0.15)',
              border: `1px solid ${colors.amber}40`,
              borderRadius: 4,
              color: colors.amber,
              width: 'fit-content'
            }}>HIGH VOL</div>
            <HoldBreakBar holdPct={level.holdPct} breakPct={level.breakPct} />
          </div>
        );
      })}

      <ZeroGammaRow />
      <MarketLevelRow label="VOL BAND LOW" value={volBandLow.toFixed(2)} />
      <MarketLevelRow label="MAX PAIN" value={maxPain.toFixed(2)} />

      {/* Levels below spot */}
      {strategicLevels.filter(l => l.strike <= currentPrice).slice(0, 3).map((level, idx) => {
        const isHovered = hoveredRow === `below-${idx}`;
        return (
          <div
            key={idx}
            onMouseEnter={() => setHoveredRow(`below-${idx}`)}
            onMouseLeave={() => setHoveredRow(null)}
            onClick={() => setSelectedLevel(level)}
            style={{
              display: 'grid',
              gridTemplateColumns: '80px 150px 140px 120px 100px 180px',
              gap: 8,
              padding: '12px 16px',
              background: isHovered ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.02)',
              borderRadius: 8,
              marginBottom: 4,
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              borderLeft: `3px solid ${colors.cyan}`,
              transform: isHovered ? 'translateX(4px)' : 'none',
              boxShadow: isHovered ? '0 4px 12px rgba(0,0,0,0.3)' : 'none',
              position: 'relative'
            }}
          >
            {/* Click for Details tooltip */}
            {isHovered && (
              <div style={{
                position: 'absolute',
                top: '50%',
                right: 12,
                transform: 'translateY(-50%)',
                background: 'rgba(20, 22, 30, 0.95)',
                border: '1px solid rgba(255,255,255,0.2)',
                borderRadius: 4,
                padding: '4px 10px',
                fontSize: 10,
                color: colors.textMuted,
                whiteSpace: 'nowrap',
                boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
                zIndex: 10,
                fontFamily: "'Inter', sans-serif"
              }}>
                Click for Details
              </div>
            )}
            <div>
              <div style={{ fontSize: 18, fontWeight: 700, color: colors.cyan }}>{level.strike}</div>
              <div style={{ fontSize: 10, color: colors.cyan }}>PUT WALL</div>
            </div>
            <div>
              <div style={{ fontSize: 10, color: colors.cyan, marginBottom: 4 }}>DIRECTIONAL</div>
              <div style={{ fontSize: 12, color: colors.text, marginBottom: 4 }}>{(level.gex * 1000).toFixed(1)}M</div>
              <DirectionalBar value={level.gex * 100} />
            </div>
            <div>
              <span style={{
                padding: '4px 8px',
                background: 'rgba(34,197,94,0.2)',
                border: `1px solid ${colors.green}`,
                borderRadius: 4,
                fontSize: 9,
                fontWeight: 600,
                color: colors.green
              }}>
                POT. SUPPORT
              </span>
            </div>
            <div style={{ fontSize: 10, color: colors.textMuted }}>—</div>
            <div style={{
              fontSize: 10,
              padding: '2px 6px',
              background: 'rgba(245,158,11,0.15)',
              border: `1px solid ${colors.amber}40`,
              borderRadius: 4,
              color: colors.amber,
              width: 'fit-content'
            }}>HIGH VOL</div>
            <HoldBreakBar holdPct={level.holdPct} breakPct={level.breakPct} />
          </div>
        );
      })}

      <CurrentSpotRow />
      <MarketLevelRow label="EM LOW" value={emLow.toFixed(2)} />
    </div>
  );

  // CARD VIEW
  const CardView = () => (
    <div>
      <MarketLevelRow label="EM HIGH" value={emHigh.toFixed(2)} />

      {/* Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12, marginBottom: 16 }}>
        {strategicLevels.filter(l => l.strike > currentPrice).slice(0, 3).map((level, idx) => (
          <div
            key={idx}
            onClick={() => setSelectedLevel(level)}
            style={{
              background: 'rgba(20,20,30,0.9)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 12,
              padding: 16,
              cursor: 'pointer'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 24, fontWeight: 700, color: level.type === 'CALL' ? colors.green : colors.magenta }}>{level.strike}</div>
                <div style={{ fontSize: 10, color: colors.cyan }}>{level.type} WALL</div>
              </div>
              <span style={{
                padding: '4px 8px',
                background: level.role.includes('RESISTANCE') ? 'rgba(239,68,68,0.2)' : 'rgba(34,197,94,0.2)',
                border: `1px solid ${level.role.includes('RESISTANCE') ? colors.red : colors.green}`,
                borderRadius: 4,
                fontSize: 8,
                fontWeight: 600,
                color: level.role.includes('RESISTANCE') ? colors.red : colors.green
              }}>
                {level.role}
              </span>
            </div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 9, color: colors.textMuted, marginBottom: 4 }}>TOT. GEX PROFILE</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontSize: 10, color: colors.cyan }}>DIRECTIONAL</span>
                <span style={{ fontSize: 12, fontWeight: 600, color: colors.text }}>{level.gex.toFixed(1)}M</span>
              </div>
              <DirectionalBar value={level.gex * 100} />
            </div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 9, color: colors.textMuted, marginBottom: 4 }}>HOLD / BREAK PROB.</div>
              <HoldBreakBar holdPct={level.holdPct} breakPct={level.breakPct} size="small" />
            </div>

            <div style={{ borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10 }}>
                <span style={{ color: colors.cyan }}>BREAK</span>
                <span style={{ color: colors.textMuted }}>Open Space</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, marginTop: 4 }}>
                <span style={{ color: colors.green }}>HOLD</span>
                <span style={{ color: colors.textMuted }}>Hold</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      <ZeroGammaRow />
      <CurrentSpotRow />
      <LowDensityRow pts={42} />

      {/* Support Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
        {strategicLevels.filter(l => l.strike <= currentPrice).slice(0, 3).map((level, idx) => (
          <div
            key={idx}
            onClick={() => setSelectedLevel(level)}
            style={{
              background: 'rgba(20,20,30,0.9)',
              border: '1px solid rgba(255,255,255,0.1)',
              borderRadius: 12,
              padding: 16,
              cursor: 'pointer'
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
              <div>
                <div style={{ fontSize: 24, fontWeight: 700, color: colors.cyan }}>{level.strike}</div>
                <div style={{ fontSize: 10, color: colors.cyan }}>PUT WALL</div>
              </div>
              <span style={{
                padding: '4px 8px',
                background: 'rgba(34,197,94,0.2)',
                border: `1px solid ${colors.green}`,
                borderRadius: 4,
                fontSize: 8,
                fontWeight: 600,
                color: colors.green
              }}>
                POT. SUPPORT
              </span>
            </div>

            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 9, color: colors.textMuted, marginBottom: 4 }}>TOT. GEX PROFILE</div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ fontSize: 10, color: colors.cyan }}>DIRECTIONAL</span>
                <span style={{ fontSize: 12, fontWeight: 600, color: colors.text }}>{level.gex.toFixed(1)}M</span>
              </div>
              <DirectionalBar value={level.gex * 100} />
            </div>

            <div>
              <div style={{ fontSize: 9, color: colors.textMuted, marginBottom: 4 }}>HOLD / BREAK PROB.</div>
              <HoldBreakBar holdPct={level.holdPct} breakPct={level.breakPct} size="small" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  // QUANTUM VIEW
  const QuantumView = () => (
    <div>
      {/* Field Status */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, padding: '12px 16px', background: 'rgba(30,30,40,0.6)', borderRadius: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: colors.textMuted }} />
          <div>
            <div style={{ fontSize: 10, color: colors.textMuted }}>FIELD</div>
            <div style={{ fontSize: 12, color: colors.text, fontWeight: 600 }}>NEUTRAL</div>
          </div>
        </div>
        <span style={{ padding: '6px 16px', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 4, fontSize: 12, color: colors.text }}>WAIT</span>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: 10, color: colors.textMuted }}>MID</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{ width: 40, height: 4, background: colors.green, borderRadius: 2 }} />
            <div style={{ width: 20, height: 4, background: colors.red, borderRadius: 2 }} />
            <span style={{ fontSize: 11, color: colors.text }}>67%</span>
          </div>
        </div>
      </div>

      {/* Quantum Field Options */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 11, color: colors.purple }}>Ψ</span>
          <span style={{ fontSize: 10, color: colors.text }}>QUANTUM FIELD</span>
          <span style={{ padding: '2px 6px', background: colors.cyan, borderRadius: 4, fontSize: 8, color: '#000', fontWeight: 600 }}>BETA</span>
        </div>
        {['EXPANDED', 'NAV', 'BOUNDS'].map(opt => (
          <span key={opt} style={{ padding: '4px 12px', border: '1px solid rgba(255,255,255,0.2)', borderRadius: 4, fontSize: 10, color: colors.text }}>{opt}</span>
        ))}
        <div style={{ marginLeft: 'auto', fontSize: 11, color: colors.textMuted }}>
          LEVELS: {levelCount} | SPOT: <span style={{ color: colors.amber }}>{currentPrice?.toFixed(2)}</span>
        </div>
      </div>

      {/* Quantum Level Rows */}
      {strategicLevels.slice(0, levelCount).map((level, idx) => {
        const isAboveSpot = level.strike > currentPrice;
        const isNearSpot = Math.abs(level.strike - currentPrice) < 10;

        return (
          <div key={idx}>
            {isNearSpot && isAboveSpot && <CurrentSpotRow />}
            <div
              onClick={() => setSelectedLevel(level)}
              style={{
                background: `linear-gradient(90deg, rgba(139,92,246,${0.1 + Math.abs(level.gex) * 0.05}) 0%, rgba(139,92,246,${0.2 + Math.abs(level.gex) * 0.1}) 50%, rgba(139,92,246,${0.1 + Math.abs(level.gex) * 0.05}) 100%)`,
                padding: '20px 24px',
                marginBottom: 4,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                transition: 'all 0.2s ease'
              }}
            >
              {/* Left: Level indicator + Price */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <div style={{ width: 4, height: 30, background: level.type === 'CALL' ? colors.green : colors.cyan, borderRadius: 2 }} />
                <span style={{ fontSize: 32, fontWeight: 700, color: colors.cyan, fontFamily: "'JetBrains Mono', monospace" }}>{level.strike}</span>
              </div>

              {/* Center: Info */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, flex: 1, justifyContent: 'center' }}>
                <span style={{ fontSize: 11, color: level.type === 'CALL' ? colors.green : colors.magenta }}>
                  {level.type} | WALL
                </span>
                <span style={{
                  padding: '4px 10px',
                  background: isAboveSpot ? 'rgba(34,197,94,0.2)' : 'rgba(34,197,94,0.2)',
                  border: `1px solid ${colors.green}`,
                  borderRadius: 4,
                  fontSize: 9,
                  fontWeight: 600,
                  color: colors.green
                }}>
                  POT. {isAboveSpot ? 'SUPPORT' : 'SUPPORT'}
                </span>
                <span style={{
                  padding: '4px 10px',
                  background: 'rgba(255,255,255,0.1)',
                  borderRadius: 4,
                  fontSize: 9,
                  color: colors.textMuted
                }}>
                  {Math.abs(level.distance)}pt {level.distance > 0 ? 'above' : 'below'} spot
                </span>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '2px 8px', background: 'rgba(0,0,0,0.3)', borderRadius: 4 }}>
                  <span style={{ fontSize: 9, color: colors.green }}>H:{level.holdPct}%</span>
                  <div style={{ width: 30, height: 4, background: colors.green, borderRadius: 2 }} />
                  <div style={{ width: 15, height: 4, background: colors.red, borderRadius: 2 }} />
                  <span style={{ fontSize: 9, color: colors.red }}>B:{level.breakPct}%</span>
                </div>
              </div>

              {/* Right: GEX Value */}
              <div style={{ textAlign: 'right' }}>
                <span style={{ fontSize: 28, fontWeight: 600, color: colors.text }}>{Math.abs(level.gex * 100).toFixed(1)}</span>
                <span style={{ fontSize: 14, color: colors.textMuted }}>M</span>
                <div style={{ fontSize: 10, color: colors.textMuted }}>
                  18PT | L↑ {level.fieldHigh.toFixed(1)} - L↓ {level.fieldLow.toFixed(1)}
                </div>
              </div>
            </div>
            {idx === 2 && <LowDensityRow pts={42} />}
          </div>
        );
      })}
    </div>
  );

  // Find max absolute GEX for scaling
  const maxGex = Math.max(...profile.map(p => Math.abs(p.gex || 0)), 0.01);

  // Chart tooltip state
  const [chartTooltip, setChartTooltip] = useState(null);
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  return (
    <div style={{
      background: 'linear-gradient(180deg, rgba(11, 17, 32, 0.98) 0%, rgba(8, 12, 24, 0.99) 100%)',
      borderRadius: 16,
      border: `1px solid ${colors.border}`,
      padding: 24,
      fontFamily: "'Inter', -apple-system, sans-serif",
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)',
      position: 'relative'
    }}>
      {/* GEX Profile Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h3 style={{ margin: 0, color: colors.text, fontSize: 18, fontWeight: 600 }}>GEX Profile</h3>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', background: colors.cyan, animation: 'pulse 2s infinite' }} />
            <span style={{ fontSize: 10, color: colors.cyan, letterSpacing: '0.05em' }}>LIVE</span>
          </div>
        </div>
        <div style={{
          padding: '6px 12px',
          borderRadius: 6,
          background: gammaRegime === 'POSITIVE' ? 'rgba(34,197,94,0.15)' : gammaRegime === 'NEGATIVE' ? 'rgba(239,68,68,0.15)' : 'rgba(161,161,170,0.15)',
          border: `1px solid ${gammaRegime === 'POSITIVE' ? colors.green : gammaRegime === 'NEGATIVE' ? colors.red : colors.textMuted}40`
        }}>
          <span style={{ color: gammaRegime === 'POSITIVE' ? colors.green : gammaRegime === 'NEGATIVE' ? colors.red : colors.textMuted, fontSize: 12, fontWeight: 600 }}>
            {gammaRegime} GEX: {totalGex > 0 ? '+' : ''}{totalGex.toFixed(3)}B
          </span>
        </div>
      </div>

      {/* GEX Profile Bar Chart - ohmygamma exact replica */}
      <div style={{
        background: 'rgba(15, 23, 42, 0.95)',
        borderRadius: 12,
        padding: '16px 0',
        marginBottom: 24,
        position: 'relative',
        border: '1px solid rgba(255,255,255,0.05)',
        cursor: chartTooltip ? 'none' : 'default'
      }}>
        {/* Chart Container with Y-axis */}
        <div style={{ position: 'relative', display: 'flex' }}>
          {(() => {
            const centerPrice = zeroGamma || currentPrice || 4600;
            const nearCenter = [...profile]
              .filter(p => Math.abs(p.strike - centerPrice) <= 300)
              .sort((a, b) => Math.abs(a.strike - centerPrice) - Math.abs(b.strike - centerPrice));
            const selectedStrikes = nearCenter.slice(0, 40);  // Show more levels
            const displayProfile = selectedStrikes.sort((a, b) => b.strike - a.strike);
            const localMax = Math.max(...displayProfile.map(p => Math.abs(p.gex || 0)), 0.01);

            // Find the single closest strike to spot price
            const closestToSpot = currentPrice ? displayProfile.reduce((closest, item) =>
              Math.abs(item.strike - currentPrice) < Math.abs(closest.strike - currentPrice) ? item : closest
            , displayProfile[0]) : null;

            // Find the single closest strike to zero gamma
            const closestToZG = zeroGamma ? displayProfile.reduce((closest, item) =>
              Math.abs(item.strike - zeroGamma) < Math.abs(closest.strike - zeroGamma) ? item : closest
            , displayProfile[0]) : null;

            // Colors: CALL = Cyan/Teal-Green, PUT = Pink/Magenta-Red
            const callBarColor = 'rgb(34, 211, 238)';
            const callBarFade = 'rgba(34, 211, 238, 0.25)';
            const putBarColor = 'rgb(244, 114, 182)';
            const putBarFade = 'rgba(244, 114, 182, 0.25)';

            // Calculate Y-axis range - extend 20 points beyond data range
            const strikes = displayProfile.map(p => p.strike);
            const dataMin = Math.min(...strikes);
            const dataMax = Math.max(...strikes);
            // Round to nearest $10 for clean Y-axis labels
            const yAxisMax = Math.ceil((dataMax + 20) / 10) * 10;
            const yAxisMin = Math.floor((dataMin - 20) / 10) * 10;
            const yAxisRange = yAxisMax - yAxisMin;
            const chartHeight = 900; // Taller chart to show more levels
            const pxPerPoint = chartHeight / yAxisRange;

            // Generate Y-axis labels at $10 intervals
            const yAxisLabels = [];
            for (let price = yAxisMax; price >= yAxisMin; price -= 10) {
              yAxisLabels.push(price);
            }

            // Render Y-axis + Chart area
            return (
              <div style={{ display: 'flex', width: '100%' }}>
                {/* Y-Axis Labels */}
                <div style={{
                  width: 55,
                  height: chartHeight,
                  position: 'relative',
                  borderRight: '1px solid rgba(255,255,255,0.1)',
                  marginRight: 8,
                  flexShrink: 0
                }}>
                  {yAxisLabels.map((price, i) => {
                    const yPos = ((yAxisMax - price) / yAxisRange) * chartHeight;
                    return (
                      <div key={price} style={{
                        position: 'absolute',
                        top: yPos - 6,
                        right: 8,
                        fontSize: 10,
                        fontFamily: "'JetBrains Mono', monospace",
                        color: 'rgba(148,163,184,0.5)'
                      }}>
                        {price}
                      </div>
                    );
                  })}
                </div>

                {/* Chart Area with bars positioned by strike price */}
                <div style={{ flex: 1, height: chartHeight, position: 'relative' }}>
                  {/* Grid lines at $10 intervals */}
                  {yAxisLabels.map((price) => {
                    const yPos = ((yAxisMax - price) / yAxisRange) * chartHeight;
                    return (
                      <div key={`grid-${price}`} style={{
                        position: 'absolute',
                        top: yPos,
                        left: 0,
                        right: 0,
                        height: 1,
                        background: 'rgba(255,255,255,0.04)',
                        pointerEvents: 'none'
                      }} />
                    );
                  })}

                  {/* SPOT line */}
                  {currentPrice && (
                    <div style={{
                      position: 'absolute',
                      top: ((yAxisMax - currentPrice) / yAxisRange) * chartHeight,
                      left: 0,
                      right: 0,
                      height: 2,
                      background: 'linear-gradient(90deg, rgba(132,204,22,0.8) 0%, rgba(132,204,22,0.2) 100%)',
                      zIndex: 5
                    }}>
                      <span style={{
                        position: 'absolute',
                        right: 0,
                        top: -10,
                        fontSize: 9,
                        background: 'rgba(132,204,22,0.2)',
                        border: '1px solid rgba(132,204,22,0.4)',
                        padding: '2px 6px',
                        borderRadius: 3,
                        color: '#84cc16',
                        fontWeight: 600,
                        fontFamily: "'JetBrains Mono', monospace"
                      }}>
                        SPOT {currentPrice?.toFixed(2)}
                      </span>
                    </div>
                  )}

                  {/* ZG line */}
                  {zeroGamma && Math.abs(zeroGamma - currentPrice) > 5 && (
                    <div style={{
                      position: 'absolute',
                      top: ((yAxisMax - zeroGamma) / yAxisRange) * chartHeight,
                      left: 0,
                      right: 0,
                      height: 2,
                      background: 'linear-gradient(90deg, rgba(34,211,238,0.6) 0%, rgba(34,211,238,0.1) 100%)',
                      zIndex: 4
                    }}>
                      <span style={{
                        position: 'absolute',
                        right: 0,
                        top: -10,
                        fontSize: 9,
                        background: 'rgba(34,211,238,0.15)',
                        border: '1px solid rgba(34,211,238,0.35)',
                        padding: '2px 6px',
                        borderRadius: 3,
                        color: '#22d3ee',
                        fontWeight: 600,
                        fontFamily: "'JetBrains Mono', monospace"
                      }}>
                        ZG {zeroGamma?.toFixed(0)}
                      </span>
                    </div>
                  )}

                  {/* GEX Bars - positioned by actual strike price */}
                  {displayProfile.map((item, idx) => {
                    const isCall = (item.gex || 0) < 0;
                    const barWidthPct = Math.min((Math.abs(item.gex || 0) / localMax) * 60, 60);
                    const isHovered = chartTooltip?.strike === item.strike;
                    const gexValue = Math.abs(item.gex || 0);
                    const gexLabel = gexValue >= 1 ? `${gexValue.toFixed(1)}B` : `${(gexValue * 1000).toFixed(0)}M`;
                    const isWall = gexValue > localMax * 0.25;
                    const distance = currentPrice ? Math.abs(Math.round(item.strike - currentPrice)) : 0;

                    // Calculate REAL C/P ratio from actual OI data
                    const callOI = item.call_oi || 0;
                    const putOI = item.put_oi || 0;
                    const totalOI = callOI + putOI || 1;
                    const callPct = Math.round((callOI / totalOI) * 100);
                    const putPct = 100 - callPct;

                    const labelColor = isCall ? '#22d3ee' : '#f472b6';

                    // Position based on actual strike price
                    const yPos = ((yAxisMax - item.strike) / yAxisRange) * chartHeight;

                    return (
                      <div
                        key={idx}
                        onMouseEnter={(e) => {
                          setMousePos({ x: e.clientX, y: e.clientY });
                          setChartTooltip({ strike: item.strike, gex: item.gex, isCall, gexLabel, isWall, callPct, putPct, callOI, putOI, distance: currentPrice ? Math.round(item.strike - currentPrice) : 0 });
                        }}
                        onMouseMove={(e) => setMousePos({ x: e.clientX, y: e.clientY })}
                        onMouseLeave={() => setChartTooltip(null)}
                        style={{
                          position: 'absolute',
                          top: yPos - 12,
                          left: 0,
                          right: 0,
                          display: 'flex',
                          alignItems: 'center',
                          height: 24,
                          cursor: chartTooltip ? 'none' : 'pointer',
                          zIndex: isHovered ? 10 : 1
                        }}
                      >
                        {/* Glass Bar */}
                        <div style={{
                          width: `${barWidthPct}%`,
                          minWidth: barWidthPct > 3 ? 10 : 0,
                          height: isHovered ? 28 : 22,
                          background: isCall
                            ? 'rgba(34, 211, 238, 0.5)'
                            : 'rgba(244, 114, 182, 0.5)',
                          backdropFilter: 'blur(4px)',
                          borderRadius: '3px 8px 8px 3px',
                          border: isCall
                            ? '1px solid rgba(34, 211, 238, 0.3)'
                            : '1px solid rgba(244, 114, 182, 0.3)',
                          boxShadow: isHovered
                            ? isCall
                              ? '0 0 12px rgba(34,211,238,0.7), 0 0 30px rgba(34,211,238,0.4), 0 8px 16px rgba(0,0,0,0.4)'
                              : '0 0 12px rgba(244,114,182,0.7), 0 0 30px rgba(244,114,182,0.4), 0 8px 16px rgba(0,0,0,0.4)'
                            : '0 2px 6px rgba(0,0,0,0.25)',
                          transition: 'all 0.15s ease-out',
                          transform: isHovered ? 'scale(1.02)' : 'none',
                          flexShrink: 0
                        }} />

                        {/* Label after bar */}
                        <div style={{
                          marginLeft: 8,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 4,
                          fontSize: 10,
                          fontFamily: "'Inter', sans-serif",
                          whiteSpace: 'nowrap'
                        }}>
                          <span style={{ color: 'rgba(148,163,184,0.6)' }}>←→</span>
                          <span style={{ color: 'rgba(255,255,255,0.85)', fontWeight: 500 }}>{isWall ? 'WALL' : 'LEVEL'}</span>
                          <span style={{
                            color: labelColor,
                            fontWeight: 600,
                            background: isCall ? 'rgba(34,211,238,0.12)' : 'rgba(244,114,182,0.12)',
                            padding: '1px 5px',
                            borderRadius: 3
                          }}>({isCall ? 'CALL' : 'PUT'})</span>
                          <span style={{ color: '#fff', fontWeight: 700, marginLeft: 2 }}>{gexLabel}</span>
                          <span style={{ color: 'rgba(148,163,184,0.5)', fontSize: 9 }}>[{distance}pts]</span>
                          <span style={{ color: 'rgba(148,163,184,0.4)', fontSize: 9 }}>C:{callPct}% P:{putPct}%</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            );
          })()}
        </div>

        {/* Legend */}
        <div style={{
          display: 'flex',
          justifyContent: 'flex-start',
          gap: 24,
          marginTop: 14,
          paddingTop: 10,
          paddingLeft: 70,
          borderTop: '1px solid rgba(255,255,255,0.04)',
          fontSize: 9,
          color: 'rgba(148,163,184,0.5)',
          fontFamily: "'Inter', sans-serif"
        }}>
          <span>←→ MAGNET (attractor)</span>
          <span>←→ WALL (barrier)</span>
          <span>Glow = Field Width</span>
        </div>

      </div>

      {/* Strategic Levels Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <h3 style={{ margin: 0, color: colors.text, fontSize: 18, fontWeight: 600 }}>Strategic Levels</h3>

        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* Level Count */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 12px', background: 'rgba(255,255,255,0.05)', borderRadius: 6 }}>
            <span style={{ fontSize: 11, color: colors.textMuted }}>LEVELS</span>
            <select
              value={levelCount}
              onChange={(e) => setLevelCount(Number(e.target.value))}
              style={{
                background: 'transparent',
                border: 'none',
                color: colors.text,
                fontSize: 12,
                cursor: 'pointer'
              }}
            >
              {[5, 10, 15, 20].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>

          {/* View Mode Toggle */}
          <div style={{ display: 'flex', background: 'rgba(255,255,255,0.05)', borderRadius: 6, overflow: 'hidden' }}>
            {[
              { id: 'table', icon: '☰' },
              { id: 'card', icon: '▦' },
              { id: 'quantum', icon: 'Ψ' }
            ].map(mode => (
              <button
                key={mode.id}
                onClick={() => setViewMode(mode.id)}
                style={{
                  padding: '8px 12px',
                  background: viewMode === mode.id ? colors.purple : 'transparent',
                  border: 'none',
                  color: viewMode === mode.id ? '#fff' : colors.textMuted,
                  fontSize: 14,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                {mode.icon}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* View Content */}
      {viewMode === 'table' && <TableView />}
      {viewMode === 'card' && <CardView />}
      {viewMode === 'quantum' && <QuantumView />}

      {/* Level Detail Modal */}
      {selectedLevel && (
        <LevelDetailModal
          level={selectedLevel}
          onClose={() => setSelectedLevel(null)}
        />
      )}

      {/* Floating Tooltip - rendered at root level to avoid backdrop-filter issues */}
      {chartTooltip && (() => {
        const typeColor = chartTooltip.isCall ? '#22d3ee' : '#f472b6';
        const typeBg = chartTooltip.isCall ? 'rgba(34,211,238,0.1)' : 'rgba(244,114,182,0.1)';
        const typeBorder = chartTooltip.isCall ? 'rgba(34,211,238,0.3)' : 'rgba(244,114,182,0.3)';
        const holdPct = chartTooltip.isCall ? 71 : 48;
        const breakPct = 100 - holdPct;

        // Position tooltip exactly at cursor (replaces cursor)
        let left = mousePos.x + 8;
        let top = mousePos.y - 8;
        // Boundary checks
        if (left + 240 > window.innerWidth - 10) left = mousePos.x - 248;
        if (top < 10) top = 10;
        if (top + 340 > window.innerHeight - 10) top = window.innerHeight - 350;

        return (
          <div style={{
            position: 'fixed',
            left,
            top,
            width: 240,
            background: 'rgba(15, 23, 42, 0.98)',
            border: `1px solid ${typeBorder}`,
            borderRadius: 12,
            padding: 16,
            zIndex: 99999,
            pointerEvents: 'none',
            boxShadow: `0 0 20px ${chartTooltip.isCall ? 'rgba(34,211,238,0.3)' : 'rgba(244,114,182,0.3)'}, 0 8px 32px rgba(0,0,0,0.5)`,
            fontFamily: "'Inter', sans-serif",
            transform: 'translateZ(0)'
          }}>
            {/* Header: Strike + Type badge */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
              <span style={{ fontSize: 30, fontWeight: 700, color: typeColor, fontFamily: "'JetBrains Mono', monospace" }}>
                {chartTooltip.strike?.toFixed(0)}
              </span>
              <span style={{ fontSize: 11, fontWeight: 600, color: typeColor, background: typeBg, padding: '4px 10px', borderRadius: 5, border: `1px solid ${typeBorder}` }}>
                ←→ {chartTooltip.isWall ? 'WALL' : 'LEVEL'} ({chartTooltip.isCall ? 'CALL' : 'PUT'})
              </span>
            </div>

            {/* C/P Ratio bar with actual OI */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'rgba(148,163,184,0.6)', marginBottom: 5 }}>
                <span>OPEN INTEREST</span>
                <span style={{ color: '#e2e8f0' }}>{((chartTooltip.callOI || 0) + (chartTooltip.putOI || 0)).toLocaleString()}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10, color: 'rgba(148,163,184,0.5)', marginBottom: 4 }}>
                <span>C: {(chartTooltip.callOI || 0).toLocaleString()}</span>
                <span>P: {(chartTooltip.putOI || 0).toLocaleString()}</span>
              </div>
              <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', background: 'rgba(0,0,0,0.4)' }}>
                <div style={{ width: `${chartTooltip.callPct}%`, background: '#22d3ee' }} />
                <div style={{ width: `${chartTooltip.putPct}%`, background: '#f472b6' }} />
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 9, marginTop: 3 }}>
                <span style={{ color: '#22d3ee' }}>{chartTooltip.callPct}%</span>
                <span style={{ color: '#f472b6' }}>{chartTooltip.putPct}%</span>
              </div>
            </div>

            {/* Quantum Field box */}
            <div style={{ background: 'rgba(139,92,246,0.1)', border: '1px solid rgba(139,92,246,0.2)', borderRadius: 8, padding: 10, marginBottom: 14 }}>
              <div style={{ fontSize: 11, color: '#a855f7', fontWeight: 600, marginBottom: 5 }}>QUANTUM FIELD</div>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, color: '#e2e8f0' }}>
                <span>L↑ {(chartTooltip.strike + 9).toFixed(0)}</span>
                <span style={{ color: 'rgba(148,163,184,0.4)' }}>→</span>
                <span>{(chartTooltip.strike - 9).toFixed(0)} L↓</span>
              </div>
              <div style={{ fontSize: 11, color: '#a855f7', textAlign: 'center', marginTop: 5 }}>18.4 pts influence</div>
            </div>

            {/* Mass + Effective row */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 14 }}>
              <div>
                <div style={{ fontSize: 11, color: 'rgba(148,163,184,0.5)' }}>MASS</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{chartTooltip.gexLabel}</div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 11, color: 'rgba(148,163,184,0.5)' }}>EFFECTIVE</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#e2e8f0' }}>{chartTooltip.gexLabel}</div>
              </div>
            </div>

            {/* Integrity bar */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'rgba(148,163,184,0.5)', marginBottom: 4 }}>
                <span>INTEGRITY</span>
                <span style={{ color: '#e2e8f0' }}>100%</span>
              </div>
              <div style={{ height: 5, background: 'rgba(0,0,0,0.4)', borderRadius: 3 }}>
                <div style={{ width: '100%', height: '100%', background: typeColor, borderRadius: 3 }} />
              </div>
            </div>

            {/* Hold/Break bar */}
            <div style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: 'rgba(148,163,184,0.5)', marginBottom: 4 }}>
                <span>HOLD / BREAK</span>
                <span>H:{holdPct}% B:{breakPct}%</span>
              </div>
              <div style={{ display: 'flex', height: 8, borderRadius: 4, overflow: 'hidden', background: 'rgba(0,0,0,0.4)' }}>
                <div style={{ width: `${holdPct}%`, background: '#22c55e' }} />
                <div style={{ width: `${breakPct}%`, background: '#ef4444' }} />
              </div>
            </div>

            {/* Distance footer */}
            <div style={{ textAlign: 'center', fontSize: 12, color: 'rgba(148,163,184,0.6)', paddingTop: 10, borderTop: '1px solid rgba(255,255,255,0.05)' }}>
              {chartTooltip.distance > 0 ? '+' : ''}{chartTooltip.distance} pts ({((Math.abs(chartTooltip.distance) / (currentPrice || 1)) * 100).toFixed(2)}%)
            </div>
          </div>
        );
      })()}
    </div>
  );
};

export default GEXPanel;
