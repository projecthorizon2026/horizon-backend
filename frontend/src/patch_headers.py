#!/usr/bin/env python3
"""Patch IB and Current Session headers with flight board style"""

# Read the file
with open('App.jsx', 'r') as f:
    content = f.read()

# 1. Replace IB section header
old_ib_header = '''        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h3 style={{ margin: 0, color: '#fff', fontSize: 14 }}>
            📊 {gexData.ib_session_name || 'Initial Balance'}
          </h3>
          <span style={{
            padding: '4px 12px',
            borderRadius: 20,
            fontSize: 11,
            fontWeight: 600,
            background: gexData.ib_locked ? 'rgba(255,170,0,0.2)' : 'rgba(0,255,136,0.2)',
            color: gexData.ib_locked ? '#ffaa00' : '#00ff88'
          }}>
            {gexData.ib_locked ? '🔒 LOCKED' : '🔄 FORMING'}
          </span>
        </div>'''

new_ib_header = '''        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
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

# 2. Replace Current Session header
old_session_header = '''          <h3 style={{ margin: 0, color: '#00aaff', fontSize: 14 }}>📈 Current Session</h3>'''

new_session_header = '''          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
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

# Apply replacements
new_content = content.replace(old_ib_header, new_ib_header)
if new_content != content:
    print("✅ IB header updated")
else:
    print("⚠️  IB header pattern not found")

content2 = new_content.replace(old_session_header, new_session_header)
if content2 != new_content:
    print("✅ Current Session header updated")
else:
    print("⚠️  Current Session header pattern not found")

# Write
with open('App.jsx', 'w') as f:
    f.write(content2)

print("✅ Patch complete!")
