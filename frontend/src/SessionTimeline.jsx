// Session Timeline Component - tradelikeadealer-inspired design
// Shows trading sessions with visual timeline

import { useState, useEffect } from 'react';

const SessionTimeline = ({ gexData, currentPrice }) => {
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Trading sessions (ET timezone)
  const sessions = [
    { id: 'asia', name: 'ASIA', time: '18:00', endTime: '03:00', label: '18:00 ET' },
    { id: 'london', name: 'LONDON', time: '03:00', endTime: '08:20', label: '03:00 ET' },
    { id: 'us_ib', name: 'US IB', time: '08:20', endTime: '09:30', label: '08:20 ET' },
    { id: 'us_open', name: 'US OPEN', time: '09:30', endTime: '16:00', label: '09:30 ET' },
    { id: 'close', name: 'CLOSE', time: '16:00', endTime: '18:00', label: '16:00 ET' },
  ];

  // Get current session based on ET time
  const getCurrentSession = () => {
    const etTime = new Date(currentTime.toLocaleString('en-US', { timeZone: 'America/New_York' }));
    const hours = etTime.getHours();
    const minutes = etTime.getMinutes();
    const timeNum = hours * 100 + minutes;

    if (timeNum >= 1800 || timeNum < 300) return 'asia';
    if (timeNum >= 300 && timeNum < 820) return 'london';
    if (timeNum >= 820 && timeNum < 930) return 'us_ib';
    if (timeNum >= 930 && timeNum < 1600) return 'us_open';
    return 'close';
  };

  const currentSession = getCurrentSession();
  const gammaFlip = gexData.gamma_flip || gexData.zero_gamma || 0;
  const distanceFromGamma = currentPrice && gammaFlip ? (currentPrice - gammaFlip).toFixed(1) : 0;
  const isAboveGamma = currentPrice > gammaFlip;
  const gammaRegime = gexData.gamma_regime || 'UNKNOWN';

  // Format current ET time
  const etTimeStr = currentTime.toLocaleString('en-US', {
    timeZone: 'America/New_York',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  });

  const etDateStr = currentTime.toLocaleString('en-US', {
    timeZone: 'America/New_York',
    year: 'numeric',
    month: 'short',
    day: '2-digit'
  });

  // Colors
  const colors = {
    cyan: '#22d3ee',
    green: '#22c55e',
    red: '#ef4444',
    amber: '#f59e0b',
    purple: '#a855f7',
    text: '#f4f4f5',
    textMuted: '#71717a',
    background: 'rgba(10, 10, 15, 0.95)',
    cardBg: 'rgba(20, 20, 30, 0.6)'
  };

  return (
    <div style={{
      background: colors.background,
      borderRadius: 16,
      border: '1px solid rgba(34, 211, 238, 0.15)',
      padding: 20,
      marginBottom: 16,
      fontFamily: "'Inter', -apple-system, sans-serif"
    }}>
      {/* Top Status Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        gap: 16,
        marginBottom: 20,
        padding: '8px 16px',
        background: 'rgba(0,0,0,0.3)',
        borderRadius: 8,
        fontSize: 12
      }}>
        <span style={{ color: colors.textMuted }}>UPDATED:</span>
        <span style={{ color: colors.text, fontFamily: "'JetBrains Mono', monospace" }}>
          {etDateStr} {etTimeStr} ET
        </span>
        <span style={{ color: colors.textMuted }}>|</span>
        <span style={{ color: colors.textMuted }}>SESSION:</span>
        <span style={{
          color: '#00ff88',
          fontWeight: 600,
          textTransform: 'uppercase',
          textShadow: '0 0 10px rgba(0, 255, 136, 0.5)'
        }}>
          {sessions.find(s => s.id === currentSession)?.name || 'UNKNOWN'}
        </span>
      </div>

      {/* Session Timeline */}
      <div style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        position: 'relative',
        padding: '0 40px',
        marginBottom: 24
      }}>
        {/* Connecting Line - passes through dots */}
        <div style={{
          position: 'absolute',
          left: 70,
          right: 70,
          top: 12,
          height: 2,
          background: 'rgba(255,255,255,0.15)',
          zIndex: 0
        }} />

        {sessions.map((session, idx) => {
          const isActive = session.id === currentSession;
          const isPast = sessions.findIndex(s => s.id === currentSession) > idx;

          return (
            <div
              key={session.id}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 8,
                zIndex: 1
              }}
            >
              {/* Circle Indicator */}
              <div style={{
                position: 'relative',
                width: 24,
                height: 24,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                {/* Outer ring for active - horizon green */}
                {isActive && (
                  <div style={{
                    position: 'absolute',
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    border: '2px solid #00ff88',
                    animation: 'sessionRingPulse 1.5s ease-in-out infinite'
                  }} />
                )}
                {/* Main circle */}
                <div style={{
                  width: 10,
                  height: 10,
                  borderRadius: '50%',
                  background: isActive ? '#00ff88' :
                              isPast ? 'rgba(255,255,255,0.5)' :
                              'rgba(255,255,255,0.2)',
                  boxShadow: isActive ? '0 0 12px #00ff88, 0 0 20px #00ff88' : 'none',
                  animation: isActive ? 'dotBlink 1.5s ease-in-out infinite' : 'none',
                  transition: 'all 0.3s ease'
                }} />
              </div>

              {/* Session Name */}
              <span style={{
                fontSize: 11,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? '#00ff88' : colors.textMuted,
                letterSpacing: '0.05em',
                marginTop: 4
              }}>
                {session.name}
              </span>

              {/* Time Label */}
              <span style={{
                fontSize: 9,
                color: colors.textMuted,
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                {session.label}
              </span>
            </div>
          );
        })}
      </div>

      {/* Market Pulse Section */}
      <div style={{
        background: colors.cardBg,
        borderRadius: 12,
        padding: 16,
        borderLeft: `3px solid ${gammaRegime === 'POSITIVE' ? colors.green : colors.red}`
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          flexWrap: 'wrap',
          gap: 16
        }}>
          {/* Left: Gamma Regime */}
          <div>
            <div style={{
              fontSize: 10,
              color: colors.textMuted,
              letterSpacing: '0.1em',
              marginBottom: 6
            }}>
              GAMMA REGIME
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {/* Pulsing indicator dot */}
              <div style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: gammaRegime === 'POSITIVE' ? colors.green : colors.red,
                boxShadow: `0 0 10px ${gammaRegime === 'POSITIVE' ? colors.green : colors.red}`,
                animation: 'gexDotPulse 2s ease-in-out infinite'
              }} />
              <span style={{
                fontSize: 18,
                fontWeight: 700,
                color: gammaRegime === 'POSITIVE' ? colors.green : colors.red
              }}>
                {gammaRegime}
              </span>
              <span style={{
                fontSize: 14,
                color: gammaRegime === 'POSITIVE' ? colors.green : colors.red,
                opacity: 0.7
              }}>
                ({gammaRegime === 'POSITIVE' ? 'STABILITY' : 'VOLATILITY'})
              </span>
            </div>
            <div style={{
              fontSize: 12,
              color: colors.textMuted,
              marginTop: 4,
              fontFamily: "'JetBrains Mono', monospace"
            }}>
              Net GEX: <span style={{ color: colors.text }}>{(gexData.total_gex || 0).toFixed(2)}B</span>
            </div>
          </div>

          {/* Right: Explanation */}
          <div style={{
            flex: 1,
            minWidth: 280,
            fontSize: 13,
            color: colors.text,
            lineHeight: 1.6
          }}>
            {currentPrice > 0 ? (
              <>
                Spot price is <span style={{
                  color: isAboveGamma ? colors.green : colors.red,
                  fontWeight: 600
                }}>
                  {Math.abs(distanceFromGamma)} points {isAboveGamma ? 'above' : 'below'}
                </span> Zero Gamma.
                {gammaRegime === 'POSITIVE' ? (
                  <> Dealers typically suppress volatility by selling into resistance and buying into support. The optimal playbook favors <span style={{ color: colors.cyan }}>reversal dynamics</span>.</>
                ) : (
                  <> Dealers amplify moves by buying rallies and selling dips. The optimal playbook favors <span style={{ color: colors.cyan }}>trend continuation</span>.</>
                )}
              </>
            ) : (
              <span style={{ color: colors.textMuted }}>Waiting for market data...</span>
            )}
          </div>
        </div>

        {/* Stats Row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
          gap: 12,
          marginTop: 16,
          paddingTop: 16,
          borderTop: '1px solid rgba(255,255,255,0.08)'
        }}>
          {[
            { label: 'CALL WALL', value: gexData.call_wall, color: colors.red },
            { label: 'GAMMA FLIP', value: gexData.gamma_flip || gexData.zero_gamma, color: colors.cyan },
            { label: 'PUT WALL', value: gexData.put_wall, color: colors.green },
            { label: 'EXP. MOVE', value: currentPrice ? (currentPrice * 0.012).toFixed(0) : 0, color: colors.amber, suffix: '' }
          ].map((stat, idx) => (
            <div
              key={idx}
              style={{
                background: 'rgba(0,0,0,0.3)',
                borderRadius: 8,
                padding: '12px 16px',
                textAlign: 'center'
              }}
            >
              <div style={{
                fontSize: 9,
                color: colors.textMuted,
                letterSpacing: '0.1em',
                marginBottom: 4
              }}>
                {stat.label}
              </div>
              <div style={{
                fontSize: 18,
                fontWeight: 600,
                color: stat.color,
                fontFamily: "'JetBrains Mono', monospace"
              }}>
                {stat.suffix !== '' ? '$' : ''}{(stat.value || 0).toLocaleString()}{stat.suffix || ''}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* CSS Animations */}
      <style>{`
        @keyframes sessionRingPulse {
          0%, 100% { opacity: 1; transform: scale(1); }
          50% { opacity: 0.4; transform: scale(1.3); }
        }
        @keyframes dotBlink {
          0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 12px #00ff88, 0 0 20px #00ff88; }
          50% { opacity: 0.7; transform: scale(0.9); box-shadow: 0 0 8px #00ff88, 0 0 15px #00ff88; }
        }
        @keyframes gexDotPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.6; }
        }
      `}</style>
    </div>
  );
};

export default SessionTimeline;
