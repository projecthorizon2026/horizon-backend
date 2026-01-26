#!/usr/bin/env python3
"""Patch PhaseIndicator in App.jsx"""
import re

# Read the file
with open('App.jsx', 'r') as f:
    content = f.read()

# New PhaseIndicator component
new_component = '''  // Updated PhaseIndicator with flight-board style
  const PhaseIndicator = ({ phase }) => {
    // Session definitions with colors and times
    const sessionInfo = {
      'JAPAN_IB': { name: 'Japan IB', time: '19:00 - 20:00 ET', color: '#9370DB' },
      'JAPAN_IB_FORMING': { name: 'Japan IB', time: '19:00 - 20:00 ET', color: '#9370DB', forming: true },
      'CHINA': { name: 'China', time: '20:00 - 23:00 ET', color: '#8B5CF6' },
      'ASIA_CLOSING': { name: 'Asia Closing', time: '23:00 - 02:00 ET', color: '#4B5563' },
      'DEADZONE': { name: 'Deadzone', time: '02:00 - 03:00 ET', color: '#6B7280' },
      'LONDON': { name: 'London', time: '03:00 - 06:00 ET', color: '#3B82F6' },
      'LOW_VOLUME': { name: 'Low Volume', time: '06:00 - 08:20 ET', color: '#4B5563' },
      'US_IB': { name: 'US IB', time: '08:20 - 09:30 ET', color: '#F59E0B' },
      'US_IB_FORMING': { name: 'US IB', time: '08:20 - 09:30 ET', color: '#F59E0B', forming: true },
      'NY_1H': { name: 'NY 1H', time: '09:30 - 10:30 ET', color: '#10B981' },
      'NY_2H': { name: 'NY 2H', time: '10:30 - 11:30 ET', color: '#14B8A6' },
      'LUNCH': { name: 'Lunch', time: '11:30 - 13:30 ET', color: '#6B7280' },
      'NY_PM': { name: 'NY PM', time: '13:30 - 16:00 ET', color: '#EF4444' },
      'NY_CLOSE': { name: 'NY Close', time: '16:00 - 17:00 ET', color: '#4B5563' },
      'MARKET_CLOSED': { name: 'Market Closed', time: '17:00 - 18:00 ET', color: '#1F2937' },
      'PRE_ASIA': { name: 'Pre-Asia', time: '18:00 - 19:00 ET', color: '#4B5563' },
    };
    
    const info = sessionInfo[phase] || { name: phase, time: '', color: '#888' };
    
    return (
      <div style={{
        padding: '16px 24px',
        borderRadius: 12,
        background: 'linear-gradient(180deg, rgba(20,20,30,0.9) 0%, rgba(10,10,15,0.95) 100%)',
        border: `2px solid ${info.color}50`,
        textAlign: 'center',
        boxShadow: `0 4px 20px ${info.color}20`
      }}>
        <div style={{ fontSize: 11, color: '#666', marginBottom: 8, letterSpacing: 2 }}>CURRENT SESSION</div>
        <div style={{ 
          fontSize: 28, 
          fontWeight: 700, 
          color: info.color,
          textShadow: `0 0 20px ${info.color}50`,
          fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: 2,
          marginBottom: 8,
          animation: info.forming ? 'pulse 1.5s ease-in-out infinite' : 'none'
        }}>
          {info.name.toUpperCase()}
        </div>
        <div style={{
          fontSize: 13,
          color: '#888',
          fontFamily: 'monospace',
          padding: '4px 12px',
          background: 'rgba(255,255,255,0.05)',
          borderRadius: 4,
          display: 'inline-block'
        }}>
          🕐 {info.time}
        </div>
        {info.forming && (
          <div style={{
            marginTop: 8,
            fontSize: 10,
            color: '#00ff88',
            fontWeight: 600,
            letterSpacing: 1,
            animation: 'pulse 1s ease-in-out infinite'
          }}>
            ● IB FORMING
          </div>
        )}
      </div>
    );
  };'''

# Pattern to match the old PhaseIndicator
pattern = r'  const PhaseIndicator = \(\{ phase \}\) => \{.*?^  \};'

# Replace
new_content = re.sub(pattern, new_component, content, flags=re.MULTILINE | re.DOTALL)

if new_content != content:
    with open('App.jsx', 'w') as f:
        f.write(new_content)
    print("✅ PhaseIndicator updated successfully!")
else:
    print("❌ Pattern not found - no changes made")
