// Price Ladder Component - Add this to App.jsx

const PriceLadder = ({ metrics, gexData }) => {
  const currentPrice = metrics.current_price || 0;
  
  // Reference levels - includes GEX levels (Call Wall, Put Wall, Gamma Flip)
  const referenceLevels = [
    // GEX Levels - Key Gamma Levels
    gexData.call_wall > 0 && { price: gexData.call_wall, name: 'CALL WALL', color: '#ef4444', type: 'gex', icon: '🛡️' },
    gexData.put_wall > 0 && { price: gexData.put_wall, name: 'PUT WALL', color: '#22c55e', type: 'gex', icon: '🛡️' },
    gexData.gamma_flip > 0 && { price: gexData.gamma_flip, name: 'GAMMA FLIP', color: '#facc15', type: 'gex', icon: '⚡' },
    gexData.hvl > 0 && { price: gexData.hvl, name: 'HVL', color: '#a855f7', type: 'gex', icon: '📊' },
    gexData.max_pain > 0 && { price: gexData.max_pain, name: 'MAX PAIN', color: '#f97316', type: 'gex', icon: '🎯' },
    gexData.zero_gamma > 0 && { price: gexData.zero_gamma, name: 'ZERO Γ', color: '#22d3ee', type: 'gex', icon: '⚖️' },

    // Market Profile Levels
    gexData.pd_high > 0 && { price: gexData.pd_high, name: 'PD High', color: '#ff4466', type: 'mp' },
    metrics.ib_high > 0 && { price: metrics.ib_high, name: 'IB High', color: '#ffaa00', type: 'mp' },
    metrics.vwap > 0 && { price: metrics.vwap, name: 'VWAP', color: '#00ddff', type: 'mp' },
    (metrics.ib_high > 0 && metrics.ib_low > 0) && { price: (metrics.ib_high + metrics.ib_low) / 2, name: 'IB Mid', color: '#ffcc00', type: 'mp' },
    metrics.ib_low > 0 && { price: metrics.ib_low, name: 'IB Low', color: '#00ff88', type: 'mp' },
    gexData.pdpoc > 0 && { price: gexData.pdpoc, name: 'pdPOC', color: '#ffaa00', type: 'mp' },
    gexData.pd_low > 0 && { price: gexData.pd_low, name: 'PD Low', color: '#00ff88', type: 'mp' },

    // Static R/S Levels
    { price: currentPrice + 50, name: 'R3', color: '#ff6b6b', type: 'rs' },
    { price: currentPrice + 30, name: 'R2', color: '#ff8c8c', type: 'rs' },
    { price: currentPrice + 15, name: 'R1', color: '#ffaaaa', type: 'rs' },
    { price: currentPrice - 15, name: 'S1', color: '#88ff88', type: 'rs' },
    { price: currentPrice - 30, name: 'S2', color: '#66dd66', type: 'rs' },
    { price: currentPrice - 50, name: 'S3', color: '#44bb44', type: 'rs' },
  ].filter(Boolean).sort((a, b) => b.price - a.price);

  // Separate levels above and below current price
  const levelsAbove = referenceLevels.filter(l => l.price > currentPrice).slice(-10);
  const levelsBelow = referenceLevels.filter(l => l.price <= currentPrice).slice(0, 10);

  // Calculate 5-min volume split
  const buyPct = metrics.total_volume > 0 
    ? (metrics.buy_volume / metrics.total_volume * 100).toFixed(1) 
    : 50;
  const sellPct = metrics.total_volume > 0 
    ? (metrics.sell_volume / metrics.total_volume * 100).toFixed(1) 
    : 50;

  const LevelRow = ({ level, position }) => {
    const distance = Math.abs(level.price - currentPrice).toFixed(2);
    const isClose = Math.abs(level.price - currentPrice) < 20;
    const isGexLevel = level.type === 'gex';

    return (
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 16px',
        background: isGexLevel
          ? `linear-gradient(90deg, ${level.color}20 0%, transparent 100%)`
          : isClose ? `${level.color}15` : 'transparent',
        borderLeft: `4px solid ${level.color}`,
        marginBottom: 2,
        transition: 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
        opacity: isClose ? 1 : 0.7,
        borderRadius: isGexLevel ? '0 8px 8px 0' : 0,
        boxShadow: isGexLevel && isClose ? `0 0 15px ${level.color}30` : 'none'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          minWidth: 140
        }}>
          {level.icon && (
            <span style={{ fontSize: 14 }}>{level.icon}</span>
          )}
          <span style={{
            color: level.color,
            fontSize: isGexLevel ? 12 : 11,
            fontWeight: isGexLevel ? 700 : 600,
            textTransform: 'uppercase',
            letterSpacing: isGexLevel ? 0.5 : 1,
            fontFamily: isGexLevel ? "'JetBrains Mono', monospace" : 'inherit'
          }}>
            {level.name}
          </span>
          {isGexLevel && (
            <span style={{
              padding: '2px 6px',
              background: `${level.color}30`,
              borderRadius: 4,
              fontSize: 9,
              color: level.color,
              fontWeight: 600
            }}>
              GEX
            </span>
          )}
        </div>
        <div style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: isGexLevel ? 18 : 16,
          fontWeight: 700,
          color: level.color,
          textShadow: isClose || isGexLevel ? `0 0 10px ${level.color}` : 'none'
        }}>
          ${level.price.toFixed(2)}
        </div>
        <div style={{
          fontSize: 11,
          color: '#888',
          minWidth: 70,
          textAlign: 'right',
          fontFamily: "'JetBrains Mono', monospace"
        }}>
          {position === 'above' ? '↑' : '↓'} ${distance}
        </div>
      </div>
    );
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ 
        color: '#fff', 
        marginBottom: 8,
        display: 'flex',
        alignItems: 'center',
        gap: 12
      }}>
        📊 Price Ladder
      </h2>
      <p style={{ color: '#888', marginBottom: 24, fontSize: 13 }}>
        Live price with reference levels • Updates in real-time
      </p>

      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 300px 1fr',
        gap: 24,
        maxWidth: 1200,
        margin: '0 auto'
      }}>
        
        {/* Volume Bars - Left */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          gap: 16
        }}>
          {/* Buy Volume */}
          <div style={{
            background: 'rgba(0,255,136,0.1)',
            border: '1px solid rgba(0,255,136,0.3)',
            borderRadius: 12,
            padding: 20,
            textAlign: 'center'
          }}>
            <div style={{ color: '#888', fontSize: 11, marginBottom: 8, letterSpacing: 2 }}>BUY VOLUME</div>
            <div style={{
              fontSize: 36,
              fontWeight: 700,
              color: '#00ff88',
              fontFamily: "'JetBrains Mono', monospace",
              textShadow: '0 0 20px rgba(0,255,136,0.5)'
            }}>
              {(metrics.buy_volume || 0).toLocaleString()}
            </div>
            <div style={{
              marginTop: 12,
              height: 8,
              background: 'rgba(0,0,0,0.3)',
              borderRadius: 4,
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${buyPct}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #00ff88, #00ddaa)',
                borderRadius: 4,
                transition: 'width 0.5s ease'
              }} />
            </div>
            <div style={{ color: '#00ff88', fontSize: 14, marginTop: 8, fontWeight: 600 }}>
              {buyPct}%
            </div>
          </div>

          {/* Sell Volume */}
          <div style={{
            background: 'rgba(255,68,102,0.1)',
            border: '1px solid rgba(255,68,102,0.3)',
            borderRadius: 12,
            padding: 20,
            textAlign: 'center'
          }}>
            <div style={{ color: '#888', fontSize: 11, marginBottom: 8, letterSpacing: 2 }}>SELL VOLUME</div>
            <div style={{
              fontSize: 36,
              fontWeight: 700,
              color: '#ff4466',
              fontFamily: "'JetBrains Mono', monospace",
              textShadow: '0 0 20px rgba(255,68,102,0.5)'
            }}>
              {(metrics.sell_volume || 0).toLocaleString()}
            </div>
            <div style={{
              marginTop: 12,
              height: 8,
              background: 'rgba(0,0,0,0.3)',
              borderRadius: 4,
              overflow: 'hidden'
            }}>
              <div style={{
                width: `${sellPct}%`,
                height: '100%',
                background: 'linear-gradient(90deg, #ff4466, #ff6688)',
                borderRadius: 4,
                transition: 'width 0.5s ease'
              }} />
            </div>
            <div style={{ color: '#ff4466', fontSize: 14, marginTop: 8, fontWeight: 600 }}>
              {sellPct}%
            </div>
          </div>

          {/* Delta */}
          <div style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 12,
            padding: 16,
            textAlign: 'center'
          }}>
            <div style={{ color: '#888', fontSize: 11, marginBottom: 4 }}>CUMULATIVE DELTA</div>
            <div style={{
              fontSize: 24,
              fontWeight: 700,
              color: (metrics.cumulative_delta || 0) >= 0 ? '#00ff88' : '#ff4466',
              fontFamily: 'monospace'
            }}>
              {(metrics.cumulative_delta || 0).toLocaleString()}
            </div>
          </div>
        </div>

        {/* Price Ladder - Center */}
        <div style={{
          background: 'linear-gradient(180deg, rgba(20,20,30,0.95) 0%, rgba(10,10,15,0.98) 100%)',
          border: '2px solid rgba(255,255,255,0.1)',
          borderRadius: 16,
          overflow: 'hidden'
        }}>
          {/* Levels Above */}
          <div style={{ 
            maxHeight: 250, 
            overflowY: 'auto',
            borderBottom: '1px solid rgba(255,255,255,0.1)'
          }}>
            {levelsAbove.map((level, idx) => (
              <LevelRow key={idx} level={level} position="above" />
            ))}
          </div>

          {/* Current Price - Center */}
          <div style={{
            padding: '24px 16px',
            background: 'linear-gradient(180deg, rgba(0,170,255,0.2) 0%, rgba(0,100,200,0.1) 100%)',
            borderTop: '2px solid #00aaff',
            borderBottom: '2px solid #00aaff',
            textAlign: 'center'
          }}>
            <div style={{ color: '#888', fontSize: 10, letterSpacing: 2, marginBottom: 8 }}>CURRENT PRICE</div>
            <div style={{
              fontSize: 48,
              fontWeight: 700,
              color: '#fff',
              fontFamily: "'JetBrains Mono', monospace",
              textShadow: '0 0 30px rgba(0,170,255,0.5)',
              animation: 'pulse 2s ease-in-out infinite'
            }}>
              ${currentPrice.toFixed(2)}
            </div>
            <div style={{ 
              marginTop: 8, 
              fontSize: 12, 
              color: metrics.cumulative_delta >= 0 ? '#00ff88' : '#ff4466',
              fontWeight: 600
            }}>
              {metrics.cumulative_delta >= 0 ? '▲' : '▼'} Delta: {metrics.cumulative_delta?.toLocaleString() || 0}
            </div>
          </div>

          {/* Levels Below */}
          <div style={{ 
            maxHeight: 250, 
            overflowY: 'auto',
            borderTop: '1px solid rgba(255,255,255,0.1)'
          }}>
            {levelsBelow.map((level, idx) => (
              <LevelRow key={idx} level={level} position="below" />
            ))}
          </div>
        </div>

        {/* Info Panel - Right */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 16
        }}>
          {/* Session Info */}
          <div style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 12,
            padding: 16
          }}>
            <div style={{ color: '#888', fontSize: 11, marginBottom: 8, letterSpacing: 2 }}>CURRENT SESSION</div>
            <div style={{
              fontSize: 20,
              fontWeight: 700,
              color: '#00aaff',
              fontFamily: "'JetBrains Mono', monospace"
            }}>
              {gexData.current_session_name || 'Loading...'}
            </div>
            <div style={{ color: '#666', fontSize: 12, marginTop: 4 }}>
              {gexData.current_session_start} - {gexData.current_session_end} ET
            </div>
          </div>

          {/* IB Range */}
          <div style={{
            background: gexData.ib_status === 'OPEN' ? 'rgba(0,255,136,0.1)' : 'rgba(255,170,0,0.1)',
            border: `1px solid ${gexData.ib_status === 'OPEN' ? 'rgba(0,255,136,0.3)' : 'rgba(255,170,0,0.3)'}`,
            borderRadius: 12,
            padding: 16
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              marginBottom: 12
            }}>
              <span style={{ color: '#888', fontSize: 11, letterSpacing: 2 }}>IB RANGE</span>
              <span style={{
                padding: '2px 8px',
                borderRadius: 4,
                fontSize: 10,
                fontWeight: 700,
                background: gexData.ib_status === 'OPEN' ? '#00ff8820' : '#ffaa0020',
                color: gexData.ib_status === 'OPEN' ? '#00ff88' : '#ffaa00'
              }}>
                {gexData.ib_status || 'ENDED'}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ color: '#888', fontSize: 12 }}>High</span>
              <span style={{ color: '#ff4466', fontFamily: 'monospace', fontWeight: 600 }}>
                ${(metrics.ib_high || 0).toFixed(2)}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span style={{ color: '#888', fontSize: 12 }}>Mid</span>
              <span style={{ color: '#ffaa00', fontFamily: 'monospace', fontWeight: 600 }}>
                ${((metrics.ib_high + metrics.ib_low) / 2 || 0).toFixed(2)}
              </span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#888', fontSize: 12 }}>Low</span>
              <span style={{ color: '#00ff88', fontFamily: 'monospace', fontWeight: 600 }}>
                ${(metrics.ib_low || 0).toFixed(2)}
              </span>
            </div>
          </div>

          {/* Key Levels */}
          <div style={{
            background: 'rgba(255,255,255,0.02)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 12,
            padding: 16
          }}>
            <div style={{ color: '#888', fontSize: 11, marginBottom: 12, letterSpacing: 2 }}>KEY LEVELS</div>
            {[
              { name: 'VWAP', value: metrics.vwap, color: '#00ddff' },
              { name: 'Zero Gamma', value: gexData.zero_gamma, color: '#00ff88' },
              { name: 'HVL', value: gexData.hvl, color: '#00aaff' },
              { name: 'pdPOC', value: gexData.pdpoc, color: '#ffaa00' },
            ].map((level, idx) => (
              <div key={idx} style={{ 
                display: 'flex', 
                justifyContent: 'space-between',
                marginBottom: 8,
                padding: '4px 0',
                borderBottom: idx < 3 ? '1px solid rgba(255,255,255,0.05)' : 'none'
              }}>
                <span style={{ color: level.color, fontSize: 12 }}>{level.name}</span>
                <span style={{ color: '#fff', fontFamily: 'monospace', fontSize: 13 }}>
                  ${(level.value || 0).toFixed(2)}
                </span>
              </div>
            ))}
          </div>

          {/* Data Source */}
          <div style={{
            background: 'rgba(0,255,136,0.1)',
            border: '1px solid rgba(0,255,136,0.2)',
            borderRadius: 8,
            padding: 12,
            textAlign: 'center'
          }}>
            <div style={{ color: '#00ff88', fontSize: 11, fontWeight: 600 }}>
              ● LIVE | {gexData.data_source || 'DATABENTO'}
            </div>
            <div style={{ color: '#666', fontSize: 10, marginTop: 4 }}>
              Updated: {gexData.last_update || '--:--:--'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
