# Project Horizon v15 - Underground Setup Trading System

## 🚀 Quick Start

### 1. Start Backend (Terminal 1)
```bash
cd scripts

# Set your Databento API key
export DATABENTO_API_KEY='db-pJKmpW8EMSpyrgnkkBQVFauttkicd'

# Install databento if needed
pip install databento --break-system-packages

# Start the feed
python3 realtime_feed.py
```

### 2. Start Frontend (Terminal 2)
```bash
cd frontend
npm install
npm run dev
```

### 3. Open Dashboard
Open http://localhost:3000 in your browser

---

## 📊 Features

### Dashboard Tabs
- **📊 Backtest Analytics** - Historical trade analysis with filters
- **🔴 Live Metrics** - Real-time price, delta, IB levels, signals
- **🗺️ Volume TreeMap** - Visual volume by sector with correlation matrix
- **📈 VSI Analysis** - Volatility Strength Index by session
- **📋 Trade Log** - Detailed trade history with CSV export
- **⚙️ Settings** - Strategy parameters + AI Optimizer

### Live Data Display
- Connection status (● LIVE / ○ DISCONNECTED)
- Latency in ms with color coding (EXCELLENT <100ms, GOOD <500ms, SLOW <3s)
- Data source (DATABENTO)
- Last update timestamp

### Key Levels
- **IB Levels** - Initial Balance High/Mid/Low (dynamic until locked)
- **PD Levels** - Previous Day High/Low/POC (STATIC, locked at 6 PM ET)
- **Current Session** - Session High/Low/VWAP (DYNAMIC)

### Signal Matrix (6 Conditions)
1. Delta below threshold
2. Price below IB Low
3. At pdPOC
4. Absorption ratio > 1.2
5. Buying imbalance meets threshold
6. 3+ stacked imbalances

### AI Optimizer
- Grid search optimization across Delta & Imbalance parameters
- Entry/Target tier optimization based on R-multiple
- One-click apply optimal settings

---

## 🔧 Configuration

### Signal Thresholds
- **Delta Threshold**: -5000 to -1000 (default: -2500)
- **Buying Imbalance %**: 200-600 (default: 400)

### Entry Tier Allocation
- Tier I (Feeler): 25%
- Tier II (Builder): 40%
- Tier III (Runner): 35%

### Target Allocation
- VWAP: 50%
- IB Mid: 35%
- IB High: 15%

---

## 📡 API Endpoints

### HTTP (Port 8080)
```
GET http://localhost:8080
```
Returns JSON with all current metrics.

---

## ⏰ Session Times (ET)

| Session | Time | IB Status |
|---------|------|-----------|
| Asia IB | 7:00 PM - 8:00 PM | Forming |
| Asia | 8:00 PM - 1:30 AM | Locked |
| Deadzone | 1:30 AM - 3:00 AM | Locked |
| London | 3:00 AM - 6:00 AM | Locked |
| US IB | 8:20 AM - 9:30 AM | Forming |
| NY IB | 9:30 AM - 10:30 AM | Forming |
| NY Session | 10:30 AM - 4:00 PM | Locked |

---

## 📝 Version History

### v15 (Current)
- AI Optimizer with grid search
- Live data with latency display
- Correlation matrix
- VSI with range columns
- Custom signal tooltips

### v14
- Fixed pdPOC (static)
- IB session tracking
- Signal Matrix tooltips

---

## 🔑 Databento API

Get your API key at: https://databento.com

Set as environment variable:
```bash
export DATABENTO_API_KEY='your-key-here'
```
