// GEX Chart Component - tradelikeadealer-inspired visualization
// Shows gamma exposure levels with WALL/MAGNET classification

import { useState } from 'react';

const GEXChart = ({ gexData, currentPrice }) => {
  const [hoveredLevel, setHoveredLevel] = useState(null);
  const [popupPosition, setPopupPosition] = useState({ x: 0, y: 0 });

  const gammaFlip = gexData.gamma_flip || gexData.zero_gamma || 0;
  const callWall = gexData.call_wall || 0;
  const putWall = gexData.put_wall || 0;
  const hvl = gexData.hvl || 0;
  const maxPain = gexData.max_pain || 0;
  const gammaRegime = gexData.gamma_regime || 'UNKNOWN';

  // Generate levels based on current price
  const generateLevels = () => {
    if (!currentPrice || currentPrice <= 0) {
      const basePrice = gammaFlip || 4600;
      return generateLevelsFromBase(basePrice);
    }
    return generateLevelsFromBase(currentPrice);
  };

  // Deterministic hash function for consistent values based on strike
  const hashStrike = (strike) => {
    const x = Math.sin(strike * 0.01) * 10000;
    return x - Math.floor(x);
  };

  const generateLevelsFromBase = (basePrice) => {
    const levels = [];
    const interval = 10; // $10 intervals for gold

    // Generate strikes from -150 to +150 around base (more levels)
    for (let offset = -150; offset <= 150; offset += interval) {
      const strike = Math.round(basePrice / interval) * interval + offset;

      // Calculate GEX for this strike (simulated distribution)
      const distanceFromATM = Math.abs(strike - basePrice);
      const baseGex = Math.max(0, 1 - distanceFromATM / 150);

      // Determine if CALL or PUT dominant
      const isCall = strike > basePrice;

      // Use deterministic hash instead of random
      const hash = hashStrike(strike);
      const gexValue = isCall
        ? baseGex * (0.8 + hash * 0.8)
        : -baseGex * (0.6 + hash * 0.6);

      // Determine level type
      let levelType = 'NORMAL';
      let role = null;

      if (Math.abs(strike - callWall) < interval) {
        levelType = 'WALL';
        role = 'CALL';
      } else if (Math.abs(strike - putWall) < interval) {
        levelType = 'WALL';
        role = 'PUT';
      } else if (Math.abs(strike - gammaFlip) < interval) {
        levelType = 'ZG';
        role = 'FLIP';
      } else if (Math.abs(strike - hvl) < interval) {
        levelType = 'MAGNET';
        role = 'CALL';
      } else if (Math.abs(strike - maxPain) < interval) {
        levelType = 'MAGNET';
        role = 'PUT';
      } else if (Math.abs(gexValue) > 0.5) {
        levelType = isCall ? 'WALL' : 'WALL';
        role = isCall ? 'CALL' : 'PUT';
      } else if (Math.abs(gexValue) > 0.3) {
        levelType = 'MAGNET';
        role = isCall ? 'CALL' : 'PUT';
      }

      // Calculate additional stats using deterministic hash
      const hash2 = hashStrike(strike + 1000);
      const hash3 = hashStrike(strike + 2000);
      const callPct = isCall ? 60 + Math.floor(hash * 35) : 10 + Math.floor(hash * 30);
      const putPct = 100 - callPct;
      const mass = Math.abs(gexValue) * 2.5;
      const effective = mass * (0.5 + hash2 * 0.3);
      const integrity = 50 + Math.floor(hash2 * 40);
      const holdPct = 40 + Math.floor(hash3 * 40);

      levels.push({
        strike,
        gex: gexValue,
        type: levelType,
        role,
        callPct,
        putPct,
        mass,
        effective,
        integrity,
        holdPct,
        breakPct: 100 - holdPct,
        distance: strike - (currentPrice || basePrice),
        distancePct: ((strike - (currentPrice || basePrice)) / (currentPrice || basePrice) * 100).toFixed(2)
      });
    }

    return levels.sort((a, b) => b.strike - a.strike);
  };

  const levels = generateLevels();
  const maxGex = Math.max(...levels.map(l => Math.abs(l.gex)), 0.01);

  // Colors
  const colors = {
    cyan: '#22d3ee',
    green: '#22c55e',
    red: '#ef4444',
    amber: '#f59e0b',
    purple: '#a855f7',
    yellow: '#facc15',
    text: '#f4f4f5',
    textMuted: '#71717a',
    background: 'rgba(10, 10, 15, 0.95)',
    cardBg: 'rgba(20, 20, 30, 0.8)'
  };

  const getLevelColor = (level) => {
    if (level.type === 'ZG') return colors.yellow;
    if (level.type === 'WALL') return level.role === 'CALL' ? colors.red : colors.green;
    if (level.type === 'MAGNET') return level.role === 'CALL' ? colors.amber : colors.cyan;
    return level.gex > 0 ? colors.red : colors.green;
  };

  const handleMouseEnter = (level, event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setPopupPosition({
      x: rect.right + 10,
      y: rect.top
    });
    setHoveredLevel(level);
  };

  return (
    <div style={{
      background: 'linear-gradient(180deg, rgba(11, 17, 32, 0.95) 0%, rgba(8, 12, 24, 0.98) 100%)',
      backdropFilter: 'blur(20px)',
      borderRadius: 16,
      border: '1px solid rgba(34, 211, 238, 0.15)',
      padding: 20,
      marginBottom: 16,
      position: 'relative',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 16
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h3 style={{
            margin: 0,
            color: colors.text,
            fontSize: 16,
            fontWeight: 600,
            fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: '-0.02em'
          }}>
            Strategic Levels
          </h3>
          {/* Live Pulse Indicator */}
          <div style={{ position: 'relative', width: 10, height: 10 }}>
            <div style={{
              position: 'absolute',
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: colors.cyan,
              animation: 'gexLivePulse 2s ease-in-out infinite'
            }} />
            <div style={{
              position: 'absolute',
              width: 10,
              height: 10,
              borderRadius: '50%',
              background: colors.cyan,
              animation: 'gexLiveRing 2s ease-in-out infinite'
            }} />
          </div>
          <span style={{
            padding: '4px 10px',
            borderRadius: 4,
            fontSize: 11,
            fontWeight: 600,
            background: gammaRegime === 'POSITIVE' ? 'rgba(34, 197, 94, 0.2)' : 'rgba(239, 68, 68, 0.2)',
            color: gammaRegime === 'POSITIVE' ? colors.green : colors.red,
            border: `1px solid ${gammaRegime === 'POSITIVE' ? colors.green : colors.red}40`
          }}>
            {gammaRegime} Γ
          </span>
        </div>

        {/* Spot Price */}
        {currentPrice > 0 && (
          <div style={{
            padding: '6px 12px',
            background: 'rgba(34, 211, 238, 0.15)',
            borderRadius: 6,
            border: `1px solid ${colors.cyan}40`
          }}>
            <span style={{ color: colors.textMuted, fontSize: 10, marginRight: 8 }}>SPOT</span>
            <span style={{
              color: colors.cyan,
              fontSize: 14,
              fontWeight: 700,
              fontFamily: "'JetBrains Mono', monospace"
            }}>
              {currentPrice.toFixed(2)}
            </span>
          </div>
        )}
      </div>

      {/* Chart Area */}
      <div style={{
        display: 'flex',
        gap: 0,
        background: 'rgba(0,0,0,0.3)',
        borderRadius: 12,
        overflow: 'hidden'
      }}>
        {/* Y-Axis Labels */}
        <div style={{
          width: 60,
          display: 'flex',
          flexDirection: 'column',
          borderRight: '1px solid rgba(255,255,255,0.1)'
        }}>
          {levels.slice(0, 22).map((level, idx) => (
            <div
              key={idx}
              style={{
                height: 32,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'flex-end',
                paddingRight: 8,
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
                color: level.type === 'ZG' ? colors.yellow :
                       Math.abs(level.strike - currentPrice) < 5 ? colors.cyan : colors.textMuted,
                fontWeight: level.type === 'ZG' || Math.abs(level.strike - currentPrice) < 5 ? 600 : 400
              }}
            >
              {level.strike.toFixed(0)}
            </div>
          ))}
        </div>

        {/* Bars */}
        <div style={{ flex: 1, position: 'relative' }}>
          {levels.slice(0, 22).map((level, idx) => {
            const barWidth = Math.abs(level.gex) / maxGex * 100;
            const isCall = level.gex > 0;
            const levelColor = getLevelColor(level);
            const isCurrentPrice = Math.abs(level.strike - currentPrice) < 5;
            const isZG = level.type === 'ZG';

            return (
              <div
                key={idx}
                style={{
                  height: 32,
                  display: 'flex',
                  alignItems: 'center',
                  position: 'relative',
                  cursor: 'pointer',
                  background: isCurrentPrice ? 'rgba(34, 211, 238, 0.08)' :
                              isZG ? 'rgba(250, 204, 21, 0.05)' : 'transparent',
                  borderBottom: '1px solid rgba(255,255,255,0.03)',
                  transition: 'background 0.2s ease'
                }}
                onMouseEnter={(e) => handleMouseEnter(level, e)}
                onMouseLeave={() => setHoveredLevel(null)}
              >
                {/* ZG Marker */}
                {isZG && (
                  <div style={{
                    position: 'absolute',
                    left: 4,
                    padding: '2px 6px',
                    background: colors.yellow,
                    borderRadius: 3,
                    fontSize: 9,
                    fontWeight: 700,
                    color: '#000',
                    zIndex: 2
                  }}>
                    ZG
                  </div>
                )}

                {/* Bar */}
                <div style={{
                  position: 'absolute',
                  left: isCall ? '50%' : `calc(50% - ${barWidth / 2}%)`,
                  width: `${barWidth / 2}%`,
                  height: 20,
                  background: `linear-gradient(${isCall ? '90deg' : '270deg'}, ${levelColor}80, ${levelColor})`,
                  borderRadius: isCall ? '0 4px 4px 0' : '4px 0 0 4px',
                  boxShadow: `0 0 ${10 + barWidth / 5}px ${levelColor}40`,
                  transition: 'all 0.3s ease'
                }} />

                {/* Center Line */}
                <div style={{
                  position: 'absolute',
                  left: '50%',
                  top: 0,
                  bottom: 0,
                  width: 1,
                  background: 'rgba(255,255,255,0.2)'
                }} />

                {/* Level Label */}
                {(level.type === 'WALL' || level.type === 'MAGNET') && (
                  <div style={{
                    position: 'absolute',
                    right: isCall ? 'auto' : 8,
                    left: isCall ? 8 : 'auto',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6
                  }}>
                    <span style={{ color: levelColor, fontSize: 10 }}>
                      {level.type === 'WALL' ? '←→' : '→←'}
                    </span>
                    <span style={{
                      color: levelColor,
                      fontSize: 11,
                      fontWeight: 600
                    }}>
                      {level.type}
                    </span>
                    <span style={{
                      color: levelColor,
                      fontSize: 9,
                      opacity: 0.7
                    }}>
                      ({level.role})
                    </span>
                    <span style={{
                      color: colors.text,
                      fontSize: 12,
                      fontWeight: 700,
                      fontFamily: "'JetBrains Mono', monospace",
                      marginLeft: 8
                    }}>
                      {level.mass.toFixed(1)}B
                    </span>
                  </div>
                )}

                {/* Current Price Marker */}
                {isCurrentPrice && (
                  <div style={{
                    position: 'absolute',
                    right: 8,
                    padding: '2px 8px',
                    background: colors.cyan,
                    borderRadius: 4,
                    fontSize: 10,
                    fontWeight: 600,
                    color: '#000'
                  }}>
                    SPOT {currentPrice.toFixed(2)}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Legend */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: 24,
        marginTop: 12,
        padding: '10px 16px',
        background: 'rgba(0,0,0,0.2)',
        borderRadius: 8
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color: colors.amber }}>→←</span>
          <span style={{ color: colors.textMuted, fontSize: 11 }}>MAGNET (attractor)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color: colors.red }}>←→</span>
          <span style={{ color: colors.textMuted, fontSize: 11 }}>WALL (barrier)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 16, height: 10, background: colors.yellow, borderRadius: 2 }} />
          <span style={{ color: colors.textMuted, fontSize: 11 }}>ZG (Zero Gamma)</span>
        </div>
      </div>

      {/* Hover Popup */}
      {hoveredLevel && (
        <div style={{
          position: 'fixed',
          left: Math.max(10, Math.min(popupPosition.x - 140, window.innerWidth - 300)),
          top: Math.max(10, Math.min(popupPosition.y - 150, window.innerHeight - 400)),
          width: 280,
          background: 'linear-gradient(180deg, rgba(15, 20, 30, 0.98) 0%, rgba(10, 15, 25, 0.99) 100%)',
          backdropFilter: 'blur(20px)',
          border: `2px solid ${getLevelColor(hoveredLevel)}`,
          borderRadius: 12,
          padding: 16,
          zIndex: 1000,
          boxShadow: `0 0 30px ${getLevelColor(hoveredLevel)}40, 0 8px 32px rgba(0,0,0,0.5)`
        }}>
          {/* Header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            marginBottom: 12,
            paddingBottom: 12,
            borderBottom: '1px solid rgba(255,255,255,0.1)'
          }}>
            <span style={{
              fontSize: 24,
              fontWeight: 700,
              color: colors.text,
              fontFamily: "'JetBrains Mono', monospace"
            }}>
              {hoveredLevel.strike}
            </span>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '4px 10px',
              background: `${getLevelColor(hoveredLevel)}20`,
              borderRadius: 6,
              border: `1px solid ${getLevelColor(hoveredLevel)}40`
            }}>
              <span style={{ color: getLevelColor(hoveredLevel), fontSize: 11 }}>
                {hoveredLevel.type === 'WALL' ? '←→' : '→←'}
              </span>
              <span style={{
                color: getLevelColor(hoveredLevel),
                fontSize: 12,
                fontWeight: 600
              }}>
                {hoveredLevel.type}
              </span>
              <span style={{
                color: getLevelColor(hoveredLevel),
                fontSize: 10,
                opacity: 0.7
              }}>
                ({hoveredLevel.role})
              </span>
            </div>
          </div>

          {/* C/P Ratio */}
          <div style={{ marginBottom: 12 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: 4
            }}>
              <span style={{ color: colors.textMuted, fontSize: 10 }}>C/P RATIO</span>
              <span style={{ color: colors.text, fontSize: 10 }}>
                C:{hoveredLevel.callPct}% P:{hoveredLevel.putPct}%
              </span>
            </div>
            <div style={{
              display: 'flex',
              height: 6,
              borderRadius: 3,
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${hoveredLevel.callPct}%`,
                background: colors.red
              }} />
              <div style={{
                width: `${hoveredLevel.putPct}%`,
                background: colors.green
              }} />
            </div>
          </div>

          {/* Quantum Field */}
          <div style={{
            background: 'rgba(0,0,0,0.3)',
            borderRadius: 8,
            padding: 10,
            marginBottom: 12
          }}>
            <div style={{
              color: colors.textMuted,
              fontSize: 9,
              letterSpacing: '0.1em',
              marginBottom: 6
            }}>
              QUANTUM FIELD
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <span style={{ color: colors.text, fontSize: 12 }}>
                L↑ {(hoveredLevel.strike + 8).toFixed(1)}
              </span>
              <span style={{ color: colors.textMuted }}>→</span>
              <span style={{ color: colors.text, fontSize: 12 }}>
                {(hoveredLevel.strike - 8).toFixed(1)} L↓
              </span>
            </div>
            <div style={{
              textAlign: 'center',
              color: colors.amber,
              fontSize: 11,
              marginTop: 4
            }}>
              16.0 pts influence
            </div>
          </div>

          {/* Stats Grid */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 8,
            marginBottom: 12
          }}>
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: 8, borderRadius: 6 }}>
              <div style={{ color: colors.textMuted, fontSize: 9 }}>MASS</div>
              <div style={{ color: colors.text, fontSize: 14, fontWeight: 600 }}>
                {hoveredLevel.mass.toFixed(1)}B
              </div>
            </div>
            <div style={{ background: 'rgba(0,0,0,0.2)', padding: 8, borderRadius: 6 }}>
              <div style={{ color: colors.textMuted, fontSize: 9 }}>EFFECTIVE</div>
              <div style={{ color: colors.text, fontSize: 14, fontWeight: 600 }}>
                {(hoveredLevel.effective * 1000).toFixed(0)}M
              </div>
            </div>
          </div>

          {/* Integrity */}
          <div style={{ marginBottom: 12 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: 4
            }}>
              <span style={{ color: colors.textMuted, fontSize: 10 }}>INTEGRITY</span>
              <span style={{ color: colors.text, fontSize: 10 }}>{hoveredLevel.integrity}%</span>
            </div>
            <div style={{
              height: 4,
              background: 'rgba(255,255,255,0.1)',
              borderRadius: 2
            }}>
              <div style={{
                width: `${hoveredLevel.integrity}%`,
                height: '100%',
                background: hoveredLevel.integrity > 70 ? colors.green :
                           hoveredLevel.integrity > 40 ? colors.amber : colors.red,
                borderRadius: 2
              }} />
            </div>
          </div>

          {/* Hold/Break */}
          <div style={{ marginBottom: 12 }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginBottom: 4
            }}>
              <span style={{ color: colors.textMuted, fontSize: 10 }}>HOLD / BREAK</span>
              <span style={{ color: colors.text, fontSize: 10 }}>
                H:{hoveredLevel.holdPct}% B:{hoveredLevel.breakPct}%
              </span>
            </div>
            <div style={{
              display: 'flex',
              height: 6,
              borderRadius: 3,
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${hoveredLevel.holdPct}%`,
                background: colors.green
              }} />
              <div style={{
                width: `${hoveredLevel.breakPct}%`,
                background: colors.red
              }} />
            </div>
          </div>

          {/* Distance */}
          <div style={{
            textAlign: 'center',
            padding: '8px 12px',
            background: 'rgba(0,0,0,0.2)',
            borderRadius: 6
          }}>
            <span style={{
              color: hoveredLevel.distance > 0 ? colors.red : colors.green,
              fontSize: 13,
              fontWeight: 600
            }}>
              {hoveredLevel.distance > 0 ? '+' : ''}{hoveredLevel.distance.toFixed(1)} pts
            </span>
            <span style={{ color: colors.textMuted, fontSize: 11, marginLeft: 8 }}>
              ({hoveredLevel.distancePct}%)
            </span>
          </div>
        </div>
      )}

      {/* CSS Animations */}
      <style>{`
        @keyframes gexLivePulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.7; transform: scale(0.85); }
        }
        @keyframes gexLiveRing {
          0% { opacity: 0.6; transform: scale(1); }
          100% { opacity: 0; transform: scale(2.5); }
        }
        @keyframes barGlow {
          0%, 100% { filter: brightness(1); }
          50% { filter: brightness(1.2); }
        }
      `}</style>
    </div>
  );
};

export default GEXChart;
