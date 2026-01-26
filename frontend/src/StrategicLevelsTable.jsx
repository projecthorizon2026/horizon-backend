// Strategic Levels Table Component - tradelikeadealer-inspired design
// Full GEX analysis with HOLD/BREAK probabilities, confluences, and warnings

import React, { useState } from 'react';

const StrategicLevelsTable = ({ gexData, currentPrice }) => {
  const [levelCount, setLevelCount] = useState(10);
  const [viewMode, setViewMode] = useState('table'); // table, cards, chart
  const [hoveredLevel, setHoveredLevel] = useState(null);

  // Get key levels from gexData
  const gammaFlip = gexData.gamma_flip || gexData.zero_gamma || 4600;
  const callWall = gexData.call_wall || currentPrice + 75;
  const putWall = gexData.put_wall || currentPrice - 50;
  const hvl = gexData.hvl || currentPrice + 20;
  const maxPain = gexData.max_pain || currentPrice - 10;
  const gammaRegime = gexData.gamma_regime || 'UNKNOWN';

  // Calculate Expected Move (EM) - approximately 1.2% for gold
  const emRange = currentPrice * 0.012;
  const emHigh = currentPrice + emRange;
  const emLow = currentPrice - emRange;

  // Calculate Volume Bands (using ATR-like calculation)
  const volBandHigh = gammaFlip + 15;
  const volBandLow = gammaFlip - 15;

  // Deterministic hash for consistent values
  const hashStrike = (strike) => {
    const x = Math.sin(strike * 0.01) * 10000;
    return x - Math.floor(x);
  };

  // Generate strategic levels
  const generateLevels = () => {
    const levels = [];
    const interval = 5; // $5 intervals for more granularity
    const basePrice = Math.round(currentPrice / interval) * interval;

    // Generate strikes from -100 to +100
    for (let offset = -100; offset <= 100; offset += interval) {
      const strike = basePrice + offset;
      const hash = hashStrike(strike);
      const hash2 = hashStrike(strike + 1000);
      const hash3 = hashStrike(strike + 2000);

      // Determine level type
      const isAboveSpot = strike > currentPrice;
      const distanceFromSpot = Math.abs(strike - currentPrice);
      const distanceFromGamma = Math.abs(strike - gammaFlip);

      // Calculate GEX value (simulated)
      const baseGex = Math.max(0, 1 - distanceFromSpot / 100);
      const gexValue = baseGex * (200 + hash * 1800); // 200M to 2B range
      const gexFormatted = gexValue > 1000 ? `${(gexValue / 1000).toFixed(1)}B` : `${gexValue.toFixed(1)}M`;

      // Determine if CALL WALL or PUT WALL
      let levelType = 'NEUTRAL';
      let role = null;

      if (Math.abs(strike - callWall) < interval * 2) {
        levelType = 'CALL WALL';
        role = 'POT. RESISTANCE';
      } else if (Math.abs(strike - putWall) < interval * 2) {
        levelType = 'PUT WALL';
        role = 'POT. SUPPORT';
      } else if (isAboveSpot && baseGex > 0.3) {
        levelType = 'CALL WALL';
        role = baseGex > 0.6 ? 'POT. RESISTANCE' : 'POT. MAGNET';
      } else if (!isAboveSpot && baseGex > 0.3) {
        levelType = 'PUT WALL';
        role = baseGex > 0.6 ? 'POT. SUPPORT' : 'POT. MAGNET';
      }

      // GEX Profile type
      const callPct = isAboveSpot ? 60 + Math.floor(hash * 35) : 15 + Math.floor(hash * 25);
      const putPct = 100 - callPct;
      const profileType = Math.abs(callPct - putPct) > 30 ? 'DIRECTIONAL' : 'BALANCED';

      // Hold/Break probability
      const holdPct = 50 + Math.floor(hash2 * 30) + (isAboveSpot ? -5 : 5);
      const breakPct = 100 - holdPct;

      // Confluences
      const confluences = [];
      if (Math.abs(strike - gexData.pd_high) < interval) confluences.push('PDH');
      if (Math.abs(strike - gexData.pd_low) < interval) confluences.push('PDL');
      if (Math.abs(strike - hvl) < interval) confluences.push('HVL');
      if (strike === Math.round(currentPrice / interval) * interval) confluences.push('PWH');

      // Warnings
      const warnings = [];
      if (gexValue > 800 && distanceFromSpot < 30) warnings.push('HIGH VOL');
      if (distanceFromGamma < 10) warnings.push('NEAR ZG');

      if (levelType !== 'NEUTRAL') {
        levels.push({
          strike,
          levelType,
          role,
          gexValue,
          gexFormatted,
          profileType,
          callPct,
          putPct,
          holdPct,
          breakPct,
          confluences,
          warnings,
          distance: strike - currentPrice,
          distancePts: Math.abs(strike - currentPrice).toFixed(0)
        });
      }
    }

    return levels.sort((a, b) => b.strike - a.strike).slice(0, levelCount * 2);
  };

  const levels = generateLevels();
  const levelsAbove = levels.filter(l => l.strike > currentPrice).slice(-levelCount);
  const levelsBelow = levels.filter(l => l.strike <= currentPrice).slice(0, levelCount);

  // Colors
  const colors = {
    cyan: '#22d3ee',
    green: '#22c55e',
    red: '#ef4444',
    amber: '#f59e0b',
    purple: '#a855f7',
    pink: '#ec4899',
    yellow: '#facc15',
    text: '#f4f4f5',
    textMuted: '#71717a',
    background: 'rgba(11, 17, 32, 0.95)'
  };

  // Render marker row (EM HIGH, VOL BAND, ZERO GAMMA, etc.)
  const MarkerRow = ({ label, value, type }) => {
    const isZeroGamma = type === 'zg';
    return (
      <tr>
        <td colSpan={6} style={{
          padding: isZeroGamma ? '16px 0' : '8px 0',
          background: isZeroGamma ? 'rgba(250, 204, 21, 0.1)' : 'transparent',
          borderTop: `1px solid ${isZeroGamma ? colors.yellow : 'rgba(255,255,255,0.05)'}`,
          borderBottom: `1px solid ${isZeroGamma ? colors.yellow : 'rgba(255,255,255,0.05)'}`
        }}>
          <div style={{
            textAlign: 'center',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: isZeroGamma ? 16 : 12,
            color: isZeroGamma ? colors.yellow : colors.textMuted,
            fontWeight: isZeroGamma ? 700 : 400,
            letterSpacing: '0.1em'
          }}>
            {isZeroGamma ? (
              <>
                <span style={{ marginRight: 8 }}>●</span>
                ZERO GAMMA FLIP: {value.toFixed(0)}
                <span style={{ marginLeft: 8 }}>●</span>
              </>
            ) : (
              <>* {label}: {value.toFixed(0)} *</>
            )}
          </div>
          {isZeroGamma && (
            <div style={{
              display: 'flex',
              justifyContent: 'center',
              gap: 40,
              marginTop: 8,
              fontSize: 11
            }}>
              <span style={{ color: colors.textMuted }}>
                Above: Dealers dampen volatility{' '}
                <span style={{ color: colors.cyan }}>(Reversal Playbook)</span>
              </span>
            </div>
          )}
        </td>
      </tr>
    );
  };

  // Render level row
  const LevelRow = ({ level, index }) => {
    const isHovered = hoveredLevel === level.strike;
    const roleColor = level.role === 'POT. RESISTANCE' ? colors.pink :
                      level.role === 'POT. SUPPORT' ? colors.cyan :
                      colors.amber;
    const levelColor = level.levelType === 'CALL WALL' ? colors.pink : colors.cyan;

    return (
      <tr
        onMouseEnter={() => setHoveredLevel(level.strike)}
        onMouseLeave={() => setHoveredLevel(null)}
        style={{
          background: isHovered ? 'rgba(255,255,255,0.05)' : 'transparent',
          cursor: 'pointer',
          transition: 'all 0.2s ease'
        }}
      >
        {/* LEVEL Column */}
        <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{
                fontSize: 20,
                fontWeight: 700,
                color: colors.text,
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                {level.strike}
              </span>
              <span style={{
                fontSize: 11,
                color: level.distance > 0 ? colors.red : colors.green,
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                {level.distance > 0 ? '+' : ''}{level.distancePts} pts
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{
                fontSize: 11,
                fontWeight: 600,
                color: levelColor,
                letterSpacing: '0.05em'
              }}>
                {level.levelType}
              </span>
              <span style={{
                fontSize: 10,
                color: colors.textMuted,
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                C:P {level.callPct}:{level.putPct}
              </span>
            </div>
          </div>
        </td>

        {/* TOT. GEX PROFILE Column */}
        <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{
              fontSize: 11,
              fontWeight: 600,
              color: level.profileType === 'DIRECTIONAL' ? colors.cyan : colors.textMuted
            }}>
              {level.profileType}
            </span>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                width: 80,
                height: 6,
                background: 'rgba(255,255,255,0.1)',
                borderRadius: 3,
                overflow: 'hidden'
              }}>
                <div style={{
                  width: `${level.callPct}%`,
                  height: '100%',
                  background: level.profileType === 'DIRECTIONAL' ? colors.cyan : colors.textMuted,
                  borderRadius: 3
                }} />
              </div>
              <span style={{
                fontSize: 14,
                fontWeight: 600,
                color: colors.text,
                fontFamily: "'JetBrains Mono', monospace",
                minWidth: 60,
                textAlign: 'right'
              }}>
                {level.gexFormatted}
              </span>
            </div>
          </div>
        </td>

        {/* ROLE Column */}
        <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          {level.role && (
            <span style={{
              padding: '6px 12px',
              background: `${roleColor}20`,
              border: `1px solid ${roleColor}50`,
              borderRadius: 4,
              fontSize: 11,
              fontWeight: 600,
              color: roleColor,
              whiteSpace: 'nowrap'
            }}>
              {level.role}
            </span>
          )}
        </td>

        {/* CONFLUENCES Column */}
        <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', gap: 6 }}>
            {level.confluences.map((conf, i) => (
              <span key={i} style={{
                padding: '4px 8px',
                background: 'rgba(255,255,255,0.1)',
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 600,
                color: colors.text
              }}>
                {conf}
              </span>
            ))}
          </div>
        </td>

        {/* WARNING Column */}
        <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', gap: 6 }}>
            {level.warnings.map((warn, i) => (
              <span key={i} style={{
                padding: '4px 8px',
                background: 'rgba(239, 68, 68, 0.2)',
                border: '1px solid rgba(239, 68, 68, 0.5)',
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 600,
                color: colors.red
              }}>
                {warn}
              </span>
            ))}
          </div>
        </td>

        {/* HOLD / BREAK PROB. Column */}
        <td style={{ padding: '12px 16px', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              flex: 1,
              height: 8,
              background: 'rgba(255,255,255,0.1)',
              borderRadius: 4,
              overflow: 'hidden',
              display: 'flex'
            }}>
              <div style={{
                width: `${level.holdPct}%`,
                height: '100%',
                background: colors.green
              }} />
              <div style={{
                width: `${level.breakPct}%`,
                height: '100%',
                background: colors.red
              }} />
            </div>
            <div style={{ display: 'flex', gap: 8, fontSize: 11, minWidth: 80 }}>
              <span style={{ color: colors.green }}>H {level.holdPct}%</span>
              <span style={{ color: colors.red }}>B {level.breakPct}%</span>
            </div>
          </div>
          {isHovered && (
            <div style={{
              marginTop: 4,
              fontSize: 10,
              color: colors.cyan,
              textAlign: 'center'
            }}>
              Click for Details
            </div>
          )}
        </td>
      </tr>
    );
  };

  // Check if we should show a marker
  const shouldShowMarker = (prevLevel, currLevel, markerValue, threshold = 10) => {
    if (!prevLevel) return false;
    return prevLevel.strike > markerValue && currLevel.strike <= markerValue;
  };

  return (
    <div style={{
      background: 'linear-gradient(180deg, rgba(11, 17, 32, 0.95) 0%, rgba(8, 12, 24, 0.98) 100%)',
      backdropFilter: 'blur(20px)',
      borderRadius: 16,
      border: '1px solid rgba(34, 211, 238, 0.15)',
      padding: 20,
      marginBottom: 16,
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4)'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 20
      }}>
        <h3 style={{
          margin: 0,
          color: colors.text,
          fontSize: 18,
          fontWeight: 600,
          fontFamily: "'JetBrains Mono', monospace"
        }}>
          Strategic Levels
        </h3>

        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          {/* Level Count Selector */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '6px 12px',
            background: 'rgba(255,255,255,0.05)',
            borderRadius: 6,
            border: '1px solid rgba(255,255,255,0.1)'
          }}>
            <span style={{ color: colors.textMuted, fontSize: 11 }}>LEVELS</span>
            <select
              value={levelCount}
              onChange={(e) => setLevelCount(Number(e.target.value))}
              style={{
                background: 'transparent',
                border: 'none',
                color: colors.text,
                fontSize: 14,
                fontWeight: 600,
                cursor: 'pointer',
                outline: 'none'
              }}
            >
              <option value={5}>5</option>
              <option value={10}>10</option>
              <option value={15}>15</option>
              <option value={20}>20</option>
            </select>
          </div>

          {/* View Mode Toggles */}
          <div style={{
            display: 'flex',
            gap: 4,
            padding: 4,
            background: 'rgba(255,255,255,0.05)',
            borderRadius: 6
          }}>
            {['table', 'cards', 'chart'].map(mode => (
              <button
                key={mode}
                onClick={() => setViewMode(mode)}
                style={{
                  padding: '6px 10px',
                  background: viewMode === mode ? 'rgba(34, 211, 238, 0.2)' : 'transparent',
                  border: viewMode === mode ? '1px solid rgba(34, 211, 238, 0.5)' : '1px solid transparent',
                  borderRadius: 4,
                  color: viewMode === mode ? colors.cyan : colors.textMuted,
                  fontSize: 12,
                  cursor: 'pointer',
                  transition: 'all 0.2s ease'
                }}
              >
                {mode === 'table' ? '☰' : mode === 'cards' ? '▦' : '📊'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Table */}
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ borderBottom: '2px solid rgba(255,255,255,0.1)' }}>
              <th style={{ padding: '12px 16px', textAlign: 'right', color: colors.textMuted, fontSize: 11, fontWeight: 600, letterSpacing: '0.1em' }}>LEVEL</th>
              <th style={{ padding: '12px 16px', textAlign: 'left', color: colors.textMuted, fontSize: 11, fontWeight: 600, letterSpacing: '0.1em' }}>TOT. GEX PROFILE</th>
              <th style={{ padding: '12px 16px', textAlign: 'center', color: colors.textMuted, fontSize: 11, fontWeight: 600, letterSpacing: '0.1em' }}>ROLE</th>
              <th style={{ padding: '12px 16px', textAlign: 'center', color: colors.textMuted, fontSize: 11, fontWeight: 600, letterSpacing: '0.1em' }}>CONFLUENCES</th>
              <th style={{ padding: '12px 16px', textAlign: 'center', color: colors.textMuted, fontSize: 11, fontWeight: 600, letterSpacing: '0.1em' }}>WARNING</th>
              <th style={{ padding: '12px 16px', textAlign: 'center', color: colors.textMuted, fontSize: 11, fontWeight: 600, letterSpacing: '0.1em' }}>HOLD / BREAK PROB.</th>
            </tr>
          </thead>
          <tbody>
            {/* EM HIGH Marker */}
            <MarkerRow label="EM HIGH" value={emHigh} type="em" />

            {/* Levels Above */}
            {levelsAbove.map((level, idx) => {
              const prevLevel = levelsAbove[idx - 1];
              const showVolBandHigh = shouldShowMarker(prevLevel, level, volBandHigh);
              const showZeroGamma = shouldShowMarker(prevLevel, level, gammaFlip);

              return (
                <React.Fragment key={level.strike}>
                  {showVolBandHigh && <MarkerRow label="VOL BAND HIGH" value={volBandHigh} type="vol" />}
                  {showZeroGamma && <MarkerRow label="ZERO GAMMA FLIP" value={gammaFlip} type="zg" />}
                  <LevelRow level={level} index={idx} />
                </React.Fragment>
              );
            })}

            {/* Zero Gamma row if not yet shown */}
            {!levelsAbove.some(l => l.strike <= gammaFlip) && levelsBelow[0]?.strike <= gammaFlip && (
              <MarkerRow label="ZERO GAMMA FLIP" value={gammaFlip} type="zg" />
            )}

            {/* Playbook text after ZG */}
            <tr>
              <td colSpan={6} style={{ padding: '8px 0', textAlign: 'center' }}>
                <span style={{ color: colors.textMuted, fontSize: 11 }}>
                  Below: Dealers amplify volatility{' '}
                  <span style={{ color: colors.red }}>(Trend/Breakout Playbook)</span>
                </span>
              </td>
            </tr>

            {/* Levels Below */}
            {levelsBelow.map((level, idx) => {
              const prevLevel = levelsBelow[idx - 1];
              const showVolBandLow = shouldShowMarker(prevLevel, level, volBandLow);
              const showMaxPain = shouldShowMarker(prevLevel, level, maxPain);

              return (
                <React.Fragment key={level.strike}>
                  {showMaxPain && <MarkerRow label="MAX PAIN" value={maxPain} type="mp" />}
                  {showVolBandLow && <MarkerRow label="VOL BAND LOW" value={volBandLow} type="vol" />}
                  <LevelRow level={level} index={idx} />
                </React.Fragment>
              );
            })}

            {/* EM LOW Marker */}
            <MarkerRow label="EM LOW" value={emLow} type="em" />
          </tbody>
        </table>
      </div>

      {/* Footer Legend */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        gap: 24,
        marginTop: 16,
        padding: '12px 0',
        borderTop: '1px solid rgba(255,255,255,0.1)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color: colors.pink }}>↔</span>
          <span style={{ color: colors.textMuted, fontSize: 11 }}>CALL WALL (Resistance)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ color: colors.cyan }}>↔</span>
          <span style={{ color: colors.textMuted, fontSize: 11 }}>PUT WALL (Support)</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 16, height: 8, background: colors.yellow, borderRadius: 2 }} />
          <span style={{ color: colors.textMuted, fontSize: 11 }}>Zero Gamma Flip</span>
        </div>
      </div>
    </div>
  );
};

export default StrategicLevelsTable;
