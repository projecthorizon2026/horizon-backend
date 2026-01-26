#!/usr/bin/env python3
"""Add session filter to VSI"""

with open('App.jsx', 'r') as f:
    content = f.read()

# Add filter line after allSessions array
old = '''  // Get current session ID based on ET time'''
new = '''  // Filter sessions based on toggle
  const sessions = sessionFilter === 'horizon' ? allSessions.filter(s => s.horizon) : allSessions;

  // Get current session ID based on ET time'''

if old in content:
    content = content.replace(old, new)
    print("✅ Session filter added")
else:
    print("⚠️  Pattern not found")

with open('App.jsx', 'w') as f:
    f.write(content)
