#!/usr/bin/env python3
"""Patch headers with flight board styling - black bg, neon text"""

with open('App.jsx', 'r') as f:
    content = f.read()

# 1. Update IB header with flight board style
old_ib = '''        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 20 }}>📊</span>
            <div>
              <div style={{ 
                fontSize: 18, 
                fontWeight: 700, 
                color: '#fff',
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: 1,
                textTransform: 'uppercase'
              }}>
                {gexData.ib_session_name || 'Initial Balance'}
              </div>
              <div style={{
                fontSize: 11,
                color: '#666',
                fontFamily: 'monospace',
                marginTop: 2
              }}>
                {gexData.ib_session_name === 'Japan IB' ? '🕐 19:00 - 20:00 ET' :
                 gexData.ib_session_name === 'US IB' ? '🕐 08:20 - 09:30 ET' :
                 '🕐 IB Range'}
              </div>
            </div>
          </div>
          <span style={{
            padding: '6px 14px',
            borderRadius: 20,
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: 1,
            background: gexData.ib_locked ? 'rgba(255,170,0,0.2)' : 'rgba(0,255,136,0.2)',
            color: gexData.ib_locked ? '#ffaa00' : '#00ff88',
            border: gexData.ib_locked ? '1px solid rgba(255,170,0,0.3)' : '1px solid rgba(0,255,136,0.3)',
            animation: !gexData.ib_locked ? 'pulse 1.5s ease-in-out infinite' : 'none'
          }}>
            {gexData.ib_locked ? '🔒 LOCKED' : '🔄 FORMING'}
          </span>
        </div>'''

new_ib = '''        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {/* Flight board style name */}
            <div style={{
              background: '#000',
              padding: '8px 16px',
              borderRadius: 6,
              border: '2px solid #333',
              boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5)'
            }}>
              <div style={{ 
                fontSize: 20, 
                fontWeight: 700, 
                color: gexData.ib_status === 'OPEN' ? '#00ff88' : '#ffaa00',
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: 3,
                textTransform: 'uppercase',
                textShadow: gexData.ib_status === 'OPEN' ? '0 0 10px #00ff88' : '0 0 10px #ffaa00'
              }}>
                {gexData.ib_session_name || 'INITIAL BALANCE'}
              </div>
            </div>
            {/* Time range */}
            <div style={{
              background: '#111',
              padding: '6px 12px',
              borderRadius: 4,
              border: '1px solid #333'
            }}>
              <div style={{
                fontSize: 12,
                color: '#888',
                fontFamily: 'monospace'
              }}>
                {gexData.ib_session_name === 'Japan IB' ? '19:00 - 20:00 ET' :
                 gexData.ib_session_name === 'US IB' ? '08:20 - 09:30 ET' :
                 'IB RANGE'}
              </div>
            </div>
          </div>
          {/* Status badge */}
          <span style={{
            padding: '8px 16px',
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: 2,
            background: gexData.ib_status === 'OPEN' ? '#001a00' : gexData.ib_status === 'ENDED' ? '#1a1000' : '#1a0000',
            color: gexData.ib_status === 'OPEN' ? '#00ff88' : gexData.ib_status === 'ENDED' ? '#ffaa00' : '#ff4466',
            border: gexData.ib_status === 'OPEN' ? '2px solid #00ff88' : gexData.ib_status === 'ENDED' ? '2px solid #ffaa00' : '2px solid #ff4466',
            textShadow: gexData.ib_status === 'OPEN' ? '0 0 10px #00ff88' : '0 0 10px #ffaa00',
            animation: gexData.ib_status === 'OPEN' ? 'pulse 1.5s ease-in-out infinite' : 'none'
          }}>
            {gexData.ib_status === 'OPEN' ? '● OPEN' : gexData.ib_status === 'ENDED' ? '■ ENDED' : '○ WAITING'}
          </span>
        </div>'''

# 2. Update Current Session header
old_session = '''          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 20 }}>📈</span>
            <div>
              <div style={{ 
                fontSize: 18, 
                fontWeight: 700, 
                color: '#00aaff',
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: 1,
                textTransform: 'uppercase'
              }}>
                {gexData.current_session_name || 'Current Session'}
              </div>
              <div style={{
                fontSize: 11,
                color: '#666',
                fontFamily: 'monospace',
                marginTop: 2
              }}>
                🕐 {gexData.current_session_start || '00:00'} - {gexData.current_session_end || '00:00'} ET
              </div>
            </div>
          </div>'''

new_session = '''          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {/* Flight board style name */}
            <div style={{
              background: '#000',
              padding: '8px 16px',
              borderRadius: 6,
              border: '2px solid #333',
              boxShadow: 'inset 0 2px 4px rgba(0,0,0,0.5)'
            }}>
              <div style={{ 
                fontSize: 20, 
                fontWeight: 700, 
                color: '#00ddff',
                fontFamily: "'JetBrains Mono', monospace",
                letterSpacing: 3,
                textTransform: 'uppercase',
                textShadow: '0 0 10px #00ddff'
              }}>
                {gexData.current_session_name || 'SESSION'}
              </div>
            </div>
            {/* Time range */}
            <div style={{
              background: '#111',
              padding: '6px 12px',
              borderRadius: 4,
              border: '1px solid #333'
            }}>
              <div style={{
                fontSize: 12,
                color: '#888',
                fontFamily: 'monospace'
              }}>
                {gexData.current_session_start || '00:00'} - {gexData.current_session_end || '00:00'} ET
              </div>
            </div>
          </div>'''

# Apply
content2 = content.replace(old_ib, new_ib)
if content2 != content:
    print("✅ IB header updated with flight board style")
else:
    print("⚠️  IB header not found")

content3 = content2.replace(old_session, new_session)
if content3 != content2:
    print("✅ Current Session header updated with flight board style")
else:
    print("⚠️  Current Session header not found")

with open('App.jsx', 'w') as f:
    f.write(content3)

print("✅ Flight board styling complete!")
