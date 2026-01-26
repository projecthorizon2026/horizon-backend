# Project Horizon - Trading Analytics Platform
## Comprehensive User Manual v15.0

---

## Table of Contents

1. [Overview](#overview)
2. [Data Sources](#data-sources)
3. [Price Ladder](#price-ladder)
4. [Order Flow Analysis](#order-flow-analysis)
5. [Big Trades Detection](#big-trades-detection)
6. [Wyckoff Phase Analysis](#wyckoff-phase-analysis)
7. [Execution Analysis](#execution-analysis)
8. [Market Profile & TPO](#market-profile--tpo)
9. [Session Analysis](#session-analysis)
10. [Gold Institutional Sentiment](#gold-institutional-sentiment)
11. [Correlation Matrix](#correlation-matrix)
12. [Zone Participation](#zone-participation)
13. [Backtesting](#backtesting)
14. [Connection Status](#connection-status)

---

## Overview

Project Horizon is a professional-grade trading analytics platform designed for futures traders, with primary focus on Gold Futures (GC). The platform combines real-time market data with institutional-level analytics including Order Flow, Volume Profile, Wyckoff Analysis, and Sentiment indicators.

### Supported Contracts

| Contract | Symbol | Exchange | Multiplier | Tick Size |
|----------|--------|----------|------------|-----------|
| Gold Futures | GCG26 | COMEX | 100 oz | $0.10 = $10 |
| E-mini S&P 500 | ES | CME | $50 | 0.25 = $12.50 |
| E-mini Nasdaq | NQ | CME | $20 | 0.25 = $5 |
| Crude Oil | CL | NYMEX | 1000 bbl | $0.01 = $10 |
| Bitcoin Futures | BTC | CME | 5 BTC | $5 = $25 |

---

## Data Sources

### Primary Data Feeds

| Source | Type | Latency | Use Case |
|--------|------|---------|----------|
| **Databento** | Real-time L2 | ~10ms | Primary tick data, order book |
| **Yahoo Finance** | Delayed | ~15min | Fallback price data |
| **CFTC** | Weekly | Friday 3:30pm | COT positioning data |
| **World Gold Council** | Daily | EOD | Central bank holdings |
| **COMEX** | Daily | EOD | Open interest data |
| **ETF Providers** | Daily | EOD | GLD/IAU/SLV flows |

### Connection States

```
LIVE (Green)         → Connected to real-time feed
RECONNECTING (Yellow) → Attempting to reconnect
OFFLINE (Red)        → No data connection
```

### Data Flow Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Databento  │────▶│   Railway   │────▶│   Vercel    │
│  (L2 Data)  │     │  (Backend)  │     │ (Frontend)  │
└─────────────┘     └─────────────┘     └─────────────┘
       │                   │
       ▼                   ▼
  Tick-by-tick       5-min OHLC
  Trade Data         Aggregation
```

---

## Price Ladder

### Overview

The Price Ladder displays real-time price with key reference levels for context-aware trading decisions.

### Reference Levels

| Level | Color | Description | Calculation |
|-------|-------|-------------|-------------|
| **VWAP** | Blue | Volume Weighted Average Price | `Σ(Price × Volume) / Σ(Volume)` |
| **PD HIGH** | Red | Prior Day High | Previous session's highest price |
| **PDPOC** | Yellow | Prior Day Point of Control | Price level with highest volume from previous day |
| **PD LOW** | Green | Prior Day Low | Previous session's lowest price |

### Distance Indicators

Each reference level shows the distance from current price:

```
VWAP      $5083.13    ↓ $9.37     ← Current price is $9.37 below VWAP
PD HIGH   $4991.40    ↓ $101.10   ← Current price is $101.10 below PD High
```

**Interpretation:**
- Price **above VWAP** = Bullish intraday bias
- Price **below VWAP** = Bearish intraday bias
- Price near **PDPOC** = High-volume support/resistance zone

### Session Indicator

```
┌─────────────────────────────┐
│ SESSION: Lunch  11:30-13:30 │
└─────────────────────────────┘
```

| Session | Time (ET) | Characteristics |
|---------|-----------|-----------------|
| Asia | 18:00-02:00 | Low volume, range-bound |
| London | 02:00-08:00 | Increased volatility |
| US Open | 08:00-11:30 | Highest volume, trends |
| Lunch | 11:30-13:30 | Reduced activity |
| US PM | 13:30-17:00 | Moderate volume |

---

## Order Flow Analysis

### Concept Summary

Order Flow Analysis tracks the **aggressor** in each trade to determine whether buyers or sellers are more aggressive. This provides insight into market sentiment beyond just price movement.

### Key Metrics

#### 1. Cumulative Volume Delta (CVD)

**Formula:**
```
CVD = Σ(Buy Volume) - Σ(Sell Volume)

Where:
- Buy Volume = Trades executed at ASK price (buyer aggressed)
- Sell Volume = Trades executed at BID price (seller aggressed)
```

**Interpretation:**
| CVD Value | Signal | Meaning |
|-----------|--------|---------|
| +500 | Bullish | 500 more contracts bought at ask than sold at bid |
| -500 | Bearish | 500 more contracts sold at bid than bought at ask |
| Near 0 | Neutral | Balanced buying and selling |

**Chart Example:**
```
CVD TREND (50m)
     +800 ┤████████████████████
     +400 ┤██████████
        0 ┤─────────────────────
     -400 ┤
     -800 ┤

Interpretation: Strong buying pressure over last 50 minutes
```

#### 2. Price Delta (Δ)

**Formula:**
```
Price Δ = Current Price - Previous Close
```

**Display:**
```
PRICE Δ: +$4.50  (Green = Up, Red = Down)
```

#### 3. Divergence Analysis

**Formula:**
```
Divergence = CVD Direction ≠ Price Direction

ALIGNED:    CVD ↑ and Price ↑  OR  CVD ↓ and Price ↓
DIVERGENT:  CVD ↑ and Price ↓  OR  CVD ↓ and Price ↑
```

**Trading Signals:**

| CVD | Price | Status | Interpretation |
|-----|-------|--------|----------------|
| ↑ | ↑ | ALIGNED | Healthy trend, continue with trend |
| ↓ | ↓ | ALIGNED | Healthy downtrend, continue with trend |
| ↑ | ↓ | DIVERGENT | Hidden buying, potential reversal UP |
| ↓ | ↑ | DIVERGENT | Hidden selling, potential reversal DOWN |

#### 4. Volume Spread Analysis (VSA)

**Formula:**
```
VSA Ratio = |Delta| / Price Spread

Where:
- Delta = Buy Volume - Sell Volume (for the candle)
- Price Spread = High - Low (for the candle)
```

**VSA Signals:**

| Signal | Condition | Meaning |
|--------|-----------|---------|
| **ABSORPTION** | High Volume + Small Spread | Large orders absorbed, potential reversal |
| **FOLLOW-THROUGH** | High Volume + Large Spread | Strong directional conviction |
| **NO DEMAND** | Low Volume + Up Move | Weak rally, likely to fail |
| **NO SUPPLY** | Low Volume + Down Move | Weak decline, likely to reverse |
| **NEUTRAL** | Average conditions | No clear signal |

#### 5. Regime Detection

**Formula:**
```
Regime = f(CVD Trend, Price Trend, VSA Signal)

ACCUMULATION: Price flat/down + CVD rising + Absorption
DISTRIBUTION: Price flat/up + CVD falling + Absorption
MARKUP:       Price rising + CVD rising + Follow-through
MARKDOWN:     Price falling + CVD falling + Follow-through
BALANCED:     No clear directional bias
```

---

## Big Trades Detection

### Concept Summary

Big Trades detection identifies institutional-sized orders that represent significant capital deployment. These trades often precede or confirm major price moves.

### Threshold Calculation

**Dynamic 90th Percentile Method:**

```python
# Collect last 1000 trade sizes
trade_sizes = [1, 1, 2, 2, 3, 3, 5, 5, 8, 12, ...]

# Calculate 90th percentile
sorted_sizes = sorted(trade_sizes)
p90_index = int(len(sorted_sizes) * 0.90)
threshold = sorted_sizes[p90_index]

# Minimum floor by contract
min_thresholds = {'GC': 5, 'NQ': 3, 'ES': 5, 'CL': 10}
final_threshold = max(threshold, min_thresholds[contract])
```

**Why 90th Percentile:**
- Top 10% of trades by size = Institutional activity
- Adapts to market conditions (high/low volatility)
- Filters noise from retail-sized trades

### Notional Value Context

**Gold Futures (GC) Example:**

| Contracts | Calculation | Notional Value | Trader Type |
|-----------|-------------|----------------|-------------|
| 1 | 1 × 100oz × $5,075 | $507,500 | Retail |
| 5 | 5 × 100oz × $5,075 | $2.54M | Active Retail |
| 10 | 10 × 100oz × $5,075 | **$5.08M** | **Institutional** |
| 25 | 25 × 100oz × $5,075 | $12.69M | Large Institution |
| 50 | 50 × 100oz × $5,075 | $25.38M | Major Dealer |

### Visual Representation

**Bubble Chart on Price OHLC:**

```
PRICE OHLC (5m)
$5100 │    [====]              (●)
$5095 │  (●)[====](●)      [====]
$5090 │    [====]   (●)(●)[====]
$5085 │      [====]    [====](●)
$5080 │  (●)  [====]  [====]
      └────────────────────────────
       10:00  10:15  10:30  10:45

Legend:
[====] = OHLC Candles
(●) Green = BIG BUY (buyer aggressed)
(●) Red = BIG SELL (seller aggressed)
Bubble size = Trade volume (larger = more contracts)
```

### Hover Tooltip Information

When hovering over a big trade bubble:

```
┌─────────────────────────────┐
│ ● BIG BUY                   │
├─────────────────────────────┤
│ Size:      14 contracts     │
│ Price:     $5,092.90        │
│ Notional:  $7.13M           │
│ vs Average: 4.7x larger     │
│ Time:      10:08:17 ET      │
├─────────────────────────────┤
│ Top 10% of trades by size   │
└─────────────────────────────┘
```

### Trading Applications

| Pattern | Interpretation | Action |
|---------|----------------|--------|
| Big BUY at support | Institutional accumulation | Look for long entries |
| Big SELL at resistance | Institutional distribution | Look for short entries |
| Cluster of big buys | Strong demand zone | Mark as support level |
| Cluster of big sells | Strong supply zone | Mark as resistance level |
| Big trade + price reversal | Stop hunt / liquidity grab | Fade the move |

---

## Wyckoff Phase Analysis

### Concept Summary

Wyckoff methodology identifies market phases based on the interplay between price, volume, and the behavior of the "Composite Operator" (smart money).

### Phase Detection

**Scoring Algorithm:**

```python
def calculate_wyckoff_phase(momentum, delta, volume, poc, dma):
    score = 0

    # Momentum contribution (0-25 points)
    if momentum > 70:
        score += 25  # Strong bullish
    elif momentum > 50:
        score += 15  # Moderate bullish
    elif momentum < 30:
        score -= 25  # Strong bearish
    elif momentum < 50:
        score -= 15  # Moderate bearish

    # Delta contribution (0-25 points)
    if delta == 'STRONG BUYING':
        score += 25
    elif delta == 'BUYING':
        score += 15
    elif delta == 'STRONG SELLING':
        score -= 25
    elif delta == 'SELLING':
        score -= 15

    # Volume contribution (0-20 points)
    if volume == 'CLIMACTIC':
        score += 20 if momentum > 50 else -20
    elif volume == 'HIGH':
        score += 10 if momentum > 50 else -10

    # POC contribution (0-15 points)
    if poc == 'RISING':
        score += 15
    elif poc == 'FALLING':
        score -= 15

    # DMA contribution (0-15 points)
    if dma == 'ABOVE':
        score += 15
    elif dma == 'BELOW':
        score -= 15

    return score  # Range: -100 to +100
```

### Phase Classification

| Score Range | Phase | Description |
|-------------|-------|-------------|
| +60 to +100 | **PHASE D/E** | Markup / Uptrend |
| +20 to +59 | **PHASE C** | Spring / Test |
| -19 to +19 | **PHASE B** | Building Cause |
| -59 to -20 | **PHASE A** | Stopping Action |
| -100 to -60 | **DISTRIBUTION** | Markdown beginning |

### Visual Indicators

```
EXECUTION ANALYSIS │ PHASE C │
──────────────────────────────
MOMENTUM    DELTA      VOLUME    POC       DMA
   67       BUYING     HIGH      RISING    ABOVE
   ●──────   ●──────   ●──────   ●──────   ●──────

Score: +55 → PHASE C (Spring / Test)
```

### Component Metrics

| Metric | Calculation | Bullish | Bearish |
|--------|-------------|---------|---------|
| Momentum | RSI-style oscillator (0-100) | >50 | <50 |
| Delta | Net buy/sell aggression | BUYING | SELLING |
| Volume | Relative to 20-period average | HIGH/CLIMACTIC | LOW |
| POC | Point of Control direction | RISING | FALLING |
| DMA | Price vs 20 DMA | ABOVE | BELOW |

---

## Execution Analysis

### Overview

Execution Analysis provides a condensed view of current market conditions to aid trade execution decisions.

### Metrics Grid

```
┌──────────┬──────────┬──────────┬──────────┬──────────┐
│ MOMENTUM │  DELTA   │  VOLUME  │   POC    │   DMA    │
│    67    │  BUYING  │   HIGH   │  RISING  │  ABOVE   │
│  ●━━━━   │  ●━━━━   │  ●━━━━   │  ●━━━━   │   1/3    │
└──────────┴──────────┴──────────┴──────────┴──────────┘
```

### Signal Interpretation

| All Green | Mixed | All Red |
|-----------|-------|---------|
| Strong buy setup | Wait for clarity | Strong sell setup |
| Execute with confidence | Reduce size | Execute shorts |

---

## Market Profile & TPO

### Concept Summary

Market Profile organizes price data by time spent at each level, revealing where the market finds acceptance (value) vs. rejection.

### Key Components

#### 1. Time Price Opportunity (TPO)

```
Price    │ A B C D E F G H I J K │ TPO Count
─────────┼───────────────────────┼──────────
$5095    │ A B                   │ 2
$5090    │ A B C D               │ 4
$5085    │ A B C D E F G H       │ 8  ← POC
$5080    │   B C D E F G         │ 6
$5075    │     C D E             │ 3
$5070    │       D               │ 1

Letters = 30-minute periods
POC = Price level with most TPOs
```

#### 2. Value Area

**Formula:**
```
Value Area = 70% of total volume/TPOs centered around POC

Steps:
1. Start at POC
2. Add TPOs above and below alternately
3. Stop when 70% of total TPOs included
4. VAH = Value Area High
5. VAL = Value Area Low
```

**Trading Rules:**

| Price Location | Interpretation | Bias |
|----------------|----------------|------|
| Above VAH | Breakout, extended | Short-term bearish |
| Within VA | Fair value, acceptance | Neutral, fade edges |
| Below VAL | Breakdown, undervalued | Short-term bullish |

#### 3. Initial Balance (IB)

**Definition:** First hour of trading range (08:30-09:30 ET for US session)

```
IB High:  $5092
IB Low:   $5078
IB Range: $14

IB Extension Targets:
- 1x IB Up:   $5106 ($5092 + $14)
- 1x IB Down: $5064 ($5078 - $14)
- 2x IB Up:   $5120
- 2x IB Down: $5050
```

### Profile Types

| Type | Characteristics | Trading Approach |
|------|-----------------|------------------|
| **Normal** | Bell curve, balanced | Fade extremes, trade to POC |
| **Double Distribution** | Two POCs | Trade breakout of developing VA |
| **P-shaped** | Long tail down | Bullish, buying emerged |
| **b-shaped** | Long tail up | Bearish, selling emerged |
| **Trending** | Elongated, no clear POC | Trade with trend |

---

## Session Analysis

### Overview

Session Analysis provides historical context for trading performance and market behavior patterns.

### Weekly Breakdown

```
WEEKLY BREAKDOWN - 2025

     W36   W37   W38   W39   W40   W41   W42   W43
     ┌─┐   ┌─┐   ┌─┐   ┌─┐   ┌─┐   ┌─┐   ┌─┐   ┌─┐
     │█│   │█│   │ │   │ │   │█│   │█│   │ │   │█│
     │█│   │█│   │█│   │█│   │█│   │ │   │█│   │█│
     └─┘   └─┘   └─┘   └─┘   └─┘   └─┘   └─┘   └─┘
     $9K   $7K   $2K   $2K   $6K   $5K   $2K   $6K

Green = Profitable week
Red = Losing week
Height = P&L magnitude
```

### Daily Calendar View

```
        January 2025
Su  Mo  Tu  We  Th  Fr  Sa
              1   2   3   4
                     +10.3K
 5   6   7   8   9  10  11
                    -2.1K
12  13  14  15  16  17  18
        +1.9K
19  20  21  22  23  24  25
                    -1.4K
26  27  28  29  30  31

Green highlight = Profitable day
Red highlight = Losing day
```

### Win Rate Calculation

**Formula:**
```
Win Rate = (Winning Sessions / Total Sessions) × 100%

Example:
- Total Sessions: 50
- Winning Sessions: 19
- Win Rate: 38%
```

---

## Gold Institutional Sentiment

### Overview

Aggregates multiple institutional data sources to provide a comprehensive view of professional positioning in gold markets.

### Data Components

#### 1. Central Banks

**Source:** World Gold Council, IMF

| Metric | Description | Bullish Signal |
|--------|-------------|----------------|
| Net Position | Cumulative central bank gold holdings | Net Buyers 15+ Years |
| Monthly Change | Month-over-month holding change | Increasing reserves |

**Current Context:**
```
CENTRAL BANKS
Net Buyers 15+ Years
Accumulating gold reserves
```

#### 2. COT Positioning

**Source:** CFTC Commitment of Traders Report (Weekly, Friday 3:30pm ET)

| Category | Description | Signal |
|----------|-------------|--------|
| **Managed Money** | Hedge funds, CTAs | Trend-following |
| **Swap Dealers** | Banks, institutions | Hedging activity |
| **Commercials** | Producers, consumers | Real economy demand |

**Interpretation:**
```
Managed Money:   LONG (+13%)  → Funds bullish
Swap Dealers:    SHORT (-7%)  → Banks hedging longs
```

**Formula for Net Position:**
```
Net Position = Long Contracts - Short Contracts
Position Change = Current Week - Previous Week
% Change = (Position Change / Previous Position) × 100
```

#### 3. COMEX Open Interest

**Source:** CME Group

```
Total OI:    485K Contracts
24h Change:  +1.5%
```

**Interpretation:**

| OI Change | Price Change | Signal |
|-----------|--------------|--------|
| ↑ OI | ↑ Price | New longs entering (Bullish) |
| ↑ OI | ↓ Price | New shorts entering (Bearish) |
| ↓ OI | ↑ Price | Short covering (Weak bullish) |
| ↓ OI | ↓ Price | Long liquidation (Weak bearish) |

#### 4. Gold ETF Flows

**Sources:** GLD (SPDR), IAU (iShares), SLV (Silver proxy)

```
GLD Holdings:  28.5M oz
Weekly Flow:   +12 tons
```

**Signal Interpretation:**
- **Inflows** = Institutional accumulation
- **Outflows** = Institutional distribution

### Overall Signal

**Formula:**
```
Sentiment Score =
  (Central Bank Signal × 0.25) +
  (COT Signal × 0.30) +
  (Open Interest Signal × 0.20) +
  (ETF Flow Signal × 0.25)

Score > 0.5 → BULLISH
Score < -0.5 → BEARISH
Otherwise → NEUTRAL
```

---

## Correlation Matrix

### Overview

Displays real-time correlations between gold and related assets to identify intermarket relationships and divergences.

### Correlation Coefficient

**Formula:**
```
ρ(X,Y) = Σ[(Xi - X̄)(Yi - Ȳ)] / √[Σ(Xi - X̄)² × Σ(Yi - Ȳ)²]

Where:
- ρ = Correlation coefficient (-1 to +1)
- X, Y = Price series of two assets
- X̄, Ȳ = Mean prices
```

### Asset Relationships

| Asset | Typical Correlation | Interpretation |
|-------|---------------------|----------------|
| **DXY** (Dollar Index) | -0.80 | Strong inverse |
| **US10Y** (10Y Yield) | -0.50 | Moderate inverse |
| **SPY** (S&P 500) | +0.30 | Weak positive |
| **GDX** (Gold Miners) | +0.85 | Strong positive |
| **SLV** (Silver) | +0.90 | Very strong positive |
| **BTC** (Bitcoin) | +0.40 | Moderate positive |

### Trading Applications

| Scenario | Signal |
|----------|--------|
| Gold ↑, DXY ↓ | Normal relationship, trend likely to continue |
| Gold ↑, DXY ↑ | Divergence, one will correct |
| Gold ↑, GDX ↓ | Miners not confirming, gold rally may fail |
| Gold ↓, GDX ↑ | Miners leading, gold may reverse up |

---

## Zone Participation

### Overview

Tracks which price zones have the highest trading activity and where institutional players are most active.

### Zone Definition

**Formula:**
```
Zone Width = ATR(20) / 4

Example for Gold (ATR = $40):
Zone Width = $40 / 4 = $10

Zones:
- $5070-$5080
- $5080-$5090
- $5090-$5100
- etc.
```

### Participation Metrics

| Metric | Calculation |
|--------|-------------|
| Volume | Total contracts traded in zone |
| Time | Minutes price spent in zone |
| Delta | Net buy/sell in zone |
| Big Trades | Institutional orders in zone |

### Heatmap Visualization

```
Zone         │ Volume │ Time │ Delta │ Big Trades
─────────────┼────────┼──────┼───────┼───────────
$5090-$5100  │ ████   │ 35m  │ +120  │ ●●●
$5080-$5090  │ ██████ │ 55m  │ +340  │ ●●●●●  ← High Activity
$5070-$5080  │ ███    │ 25m  │ -80   │ ●●
$5060-$5070  │ █      │ 10m  │ -200  │ ●
```

---

## Backtesting

### Overview

Historical analysis module for testing trading strategies against past market data.

### Available Strategies

| Strategy | Parameters | Description |
|----------|------------|-------------|
| VWAP Reversion | Distance threshold | Fade moves away from VWAP |
| Breakout | ATR multiple | Trade breaks of ranges |
| Mean Reversion | Bollinger bands | Fade extreme moves |
| Momentum | ROC period | Trade with momentum |

### Performance Metrics

| Metric | Formula |
|--------|---------|
| Win Rate | Winning Trades / Total Trades |
| Profit Factor | Gross Profit / Gross Loss |
| Sharpe Ratio | (Return - Risk Free) / Std Dev |
| Max Drawdown | Peak to Trough decline |
| Expectancy | (Win% × Avg Win) - (Loss% × Avg Loss) |

### Results Display

```
BACKTEST RESULTS - VWAP Reversion (30 days)
──────────────────────────────────────────
Total Trades:    127
Win Rate:        58.3%
Profit Factor:   1.85
Avg Winner:      $850
Avg Loser:       $520
Max Drawdown:    -$4,200
Net P&L:         +$12,450
Sharpe Ratio:    1.42
```

---

## Connection Status

### Status Indicators

| Status | Visual | Meaning |
|--------|--------|---------|
| **LIVE** | Green dots (pulsing) | Real-time data connected |
| **RECONNECTING** | Yellow dots (pulsing) | Attempting to reconnect |
| **OFFLINE** | Red dots (static) | No data connection |

### Latency Indicator

```
LATENCY: ~10ms [EXCELLENT]
```

| Latency | Rating | Color |
|---------|--------|-------|
| <20ms | EXCELLENT | Green |
| 20-100ms | GOOD | Yellow |
| >100ms | POOR | Red |

### Source Display

Shows current data source:
- `DATABENTO_LIVE` - Primary real-time feed
- `YFINANCE (fallback)` - Backup delayed feed
- `RECONNECTING...` - Attempting connection
- `WAITING_CONNECTION_SLOT` - Queued for connection

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `G` | Toggle Gamma Levels |
| `1-5` | Switch timeframes |
| `Esc` | Close modals/tooltips |

---

## Best Practices

### Pre-Market Checklist

1. Check **COT positioning** for weekly bias
2. Review **prior day levels** (PD High, Low, POC)
3. Note **ETF flows** for institutional sentiment
4. Identify **key support/resistance** zones

### During Session

1. Monitor **Order Flow** for real-time bias
2. Watch for **Big Trades** at key levels
3. Track **CVD divergences** for reversals
4. Use **Wyckoff phase** for context

### Position Management

1. Size based on **notional value** not contracts
2. Reduce size when **divergent** signals
3. Add when **aligned** signals confirm
4. Respect **Value Area** boundaries

---

## Glossary

| Term | Definition |
|------|------------|
| **CVD** | Cumulative Volume Delta - Running total of buy vs sell aggression |
| **POC** | Point of Control - Price with highest volume |
| **VAH/VAL** | Value Area High/Low - 70% volume bounds |
| **TPO** | Time Price Opportunity - Time-based profile |
| **IB** | Initial Balance - First hour range |
| **COT** | Commitment of Traders - CFTC positioning report |
| **OI** | Open Interest - Outstanding contracts |
| **VSA** | Volume Spread Analysis - Volume vs price spread |
| **ATR** | Average True Range - Volatility measure |
| **VWAP** | Volume Weighted Average Price |

---

## Support & Resources

- **Live Dashboard:** https://frontend-blue-two-84.vercel.app
- **Backend API:** https://backend-production-ea57.up.railway.app
- **Data Updates:** Real-time via Databento WebSocket

---

*Last Updated: January 2026*
*Version: 15.0*
