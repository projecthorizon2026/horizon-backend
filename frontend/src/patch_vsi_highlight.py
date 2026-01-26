#!/usr/bin/env python3
"""
Patches:
1. IB badge - only OPEN/ENDED
2. VSI table current session highlight
"""

with open('App.jsx', 'r') as f:
    content = f.read()

changes_made = 0

# 1. Fix IB status badge - only OPEN/ENDED
old_badge = '''          {/* Status badge */}
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
          </span>'''

new_badge = '''          {/* Status badge - only OPEN or ENDED */}
          <span style={{
            padding: '8px 16px',
            borderRadius: 6,
            fontSize: 12,
            fontWeight: 700,
            letterSpacing: 2,
            background: gexData.ib_status === 'OPEN' ? '#001a00' : '#1a1000',
            color: gexData.ib_status === 'OPEN' ? '#00ff88' : '#ffaa00',
            border: gexData.ib_status === 'OPEN' ? '2px solid #00ff88' : '2px solid #ffaa00',
            textShadow: gexData.ib_status === 'OPEN' ? '0 0 10px #00ff88' : '0 0 10px #ffaa00',
            animation: gexData.ib_status === 'OPEN' ? 'pulse 1.5s ease-in-out infinite' : 'none'
          }}>
            {gexData.ib_status === 'OPEN' ? '● OPEN' : '■ ENDED'}
          </span>'''

if old_badge in content:
    content = content.replace(old_badge, new_badge)
    print("✅ IB badge updated (OPEN/ENDED only)")
    changes_made += 1
else:
    print("⚠️  IB badge pattern not found")

# 2. Add getCurrentSessionId function and highlight to VSI table
# Find the VSI sessions definition and add getCurrentSessionId after it
old_sessions_filter = '''  // Filter sessions based on toggle
  const sessions = sessionFilter === 'horizon' 
    ? allSessions.filter(s => s.horizon) 
    : allSessions;'''

new_sessions_filter = '''  // Filter sessions based on toggle
  const sessions = sessionFilter === 'horizon' 
    ? allSessions.filter(s => s.horizon) 
    : allSessions;

  // Get current session ID based on ET time
  const getCurrentSessionId = () => {
    const now = new Date();
    const utc = now.getTime() + (now.getTimezoneOffset() * 60000);
    const et = new Date(utc - (5 * 3600000)); // ET = UTC - 5
    const hours = et.getHours();
    const mins = et.getMinutes();
    const timeVal = hours * 100 + mins;
    
    // Match against session times
    if (timeVal >= 1900 && timeVal < 2000) return 'japan_ib';
    if (timeVal >= 2000 && timeVal < 2300) return 'china';
    if (timeVal >= 2300 || timeVal < 200) return 'asia_close';
    if (timeVal >= 200 && timeVal < 300) return 'deadzone';
    if (timeVal >= 300 && timeVal < 600) return 'london';
    if (timeVal >= 600 && timeVal < 820) return 'low_volume';
    if (timeVal >= 820 && timeVal < 930) return 'us_ib';
    if (timeVal >= 930 && timeVal < 1030) return 'ny_1h';
    if (timeVal >= 1030 && timeVal < 1130) return 'ny_2h';
    if (timeVal >= 1130 && timeVal < 1330) return 'lunch';
    if (timeVal >= 1330 && timeVal < 1600) return 'ny_pm';
    if (timeVal >= 1600 && timeVal < 1700) return 'ny_close';
    if (timeVal >= 1700 && timeVal < 1800) return 'market_closed';
    if (timeVal >= 1800 && timeVal < 1900) return 'pre_asia';
    return null;
  };
  
  const currentSessionId = getCurrentSessionId();'''

if old_sessions_filter in content:
    content = content.replace(old_sessions_filter, new_sessions_filter)
    print("✅ getCurrentSessionId function added to VSI")
    changes_made += 1
else:
    print("⚠️  Sessions filter pattern not found")

# 3. Update table row to highlight current session
old_row = '''                <tr key={session.id} style={{ 
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)'
                }}>'''

new_row = '''                <tr key={session.id} style={{ 
                  borderBottom: '1px solid rgba(255,255,255,0.05)',
                  background: session.id === currentSessionId 
                    ? `${session.color}25` 
                    : idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                  boxShadow: session.id === currentSessionId ? `inset 0 0 20px ${session.color}15, 0 0 10px ${session.color}10` : 'none',
                  border: session.id === currentSessionId ? `1px solid ${session.color}50` : 'none',
                  animation: session.id === currentSessionId ? 'pulse 2s ease-in-out infinite' : 'none'
                }}>'''

if old_row in content:
    content = content.replace(old_row, new_row)
    print("✅ VSI table row highlight added")
    changes_made += 1
else:
    print("⚠️  Table row pattern not found")

# 4. Add pulsing indicator to current session name
old_session_name = '''                        <div style={{ color: '#fff', fontSize: 14, fontWeight: 500 }}>{session.name}</div>'''

new_session_name = '''                        <div style={{ 
                          color: session.id === currentSessionId ? session.color : '#fff', 
                          fontSize: 14, 
                          fontWeight: session.id === currentSessionId ? 700 : 500,
                          textShadow: session.id === currentSessionId ? `0 0 10px ${session.color}` : 'none'
                        }}>
                          {session.id === currentSessionId && <span style={{ marginRight: 6 }}>●</span>}
                          {session.name}
                          {session.id === currentSessionId && <span style={{ marginLeft: 8, fontSize: 10, color: '#00ff88' }}>NOW</span>}
                        </div>'''

if old_session_name in content:
    content = content.replace(old_session_name, new_session_name)
    print("✅ Session name highlight added")
    changes_made += 1
else:
    print("⚠️  Session name pattern not found")

# Write
with open('App.jsx', 'w') as f:
    f.write(content)

print(f"\n✅ Patch complete! {changes_made} changes made.")
