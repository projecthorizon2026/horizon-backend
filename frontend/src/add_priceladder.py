#!/usr/bin/env python3
"""Add Price Ladder component and tab to App.jsx"""

# Read the component file
with open('PriceLadder.jsx', 'r') as f:
    price_ladder_code = f.read()

# Read App.jsx
with open('App.jsx', 'r') as f:
    content = f.read()

# 1. Add PriceLadder component before VSIAnalysis
# Find const VSIAnalysis
insert_point = content.find('const VSIAnalysis = () => {')
if insert_point == -1:
    print("❌ Could not find VSIAnalysis")
else:
    # Insert the component
    content = content[:insert_point] + price_ladder_code + '\n\n' + content[insert_point:]
    print("✅ PriceLadder component added")

# 2. Add tab to navigation
# Find the Trade Log tab button
old_nav = "{ id: 'tradelog', label: 'Trade Log', icon: '📋' }"
new_nav = "{ id: 'tradelog', label: 'Trade Log', icon: '📋' },\n    { id: 'priceladder', label: 'Price Ladder', icon: '📊' }"

if old_nav in content:
    content = content.replace(old_nav, new_nav)
    print("✅ Navigation tab added")
else:
    print("⚠️  Could not find Trade Log nav - trying alternate")
    # Try alternate pattern
    old_nav2 = "'tradelog', label: 'Trade Log'"
    if old_nav2 in content:
        print("   Found alternate nav pattern")

# 3. Add tab rendering in switch/conditional
# Find where tabs are rendered
old_render = "{activeTab === 'settings' && <SettingsPanel"
new_render = "{activeTab === 'priceladder' && <PriceLadder metrics={metrics} gexData={gexData} />}\n        {activeTab === 'settings' && <SettingsPanel"

if old_render in content:
    content = content.replace(old_render, new_render)
    print("✅ Tab rendering added")
else:
    print("⚠️  Could not find settings tab render")

# Write back
with open('App.jsx', 'w') as f:
    f.write(content)

print("\n✅ Patch complete! Refresh browser to see Price Ladder tab.")
