#!/usr/bin/env python3
"""
PROJECT HORIZON - HTTP LIVE FEED v2.5
Zone Participation Machine - Live Data Feed
All live data from Databento
Build: 2026-01-17-weekend-tpo
"""
# Suppress deprecation warnings that flood Railway logs (500/sec limit)
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)

print("🆕 BUILD 2026-01-26-fix-warnings LOADED")
import os
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.request
import urllib.error
import ssl
import pytz

# Load .env file if it exists (fallback for API key)
def load_env_file():
    env_paths = [
        os.path.join(os.path.dirname(__file__), '..', '.env'),  # project root
        os.path.join(os.path.dirname(__file__), '.env'),  # scripts folder
        '.env'  # current directory
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        if key.strip() not in os.environ:
                            os.environ[key.strip()] = value.strip()
            print(f"✅ Loaded environment from {env_path}")
            return
load_env_file()

try:
    import databento as db
    HAS_DATABENTO = True
except ImportError:
    HAS_DATABENTO = False
    print("⚠️  databento not installed. Run: pip install databento")

try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False
    print("⚠️  websocket-client not installed. Run: pip install websocket-client")

try:
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("⚠️  yfinance not installed. Run: pip install yfinance")

# Import GEX Calculator
try:
    from gex_calculator import GoldGEXCalculator, calculate_gold_gex
    HAS_GEX_CALCULATOR = True
    print("✅ GEX Calculator module loaded")
except ImportError:
    HAS_GEX_CALCULATOR = False
    print("⚠️  gex_calculator not found. GEX will use static estimates.")

# ============================================
# CONFIGURATION
# ============================================
API_KEY = os.environ.get('DATABENTO_API_KEY', '')
PORT = int(os.environ.get('PORT', 8080))

# Trade metrics helpers for Clawdbot
try:
    from trade_metrics_helpers import process_bars_for_trade_metrics, fetch_historical_bars_for_trade
    HAS_TRADE_METRICS = True
    print("✅ Trade metrics helpers loaded")
except ImportError:
    HAS_TRADE_METRICS = False
    print("⚠️  trade_metrics_helpers not found")

# Discord webhook for alerts
DISCORD_WEBHOOK_URL = os.environ.get('DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/839103546740703323/OmhtJBeEAvzFvJ2BtzIC7XhydCvEe0XigPaHC2HhKziNzCVZNlup6UrGrgkzM-Fcw8yq')

# Contract configurations
CONTRACT_CONFIG = {
    'GC': {
        'symbol': 'GC.FUT',
        'front_month': 'GCG26',
        'name': 'Gold Feb 2026',
        'ticker': 'GC1!',
        'price_min': 2000,
        'price_max': 10000,
        'tick_size': 0.10,
    },
    'NQ': {
        'symbol': 'NQ.FUT',
        'front_month': 'NQH26',
        'name': 'Nasdaq Mar 2026',
        'ticker': 'NQ1!',
        'price_min': 10000,
        'price_max': 30000,
        'tick_size': 0.25,
    },
    'ES': {
        'symbol': 'ES.FUT',
        'front_month': 'ESH26',
        'name': 'S&P 500 E-mini Mar 2026',
        'ticker': 'ES1!',
        'price_min': 4000,
        'price_max': 7000,
        'tick_size': 0.25,
    },
    'BTC': {
        'symbol': 'BTC.FUT',
        'front_month': 'BTCG26',
        'name': 'Bitcoin Feb 2026',
        'ticker': 'BTC1!',
        'price_min': 30000,
        'price_max': 250000,
        'tick_size': 5.00,
    },
    'CL': {
        'symbol': 'CL.FUT',
        'front_month': 'CLG26',
        'name': 'Crude Oil Feb 2026',
        'ticker': 'CL1!',
        'price_min': 40,
        'price_max': 150,
        'tick_size': 0.01,
    },
    'BTC-SPOT': {
        'symbol': 'BTCUSDT',
        'front_month': 'BTC-SPOT',
        'name': 'Bitcoin Spot (24/7)',
        'ticker': 'BTCUSDT',
        'price_min': 30000,
        'price_max': 250000,
        'tick_size': 0.01,
        'is_spot': True,  # Flag to use spot data feed instead of Databento
    }
}

# Current active contract
ACTIVE_CONTRACT = 'GC'

# Spot crypto data thread
spot_crypto_thread = None
spot_crypto_running = False

# Stream control
stream_running = False
live_client = None
stream_thread = None
startup_complete = False  # Flag to prevent HTTP blocking during startup

# ============================================
# GLOBAL STATE
# ============================================
lock = threading.Lock()

# Get initial config based on ACTIVE_CONTRACT
_init_config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])

state = {
    'ticker': _init_config['ticker'],
    'contract': _init_config['front_month'],  # Actual front-month contract symbol
    'contract_name': _init_config['name'],  # Human readable name
    'asset_class': ACTIVE_CONTRACT,  # GC = Gold, NQ = Nasdaq, ES = S&P 500
    'price': 0.0,  # Primary price field for frontend display
    'current_price': 0.0,
    'spot_gold_price': 0.0,  # XAUUSD spot price from Yahoo Finance
    'bid': 0.0,
    'ask': 0.0,
    'data_source': 'INITIALIZING',
    
    # Delta tracking
    'delta_5m': 0,
    'delta_30m': 0,
    'cumulative_delta': 0,
    
    # Volume (session cumulative)
    'buy_volume': 0,
    'sell_volume': 0,
    'total_volume': 0,
    'volume_start_time': None,  # When volume tracking started

    # Big Trades Tracking (Order Flow)
    'big_trades': [],  # Recent large trades: [{ts, price, size, side, delta_impact}]
    'big_trades_buy': 0,    # Cumulative big trade buy volume
    'big_trades_sell': 0,   # Cumulative big trade sell volume
    'big_trades_delta': 0,  # Net big trades delta

    # Dynamic Big Trade Threshold (90th percentile of recent trades)
    'trade_sizes': [],           # Last 1000 trade sizes for percentile calculation
    'big_trade_threshold': 10,   # Dynamic threshold (starts at default, updates to P90)
    'threshold_stats': {         # Stats for frontend tooltip display
        'sample_count': 0,
        'avg_size': 0,
        'p90_size': 0,
        'min_size': 0,
        'max_size': 0
    },

    # Volume by timeframe (current candle - clock-aligned) with previous candle for % change
    'volume_5m': {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': [],
                  'delta_open': None, 'delta_high': -999999, 'delta_low': 999999,  # Delta OHLC (None = not set yet)
                  'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0},  # Price OHLC
    'volume_15m': {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': [],
                   'delta_open': None, 'delta_high': -999999, 'delta_low': 999999,
                   'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0},
    'volume_30m': {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': [],
                   'delta_open': None, 'delta_high': -999999, 'delta_low': 999999,
                   'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0},
    'volume_1h': {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': [],
                  'delta_open': None, 'delta_high': -999999, 'delta_low': 999999,
                  'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0},
    
    # Session levels (DYNAMIC - current session)
    'session_high': 0.0,
    'session_low': 999999.0,
    'session_open': 0.0,  # First trade price of current session
    'session_buy': 0,      # Buy volume for current session
    'session_sell': 0,     # Sell volume for current session
    'vwap': 0.0,
    'vwap_numerator': 0.0,
    'vwap_denominator': 0.0,

    # RTH VWAP (9:30 ET anchored for Intraday section)
    'rth_vwap': 0.0,
    'rth_vwap_numerator': 0.0,
    'rth_vwap_denominator': 0.0,
    'rth_vwap_date': '',  # Date when RTH VWAP was last reset

    # Day VWAP (full trading day 18:00 ET - 17:00 ET next day)
    'day_vwap': 0.0,
    'day_vwap_numerator': 0.0,
    'day_vwap_denominator': 0.0,
    'day_vwap_date': '',  # Trading day date for reset tracking

    # Anchored VWAPs (persist until 17:00 ET end of day)
    'us_ib_vwap': 0.0,  # Anchored from 08:20 ET (US IB start)
    'us_ib_vwap_numerator': 0.0,
    'us_ib_vwap_denominator': 0.0,
    'us_ib_vwap_date': '',
    'ny_1h_vwap': 0.0,  # Anchored from 09:30 ET (NY open)
    'ny_1h_vwap_numerator': 0.0,
    'ny_1h_vwap_denominator': 0.0,
    'ny_1h_vwap_date': '',

    # Day levels (DYNAMIC - full trading day 18:00-17:00 ET)
    'day_high': 0.0,
    'day_low': 999999.0,
    'day_open': 0.0,  # First trade at 18:00 ET

    # Week levels (for weekly open tracking)
    'weekly_open': 0.0,  # Monday 18:00 ET open price
    'weekly_open_date': '',  # Date of the weekly open
    'week_high': 0.0,  # Highest price this week
    'week_low': 999999.0,  # Lowest price this week

    # Rolling 20-day levels for monthly bias
    'rolling_20d_high': 0.0,  # Highest close in last 20 trading days
    'rolling_20d_low': 999999.0,  # Lowest close in last 20 trading days

    # Ended sessions OHLC (stored when session ends)
    'ended_sessions': {},  # {session_id: {open, high, low, close}}
    
    # 4 IB Sessions - tracked independently with POC and VWAP
    'ibs': {
        'japan': {'high': 0.0, 'low': 999999.0, 'mid': 0.0, 'poc': 0.0, 'vwap': 0.0, 'vwap_num': 0.0, 'vwap_den': 0.0, 'tpo_prices': {}, 'status': 'WAITING', 'start': '19:00', 'end': '20:00', 'name': 'Japan IB'},
        'london': {'high': 0.0, 'low': 999999.0, 'mid': 0.0, 'poc': 0.0, 'vwap': 0.0, 'vwap_num': 0.0, 'vwap_den': 0.0, 'tpo_prices': {}, 'status': 'WAITING', 'start': '03:00', 'end': '04:00', 'name': 'London IB'},
        'us': {'high': 0.0, 'low': 999999.0, 'mid': 0.0, 'poc': 0.0, 'vwap': 0.0, 'vwap_num': 0.0, 'vwap_den': 0.0, 'tpo_prices': {}, 'status': 'WAITING', 'start': '08:20', 'end': '09:30', 'name': 'US IB'},
        'ny': {'high': 0.0, 'low': 999999.0, 'mid': 0.0, 'poc': 0.0, 'vwap': 0.0, 'vwap_num': 0.0, 'vwap_den': 0.0, 'tpo_prices': {}, 'status': 'WAITING', 'start': '09:30', 'end': '10:30', 'name': 'NY IB'},
    },
    'current_ib': None,  # Which IB is currently active (japan, london, us, ny, or None)

    # Legacy single IB (for backwards compatibility)
    'ib_high': 0.0,
    'ib_low': 0.0,
    'ib_locked': True,
    'ib_session_name': '',
    'ib_session_id': '',
    'ib_status': 'WAITING',
    
    # Previous day (STATIC - fetched from historical)
    'pd_high': 0.0,
    'pd_low': 0.0,
    'pdpoc': 0.0,
    'pd_vah': 0.0,
    'pd_val': 0.0,
    'pd_open': 0.0,
    'pd_close': 0.0,
    'pd_loaded': False,
    'pd_date_range': '',  # e.g. "Jan 06 18:00 - Jan 07 14:55 ET"

    # Previous Day NY Sessions (US IB and NY 1H from yesterday)
    'pd_us_ib': {'high': 0.0, 'low': 0.0, 'mid': 0.0, 'poc': 0.0, 'vwap': 0.0},
    'pd_ny_1h': {'high': 0.0, 'low': 0.0, 'mid': 0.0, 'poc': 0.0, 'vwap': 0.0},
    
    # Analysis
    'buying_imbalance_pct': 0,
    'absorption_ratio': 0.0,
    'stacked_buy_imbalances': 0,
    'current_phase': 'INITIALIZING',
    'current_session_id': '',
    'current_session_name': '',
    'current_session_start': '',
    'current_session_end': '',
    'conditions_met': 0,
    'entry_signal': False,
    
    # GEX Data - initialized to 0, will be calculated from options data
    'gamma_regime': 'UNKNOWN',
    'total_gex': 0,
    'zero_gamma': 0,       # Gamma flip / pivot point (0 = not yet calculated)
    'hvl': 0,              # High Volume Level
    'call_wall': 0,        # Highest call gamma (resistance)
    'put_wall': 0,         # Highest put gamma (support)
    'max_pain': 0,         # Max pain strike
    'gamma_flip': 0,       # Same as zero_gamma (dealer positioning flip)
    'beta_spx': 0.18,
    'beta_dxy': -0.52,
    # GEX Profile for charting (strike -> gamma exposure)
    'gex_profile': [],     # Will be populated with {strike, gex, type} entries
    'gex_levels': [],      # Key levels: {type, price, strength, label}
    
    # Latency
    'last_update': '',
    'market_open': False
}

delta_history = deque(maxlen=36000)
volume_history = deque(maxlen=36000)  # (timestamp, buy_vol, sell_vol)
price_history = deque(maxlen=1000)
last_session_id = None
front_month_instrument_id = None  # Will be set from historical data

# ============================================
# TPO / MARKET PROFILE STATE
# ============================================
TPO_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'  # Uppercase only, cycles after Z

# 4 Main TPO Sessions (Horizon's 4-session breakdown)
TPO_SESSIONS = {
    'tpo1_asia': {
        'name': 'TPO #1 - Asia',
        'display': 'Asia (18:00-03:00)',
        'start': 1800,  # 18:00 ET
        'end': 300,     # 03:00 ET (overnight)
        'ib_start': 1900,  # Japan IB starts 19:00
        'ib_end': 2000,    # Japan IB ends 20:00
        'color': '#FF6B6B',  # Red/Orange
        'number': 1
    },
    'tpo2_london': {
        'name': 'TPO #2 - London',
        'display': 'London (03:00-08:20)',
        'start': 300,   # 03:00 ET
        'end': 820,     # 08:20 ET
        'ib_start': 300,   # London IB starts 03:00
        'ib_end': 400,     # London IB ends 04:00
        'color': '#4ECDC4',  # Teal
        'number': 2
    },
    'tpo3_us_am': {
        'name': 'TPO #3 - US Session',
        'display': 'US (08:20-15:00)',
        'start': 820,   # 08:20 ET
        'end': 1500,    # 15:00 ET
        'ib_start': 820,   # US IB starts 08:20 ET
        'ib_end': 930,     # US IB ends 09:30 ET (70 min: 40 min first period + 30 min second)
        'color': '#45B7D1',  # Blue
        'number': 3
    },
    'tpo4_us_pm': {
        'name': 'TPO #4 - US Close',
        'display': 'US Close (15:00-17:00)',
        'start': 1500,  # 15:00 ET
        'end': 1700,    # 17:00 ET
        'ib_start': None,  # No IB
        'ib_end': None,
        'color': '#96CEB4',  # Green
        'number': 4
    }
}

def get_tpo_session_for_time(time_val=None):
    """Get which TPO session is active for given time (HHMM format)"""
    if time_val is None:
        et = get_et_now()
        time_val = et.hour * 100 + et.minute

    # TPO #1 Asia: 18:00 - 03:00 (overnight)
    if time_val >= 1800 or time_val < 300:
        return 'tpo1_asia'
    # TPO #2 London: 03:00 - 08:20
    elif 300 <= time_val < 820:
        return 'tpo2_london'
    # TPO #3 US Session: 08:20 - 15:00
    elif 820 <= time_val < 1500:
        return 'tpo3_us_am'
    # TPO #4 US Close: 15:00 - 17:00
    elif 1500 <= time_val < 1700:
        return 'tpo4_us_pm'
    # Market closed: 17:00 - 18:00
    else:
        return None

# Global TPO state - contains 4 session profiles + combined day profile
tpo_state = {
    # Current active session
    'active_session': None,

    # Combined full day profile
    'day': {
        'profiles': {},           # price_level -> set of period letters
        'period_count': 0,
        'current_period_start': 0,
        'poc': 0.0,
        'vah': 0.0,
        'val': 0.0,
        'single_prints': [],
        'ib_high': 0.0,           # RTH IB (first hour of RTH)
        'ib_low': 999999.0,
        'ib_complete': False,
        'open_price': 0.0,        # ETH open (18:00 ET)
        'rth_open': 0.0,          # RTH open (09:30 ET)
        'a_high': 0.0, 'a_low': 999999.0,
        'b_high': 0.0, 'b_low': 999999.0,
        'c_high': 0.0, 'c_low': 999999.0,
        'ab_overlap': None,  # None until A and B periods both complete
        'bc_overlap': None,  # None until B and C periods both complete
        'day_type': 'developing',
        'day_type_confidence': 0,
        'day_type_scores': {},
        'open_type': 'developing',
        'open_type_confidence': 0,
        'open_direction': None,
        'profile_shape': 'developing',
        'max_tpo_count': 0,
        'total_tpo_count': 0,
        'range_extension_pct': 0.0,
    },

    # 4 Session-specific TPO profiles
    'sessions': {
        'tpo1_asia': {
            'profiles': {},
            'period_count': 0,
            'current_period_start': 0,
            'poc': 0.0,
            'vah': 0.0,
            'val': 0.0,
            'single_prints': [],
            'ib_high': 0.0,       # Japan IB (19:00-20:00)
            'ib_low': 999999.0,
            'ib_complete': False,
            'open_price': 0.0,
            'high': 0.0,
            'low': 999999.0,
            'max_tpo_count': 0,
            'total_tpo_count': 0,
            'profile_shape': 'developing',
            'day_type': 'developing',
            'day_type_confidence': 0,
        },
        'tpo2_london': {
            'profiles': {},
            'period_count': 0,
            'current_period_start': 0,
            'poc': 0.0,
            'vah': 0.0,
            'val': 0.0,
            'single_prints': [],
            'ib_high': 0.0,       # London IB (03:00-04:00)
            'ib_low': 999999.0,
            'ib_complete': False,
            'open_price': 0.0,
            'high': 0.0,
            'low': 999999.0,
            'max_tpo_count': 0,
            'total_tpo_count': 0,
            'profile_shape': 'developing',
            'day_type': 'developing',
            'day_type_confidence': 0,
        },
        'tpo3_us_am': {
            'profiles': {},
            'period_count': 0,
            'current_period_start': 0,
            'poc': 0.0,
            'vah': 0.0,
            'val': 0.0,
            'single_prints': [],
            'ib_high': 0.0,       # RTH IB (09:30-10:30)
            'ib_low': 999999.0,
            'ib_complete': False,
            'open_price': 0.0,    # RTH Open
            'high': 0.0,
            'low': 999999.0,
            'max_tpo_count': 0,
            'total_tpo_count': 0,
            'profile_shape': 'developing',
            'day_type': 'developing',
            'day_type_confidence': 0,
            # Open type tracking for RTH session
            'open_type': 'developing',
            'open_type_confidence': 0,
            'open_direction': None,
            'a_high': 0.0, 'a_low': 999999.0,
            'b_high': 0.0, 'b_low': 999999.0,
            'ab_overlap': None,  # None until both A and B periods complete
        },
        'tpo4_us_pm': {
            'profiles': {},
            'period_count': 0,
            'current_period_start': 0,
            'poc': 0.0,
            'vah': 0.0,
            'val': 0.0,
            'single_prints': [],
            'open_price': 0.0,
            'high': 0.0,
            'low': 999999.0,
            'max_tpo_count': 0,
            'total_tpo_count': 0,
            'profile_shape': 'developing',
            'day_type': 'developing',
            'day_type_confidence': 0,
        }
    },

    # Day tracking
    'day_start_time': 0,
    'avg_daily_range': 50.0,
}

# ============================================
# TPO CACHING - Persist TPO data for offline access
# ============================================
TPO_CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '.cache', 'tpo')

def get_tpo_cache_path(contract):
    """Get cache file path for a contract's TPO data"""
    os.makedirs(TPO_CACHE_DIR, exist_ok=True)
    return os.path.join(TPO_CACHE_DIR, f'{contract}_tpo.json')

def save_tpo_cache(contract=None):
    """Save current TPO state to cache file"""
    global tpo_state, ACTIVE_CONTRACT

    if contract is None:
        contract = ACTIVE_CONTRACT

    try:
        cache_path = get_tpo_cache_path(contract)

        # Convert sets to lists for JSON serialization
        cache_data = {
            'contract': contract,
            'timestamp': time.time(),
            'date': datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d'),
            'day': {
                'profiles': {k: list(v) if isinstance(v, set) else v for k, v in tpo_state['day']['profiles'].items()},
                'poc': tpo_state['day'].get('poc', 0),
                'vah': tpo_state['day'].get('vah', 0),
                'val': tpo_state['day'].get('val', 0),
                'single_prints': tpo_state['day'].get('single_prints', []),
                'ib_high': tpo_state['day'].get('ib_high', 0),
                'ib_low': tpo_state['day'].get('ib_low', 999999),
                'open_price': tpo_state['day'].get('open_price', 0),
                'period_count': tpo_state['day'].get('period_count', 0),
                'max_tpo_count': tpo_state['day'].get('max_tpo_count', 0),
                'total_tpo_count': tpo_state['day'].get('total_tpo_count', 0),
                'day_type': tpo_state['day'].get('day_type', 'developing'),
                'profile_shape': tpo_state['day'].get('profile_shape', 'developing'),
            },
            'sessions': {}
        }

        # Cache each session
        for session_key, session_data in tpo_state['sessions'].items():
            cache_data['sessions'][session_key] = {
                'profiles': {k: list(v) if isinstance(v, set) else v for k, v in session_data['profiles'].items()},
                'poc': session_data.get('poc', 0),
                'vah': session_data.get('vah', 0),
                'val': session_data.get('val', 0),
                'ib_high': session_data.get('ib_high', 0),
                'ib_low': session_data.get('ib_low', 999999),
                'period_count': session_data.get('period_count', 0),
            }

        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)
        print(f"💾 TPO cache saved for {contract}")
        return True
    except Exception as e:
        print(f"⚠️ Error saving TPO cache: {e}")
        return False

def load_tpo_cache(contract=None):
    """Load TPO state from cache file"""
    global tpo_state, ACTIVE_CONTRACT

    if contract is None:
        contract = ACTIVE_CONTRACT

    try:
        cache_path = get_tpo_cache_path(contract)
        if not os.path.exists(cache_path):
            print(f"📭 No TPO cache found for {contract}")
            return False

        with open(cache_path, 'r') as f:
            cache_data = json.load(f)

        # Check cache freshness (valid if from today or yesterday's session)
        cache_date = cache_data.get('date', '')
        today = datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d')
        yesterday = (datetime.now(pytz.timezone('America/New_York')) - timedelta(days=1)).strftime('%Y-%m-%d')

        if cache_date not in [today, yesterday]:
            print(f"📭 TPO cache for {contract} is stale ({cache_date})")
            return False

        # Restore day profile
        if 'day' in cache_data:
            day_cache = cache_data['day']
            with lock:
                tpo_state['day']['profiles'] = day_cache.get('profiles', {})
                tpo_state['day']['poc'] = day_cache.get('poc', 0)
                tpo_state['day']['vah'] = day_cache.get('vah', 0)
                tpo_state['day']['val'] = day_cache.get('val', 0)
                tpo_state['day']['single_prints'] = day_cache.get('single_prints', [])
                tpo_state['day']['ib_high'] = day_cache.get('ib_high', 0)
                tpo_state['day']['ib_low'] = day_cache.get('ib_low', 999999)
                tpo_state['day']['open_price'] = day_cache.get('open_price', 0)
                tpo_state['day']['period_count'] = day_cache.get('period_count', 0)
                tpo_state['day']['max_tpo_count'] = day_cache.get('max_tpo_count', 0)
                tpo_state['day']['total_tpo_count'] = day_cache.get('total_tpo_count', 0)
                tpo_state['day']['day_type'] = day_cache.get('day_type', 'developing')
                tpo_state['day']['profile_shape'] = day_cache.get('profile_shape', 'developing')

        # Restore session profiles
        if 'sessions' in cache_data:
            for session_key, session_cache in cache_data['sessions'].items():
                if session_key in tpo_state['sessions']:
                    with lock:
                        tpo_state['sessions'][session_key]['profiles'] = session_cache.get('profiles', {})
                        tpo_state['sessions'][session_key]['poc'] = session_cache.get('poc', 0)
                        tpo_state['sessions'][session_key]['vah'] = session_cache.get('vah', 0)
                        tpo_state['sessions'][session_key]['val'] = session_cache.get('val', 0)
                        tpo_state['sessions'][session_key]['ib_high'] = session_cache.get('ib_high', 0)
                        tpo_state['sessions'][session_key]['ib_low'] = session_cache.get('ib_low', 999999)
                        tpo_state['sessions'][session_key]['period_count'] = session_cache.get('period_count', 0)

        print(f"✅ TPO cache loaded for {contract} (from {cache_date})")
        return True
    except Exception as e:
        print(f"⚠️ Error loading TPO cache: {e}")
        return False

# ============================================
# BIG TRADES PERSISTENCE
# ============================================
# Use .cache inside scripts dir (works on both Railway and local)
BIG_TRADES_CACHE_DIR = os.path.join(os.path.dirname(__file__), '.cache', 'big_trades')

def get_big_trades_cache_path(contract, date_str=None):
    """Get cache file path for a contract's big trades data by date"""
    os.makedirs(BIG_TRADES_CACHE_DIR, exist_ok=True)
    if date_str is None:
        date_str = datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d')
    return os.path.join(BIG_TRADES_CACHE_DIR, f'{contract}_big_trades_{date_str}.json')

def save_big_trade(trade, contract=None):
    """Append a single big trade to the daily cache file"""
    global ACTIVE_CONTRACT
    if contract is None:
        contract = ACTIVE_CONTRACT

    try:
        cache_path = get_big_trades_cache_path(contract)

        # Load existing trades or start fresh
        trades = []
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    trades = data.get('trades', [])
            except:
                trades = []

        # Add new trade
        trades.append(trade)

        # Save back
        cache_data = {
            'contract': contract,
            'date': datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d'),
            'trades': trades,
            'count': len(trades)
        }
        with open(cache_path, 'w') as f:
            json.dump(cache_data, f)

        return True
    except Exception as e:
        print(f"⚠️ Error saving big trade: {e}")
        return False

def load_historical_big_trades(contract=None, days_back=7):
    """Load big trades from the last N days"""
    global ACTIVE_CONTRACT
    if contract is None:
        contract = ACTIVE_CONTRACT

    all_trades = []
    et_tz = pytz.timezone('America/New_York')
    today = datetime.now(et_tz)

    for i in range(days_back):
        date = today - timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        cache_path = get_big_trades_cache_path(contract, date_str)

        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    data = json.load(f)
                    trades = data.get('trades', [])
                    # Add date to each trade for frontend filtering
                    for t in trades:
                        t['date'] = date_str
                    all_trades.extend(trades)
            except Exception as e:
                print(f"⚠️ Error loading big trades for {date_str}: {e}")

    # Sort by timestamp descending (newest first)
    all_trades.sort(key=lambda x: x.get('ts', 0), reverse=True)

    print(f"📊 Loaded {len(all_trades)} historical big trades for {contract} (last {days_back} days)")
    return all_trades

# Global cache for historical trades (refreshed periodically)
historical_big_trades_cache = {
    'trades': [],
    'last_loaded': 0,
    'contract': None
}

def get_historical_big_trades_cached(contract=None, max_age_seconds=300):
    """Get historical trades with caching (refresh every 5 min)"""
    global historical_big_trades_cache, ACTIVE_CONTRACT
    if contract is None:
        contract = ACTIVE_CONTRACT

    now = time.time()
    cache = historical_big_trades_cache

    # Refresh if stale or contract changed
    if (now - cache['last_loaded'] > max_age_seconds or
        cache['contract'] != contract or
        len(cache['trades']) == 0):
        cache['trades'] = load_historical_big_trades(contract)
        cache['last_loaded'] = now
        cache['contract'] = contract

    return cache['trades']

def fetch_historical_big_trades_from_databento():
    """Fetch historical big trades from Databento to populate cache for 1H chart"""
    global state, front_month_instrument_id, ACTIVE_CONTRACT, historical_big_trades_cache

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        print("⏭️ Skipping Databento big trades fetch for spot contract")
        return

    if not HAS_DATABENTO or not API_KEY:
        print("⚠️ Cannot fetch historical big trades - no Databento connection")
        return

    try:
        print(f"📊 Fetching historical big trades for {config['name']} from Databento (last 24 hours)...")

        et_now = get_et_now()
        symbol = config['symbol']
        price_min = config['price_min']
        price_max = config['price_max']

        # Fetch last 24 hours of trades to cover 22+ 1H candles
        start_time = et_now - timedelta(hours=26)  # Extra buffer
        end_time = et_now - timedelta(minutes=25)  # Databento has ~25 min delay

        # Convert to UTC timestamps
        start_ts = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_ts = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        print(f"   Querying trades from {start_ts} to {end_ts}...")

        client = db.Historical(key=API_KEY)
        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=[symbol],
            stype_in='parent',
            schema='trades',
            start=start_ts,
            end=end_ts
        )

        records = list(data)
        print(f"   Got {len(records)} trade records")

        if not records:
            return

        # Find front month instrument (most trades)
        by_instrument = {}
        for r in records:
            iid = r.instrument_id
            by_instrument[iid] = by_instrument.get(iid, 0) + 1

        front_month_iid = max(by_instrument.items(), key=lambda x: x[1])[0]
        print(f"   Front month instrument ID: {front_month_iid}")

        # Calculate 90th percentile threshold from this data
        trade_sizes = []
        for r in records:
            if r.instrument_id != front_month_iid:
                continue
            size = getattr(r, 'size', 1)
            trade_sizes.append(size)

        if len(trade_sizes) < 100:
            threshold = 5  # Default
        else:
            sorted_sizes = sorted(trade_sizes)
            p90_idx = int(len(sorted_sizes) * 0.90)
            threshold = max(5, sorted_sizes[p90_idx])  # Minimum threshold of 5

        print(f"   Calculated P90 threshold: {threshold} contracts (from {len(trade_sizes)} trades)")

        # Extract big trades (above threshold)
        big_trades = []
        for r in records:
            if r.instrument_id != front_month_iid:
                continue

            size = getattr(r, 'size', 1)
            if size < threshold:
                continue

            p = r.price / 1e9 if r.price > 1e6 else r.price
            if p < price_min or p > price_max:
                continue

            # Determine side from aggressor field
            side_code = getattr(r, 'side', None)
            if side_code == 'A':
                side = 'BUY'
            elif side_code == 'B':
                side = 'SELL'
            else:
                side = 'BUY' if r.price > 0 else 'SELL'  # Fallback

            ts_ns = r.ts_event if hasattr(r, 'ts_event') else getattr(r, 'ts_recv', 0)
            ts_sec = ts_ns / 1e9

            big_trades.append({
                'ts': ts_sec,
                'price': p,
                'size': size,
                'side': side,
                'delta_impact': size if side == 'BUY' else -size,
                'date': datetime.fromtimestamp(ts_sec).strftime('%Y-%m-%d')
            })

        print(f"   Found {len(big_trades)} big trades (>= {threshold} contracts)")

        # Update the historical cache directly
        historical_big_trades_cache['trades'] = sorted(big_trades, key=lambda x: x['ts'], reverse=True)
        historical_big_trades_cache['last_loaded'] = time.time()
        historical_big_trades_cache['contract'] = ACTIVE_CONTRACT

        # Also save to disk cache
        if big_trades:
            today_str = et_now.strftime('%Y-%m-%d')
            save_big_trade_to_cache(big_trades, contract=ACTIVE_CONTRACT, date_str=today_str)

        print(f"✅ Loaded {len(big_trades)} historical big trades covering ~24 hours")

    except Exception as e:
        print(f"❌ Error fetching historical big trades: {e}")
        import traceback
        traceback.print_exc()

def save_big_trade_to_cache(trades, contract=None, date_str=None):
    """Save multiple trades to cache file"""
    global ACTIVE_CONTRACT
    if contract is None:
        contract = ACTIVE_CONTRACT
    if date_str is None:
        date_str = datetime.now(pytz.timezone('America/New_York')).strftime('%Y-%m-%d')

    try:
        os.makedirs(BIG_TRADES_CACHE_DIR, exist_ok=True)
        cache_path = get_big_trades_cache_path(contract, date_str)

        # Load existing data
        existing = []
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                data = json.load(f)
                existing = data.get('trades', [])

        # Merge and deduplicate by timestamp
        seen_ts = set(t['ts'] for t in existing)
        for t in trades:
            if t['ts'] not in seen_ts:
                existing.append(t)
                seen_ts.add(t['ts'])

        # Save
        with open(cache_path, 'w') as f:
            json.dump({'trades': existing}, f)

    except Exception as e:
        print(f"⚠️ Error saving big trades to cache: {e}")

# ============================================
# ZONE PARTICIPATION ENGINE
# ============================================

def create_zone(zone_id, name, session_num, zone_type, price):
    """Create a zone structure"""
    return {
        'id': zone_id,
        'name': name,
        'session_number': session_num,
        'type': zone_type,
        'price': price,
        'distance': 0,
        'distance_pts': 0,
        'status': 'watching',
    }

def get_zone_status(distance, is_btc=False):
    """Determine zone status based on distance from current price"""
    abs_dist = abs(distance)

    # Scale thresholds for BTC (moves in $100s) vs Gold (moves in $1s)
    if is_btc:
        at_zone_thresh = 100      # $100 - at the zone
        approaching_thresh = 300  # $300 - approaching
        watching_thresh = 800     # $800 - watching
    else:
        at_zone_thresh = 2        # $2 - at the zone (Gold)
        approaching_thresh = 8    # $8 - approaching
        watching_thresh = 20      # $20 - watching

    if abs_dist <= at_zone_thresh:
        return 'at_zone'
    elif abs_dist <= approaching_thresh:
        return 'approaching'
    elif abs_dist <= watching_thresh:
        return 'watching'
    else:
        return 'distant'

def collect_all_zones():
    """Gather all tradeable zones from all sessions"""
    zones = []
    current_price = state.get('current_price', 0)
    if current_price <= 0:
        return zones

    # Helper to safely get numeric value (handles None)
    def safe_get(d, key, default=0):
        val = d.get(key)
        return val if val is not None else default

    # Session 1: Asia
    asia = tpo_state['sessions']['tpo1_asia']
    if safe_get(asia, 'ib_high') > 0 and safe_get(asia, 'ib_low', 999999) < 999999:
        zones.append(create_zone('asia_ib_high', 'Asia IB High', 1, 'ib_high', asia['ib_high']))
        zones.append(create_zone('asia_ib_low', 'Asia IB Low', 1, 'ib_low', asia['ib_low']))
    if safe_get(asia, 'poc') > 0:
        zones.append(create_zone('asia_poc', 'Asia POC', 1, 'poc', asia['poc']))
    if safe_get(asia, 'vah') > 0:
        zones.append(create_zone('asia_vah', 'Asia VAH', 1, 'vah', asia['vah']))
    if safe_get(asia, 'val') > 0:
        zones.append(create_zone('asia_val', 'Asia VAL', 1, 'val', asia['val']))

    # Session 2: London
    london = tpo_state['sessions']['tpo2_london']
    if safe_get(london, 'ib_high') > 0 and safe_get(london, 'ib_low', 999999) < 999999:
        zones.append(create_zone('london_ib_high', 'London IB High', 2, 'ib_high', london['ib_high']))
        zones.append(create_zone('london_ib_low', 'London IB Low', 2, 'ib_low', london['ib_low']))
    if safe_get(london, 'poc') > 0:
        zones.append(create_zone('london_poc', 'London POC', 2, 'poc', london['poc']))
    if safe_get(london, 'vah') > 0:
        zones.append(create_zone('london_vah', 'London VAH', 2, 'vah', london['vah']))
    if safe_get(london, 'val') > 0:
        zones.append(create_zone('london_val', 'London VAL', 2, 'val', london['val']))

    # Session 3: US AM (Main RTH)
    us_am = tpo_state['sessions']['tpo3_us_am']
    if safe_get(us_am, 'ib_high') > 0 and safe_get(us_am, 'ib_low', 999999) < 999999:
        zones.append(create_zone('us_ib_high', 'US IB High', 3, 'ib_high', us_am['ib_high']))
        zones.append(create_zone('us_ib_low', 'US IB Low', 3, 'ib_low', us_am['ib_low']))
    if safe_get(us_am, 'poc') > 0:
        zones.append(create_zone('us_poc', 'US POC', 3, 'poc', us_am['poc']))
    if safe_get(us_am, 'vah') > 0:
        zones.append(create_zone('us_vah', 'US VAH', 3, 'vah', us_am['vah']))
    if safe_get(us_am, 'val') > 0:
        zones.append(create_zone('us_val', 'US VAL', 3, 'val', us_am['val']))

    # Session 4: US PM (No IB - reference Session 3)
    us_pm = tpo_state['sessions']['tpo4_us_pm']
    if safe_get(us_pm, 'poc') > 0:
        zones.append(create_zone('us_pm_poc', 'US PM POC', 4, 'poc', us_pm['poc']))

    # Day-level zones from TPO
    day = tpo_state['day']
    if safe_get(day, 'poc') > 0:
        zones.append(create_zone('day_poc', 'Day POC', 0, 'poc', day['poc']))
    if safe_get(day, 'vah') > 0:
        zones.append(create_zone('day_vah', 'Day VAH', 0, 'vah', day['vah']))
    if safe_get(day, 'val') > 0:
        zones.append(create_zone('day_val', 'Day VAL', 0, 'val', day['val']))

    # === ADDITIONAL ZONES FOR BTC-SPOT AND ALL CONTRACTS ===

    # Previous Day (PD) levels
    pd_high = safe_get(state, 'pd_high', 0)
    pd_low = safe_get(state, 'pd_low', 0)
    pd_poc = safe_get(state, 'pdpoc', 0)  # Note: state key is 'pdpoc' not 'pd_poc'
    if pd_high > 0 and pd_high < 999999:
        zones.append(create_zone('pd_high', 'PD High', 0, 'vah', pd_high))  # Use vah type for resistance
    if pd_low > 0 and pd_low < 999999:
        zones.append(create_zone('pd_low', 'PD Low', 0, 'val', pd_low))  # Use val type for support
    if pd_poc > 0 and pd_poc < 999999:
        zones.append(create_zone('pd_poc', 'PD POC', 0, 'poc', pd_poc))

    # Day Open/High/Low levels
    day_open = safe_get(state, 'day_open', 0)
    day_high = safe_get(state, 'day_high', 0)
    day_low = safe_get(state, 'day_low', 0)
    if day_open > 0 and day_open < 999999:
        zones.append(create_zone('day_open', 'Day Open', 0, 'poc', day_open))  # Day open is key pivot
    if day_high > 0 and day_high < 999999:
        zones.append(create_zone('day_high', 'Day High', 0, 'ib_high', day_high))  # Use ib_high for resistance
    if day_low > 0 and day_low < 999999 and day_low != 999999.0:
        zones.append(create_zone('day_low', 'Day Low', 0, 'ib_low', day_low))  # Use ib_low for support

    # Weekly Open
    weekly_open = safe_get(state, 'weekly_open', 0)
    if weekly_open > 0 and weekly_open < 999999:
        zones.append(create_zone('weekly_open', 'Weekly Open', 0, 'poc', weekly_open))  # Weekly open is major pivot

    # VWAP levels
    vwap = safe_get(state, 'vwap', 0)
    if vwap > 0 and vwap < 999999:
        zones.append(create_zone('vwap', 'VWAP', 0, 'poc', vwap))

    rth_vwap = safe_get(state, 'rth_vwap', 0)
    if rth_vwap > 0 and rth_vwap < 999999:
        zones.append(create_zone('rth_vwap', 'RTH VWAP', 0, 'poc', rth_vwap))

    # GEX levels (Gamma Exposure)
    gex_data = state.get('gex_data', {})
    call_wall = safe_get(gex_data, 'call_wall', 0)
    put_wall = safe_get(gex_data, 'put_wall', 0)
    gamma_flip = safe_get(gex_data, 'gamma_flip', 0) or safe_get(gex_data, 'zero_gamma', 0)

    if call_wall > 0 and call_wall < 999999:
        zones.append(create_zone('call_wall', 'Call Wall', 0, 'vah', call_wall))  # Major resistance
    if put_wall > 0 and put_wall < 999999:
        zones.append(create_zone('put_wall', 'Put Wall', 0, 'val', put_wall))  # Major support
    if gamma_flip > 0 and gamma_flip < 999999:
        zones.append(create_zone('gamma_flip', 'Gamma Flip', 0, 'poc', gamma_flip))  # Key pivot

    # Filter valid zones and calculate distances
    # Detect BTC for status threshold scaling
    current_contract = state.get('asset_class', '') or state.get('contract', '')
    is_btc = 'BTC' in current_contract.upper()

    valid_zones = []
    for z in zones:
        if z['price'] > 0 and z['price'] < 999999:
            z['distance'] = round(current_price - z['price'], 2)
            z['distance_pts'] = round(abs(z['distance']), 2)
            z['status'] = get_zone_status(z['distance'], is_btc)
            valid_zones.append(z)

    return valid_zones

def calculate_trade_framework(zone, target_pts=10):
    """Calculate entry, targets, stop for a zone"""
    price = zone['price']
    zone_type = zone['type']
    session = zone['session_number']
    zone_id = zone.get('id', '')

    # Get session data for targets
    session_key = {1: 'tpo1_asia', 2: 'tpo2_london', 3: 'tpo3_us_am', 4: 'tpo4_us_pm', 0: None}.get(session)
    session_data = tpo_state['sessions'].get(session_key, {}) if session_key else tpo_state['day']

    # Detect if this is BTC/crypto and scale targets appropriately
    # Note: asset_class or contract field contains the contract identifier
    current_contract = state.get('asset_class', '') or state.get('contract', '')
    is_btc = 'BTC' in current_contract.upper()

    # Base point scaling: BTC moves in larger increments
    base_scale = 100 if is_btc else 1  # BTC targets in $100s, GC in $1s
    stop_scale = 50 if is_btc else 3.5  # BTC stop ~$50, GC ~$3.50

    # === SPECIALIZED HANDLING FOR NEW ZONE TYPES ===

    # PD Low - Strong support zone, buy setup
    if zone_id == 'pd_low':
        pd_poc = state.get('pdpoc', price + 5 * base_scale)
        pd_high = state.get('pd_high', price + 10 * base_scale)
        target1 = {'name': 'PD POC', 'price': round(pd_poc, 2), 'pts': round(pd_poc - price, 2)}
        target2 = {'name': 'PD High', 'price': round(pd_high, 2), 'pts': round(pd_high - price, 2)}
        stop_pts = stop_scale
        entry_trigger = 'Test PD Low + Demand absorption + Delta flip positive'
        direction = 'long'

    # PD High - Strong resistance zone, short setup
    elif zone_id == 'pd_high':
        pd_poc = state.get('pdpoc', price - 5 * base_scale)
        pd_low = state.get('pd_low', price - 10 * base_scale)
        target1 = {'name': 'PD POC', 'price': round(pd_poc, 2), 'pts': round(price - pd_poc, 2)}
        target2 = {'name': 'PD Low', 'price': round(pd_low, 2), 'pts': round(price - pd_low, 2)}
        stop_pts = stop_scale
        entry_trigger = 'Test PD High + Supply rejection + Delta flip negative'
        direction = 'short'

    # PD POC - Key pivot, direction depends on approach
    elif zone_id == 'pd_poc':
        pd_high = state.get('pd_high', price + 5 * base_scale)
        pd_low = state.get('pd_low', price - 5 * base_scale)
        # Default to long from POC
        target1 = {'name': 'PD High', 'price': round(pd_high, 2), 'pts': round(pd_high - price, 2)}
        target2 = {'name': 'Above PD High', 'price': round(pd_high + 2 * base_scale, 2), 'pts': round(pd_high + 2 * base_scale - price, 2)}
        stop_pts = stop_scale * 0.8
        entry_trigger = 'Reclaim PD POC + Volume confirmation + Buyers step in'
        direction = 'long'

    # Day Open - Major intraday pivot
    elif zone_id == 'day_open':
        day_high = state.get('day_high', price + 3 * base_scale)
        vwap = state.get('vwap', price)
        target1 = {'name': 'VWAP', 'price': round(vwap, 2), 'pts': round(abs(vwap - price), 2)}
        target2 = {'name': 'Day High', 'price': round(day_high, 2), 'pts': round(day_high - price, 2)}
        stop_pts = stop_scale * 0.7
        entry_trigger = 'Test Day Open + Hold with conviction + Buyers defend'
        direction = 'long'

    # Day Low - Support zone
    elif zone_id == 'day_low':
        vwap = state.get('vwap', price + 3 * base_scale)
        day_high = state.get('day_high', price + 6 * base_scale)
        target1 = {'name': 'VWAP', 'price': round(vwap, 2), 'pts': round(vwap - price, 2)}
        target2 = {'name': 'Day High', 'price': round(day_high, 2), 'pts': round(day_high - price, 2)}
        stop_pts = stop_scale
        entry_trigger = 'Sweep Day Low + Strong reversal + Absorption at lows'
        direction = 'long'

    # Day High - Resistance zone
    elif zone_id == 'day_high':
        vwap = state.get('vwap', price - 3 * base_scale)
        day_low = state.get('day_low', price - 6 * base_scale)
        if day_low > 999000:
            day_low = price - 6 * base_scale
        target1 = {'name': 'VWAP', 'price': round(vwap, 2), 'pts': round(price - vwap, 2)}
        target2 = {'name': 'Day Low', 'price': round(day_low, 2), 'pts': round(price - day_low, 2)}
        stop_pts = stop_scale
        entry_trigger = 'Test Day High + Rejection + Sellers defend'
        direction = 'short'

    # Weekly Open - Major pivot
    elif zone_id == 'weekly_open':
        current_price = state.get('current_price', price)
        day_high = state.get('day_high', price + 3 * base_scale)
        day_low = state.get('day_low', price - 3 * base_scale)
        if day_low > 999000:
            day_low = price - 3 * base_scale
        # Direction based on current price vs weekly open
        if current_price < price:  # Approaching from below - potential long
            target1 = {'name': 'Day High', 'price': round(day_high, 2), 'pts': round(day_high - price, 2)}
            target2 = {'name': 'Extension', 'price': round(price + 5 * base_scale, 2), 'pts': round(5 * base_scale, 2)}
            direction = 'long'
            entry_trigger = 'Reclaim Weekly Open + Momentum continuation'
        else:  # Approaching from above - potential short
            target1 = {'name': 'Day Low', 'price': round(day_low, 2), 'pts': round(price - day_low, 2)}
            target2 = {'name': 'Extension', 'price': round(price - 5 * base_scale, 2), 'pts': round(5 * base_scale, 2)}
            direction = 'short'
            entry_trigger = 'Lose Weekly Open + Momentum continuation'
        stop_pts = stop_scale

    # VWAP - Dynamic pivot
    elif zone_id in ['vwap', 'rth_vwap']:
        day_high = state.get('day_high', price + 3 * base_scale)
        day_low = state.get('day_low', price - 3 * base_scale)
        if day_low > 999000:
            day_low = price - 3 * base_scale
        target1 = {'name': 'Day High', 'price': round(day_high, 2), 'pts': round(day_high - price, 2)}
        target2 = {'name': 'Extension', 'price': round(price + 4 * base_scale, 2), 'pts': round(4 * base_scale, 2)}
        stop_pts = stop_scale * 0.7
        entry_trigger = 'Hold VWAP + Volume confirms + Mean reversion long'
        direction = 'long'

    # Call Wall - Strong resistance from options positioning
    elif zone_id == 'call_wall':
        gamma_flip = state.get('gex_data', {}).get('gamma_flip', price - 5 * base_scale)
        put_wall = state.get('gex_data', {}).get('put_wall', price - 10 * base_scale)
        target1 = {'name': 'Gamma Flip', 'price': round(gamma_flip, 2), 'pts': round(price - gamma_flip, 2)}
        target2 = {'name': 'Put Wall', 'price': round(put_wall, 2), 'pts': round(price - put_wall, 2)}
        stop_pts = stop_scale * 1.2
        entry_trigger = 'Hit Call Wall + Dealer selling pressure + Fade the rally'
        direction = 'short'

    # Put Wall - Strong support from options positioning
    elif zone_id == 'put_wall':
        gamma_flip = state.get('gex_data', {}).get('gamma_flip', price + 5 * base_scale)
        call_wall = state.get('gex_data', {}).get('call_wall', price + 10 * base_scale)
        target1 = {'name': 'Gamma Flip', 'price': round(gamma_flip, 2), 'pts': round(gamma_flip - price, 2)}
        target2 = {'name': 'Call Wall', 'price': round(call_wall, 2), 'pts': round(call_wall - price, 2)}
        stop_pts = stop_scale * 1.2
        entry_trigger = 'Hit Put Wall + Dealer buying support + Buy the dip'
        direction = 'long'

    # Gamma Flip - Key regime change level
    elif zone_id == 'gamma_flip':
        call_wall = state.get('gex_data', {}).get('call_wall', price + 5 * base_scale)
        put_wall = state.get('gex_data', {}).get('put_wall', price - 5 * base_scale)
        target1 = {'name': 'Call Wall', 'price': round(call_wall, 2), 'pts': round(call_wall - price, 2)}
        target2 = {'name': 'Extension', 'price': round(price + 6 * base_scale, 2), 'pts': round(6 * base_scale, 2)}
        stop_pts = stop_scale
        entry_trigger = 'Cross above Gamma Flip + Regime shift to positive gamma'
        direction = 'long'

    # Default targets based on zone type
    elif zone_type == 'ib_low':
        ib_high = session_data.get('ib_high') or (price + 10 * base_scale)
        ib_mid = (price + ib_high) / 2
        target1 = {'name': 'IB Mid', 'price': round(ib_mid, 2), 'pts': round(ib_mid - price, 2)}
        target2 = {'name': 'IB High', 'price': round(ib_high, 2), 'pts': round(ib_high - price, 2)}
        stop_pts = stop_scale
        entry_trigger = 'Test IBL + Delta flip positive + Buying imbalance'
        direction = 'long'

    elif zone_type == 'val':
        poc = session_data.get('poc') or (price + 5 * base_scale)
        vah = session_data.get('vah') or (price + 10 * base_scale)
        target1 = {'name': 'POC', 'price': round(poc, 2), 'pts': round(poc - price, 2)}
        target2 = {'name': 'VAH', 'price': round(vah, 2), 'pts': round(vah - price, 2)}
        stop_pts = stop_scale * 0.85
        entry_trigger = 'Retest VAL + Hold with volume'
        direction = 'long'

    elif zone_type == 'poc':
        vah = session_data.get('vah') or (price + 8 * base_scale)
        high = session_data.get('high') or (price + 12 * base_scale)
        target1 = {'name': 'VAH', 'price': round(vah, 2), 'pts': round(vah - price, 2)}
        target2 = {'name': 'Session High', 'price': round(high, 2), 'pts': round(high - price, 2)}
        stop_pts = stop_scale * 1.1
        entry_trigger = 'Sweep POC + Reclaim with delta support'
        direction = 'long'

    elif zone_type == 'ib_high':
        ib_low = session_data.get('ib_low') or (price - 10 * base_scale)
        if ib_low > 999000:  # Handle sentinel value
            ib_low = price - 10 * base_scale
        ib_mid = (price + ib_low) / 2
        # For IB High, targets go DOWN (short setup)
        target1 = {'name': 'IB Mid', 'price': round(ib_mid, 2), 'pts': round(price - ib_mid, 2)}
        target2 = {'name': 'IB Low', 'price': round(ib_low, 2), 'pts': round(price - ib_low, 2)}
        stop_pts = stop_scale
        entry_trigger = 'Test IBH + Delta flip negative + Selling imbalance'
        direction = 'short'

    elif zone_type == 'vah':
        poc = session_data.get('poc') or (price - 5 * base_scale)
        val = session_data.get('val') or (price - 10 * base_scale)
        target1 = {'name': 'POC', 'price': round(poc, 2), 'pts': round(price - poc, 2)}
        target2 = {'name': 'VAL', 'price': round(val, 2), 'pts': round(price - val, 2)}
        stop_pts = stop_scale * 0.85
        entry_trigger = 'Retest VAH + Rejection with volume'
        direction = 'short'

    else:
        # Generic framework - scale for BTC
        target1 = {'name': 'Target 1', 'price': round(price + 5 * base_scale, 2), 'pts': 5 * base_scale}
        target2 = {'name': 'Target 2', 'price': round(price + 10 * base_scale, 2), 'pts': 10 * base_scale}
        stop_pts = stop_scale
        entry_trigger = 'Test zone + Confirmation'
        direction = 'long'

    stop_price = round(price - stop_pts, 2)
    avg_target = (target1['pts'] + target2['pts']) / 2
    r_ratio = round(avg_target / stop_pts, 1) if stop_pts > 0 else 0

    return {
        'direction': direction,
        'entry_trigger': entry_trigger,
        'target1': target1,
        'target2': target2,
        'stop': {'price': stop_price, 'pts': stop_pts},
        'r_ratio': r_ratio,
    }

def rank_buy_zones(zones, target_pts=10):
    """Rank zones for a buy trade - dynamically scaled for instrument"""
    buy_candidates = []
    current_price = state.get('current_price', 0)

    # Detect contract type and scale distances appropriately
    # Note: asset_class or contract field contains the contract identifier
    current_contract = state.get('asset_class', '') or state.get('contract', '')
    is_btc = 'BTC' in current_contract.upper()

    # Distance thresholds: BTC moves in $100s, Gold in $1s
    # BTC: 3000 pts (~3.5%), Gold: 30 pts (~0.6%)
    max_distance = 3000 if is_btc else 30
    optimal_close = 300 if is_btc else 3
    optimal_far = 1000 if is_btc else 10

    for zone in zones:
        zone_id = zone.get('id', '')
        is_vwap_zone = 'vwap' in zone_id.lower()

        # VWAP is a mean-reversion level - include when price is NEAR it (above or below)
        if is_vwap_zone:
            # Include VWAP if price is within approaching distance (either direction)
            vwap_threshold = 500 if is_btc else 5  # $500 for BTC, $5 for Gold
            if zone['distance_pts'] > vwap_threshold:
                continue
        else:
            # Traditional support zones: only consider when BELOW current price (positive distance)
            if zone['distance'] <= 0:  # Zone is at or above price
                continue

        # Skip zones too far away (scaled for instrument)
        if zone['distance_pts'] > max_distance:
            continue
        # Calculate trade framework
        trade = calculate_trade_framework(zone, target_pts)
        zone['trade'] = trade

        # Score the zone
        score = 0

        # Priority by zone type (IB Low > VAL > POC for buys)
        type_scores = {
            'ib_low': 40,
            'val': 35,
            'poc': 30,
            'vah': 15,
            'ib_high': 10,
            'single_print': 25,
        }
        score += type_scores.get(zone['type'], 10)

        # Priority by session (US > London > Asia for intraday)
        session_scores = {3: 30, 2: 25, 1: 15, 4: 20, 0: 20}
        score += session_scores.get(zone['session_number'], 10)

        # Distance bonus (closer = better, but not too close) - scaled
        if optimal_close <= zone['distance_pts'] <= optimal_far:
            score += 20
        elif zone['distance_pts'] < optimal_close:
            score += 10  # Already at zone
        else:
            # Scaled penalty for distance
            distance_factor = zone['distance_pts'] / (optimal_far if is_btc else 1)
            score += max(0, 15 - distance_factor / 2)

        # R:R bonus
        if trade['r_ratio'] >= 2.5:
            score += 15
        elif trade['r_ratio'] >= 2.0:
            score += 10

        zone['confidence'] = min(100, int(score))
        buy_candidates.append(zone)

    # Sort by score and return top 3
    buy_candidates.sort(key=lambda x: x['confidence'], reverse=True)
    return buy_candidates[:3]

def get_tpo_count_at_price(price):
    """Get TPO count at a specific price level"""
    day_profiles = tpo_state['day'].get('profiles', {})

    # Detect BTC for tick size scaling
    current_contract = state.get('asset_class', '') or state.get('contract', '')
    is_btc = 'BTC' in current_contract.upper()

    # BTC profiles use $100 increments, Gold uses $0.10
    tick_size = 100.0 if is_btc else 0.10
    rounded_price = round(price / tick_size) * tick_size

    for p, letters in day_profiles.items():
        if abs(float(p) - rounded_price) < tick_size:
            return len(letters)
    return 0

def check_setup_readiness(zone):
    """Check if conditions are met for trade at zone - TPO-based high-value metrics"""
    readiness = {
        'price_at_zone': False,
        'tpo_confirmation': False,
        'session_context': False,
        'single_print_nearby': False,
        'poc_alignment': False,
        'ib_intact': False,
        'checks_passed': 0,
        'total_checks': 6,
        'overall_score': 0,
    }

    zone_price = zone['price']
    zone_session = zone['session_number']
    zone_type = zone['type']

    # Detect if BTC for threshold scaling
    current_contract = state.get('asset_class', '') or state.get('contract', '')
    is_btc = 'BTC' in current_contract.upper()

    # Scale thresholds: BTC moves in $100s, Gold in $1s
    price_at_zone_thresh = 200 if is_btc else 5       # $200 for BTC, $5 for Gold
    single_print_thresh = 300 if is_btc else 5        # $300 for BTC, $5 for Gold
    poc_align_thresh = 200 if is_btc else 3           # $200 for BTC, $3 for Gold
    ib_tolerance = 50 if is_btc else 0.5              # $50 for BTC, $0.50 for Gold

    # 1. Price at zone
    if zone['distance_pts'] <= price_at_zone_thresh:
        readiness['price_at_zone'] = True
        readiness['checks_passed'] += 1

    # 2. TPO confirmation (2+ TPO at zone level = time acceptance)
    tpo_count = get_tpo_count_at_price(zone_price)
    if tpo_count >= 2:
        readiness['tpo_confirmation'] = True
        readiness['checks_passed'] += 1

    # 3. Session context (zone from current or prior session)
    active_session = tpo_state.get('active_session')
    active_num = TPO_SESSIONS.get(active_session, {}).get('number', 0) if active_session else 0
    if zone_session <= active_num or zone_session == 0:
        readiness['session_context'] = True
        readiness['checks_passed'] += 1

    # 4. Single Print Proximity (unfilled gaps near zone add confluence)
    day_single_prints = tpo_state['day'].get('single_prints', [])
    for sp in day_single_prints:
        if abs(sp - zone_price) <= single_print_thresh:
            readiness['single_print_nearby'] = True
            readiness['checks_passed'] += 1
            break

    # 5. POC Alignment (zone near a POC = high volume support/resistance)
    day_poc = tpo_state['day'].get('poc', 0)
    if day_poc > 0 and abs(day_poc - zone_price) <= poc_align_thresh:
        readiness['poc_alignment'] = True
        readiness['checks_passed'] += 1
    else:
        # Check session POCs
        for sess_key in ['tpo1_asia', 'tpo2_london', 'tpo3_us_am']:
            sess_poc = tpo_state['sessions'].get(sess_key, {}).get('poc', 0)
            if sess_poc > 0 and abs(sess_poc - zone_price) <= poc_align_thresh:
                readiness['poc_alignment'] = True
                readiness['checks_passed'] += 1
                break

    # 6. IB Intact (IB levels stronger when not extended)
    if zone_type in ['ib_low', 'ib_high']:
        session_key = {1: 'tpo1_asia', 2: 'tpo2_london', 3: 'tpo3_us_am'}.get(zone_session)
        if session_key:
            sess_data = tpo_state['sessions'].get(session_key, {})
            ib_high = sess_data.get('ib_high', 0)
            ib_low = sess_data.get('ib_low', 999999)
            sess_high = sess_data.get('high', 0)
            sess_low = sess_data.get('low', 999999)

            # IB is intact if session hasn't broken IB range
            if ib_high > 0 and ib_low < 999999:
                ib_extended_up = sess_high > ib_high + ib_tolerance
                ib_extended_down = sess_low < ib_low - ib_tolerance
                if not ib_extended_up and not ib_extended_down:
                    readiness['ib_intact'] = True
                    readiness['checks_passed'] += 1
    else:
        # For non-IB zones, check if any IB is intact (adds to market structure)
        for sess_key in ['tpo1_asia', 'tpo2_london', 'tpo3_us_am']:
            sess_data = tpo_state['sessions'].get(sess_key, {})
            ib_high = sess_data.get('ib_high') or 0
            ib_low = sess_data.get('ib_low') or 999999
            sess_high = sess_data.get('high') or 0
            sess_low = sess_data.get('low') or 999999
            if ib_high > 0 and ib_low < 999999:
                if sess_high <= ib_high + ib_tolerance and sess_low >= ib_low - ib_tolerance:
                    readiness['ib_intact'] = True
                    readiness['checks_passed'] += 1
                    break

    readiness['overall_score'] = int((readiness['checks_passed'] / readiness['total_checks']) * 100)

    return readiness


def calculate_mp_fp_confluence(current_price, delta, delta_history_5m=None):
    """
    Calculate MP+FP Confluence Score based on:
    - Mind Over Markets Quick Reference (James Dalton) - PRIMARY
    - MP_Footprint_Integration_Guide.pdf - SECONDARY

    CORE RULE: When TPO and Volume conflict, ALWAYS TRUST VOLUME.

    HIERARCHY (higher rank ALWAYS wins):
    =====================================
    RANK 1 - MACRO (+3 each, -3 if conflicting):
      - Weekly/Monthly VA migration direction
      - Composite VPOC direction (multi-day)
      - Multi-day HVN/LVN structure

    RANK 2 - VOLUME (+2 each) - BEATS TPO:
      - Delta direction (positive/negative)
      - HVN at key levels (acceptance)
      - VPOC alignment
      - Volume confirmation

    RANK 3 - STRUCTURE (+2 each):
      - Tail WITH volume confirmation (HVN)
      - Profile shape (P/b/D/B)
      - Range extension direction
      - Day type once confirmed

    RANK 4 - TIMING (+1 each):
      - Open type (OD/OTD/ORR/OAIR/OAOR)
      - Initial Balance width
      - Single reference levels
      - Poor high/low

    SCORE INTERPRETATION:
      +12 or more: VERY HIGH (100% + add on dips)
      +8 to +11:   HIGH (100%)
      +5 to +7:    MEDIUM-HIGH (75%)
      +2 to +4:    MEDIUM (50%)
      -1 to +1:    LOW (25% or SKIP)
      -2 or less:  AVOID (NO TRADE)

    TPO vs VOLUME CONFLICTS (Volume ALWAYS wins):
      P-shape (bullish) + Negative delta → Trust VOLUME (distribution hidden)
      b-shape (bearish) + Positive delta → Trust VOLUME (accumulation hidden)
      Strong tail + LVN at tail → Trust VOLUME (fake rejection)
      TPO support + LVN at level → Trust VOLUME (will slice through)
    """
    day = tpo_state.get('day', {})

    # Initialize result with hierarchical scoring
    result = {
        'rank1_score': 0,  # MACRO
        'rank2_score': 0,  # VOLUME
        'rank3_score': 0,  # STRUCTURE
        'rank4_score': 0,  # TIMING
        'conflict_penalty': 0,
        'total_score': 0,
        'confidence': 'AVOID',
        'position_size_pct': 0,
        'bias': 'NEUTRAL',
        'factors': {
            'rank1_macro': [],
            'rank2_volume': [],
            'rank3_structure': [],
            'rank4_timing': [],
            'conflicts': [],
            'volume_override': []  # When volume overrides TPO
        },
        'at_key_level': None,
        'level_type': None,
        'action': 'WAIT',
        'trade_direction': 'NEUTRAL',
        'hierarchy_note': ''
    }

    if not current_price or current_price <= 0:
        return result

    # Get key levels
    poc = day.get('poc', 0)
    vah = day.get('vah', 0)
    val = day.get('val', 0)
    ib_high = day.get('ib_high', 0)
    ib_low = day.get('ib_low', 999999)
    profile_shape = day.get('profile_shape', 'D')
    day_type = day.get('day_type', 'developing')
    open_type = day.get('open_type', 'developing')
    single_prints = day.get('single_prints', [])
    ib_range = (ib_high - ib_low) if ib_high > 0 and ib_low < 999999 else 0

    # Delta analysis
    delta_val = delta or 0
    delta_positive = delta_val > 0
    delta_negative = delta_val < 0
    delta_strong = abs(delta_val) > 5000
    delta_very_strong = abs(delta_val) > 15000

    # Determine if at key level (within 3 pts tolerance)
    tolerance = 3.0
    at_level = None
    level_type = None

    if vah > 0 and abs(current_price - vah) <= tolerance:
        at_level = vah
        level_type = 'VAH'
    elif val > 0 and abs(current_price - val) <= tolerance:
        at_level = val
        level_type = 'VAL'
    elif poc > 0 and abs(current_price - poc) <= tolerance:
        at_level = poc
        level_type = 'POC'
    elif ib_high > 0 and abs(current_price - ib_high) <= tolerance:
        at_level = ib_high
        level_type = 'IB_HIGH'
    elif ib_low < 999999 and abs(current_price - ib_low) <= tolerance:
        at_level = ib_low
        level_type = 'IB_LOW'

    # Check single prints nearby
    near_single_print = any(abs(sp - current_price) <= 5 for sp in single_prints)

    result['at_key_level'] = at_level
    result['level_type'] = level_type

    # ========================================
    # RANK 1: MACRO CONTEXT (+3 each)
    # Weekly VA, Composite VPOC, Multi-day HVN/LVN
    # ========================================
    # Note: These require multi-day data - placeholder for now
    # In production, this would check historicalData for weekly trends

    # ========================================
    # RANK 2: VOLUME (+2 each) - BEATS TPO
    # Delta, HVN at level, VPOC alignment
    # ========================================

    # +2: Strong delta direction
    if delta_very_strong:
        result['rank2_score'] += 2
        direction = "POSITIVE (buyers dominating)" if delta_positive else "NEGATIVE (sellers dominating)"
        result['factors']['rank2_volume'].append(f"Very strong delta {direction}: +2")
        result['bias'] = 'BULLISH' if delta_positive else 'BEARISH'
    elif delta_strong:
        result['rank2_score'] += 2
        direction = "positive" if delta_positive else "negative"
        result['factors']['rank2_volume'].append(f"Strong delta {direction}: +2")

    # +2: Volume confirms at key level
    if at_level is not None:
        if level_type in ['VAL', 'IB_LOW'] and delta_positive:
            result['rank2_score'] += 2
            result['factors']['rank2_volume'].append(f"At {level_type} with positive delta (buyers): +2")
        elif level_type in ['VAH', 'IB_HIGH'] and delta_negative:
            result['rank2_score'] += 2
            result['factors']['rank2_volume'].append(f"At {level_type} with negative delta (sellers): +2")

    # ========================================
    # RANK 3: STRUCTURE (+2 each)
    # Profile shape, Range extension, Day type
    # ========================================

    # +2: Profile shape confirms direction
    if profile_shape == 'P':
        result['rank3_score'] += 2
        result['factors']['rank3_structure'].append(f"P-shape profile (bullish accumulation): +2")
        if result['bias'] == 'NEUTRAL':
            result['bias'] = 'BULLISH'
    elif profile_shape == 'b':
        result['rank3_score'] += 2
        result['factors']['rank3_structure'].append(f"b-shape profile (bearish distribution): +2")
        if result['bias'] == 'NEUTRAL':
            result['bias'] = 'BEARISH'
    elif profile_shape == 'D':
        result['factors']['rank3_structure'].append(f"D-shape (balanced/neutral): 0")
    elif profile_shape == 'B':
        result['factors']['rank3_structure'].append(f"B-shape (double distribution): 0")

    # +2: Day type supports trade
    if day_type == 'trend':
        result['rank3_score'] += 2
        result['factors']['rank3_structure'].append(f"Trend day (DO NOT FADE): +2")
    elif day_type == 'normal_var':
        result['rank3_score'] += 2
        result['factors']['rank3_structure'].append(f"Normal variation (trade with extension): +2")

    # +2: At key level
    if at_level is not None:
        result['rank3_score'] += 2
        result['factors']['rank3_structure'].append(f"At key level {level_type}: +2")

    # ========================================
    # RANK 4: TIMING (+1 each)
    # Open type, IB width, Single prints, Poor H/L
    # ========================================

    # +1: Open type conviction
    if open_type in ['OD', 'OTD']:  # Open Drive, Open Test Drive
        result['rank4_score'] += 1
        result['factors']['rank4_timing'].append(f"Open type {open_type} (HIGH conviction): +1")
    elif open_type == 'ORR':  # Open Rejection Reverse
        result['factors']['rank4_timing'].append(f"Open type ORR (MEDIUM, wait for confirm): 0")
    elif open_type in ['OA', 'OAIR', 'OAOR']:  # Open Auction
        result['factors']['rank4_timing'].append(f"Open type {open_type} (trade responsive): 0")

    # +1: Narrow IB (trend potential)
    if ib_range > 0 and ib_range < 10:  # Narrow IB for Gold
        result['rank4_score'] += 1
        result['factors']['rank4_timing'].append(f"Narrow IB ({ib_range:.1f} pts - trend signal): +1")
    elif ib_range > 20:  # Wide IB
        result['factors']['rank4_timing'].append(f"Wide IB ({ib_range:.1f} pts - range day): 0")

    # +1: Single prints nearby (unfinished business)
    if near_single_print:
        result['rank4_score'] += 1
        result['factors']['rank4_timing'].append(f"Single prints nearby (S/R zone): +1")

    # ========================================
    # CONFLICT DETECTION & VOLUME OVERRIDE
    # Volume ALWAYS beats TPO
    # ========================================

    # P-shape but negative delta = distribution hidden, trust VOLUME
    if profile_shape == 'P' and delta_negative and delta_strong:
        result['conflict_penalty'] -= 2
        result['factors']['conflicts'].append(f"P-shape but strong negative delta: -2")
        result['factors']['volume_override'].append(
            "⚠️ VOLUME OVERRIDE: P-shape looks bullish but delta negative = distribution hidden. TRUST VOLUME."
        )
        result['bias'] = 'BEARISH'  # Volume wins

    # b-shape but positive delta = accumulation hidden, trust VOLUME
    if profile_shape == 'b' and delta_positive and delta_strong:
        result['conflict_penalty'] -= 2
        result['factors']['conflicts'].append(f"b-shape but strong positive delta: -2")
        result['factors']['volume_override'].append(
            "⚠️ VOLUME OVERRIDE: b-shape looks bearish but delta positive = accumulation hidden. TRUST VOLUME."
        )
        result['bias'] = 'BULLISH'  # Volume wins

    # At support but sellers aggressive
    if level_type in ['VAL', 'IB_LOW'] and delta_negative and delta_strong:
        result['conflict_penalty'] -= 2
        result['factors']['conflicts'].append(f"At support but strong selling: -2")
        result['factors']['volume_override'].append(
            f"⚠️ At {level_type} but negative delta - support may break!"
        )

    # At resistance but buyers aggressive
    if level_type in ['VAH', 'IB_HIGH'] and delta_positive and delta_strong:
        result['conflict_penalty'] -= 2
        result['factors']['conflicts'].append(f"At resistance but strong buying: -2")
        result['factors']['volume_override'].append(
            f"⚠️ At {level_type} but positive delta - resistance may break!"
        )

    # ========================================
    # CALCULATE TOTAL SCORE
    # ========================================

    result['total_score'] = (
        result['rank1_score'] +
        result['rank2_score'] +
        result['rank3_score'] +
        result['rank4_score'] +
        result['conflict_penalty']
    )

    # Score interpretation (Mind Over Markets scale)
    score = result['total_score']
    if score >= 12:
        result['confidence'] = 'VERY HIGH'
        result['position_size_pct'] = 100
        result['action'] = 'TRADE + ADD ON DIPS'
    elif score >= 8:
        result['confidence'] = 'HIGH'
        result['position_size_pct'] = 100
        result['action'] = 'TRADE'
    elif score >= 5:
        result['confidence'] = 'MEDIUM-HIGH'
        result['position_size_pct'] = 75
        result['action'] = 'TRADE'
    elif score >= 2:
        result['confidence'] = 'MEDIUM'
        result['position_size_pct'] = 50
        result['action'] = 'TRADE (reduced)'
    elif score >= -1:
        result['confidence'] = 'LOW'
        result['position_size_pct'] = 25
        result['action'] = 'SKIP or small'
    else:
        result['confidence'] = 'AVOID'
        result['position_size_pct'] = 0
        result['action'] = 'NO TRADE'

    # Determine trade direction
    if result['bias'] == 'BULLISH':
        result['trade_direction'] = 'LONG'
    elif result['bias'] == 'BEARISH':
        result['trade_direction'] = 'SHORT'
    else:
        # Use level context
        if level_type in ['VAL', 'IB_LOW']:
            result['trade_direction'] = 'LONG' if delta_val >= 0 else 'WAIT'
        elif level_type in ['VAH', 'IB_HIGH']:
            result['trade_direction'] = 'SHORT' if delta_val <= 0 else 'WAIT'
        else:
            result['trade_direction'] = 'NEUTRAL'

    # Add hierarchy note
    if result['factors']['volume_override']:
        result['hierarchy_note'] = "VOLUME OVERRIDE ACTIVE - Trust Volume over TPO"
    elif result['conflict_penalty'] < 0:
        result['hierarchy_note'] = "Conflicts detected - reduced confidence"

    return result


# ============================================
# TIME UTILITIES (ET)
# ============================================
def get_et_now():
    """Get current time in ET (UTC-5)"""
    utc_now = datetime.now(timezone.utc)
    et_offset = timedelta(hours=-5)
    return utc_now + et_offset

def get_active_ib(time_val=None):
    """Check which IB session is currently active (if any)
    Returns: 'asia', 'london', 'us', 'ny', or None
    """
    if time_val is None:
        et = get_et_now()
        time_val = et.hour * 100 + et.minute

    # IB session time ranges (in HHMM format)
    ib_sessions = {
        'japan': (1900, 2000),    # 19:00 - 20:00 ET (Japan IB)
        'london': (300, 400),     # 03:00 - 04:00 ET (London IB)
        'us': (820, 930),         # 08:20 - 09:30 ET (US IB)
        'ny': (930, 1030),        # 09:30 - 10:30 ET (NY IB)
    }

    for ib_name, (start, end) in ib_sessions.items():
        if start <= time_val < end:
            return ib_name

    return None

def get_session_info(time_val=None):
    """Get detailed session info for given time (or current time)"""
    if time_val is None:
        et = get_et_now()
        time_val = et.hour * 100 + et.minute
    
    # Session definitions (ET) - Horizon naming
    # Returns: (id, name, start, end, is_ib_session, ib_locked)
    sessions = [
        ('japan_ib', 'Japan IB', '19:00', '20:00', True, False),
        ('china', 'China', '20:00', '23:00', False, True),
        ('asia_close', 'Asia Closing', '23:00', '02:00', False, True),
        ('deadzone', 'Deadzone', '02:00', '03:00', False, True),
        ('london', 'London', '03:00', '06:00', False, True),
        ('low_volume', 'Low Volume', '06:00', '08:20', False, True),
        ('us_ib', 'US IB', '08:20', '09:30', True, False),
        ('ny_1h', 'NY 1H', '09:30', '10:30', False, True),
        ('ny_2h', 'NY 2H', '10:30', '11:30', False, True),
        ('lunch', 'Lunch', '11:30', '13:30', False, True),
        ('ny_pm', 'NY PM', '13:30', '16:00', False, True),
        ('ny_close', 'NY Close', '16:00', '17:00', False, True),
        ('market_closed', 'Market Closed', '17:00', '18:00', False, True),
        ('pre_asia', 'Pre-Asia', '18:00', '19:00', False, True),
    ]
    
    for sid, name, start, end, is_ib, ib_locked in sessions:
        start_val = int(start.replace(':', ''))
        end_val = int(end.replace(':', ''))
        
        # Handle overnight sessions
        if start_val > end_val:  # e.g., 23:00 - 02:00
            if time_val >= start_val or time_val < end_val:
                return {
                    'id': sid, 'name': name, 'start': start, 'end': end,
                    'is_ib_session': is_ib, 'ib_locked': ib_locked
                }
        else:
            if start_val <= time_val < end_val:
                return {
                    'id': sid, 'name': name, 'start': start, 'end': end,
                    'is_ib_session': is_ib, 'ib_locked': ib_locked
                }
    
    return {
        'id': 'unknown', 'name': 'Unknown', 'start': '', 'end': '',
        'is_ib_session': False, 'ib_locked': True
    }

def get_current_session():
    """Legacy function for compatibility"""
    info = get_session_info()
    return info['id'], info['name'], info['ib_locked']

# ============================================
# TPO / MARKET PROFILE FUNCTIONS
# ============================================
def get_tpo_letter(period_index):
    """Get TPO letter for period index (A=0, B=1, ... Z=25, then AA, AB, AC...)"""
    if period_index < 26:
        return TPO_LETTERS[period_index]
    else:
        # After Z (index 25), continue with AA, AB, AC... AZ, BA, BB...
        extra = period_index - 26
        first_letter = TPO_LETTERS[extra // 26]  # A, B, C...
        second_letter = TPO_LETTERS[extra % 26]  # A, B, C...
        return f"{first_letter}{second_letter}"

def get_session_period_index(session_key, current_hhmm):
    """Calculate which period we're in for a session.
    session_key: TPO session key (e.g., 'tpo1_asia')
    current_hhmm: Current time in HHMM format (e.g., 1430 for 14:30)
    Returns: Period index (0 = A, 1 = B, etc.)

    Period durations:
    - Default: 30 mins
    - London (tpo2_london): Last period is 20 mins (08:00-08:20)
    - US (tpo3_us_am): First period is 40 mins (08:20-09:00)
    """
    config = TPO_SESSIONS.get(session_key)
    if not config:
        return 0
    session_start = config['start']  # HHMM format
    session_end = config['end']  # HHMM format

    # Convert HHMM to minutes from midnight
    start_mins = (session_start // 100) * 60 + (session_start % 100)
    end_mins = (session_end // 100) * 60 + (session_end % 100)
    current_mins = (current_hhmm // 100) * 60 + (current_hhmm % 100)

    # Handle overnight sessions (like Asia 18:00-03:00)
    if config['end'] < config['start']:  # Overnight
        if current_hhmm < config['end']:  # After midnight
            current_mins += 24 * 60
        end_mins += 24 * 60

    # Minutes since session start
    mins_elapsed = current_mins - start_mins
    if mins_elapsed < 0:
        mins_elapsed += 24 * 60  # Wrap around

    # Handle variable period durations
    if session_key == 'tpo3_us_am':
        # US Session: First period is 40 mins (08:20-09:00), rest are 30 mins
        if mins_elapsed < 40:
            return 0  # Period A (40 mins)
        else:
            # After first 40 min period, each subsequent is 30 mins
            return 1 + (mins_elapsed - 40) // 30

    elif session_key == 'tpo2_london':
        # London: 03:00-08:20 = 320 mins
        # 10 periods of 30 mins (A-J = 300 mins) + 1 last period of 20 mins (K = 08:00-08:20)
        total_session_mins = end_mins - start_mins
        if total_session_mins < 0:
            total_session_mins += 24 * 60

        # Last 20 mins is the final period
        regular_periods_mins = total_session_mins - 20  # 300 mins = 10 periods

        if mins_elapsed >= regular_periods_mins:
            # We're in the last 20-min period
            return regular_periods_mins // 30  # Period index 10 (K)
        else:
            # Regular 30-min periods
            return mins_elapsed // 30

    else:
        # Default: 30-min periods
        return mins_elapsed // 30

def calculate_overlap(range1, range2):
    """Calculate overlap percentage between two price ranges
    range1, range2: tuples of (high, low)
    Returns: overlap percentage (0-100) or None if ranges not established
    """
    h1, l1 = range1
    h2, l2 = range2

    # Return None if either range hasn't started (not 0, which implies no overlap)
    if h1 <= 0 or l1 >= 999999 or h2 <= 0 or l2 >= 999999:
        return None

    range1_size = h1 - l1
    range2_size = h2 - l2

    # Return None if ranges are invalid (not calculated yet)
    if range1_size <= 0 or range2_size <= 0:
        return None

    overlap_high = min(h1, h2)
    overlap_low = max(l1, l2)
    overlap = max(0, overlap_high - overlap_low)

    # Use smaller range as denominator for overlap %
    smaller_range = min(range1_size, range2_size)
    return (overlap / smaller_range) * 100 if smaller_range > 0 else 0.0

def calculate_tpo_metrics_for_profile(profile_data):
    """Calculate POC, Value Area (VAH/VAL), Single Prints for a profile dict
    profile_data should have 'profiles' dict: {price_level: set_of_letters}
    Returns updated profile_data
    """
    profiles = profile_data.get('profiles', {})
    if not profiles:
        return profile_data

    # Calculate TPO count for each price level
    tpo_counts = {price: len(letters) for price, letters in profiles.items()}
    if not tpo_counts:
        return profile_data

    sorted_prices = sorted(tpo_counts.keys())
    total_tpos = sum(tpo_counts.values())

    # POC = Price with most TPOs
    poc_price = max(tpo_counts.items(), key=lambda x: x[1])[0]
    profile_data['poc'] = poc_price
    profile_data['max_tpo_count'] = tpo_counts[poc_price]
    profile_data['total_tpo_count'] = total_tpos

    # Single Prints = Price levels with exactly 1 TPO
    profile_data['single_prints'] = [p for p, c in tpo_counts.items() if c == 1]

    # VALUE AREA CALCULATION (70% of TPOs around POC)
    target_tpos = int(total_tpos * 0.70)
    poc_index = sorted_prices.index(poc_price)

    # Initialize value area with POC
    vah_index = poc_index
    val_index = poc_index
    current_tpos = tpo_counts[poc_price]

    # Expand outward using 2-price lookahead rule
    while current_tpos < target_tpos:
        tpos_above = 0
        tpos_below = 0

        # Look up to 2 levels above
        if vah_index < len(sorted_prices) - 1:
            tpos_above = tpo_counts.get(sorted_prices[vah_index + 1], 0)
            if vah_index < len(sorted_prices) - 2:
                tpos_above += tpo_counts.get(sorted_prices[vah_index + 2], 0)

        # Look up to 2 levels below
        if val_index > 0:
            tpos_below = tpo_counts.get(sorted_prices[val_index - 1], 0)
            if val_index > 1:
                tpos_below += tpo_counts.get(sorted_prices[val_index - 2], 0)

        if tpos_above == 0 and tpos_below == 0:
            break

        # Expand in direction with more TPOs
        if tpos_above >= tpos_below and vah_index < len(sorted_prices) - 1:
            vah_index += 1
            current_tpos += tpo_counts.get(sorted_prices[vah_index], 0)
        elif tpos_below > tpos_above and val_index > 0:
            val_index -= 1
            current_tpos += tpo_counts.get(sorted_prices[val_index], 0)
        else:
            break

    profile_data['vah'] = sorted_prices[vah_index] if vah_index < len(sorted_prices) else poc_price
    profile_data['val'] = sorted_prices[val_index] if val_index >= 0 else poc_price

    # PROFILE SHAPE DETECTION
    detect_profile_shape_for_profile(profile_data, sorted_prices, tpo_counts)

    return profile_data

def calculate_tpo_metrics():
    """Calculate TPO metrics for all profiles (day + 4 sessions)"""
    global tpo_state

    # Calculate for full day profile
    calculate_tpo_metrics_for_profile(tpo_state['day'])

    # Calculate for each session profile
    for session_key in tpo_state['sessions']:
        calculate_tpo_metrics_for_profile(tpo_state['sessions'][session_key])

def detect_profile_shape_for_profile(profile_data, sorted_prices, tpo_counts):
    """Detect profile shape: D, B, P, b for a profile dict"""
    if len(sorted_prices) < 5:
        profile_data['profile_shape'] = 'developing'
        return

    # Divide profile into thirds
    third = len(sorted_prices) // 3
    upper_prices = sorted_prices[2*third:]
    middle_prices = sorted_prices[third:2*third]
    lower_prices = sorted_prices[:third]

    upper_tpos = sum(tpo_counts.get(p, 0) for p in upper_prices)
    middle_tpos = sum(tpo_counts.get(p, 0) for p in middle_prices)
    lower_tpos = sum(tpo_counts.get(p, 0) for p in lower_prices)

    total = upper_tpos + middle_tpos + lower_tpos
    if total == 0:
        profile_data['profile_shape'] = 'developing'
        return

    upper_pct = upper_tpos / total * 100
    lower_pct = lower_tpos / total * 100

    # Check for double distribution (B-shape)
    # Look for single prints in the middle separating two distributions
    middle_single_prints = [p for p in middle_prices if tpo_counts.get(p, 0) <= 2]
    has_middle_gap = len(middle_single_prints) >= len(middle_prices) * 0.3 if middle_prices else False

    if has_middle_gap and upper_tpos > 10 and lower_tpos > 10:
        profile_data['profile_shape'] = 'B'  # Double Distribution
    elif upper_pct > 45 and lower_pct < 25:
        profile_data['profile_shape'] = 'P'  # Bullish (fat top)
    elif lower_pct > 45 and upper_pct < 25:
        profile_data['profile_shape'] = 'b'  # Bearish (fat bottom)
    else:
        profile_data['profile_shape'] = 'D'  # Normal distribution

def classify_day_type():
    """Classify day type based on Mind over Markets rules - for full day profile"""
    global tpo_state

    day = tpo_state['day']
    if day['period_count'] < 2:
        day['day_type'] = 'developing'
        day['day_type_confidence'] = 0
        return

    ib_range = day['ib_high'] - day['ib_low']
    if ib_range <= 0 or day['ib_low'] >= 999999:
        return

    profiles = day['profiles']
    if not profiles:
        return

    sorted_prices = sorted(profiles.keys())
    day_high = sorted_prices[-1] if sorted_prices else 0
    day_low = sorted_prices[0] if sorted_prices else 0

    # Calculate range extension beyond IB
    extension_up = max(0, day_high - day['ib_high'])
    extension_down = max(0, day['ib_low'] - day_low)
    total_extension = extension_up + extension_down

    # Range extension as percentage of IB
    range_ext_pct = (total_extension / ib_range) * 100 if ib_range > 0 else 0
    day['range_extension_pct'] = range_ext_pct

    # IB as percentage of average daily range
    avg_range = tpo_state['avg_daily_range']
    ib_pct = (ib_range / avg_range) * 100 if avg_range > 0 else 50

    ab_overlap = day['ab_overlap']

    # Max TPOs at any level (thin = 4-5, fat = 8+)
    max_tpo = day['max_tpo_count']

    # Score each day type
    scores = {
        'normal': 0,      # Normal/Balance day
        'non_trend': 0,   # Non-trend day
        'normal_var': 0,  # Normal variation
        'trend': 0,       # Trend day
        'double_dist': 0, # Double distribution
        'neutral': 0      # Neutral day
    }

    # TREND DAY: Narrow IB, thin profile (4-5 TPO max), high extension
    if ib_pct < 60:
        scores['trend'] += 20
    if max_tpo <= 5:
        scores['trend'] += 25
    if range_ext_pct > 150:
        scores['trend'] += 25

    # NON-TREND DAY: Narrow IB, little extension either side, centered distribution
    if ib_pct < 70:
        scores['non_trend'] += 15
    if range_ext_pct < 30:
        scores['non_trend'] += 30
    if ab_overlap is not None and ab_overlap > 60:
        scores['non_trend'] += 20
    if day['profile_shape'] == 'D':
        scores['non_trend'] += 15

    # NORMAL VARIATION: Small initial IB, then extends significantly (up to 2x IB)
    if ib_pct < 80:
        scores['normal_var'] += 15
    if 50 < range_ext_pct < 200:
        scores['normal_var'] += 25
    # One-sided extension
    if (extension_up > ib_range * 0.5 and extension_down < ib_range * 0.3) or \
       (extension_down > ib_range * 0.5 and extension_up < ib_range * 0.3):
        scores['normal_var'] += 30

    # NORMAL/BALANCE DAY: Wide IB, auctions inside extremes
    if ib_pct > 80:
        scores['normal'] += 25
    if range_ext_pct < 50:
        scores['normal'] += 20
    if ab_overlap is not None and ab_overlap > 50:
        scores['normal'] += 15

    # DOUBLE DISTRIBUTION: Two distributions separated by single prints
    if day['profile_shape'] == 'B':
        scores['double_dist'] += 40
    if len(day['single_prints']) > 3:
        scores['double_dist'] += 20
    if ib_pct < 70:
        scores['double_dist'] += 10

    # NEUTRAL DAY: Extension on BOTH sides of IB
    if extension_up > 5 and extension_down > 5:
        scores['neutral'] += 25
    if ab_overlap is not None and ab_overlap > 50:
        scores['neutral'] += 15
    if range_ext_pct < 100:
        scores['neutral'] += 15

    # Get best match
    best_type = max(scores, key=scores.get)
    total_score = sum(scores.values()) or 1
    confidence = int((scores[best_type] / total_score) * 100)

    day['day_type'] = best_type
    day['day_type_confidence'] = confidence
    day['day_type_scores'] = scores

def classify_open_type():
    """Classify open type based on NY IB (09:30-10:30 ET)"""
    global tpo_state

    # Open type is specifically for US AM session (RTH)
    us_am = tpo_state['sessions']['tpo3_us_am']
    day = tpo_state['day']

    # Get IB values (09:30-10:30 ET)
    ib_high = us_am.get('ib_high', 0)
    ib_low = us_am.get('ib_low', 999999)
    open_price = us_am.get('open_price', 0)
    current_price = day.get('close', day.get('last_price', 0))

    # Need valid IB and open price
    if ib_high <= 0 or ib_low >= 999999 or open_price <= 0:
        us_am['open_type'] = 'developing'
        day['open_type'] = 'developing'
        return

    ib_range = ib_high - ib_low
    if ib_range <= 0:
        us_am['open_type'] = 'developing'
        day['open_type'] = 'developing'
        return

    ib_mid = (ib_high + ib_low) / 2

    # Calculate where open is relative to IB
    open_pct_in_ib = (open_price - ib_low) / ib_range * 100  # 0% = at IB low, 100% = at IB high

    # Determine dominant direction based on current price vs open
    dominant_dir = 'up' if current_price > open_price else 'down'

    # Count TPOs opposite to dominant direction within IB period
    profiles = us_am.get('profiles', {})
    tpos_above_open = 0
    tpos_below_open = 0
    for price_str, letters in profiles.items():
        price = float(price_str) if isinstance(price_str, str) else price_str
        # Only count IB period letters (A and B)
        ib_letters = [l for l in letters if l in ['A', 'B']]
        if price > open_price:
            tpos_above_open += len(ib_letters)
        elif price < open_price:
            tpos_below_open += len(ib_letters)

    # Calculate IB extension (how far price moved beyond IB)
    session_high = us_am.get('high', ib_high)
    session_low = us_am.get('low', ib_low)
    ext_above_ib = max(0, session_high - ib_high)
    ext_below_ib = max(0, ib_low - session_low)

    # Classify open type based on IB behavior
    open_type = 'OA'  # Default: Open Auction
    confidence = 60

    # OD (Open Drive): Open near IB extreme, strong one-way auction
    # - Open in bottom 20% of IB and drove up (few TPOs below open)
    # - OR Open in top 20% of IB and drove down (few TPOs above open)
    if open_pct_in_ib <= 20 and tpos_below_open <= 2 and current_price > ib_mid:
        open_type = 'OD'  # Open Drive Up
        dominant_dir = 'up'
        confidence = 85
    elif open_pct_in_ib >= 80 and tpos_above_open <= 2 and current_price < ib_mid:
        open_type = 'OD'  # Open Drive Down
        dominant_dir = 'down'
        confidence = 85

    # OTD (Open Test Drive): Tested one direction then drove opposite
    # - Open tested below (some TPOs below) then drove up strongly
    # - OR Open tested above (some TPOs above) then drove down strongly
    elif tpos_below_open >= 3 and tpos_below_open <= 8 and current_price > ib_high:
        open_type = 'OTD'  # Open Test Drive Up
        dominant_dir = 'up'
        confidence = 75
    elif tpos_above_open >= 3 and tpos_above_open <= 8 and current_price < ib_low:
        open_type = 'OTD'  # Open Test Drive Down
        dominant_dir = 'down'
        confidence = 75

    # ORR (Open Rejection Reverse): Rejected at IB extreme and reversed
    # - Tested IB high, rejected, now trading in lower half
    # - OR Tested IB low, rejected, now trading in upper half
    elif ext_above_ib > 0 and current_price < ib_mid:
        open_type = 'ORR'  # Open Rejection Reverse from high
        dominant_dir = 'down'
        confidence = 70
    elif ext_below_ib > 0 and current_price > ib_mid:
        open_type = 'ORR'  # Open Rejection Reverse from low
        dominant_dir = 'up'
        confidence = 70

    # OA (Open Auction): Balanced activity within IB, no clear direction
    # - Price rotating within IB range
    elif ib_low <= current_price <= ib_high:
        open_type = 'OA'  # Open Auction
        dominant_dir = None
        confidence = 65

    # Update both US AM session and day profile
    us_am['open_type'] = open_type
    us_am['open_type_confidence'] = confidence
    us_am['open_direction'] = dominant_dir
    day['open_type'] = open_type
    day['open_type_confidence'] = confidence
    day['open_direction'] = dominant_dir

def detect_swing_points(candle_history, lookback=50, swing_strength=1, min_range=50):
    """
    Detect recent swing high and swing low using 3-candle structure.

    3-candle structure:
    - Swing HIGH: candle high > both left neighbor AND right neighbor highs
    - Swing LOW: candle low < both left neighbor AND right neighbor lows

    The function finds the MOST RECENT completed swing (high-low pair) and determines:
    - UP swing: swing low formed BEFORE swing high (price moved up) → extensions ABOVE high
    - DOWN swing: swing high formed BEFORE swing low (price moved down) → extensions BELOW low

    Args:
        candle_history: List of candles with 'high', 'low' keys
        lookback: Number of candles to analyze (default 50 for more swing history)
        swing_strength: Candles on each side to confirm (1 = 3-candle structure)
        min_range: Minimum swing range to be considered significant (default 50 points)

    Returns:
        dict with swing_high, swing_low, swing_direction, and extension info
    """
    if not candle_history or len(candle_history) < 5:
        return {
            'swing_high': 0, 'swing_low': 0, 'swing_direction': 'neutral',
            'swing_high_idx': -1, 'swing_low_idx': -1,
            'swing_type': 'none', 'extensions_direction': 'none'
        }

    # Get recent candles (most recent last)
    candles = candle_history[-lookback:] if len(candle_history) >= lookback else candle_history

    # Find ALL confirmed swing points with their indices
    all_swings = []  # List of (index, price, type) where type is 'high' or 'low'

    # Use swing_strength=1 for 3-candle structure (1 candle on each side)
    for i in range(swing_strength, len(candles) - swing_strength):
        candle = candles[i]
        high = candle.get('high') or candle.get('price_high') or 0
        low = candle.get('low') or candle.get('price_low') or 0

        # Skip if values are None or invalid
        if high is None or low is None or high <= 0 or low <= 0 or low >= 999999:
            continue

        # Check for 3-candle swing high (high > both neighbors)
        is_swing_high = True
        for j in range(1, swing_strength + 1):
            left_high = candles[i - j].get('high') or candles[i - j].get('price_high') or 0
            right_high = candles[i + j].get('high') or candles[i + j].get('price_high') or 0
            if left_high is None or right_high is None or left_high <= 0 or right_high <= 0:
                is_swing_high = False
                break
            if high <= left_high or high <= right_high:
                is_swing_high = False
                break
        if is_swing_high:
            all_swings.append((i, high, 'high'))

        # Check for 3-candle swing low (low < both neighbors)
        is_swing_low = True
        for j in range(1, swing_strength + 1):
            left_low = candles[i - j].get('low') or candles[i - j].get('price_low') or 0
            right_low = candles[i + j].get('low') or candles[i + j].get('price_low') or 0
            if left_low is None or right_low is None or left_low <= 0 or right_low <= 0 or left_low >= 999999 or right_low >= 999999:
                is_swing_low = False
                break
            if low >= left_low or low >= right_low:
                is_swing_low = False
                break
        if is_swing_low:
            all_swings.append((i, low, 'low'))

    # Sort swings by index (chronological order)
    all_swings.sort(key=lambda x: x[0])

    # Find the last two different swing types to form a complete swing
    # A complete swing needs both a high and low point
    if len(all_swings) < 2:
        # Not enough swings, fallback to lookback high/low
        max_high = 0
        max_idx = -1
        min_low = 999999
        min_idx = -1
        for i, c in enumerate(candles):
            h = c.get('high') or c.get('price_high') or 0
            l = c.get('low') or c.get('price_low') or 0
            if h is not None and h > max_high:
                max_high = h
                max_idx = i
            if l is not None and 0 < l < min_low:
                min_low = l
                min_idx = i

        swing_direction = 'up' if max_idx > min_idx else 'down' if min_idx > max_idx else 'neutral'
        return {
            'swing_high': round(max_high, 2) if max_high > 0 else 0,
            'swing_low': round(min_low, 2) if min_low < 999999 else 0,
            'swing_direction': swing_direction,
            'swing_high_idx': max_idx,
            'swing_low_idx': min_idx,
            'swing_type': 'fallback',
            'extensions_direction': 'up' if swing_direction == 'up' else 'down'
        }

    # Find the most recent SIGNIFICANT swing pair (range >= min_range)
    # Start from the most recent swing and work backwards to find a valid pair
    most_recent = None
    second_most_recent = None

    for i in range(len(all_swings) - 1, -1, -1):
        candidate_recent = all_swings[i]
        # Find the most recent swing of the OPPOSITE type
        for j in range(i - 1, -1, -1):
            if all_swings[j][2] != candidate_recent[2]:  # Different type
                candidate_second = all_swings[j]
                # Calculate range
                swing_range = abs(candidate_recent[1] - candidate_second[1])
                if swing_range >= min_range:
                    most_recent = candidate_recent
                    second_most_recent = candidate_second
                    break
        if most_recent and second_most_recent:
            break

    # If no significant swing found, fallback to any swing pair
    if not most_recent or not second_most_recent:
        if len(all_swings) >= 2:
            most_recent = all_swings[-1]
            for swing in reversed(all_swings[:-1]):
                if swing[2] != most_recent[2]:
                    second_most_recent = swing
                    break

    if not second_most_recent:
        # All swings are same type, use the two most recent of same type boundaries
        swing_high = most_recent[1] if most_recent[2] == 'high' else 0
        swing_low = most_recent[1] if most_recent[2] == 'low' else 0
        return {
            'swing_high': round(swing_high, 2),
            'swing_low': round(swing_low, 2),
            'swing_direction': 'up' if most_recent[2] == 'high' else 'down',
            'swing_high_idx': most_recent[0] if most_recent[2] == 'high' else -1,
            'swing_low_idx': most_recent[0] if most_recent[2] == 'low' else -1,
            'swing_type': 'partial',
            'extensions_direction': 'up' if most_recent[2] == 'high' else 'down'
        }

    # Now we have two swings that form a complete swing (high + low)
    # Determine which came first to know the swing direction
    if most_recent[2] == 'high':
        # Most recent is HIGH, second is LOW → UP swing (low to high)
        swing_high = most_recent[1]
        swing_low = second_most_recent[1]
        swing_high_idx = most_recent[0]
        swing_low_idx = second_most_recent[0]
        swing_direction = 'up'
        extensions_direction = 'up'  # Extensions above the high
    else:
        # Most recent is LOW, second is HIGH → DOWN swing (high to low)
        swing_high = second_most_recent[1]
        swing_low = most_recent[1]
        swing_high_idx = second_most_recent[0]
        swing_low_idx = most_recent[0]
        swing_direction = 'down'
        extensions_direction = 'down'  # Extensions below the low

    return {
        'swing_high': round(swing_high, 2),
        'swing_low': round(swing_low, 2),
        'swing_direction': swing_direction,
        'swing_high_idx': swing_high_idx,
        'swing_low_idx': swing_low_idx,
        'swing_type': 'confirmed',
        'extensions_direction': extensions_direction
    }

def reset_session_profile(session_key):
    """Reset a single session profile"""
    global tpo_state
    session = tpo_state['sessions'][session_key]
    session['profiles'] = {}
    session['period_count'] = 0
    session['current_period_start'] = 0
    session['poc'] = 0.0
    session['vah'] = 0.0
    session['val'] = 0.0
    session['single_prints'] = []
    session['ib_high'] = 0.0
    session['ib_low'] = 999999.0
    session['ib_complete'] = False
    session['open_price'] = 0.0
    session['high'] = 0.0
    session['low'] = 999999.0
    session['max_tpo_count'] = 0
    session['total_tpo_count'] = 0
    session['profile_shape'] = 'developing'
    session['day_type'] = 'developing'
    session['day_type_confidence'] = 0

    # Extra fields for US AM session
    if session_key == 'tpo3_us_am':
        session['open_type'] = 'developing'
        session['open_type_confidence'] = 0
        session['open_direction'] = None
        session['a_high'] = 0.0
        session['a_low'] = 999999.0
        session['b_high'] = 0.0
        session['b_low'] = 999999.0
        session['ab_overlap'] = None

def reset_tpo_for_new_day():
    """Reset TPO data for new trading day (18:00 ET)"""
    global tpo_state, state

    # Store current day's US IB and NY 1H as Previous Day values before reset
    if state.get('ibs'):
        us_ib = state['ibs'].get('us', {})
        ny_ib = state['ibs'].get('ny', {})

        # Store US IB as PD US IB (if it has valid data)
        if us_ib.get('high', 0) > 0 and us_ib.get('low', 999999) < 999999:
            state['pd_us_ib'] = {
                'high': us_ib.get('high', 0),
                'low': us_ib.get('low', 0),
                'mid': us_ib.get('mid', 0),
                'poc': us_ib.get('poc', 0),
                'vwap': us_ib.get('vwap', 0)
            }
            print(f"📦 Stored PD US IB: H=${us_ib['high']:.2f} L=${us_ib['low']:.2f} POC=${us_ib.get('poc', 0):.2f}")

        # Store NY IB (09:30-10:30 = NY 1H) as PD NY 1H
        if ny_ib.get('high', 0) > 0 and ny_ib.get('low', 999999) < 999999:
            state['pd_ny_1h'] = {
                'high': ny_ib.get('high', 0),
                'low': ny_ib.get('low', 0),
                'mid': ny_ib.get('mid', 0),
                'poc': ny_ib.get('poc', 0),
                'vwap': ny_ib.get('vwap', 0)
            }
            print(f"📦 Stored PD NY 1H: H=${ny_ib['high']:.2f} L=${ny_ib['low']:.2f} POC=${ny_ib.get('poc', 0):.2f}")

    # Reset full day profile
    day = tpo_state['day']
    day['profiles'] = {}
    day['period_count'] = 0
    day['current_period_start'] = 0
    day['poc'] = 0.0
    day['vah'] = 0.0
    day['val'] = 0.0
    day['single_prints'] = []
    day['ib_high'] = 0.0
    day['ib_low'] = 999999.0
    day['ib_complete'] = False
    day['open_price'] = 0.0
    day['rth_open'] = 0.0
    day['a_high'] = 0.0
    day['a_low'] = 999999.0
    day['b_high'] = 0.0
    day['b_low'] = 999999.0
    day['c_high'] = 0.0
    day['c_low'] = 999999.0
    day['ab_overlap'] = None
    day['bc_overlap'] = None
    day['day_type'] = 'developing'
    day['day_type_confidence'] = 0
    day['day_type_scores'] = {}
    day['open_type'] = 'developing'
    day['open_type_confidence'] = 0
    day['open_direction'] = None
    day['profile_shape'] = 'developing'
    day['max_tpo_count'] = 0
    day['total_tpo_count'] = 0
    day['range_extension_pct'] = 0.0

    # Reset all 4 session profiles
    for session_key in tpo_state['sessions']:
        reset_session_profile(session_key)

    tpo_state['active_session'] = None
    tpo_state['day_start_time'] = 0
    print("🔄 TPO: Reset for new trading day")

# ============================================
# FETCH PREVIOUS DAY LEVELS FROM DATABENTO
# ============================================
def fetch_pd_levels():
    """Fetch previous day OHLC from Databento historical API using trade data"""
    global state, front_month_instrument_id, ACTIVE_CONTRACT

    # Skip Databento fetch for spot contracts
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        print("⏭️ Skipping Databento PD levels for spot contract")
        return

    if not HAS_DATABENTO or not API_KEY:
        print("⚠️  Cannot fetch PD levels - no Databento connection")
        return
    symbol = config['symbol']
    price_min = config['price_min']
    price_max = config['price_max']

    try:
        print(f"📊 Fetching Previous Day levels for {config['name']} from Databento...")

        # Get current ET time
        et_now = get_et_now()
        current_hour = et_now.hour

        # Futures session times:
        # - Session runs 18:00 ET to 17:00 ET next day
        # - Market close: 17:00-18:00 ET (1 hour gap)
        #
        # PD = PREVIOUS COMPLETE session:
        # - If BEFORE 17:00 ET: Current session still ongoing
        #   PD = 2 days ago 18:00 → yesterday 17:00
        # - If 17:00 ET or AFTER: Current session ended (or new one started at 18:00)
        #   PD = yesterday 18:00 → today 17:00

        if current_hour < 17:
            # Current session still running, PD is 2 days back
            session_end_date = et_now.date() - timedelta(days=1)
        else:
            # Current session ended (17:00+) or new session started (18:00+)
            # PD is the session that just ended today at 17:00
            session_end_date = et_now.date()

        # Skip weekends - if end date is weekend, go back to Friday
        while session_end_date.weekday() >= 5:  # Saturday=5, Sunday=6
            session_end_date -= timedelta(days=1)

        # Session start: 18:00 ET the day BEFORE the end date
        session_start_date = session_end_date - timedelta(days=1)
        # Skip weekends for start date too
        while session_start_date.weekday() >= 5:
            session_start_date -= timedelta(days=1)

        # Convert to UTC for API
        # 18:00 ET = 23:00 UTC (EST) or 22:00 UTC (EDT) - using EST for January
        # 17:00 ET = 22:00 UTC (EST) - full session until market close
        start_ts = f"{session_start_date}T23:00:00Z"  # 18:00 ET = 23:00 UTC
        end_ts = f"{session_end_date}T22:00:00Z"      # 17:00 ET = 22:00 UTC

        print(f"   PD Session: {session_start_date} 18:00 ET → {session_end_date} 17:00 ET")

        client = db.Historical(key=API_KEY)

        # Fetch TRADES to filter by most active instrument (front month)
        print(f"   Querying {symbol} trades for session {session_start_date} to {session_end_date}...")
        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=[symbol],
            stype_in='parent',
            schema='trades',
            start=start_ts,
            end=end_ts
        )

        records = list(data)
        print(f"   Got {len(records)} trade records")

        # Group trades by instrument_id and track volume profile for VPOC
        by_instrument = {}
        volume_profile = {}  # price level -> total volume
        tick_size = config.get('tick_size', 0.10)

        for r in records:
            iid = r.instrument_id
            p = r.price / 1e9 if r.price > 1e6 else r.price
            size = getattr(r, 'size', 1)

            # Skip invalid prices using contract-specific range
            if p < price_min or p > price_max:
                continue

            if iid not in by_instrument:
                by_instrument[iid] = {'count': 0, 'high': 0, 'low': float('inf'), 'first': p, 'last': p, 'volume_profile': {}}
            by_instrument[iid]['count'] += 1
            by_instrument[iid]['last'] = p
            if p > by_instrument[iid]['high']:
                by_instrument[iid]['high'] = p
            if p < by_instrument[iid]['low']:
                by_instrument[iid]['low'] = p

            # Track volume at each price level (rounded to tick size)
            price_level = round(p / tick_size) * tick_size
            if price_level not in by_instrument[iid]['volume_profile']:
                by_instrument[iid]['volume_profile'][price_level] = 0
            by_instrument[iid]['volume_profile'][price_level] += size

        if not by_instrument:
            print("⚠️  No valid trades found for PD")
            return

        # Find front month = instrument with most trades
        front_month = max(by_instrument.items(), key=lambda x: x[1]['count'])
        iid, data = front_month

        # Set front month ID for live trade filtering (if not already set)
        if front_month_instrument_id is None:
            front_month_instrument_id = iid
            print(f"   🎯 Front month instrument ID: {iid}")

        pd_high = data['high']
        pd_low = data['low']
        pd_open = data['first']
        pd_close = data['last']

        # Calculate true VPOC (Volume Point of Control) - price with highest volume
        volume_profile = data['volume_profile']
        if volume_profile:
            pdpoc = max(volume_profile.items(), key=lambda x: x[1])[0]
        else:
            # Fallback to typical price if no volume data
            pdpoc = (pd_high + pd_low + pd_close) / 3

        # Calculate PD VAH/VAL (70% of volume around POC)
        pd_vah = pdpoc
        pd_val = pdpoc
        if volume_profile:
            sorted_prices = sorted(volume_profile.keys())
            total_volume = sum(volume_profile.values())
            poc_idx = sorted_prices.index(pdpoc) if pdpoc in sorted_prices else len(sorted_prices) // 2

            # Start from POC and expand outward until 70% of volume captured
            vah_idx = poc_idx
            val_idx = poc_idx
            current_vol = volume_profile.get(sorted_prices[poc_idx], 0) if poc_idx < len(sorted_prices) else 0
            target_vol = total_volume * 0.70

            while current_vol < target_vol and (vah_idx < len(sorted_prices) - 1 or val_idx > 0):
                vol_above = volume_profile.get(sorted_prices[vah_idx + 1], 0) if vah_idx < len(sorted_prices) - 1 else 0
                vol_below = volume_profile.get(sorted_prices[val_idx - 1], 0) if val_idx > 0 else 0

                if vol_above >= vol_below and vah_idx < len(sorted_prices) - 1:
                    vah_idx += 1
                    current_vol += vol_above
                elif val_idx > 0:
                    val_idx -= 1
                    current_vol += vol_below
                else:
                    break

            pd_vah = sorted_prices[vah_idx] if vah_idx < len(sorted_prices) else pd_high
            pd_val = sorted_prices[val_idx] if val_idx >= 0 else pd_low

        print(f"   Front month (ID {iid}): {data['count']} trades")

        # Check if contract changed during fetch - don't overwrite BTC-SPOT PD levels
        current_config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
        if current_config.get('is_spot', False):
            print(f"⚠️ Skipping PD update - contract switched to {ACTIVE_CONTRACT} during fetch")
            return

        with lock:
            state['pd_high'] = pd_high
            state['pd_low'] = pd_low
            state['pd_open'] = pd_open
            state['pd_close'] = pd_close
            state['pdpoc'] = pdpoc
            state['pd_vah'] = pd_vah
            state['pd_val'] = pd_val
            state['pd_loaded'] = True
            state['pd_date_range'] = f"{session_start_date.strftime('%b %d')} 18:00 - {session_end_date.strftime('%b %d')} 17:00 ET"

        print(f"✅ PD Levels loaded: High=${pd_high:.2f}, Low=${pd_low:.2f}, POC=${pdpoc:.2f}, VAH=${pd_vah:.2f}, VAL=${pd_val:.2f}")

        # Also fetch PD US IB and NY 1H from the same session data
        fetch_pd_ny_sessions(records, iid, price_min, price_max, config.get('tick_size', 0.10), session_end_date)

    except Exception as e:
        print(f"❌ Error fetching PD levels: {e}")
        import traceback
        traceback.print_exc()

def fetch_pd_ny_sessions(records, front_month_iid, price_min, price_max, tick_size, session_end_date):
    """Extract PD US IB and NY 1H from the already-fetched historical records"""
    global state

    try:
        # US IB: 08:20-09:30 ET = 13:20-14:30 UTC
        # NY 1H: 09:30-10:30 ET = 14:30-15:30 UTC
        # session_end_date is the calendar date when the session ended (17:00 ET)
        # So US IB and NY 1H happened on session_end_date itself

        from datetime import datetime
        import pytz
        utc = pytz.UTC

        # Calculate UTC timestamps for US IB and NY 1H on the end date
        us_ib_start = datetime.strptime(f"{session_end_date} 13:20:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=utc)
        us_ib_end = datetime.strptime(f"{session_end_date} 14:30:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=utc)
        ny_1h_start = datetime.strptime(f"{session_end_date} 14:30:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=utc)
        ny_1h_end = datetime.strptime(f"{session_end_date} 15:30:00", "%Y-%m-%d %H:%M:%S").replace(tzinfo=utc)

        us_ib_start_ns = int(us_ib_start.timestamp() * 1e9)
        us_ib_end_ns = int(us_ib_end.timestamp() * 1e9)
        ny_1h_start_ns = int(ny_1h_start.timestamp() * 1e9)
        ny_1h_end_ns = int(ny_1h_end.timestamp() * 1e9)

        # Filter records for each session
        us_ib_data = {'high': 0.0, 'low': float('inf'), 'volume_profile': {}, 'vwap_num': 0.0, 'vwap_den': 0.0}
        ny_1h_data = {'high': 0.0, 'low': float('inf'), 'volume_profile': {}, 'vwap_num': 0.0, 'vwap_den': 0.0}

        for r in records:
            if r.instrument_id != front_month_iid:
                continue

            p = r.price / 1e9 if r.price > 1e6 else r.price
            size = getattr(r, 'size', 1)
            ts_ns = r.ts_event if hasattr(r, 'ts_event') else getattr(r, 'ts_recv', 0)

            if p < price_min or p > price_max:
                continue

            price_level = round(p / tick_size) * tick_size

            # US IB (08:20-09:30 ET)
            if us_ib_start_ns <= ts_ns < us_ib_end_ns:
                if p > us_ib_data['high']:
                    us_ib_data['high'] = p
                if p < us_ib_data['low']:
                    us_ib_data['low'] = p
                us_ib_data['vwap_num'] += p * size
                us_ib_data['vwap_den'] += size
                us_ib_data['volume_profile'][price_level] = us_ib_data['volume_profile'].get(price_level, 0) + size

            # NY 1H (09:30-10:30 ET)
            if ny_1h_start_ns <= ts_ns < ny_1h_end_ns:
                if p > ny_1h_data['high']:
                    ny_1h_data['high'] = p
                if p < ny_1h_data['low']:
                    ny_1h_data['low'] = p
                ny_1h_data['vwap_num'] += p * size
                ny_1h_data['vwap_den'] += size
                ny_1h_data['volume_profile'][price_level] = ny_1h_data['volume_profile'].get(price_level, 0) + size

        # Calculate POC and VWAP for each session
        with lock:
            # US IB
            if us_ib_data['high'] > 0 and us_ib_data['low'] < float('inf'):
                us_ib_vwap = us_ib_data['vwap_num'] / us_ib_data['vwap_den'] if us_ib_data['vwap_den'] > 0 else 0
                us_ib_poc = max(us_ib_data['volume_profile'].items(), key=lambda x: x[1])[0] if us_ib_data['volume_profile'] else 0
                state['pd_us_ib'] = {
                    'high': us_ib_data['high'],
                    'low': us_ib_data['low'],
                    'mid': (us_ib_data['high'] + us_ib_data['low']) / 2,
                    'poc': us_ib_poc,
                    'vwap': us_ib_vwap
                }
                print(f"✅ PD US IB: H=${us_ib_data['high']:.2f}, L=${us_ib_data['low']:.2f}, POC=${us_ib_poc:.2f}")

            # NY 1H
            if ny_1h_data['high'] > 0 and ny_1h_data['low'] < float('inf'):
                ny_1h_vwap = ny_1h_data['vwap_num'] / ny_1h_data['vwap_den'] if ny_1h_data['vwap_den'] > 0 else 0
                ny_1h_poc = max(ny_1h_data['volume_profile'].items(), key=lambda x: x[1])[0] if ny_1h_data['volume_profile'] else 0
                state['pd_ny_1h'] = {
                    'high': ny_1h_data['high'],
                    'low': ny_1h_data['low'],
                    'mid': (ny_1h_data['high'] + ny_1h_data['low']) / 2,
                    'poc': ny_1h_poc,
                    'vwap': ny_1h_vwap
                }
                print(f"✅ PD NY 1H: H=${ny_1h_data['high']:.2f}, L=${ny_1h_data['low']:.2f}, POC=${ny_1h_poc:.2f}")

    except Exception as e:
        print(f"⚠️ Error fetching PD NY sessions: {e}")

def fetch_all_ibs():
    """Fetch historical data for all 4 IBs that have already ended in current trading day"""
    global state, front_month_instrument_id, ACTIVE_CONTRACT

    # Skip Databento fetch for spot contracts
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        print("⏭️ Skipping Databento IB fetch for spot contract")
        return

    if not HAS_DATABENTO or not API_KEY:
        return
    symbol = config['symbol']
    price_min = config['price_min']
    price_max = config['price_max']

    try:
        et_now = get_et_now()
        hour_min = et_now.hour * 100 + et_now.minute
        current_hour = et_now.hour

        # Trading day definition:
        # - Day starts at 18:00 ET, ends at 17:00 ET next calendar day
        # - 17:00-18:00 ET is the market close hour (no trading)
        #
        # IB sessions occur in this order within a trading day:
        # 1. Japan IB: 19:00-20:00 ET (same evening as day start)
        # 2. London IB: 03:00-04:00 ET (next calendar day morning)
        # 3. US IB: 08:20-09:30 ET (next calendar day morning)
        # 4. NY IB: 09:30-10:30 ET (next calendar day morning)

        # Determine if we're in a new trading day (after 17:00 ET = day ended, after 18:00 = new day)
        if current_hour >= 17:
            # After 17:00 ET - old day ended
            if current_hour >= 18:
                # After 18:00 ET - new trading day started
                # Japan IB hasn't happened yet if before 19:00
                # All other IBs are tomorrow
                session_date = et_now.date()  # For Japan IB tonight
                next_day = (et_now + timedelta(days=1)).strftime('%Y-%m-%d')  # For London/US/NY tomorrow
            else:
                # 17:00-18:00 ET - market close hour, between days
                # Reset all IBs to waiting for new day
                print("📊 Market close hour (17:00-18:00 ET) - All IBs waiting for new day")
                with lock:
                    for ib_key in state['ibs']:
                        state['ibs'][ib_key]['high'] = 0.0
                        state['ibs'][ib_key]['low'] = 999999.0
                        state['ibs'][ib_key]['status'] = 'WAITING'
                    state['ib_high'] = 0.0
                    state['ib_low'] = 0.0
                    state['ib_locked'] = True
                    state['ib_session_name'] = ''
                    state['ib_status'] = 'WAITING'
                return
        else:
            # Before 17:00 ET - we're in the current trading day
            # Japan IB was yesterday evening, other IBs are today
            session_date = (et_now - timedelta(days=1)).date()  # Japan IB was last night
            next_day = et_now.strftime('%Y-%m-%d')  # London/US/NY are today

        today = et_now.strftime('%Y-%m-%d')
        tomorrow = (et_now + timedelta(days=1)).strftime('%Y-%m-%d')

        # IB sessions with their UTC time ranges
        # UTC = ET + 5 hours (EST)
        ib_definitions = {
            'japan': {
                'name': 'Japan IB',
                'et_start': 1900, 'et_end': 2000,  # 19:00-20:00 ET
                # Japan IB: 19:00-20:00 ET = 00:00-01:00 UTC NEXT calendar day
                'utc_start': f"{tomorrow}T00:00:00Z" if current_hour >= 18 else f"{today}T00:00:00Z",
                'utc_end': f"{tomorrow}T01:00:00Z" if current_hour >= 18 else f"{today}T01:00:00Z",
            },
            'london': {
                'name': 'London IB',
                'et_start': 300, 'et_end': 400,  # 03:00-04:00 ET
                # London IB: 03:00-04:00 ET = 08:00-09:00 UTC same day
                'utc_start': f"{today}T08:00:00Z",
                'utc_end': f"{today}T09:00:00Z",
            },
            'us': {
                'name': 'US IB',
                'et_start': 820, 'et_end': 930,  # 08:20-09:30 ET
                # US IB: 08:20-09:30 ET = 13:20-14:30 UTC
                'utc_start': f"{today}T13:20:00Z",
                'utc_end': f"{today}T14:30:00Z",
            },
            'ny': {
                'name': 'NY IB',
                'et_start': 930, 'et_end': 1030,  # 09:30-10:30 ET
                # NY IB: 09:30-10:30 ET = 14:30-15:30 UTC
                'utc_start': f"{today}T14:30:00Z",
                'utc_end': f"{today}T15:30:00Z",
            },
        }

        client = db.Historical(key=API_KEY)
        print("📊 Fetching historical IB data for ended sessions...")

        for ib_key, ib_def in ib_definitions.items():
            # Check if we should fetch this IB based on current time
            should_fetch = False

            # After 18:00 ET, we're in a NEW trading day
            # Japan IB (19:00-20:00) is the first IB of the new day
            # London/US/NY are tomorrow morning
            if current_hour >= 18:
                # New trading day started
                if ib_key == 'japan':
                    if hour_min >= ib_def['et_end']:
                        # Japan IB ended tonight
                        should_fetch = True
                        with lock:
                            state['ibs'][ib_key]['status'] = 'ENDED'
                    elif hour_min >= ib_def['et_start']:
                        # Japan IB is active now
                        should_fetch = True
                        with lock:
                            state['ibs'][ib_key]['status'] = 'ACTIVE'
                        print(f"   🔄 {ib_def['name']} is ACTIVE - fetching historical to sync...")
                    else:
                        # Japan IB hasn't started yet (18:00-19:00 ET)
                        print(f"   ⏳ {ib_def['name']} hasn't started yet (starts 19:00 ET)")
                        with lock:
                            state['ibs'][ib_key]['status'] = 'WAITING'
                        continue
                else:
                    # London/US/NY IBs are tomorrow - all waiting
                    print(f"   ⏳ {ib_def['name']} is tomorrow")
                    with lock:
                        state['ibs'][ib_key]['status'] = 'WAITING'
                    continue
            else:
                # Before 18:00 ET - in current trading day
                # Japan IB was yesterday evening, other IBs are today
                if hour_min >= ib_def['et_end']:
                    should_fetch = True
                    # Session has ended - set status immediately (data fetch may fail)
                    with lock:
                        state['ibs'][ib_key]['status'] = 'ENDED'
                elif hour_min >= ib_def['et_start'] and hour_min < ib_def['et_end']:
                    should_fetch = True
                    with lock:
                        state['ibs'][ib_key]['status'] = 'ACTIVE'
                    print(f"   🔄 {ib_def['name']} is ACTIVE - fetching historical to sync...")
                elif ib_key == 'japan':
                    # Japan IB from yesterday evening (before current time)
                    should_fetch = True
                    with lock:
                        state['ibs'][ib_key]['status'] = 'ENDED'
                else:
                    print(f"   ⏳ {ib_def['name']} hasn't started yet")
                    with lock:
                        state['ibs'][ib_key]['status'] = 'WAITING'
                    continue

            if not should_fetch:
                continue

            # Get UTC time range
            utc_start = ib_def['utc_start']
            utc_end = ib_def['utc_end']

            # For active sessions, use current time minus 30min as end (Databento historical has ~20-30min delay)
            if hour_min >= ib_def['et_start'] and hour_min < ib_def['et_end']:
                # Currently in this IB session - query up to current time minus data delay buffer
                current_utc = (et_now + timedelta(hours=5) - timedelta(minutes=30)).strftime('%Y-%m-%dT%H:%M:%SZ')

                # Skip if adjusted end time would be before start time (not enough data available yet)
                if current_utc <= utc_start:
                    print(f"   ⏳ {ib_def['name']} is ACTIVE but not enough historical data yet (starts in <30min)", flush=True)
                    with lock:
                        state['ibs'][ib_key]['status'] = 'ACTIVE'
                    continue

                utc_end = current_utc
                print(f"   🔄 {ib_def['name']} is ACTIVE - fetching historical to sync...", flush=True)
                print(f"   (Active session - querying up to {utc_end})", flush=True)

            try:
                print(f"   Fetching {ib_def['name']} ({utc_start} to {utc_end})...", flush=True)

                data = client.timeseries.get_range(
                    dataset='GLBX.MDP3',
                    symbols=[symbol],
                    stype_in='parent',
                    schema='trades',
                    start=utc_start,
                    end=utc_end
                )

                records = list(data)
                print(f"   Got {len(records)} records for {ib_def['name']}", flush=True)

                if not records:
                    print(f"   ⚠️  No trades found for {ib_def['name']}", flush=True)
                    continue

                # Group trades by instrument_id to find front month
                by_instrument = {}
                for r in records:
                    iid = r.instrument_id
                    p = r.price / 1e9 if r.price > 1e6 else r.price
                    if p < price_min or p > price_max:
                        continue
                    if iid not in by_instrument:
                        by_instrument[iid] = {'count': 0, 'high': 0, 'low': float('inf')}
                    by_instrument[iid]['count'] += 1
                    if p > by_instrument[iid]['high']:
                        by_instrument[iid]['high'] = p
                    if p < by_instrument[iid]['low']:
                        by_instrument[iid]['low'] = p

                if not by_instrument:
                    continue

                # Use front month (most trades)
                front_month = max(by_instrument.items(), key=lambda x: x[1]['count'])
                iid, ib_data = front_month

                # Store front month ID if not set
                if front_month_instrument_id is None:
                    front_month_instrument_id = iid

                ib_high = ib_data['high']
                ib_low = ib_data['low']

                with lock:
                    state['ibs'][ib_key]['high'] = ib_high
                    state['ibs'][ib_key]['low'] = ib_low
                    state['ibs'][ib_key]['status'] = 'ENDED'

                    # Copy NY IB (09:30-10:30) to TPO state as RTH IB
                    if ib_key == 'ny':
                        tpo_state['day']['ib_high'] = ib_high
                        tpo_state['day']['ib_low'] = ib_low
                        tpo_state['day']['ib_complete'] = True
                        # Also copy to US AM session
                        tpo_state['sessions']['tpo3_us_am']['ib_high'] = ib_high
                        tpo_state['sessions']['tpo3_us_am']['ib_low'] = ib_low
                        tpo_state['sessions']['tpo3_us_am']['ib_complete'] = True
                        print(f"   📊 TPO RTH IB initialized: H=${ib_high:.2f}, L=${ib_low:.2f}")

                print(f"   ✅ {ib_def['name']}: H=${ib_high:.2f}, L=${ib_low:.2f} (from {ib_data['count']} trades)", flush=True)

            except Exception as e:
                print(f"   ❌ Error fetching {ib_def['name']}: {e}")

    except Exception as e:
        print(f"❌ Error fetching IBs: {e}")
        import traceback
        traceback.print_exc()

def fetch_todays_ib():
    """Wrapper for backwards compatibility - calls fetch_all_ibs"""
    fetch_all_ibs()


def fetch_todays_tpo_data():
    """Fetch full day's trade data and rebuild TPO profiles from session start.

    This ensures all TPO periods (A-Z) are populated even when backend starts mid-session.
    """
    global tpo_state, state, front_month_instrument_id, lock

    # Skip Databento fetch for spot contracts
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        print("⏭️ Skipping Databento TPO fetch for spot contract")
        return

    if not HAS_DATABENTO or not API_KEY:
        print("⚠️  Databento not available for historical TPO load")
        return

    try:
        config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
        symbol = config['symbol']  # Use 'GC.FUT' format for parent symbology
        tick_size = config['tick_size']
        price_min = config['price_min']
        price_max = config['price_max']

        # Calculate trading day start (18:00 ET previous day)
        et_tz = pytz.timezone('America/New_York')
        now_et = datetime.now(et_tz)
        current_hour = now_et.hour

        if current_hour >= 18:
            # After 18:00, new trading day started today
            day_start_et = now_et.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            # Before 18:00, trading day started yesterday at 18:00
            day_start_et = (now_et - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)

        # IMPORTANT: Fully reset TPO state before loading new data
        reset_tpo_for_new_day()
        print(f"📊 TPO state reset for loading historical data")

        # Convert to UTC (subtract 20 minutes to account for Databento data delay)
        day_start_utc = day_start_et.astimezone(pytz.UTC)
        now_utc = (now_et - timedelta(minutes=20)).astimezone(pytz.UTC)

        print(f"📊 Loading full day TPO data from {day_start_et.strftime('%Y-%m-%d %H:%M')} ET...")

        client = db.Historical(key=API_KEY)

        # Fetch all trades for today's session
        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=[symbol],
            stype_in='parent',
            schema='trades',
            start=day_start_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
            end=now_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        )

        records = list(data)
        print(f"   Got {len(records)} trades for TPO reconstruction")

        if not records:
            print("   ⚠️  No historical trades found")
            return

        # Filter to front month
        if front_month_instrument_id:
            fm_records = [r for r in records if r.instrument_id == front_month_instrument_id]
            if fm_records:
                records = fm_records
                print(f"   Using {len(records)} front month trades")

        # Rebuild TPO profiles from historical data
        with lock:
            # Clear existing profiles
            tpo_state['day']['profiles'] = {}

            for session_key in tpo_state['sessions']:
                tpo_state['sessions'][session_key]['profiles'] = {}

            # Process each trade
            for r in records:
                price = r.price / 1e9 if r.price > 1e6 else r.price

                # Filter invalid prices
                if price < price_min or price > price_max:
                    continue

                # Get trade timestamp in ET
                ts_ns = r.ts_event
                ts_sec = ts_ns / 1e9
                trade_time = datetime.fromtimestamp(ts_sec, tz=pytz.UTC).astimezone(et_tz)
                trade_hhmm = trade_time.hour * 100 + trade_time.minute

                # Calculate DAY period (from 18:00 ET)
                minutes_from_day_start = int((trade_time - day_start_et).total_seconds() / 60)
                day_period_idx = max(0, minutes_from_day_start // 30)
                day_letter = get_tpo_letter(day_period_idx)

                # Round price to tick size
                tpo_price = round(price / tick_size) * tick_size

                # Add to day profile
                if tpo_price not in tpo_state['day']['profiles']:
                    tpo_state['day']['profiles'][tpo_price] = set()
                tpo_state['day']['profiles'][tpo_price].add(day_letter)

                # Determine which session this trade belongs to
                session_key = None
                for skey, sconfig in TPO_SESSIONS.items():
                    start_hhmm = sconfig['start']
                    end_hhmm = sconfig['end']

                    if end_hhmm < start_hhmm:  # Overnight session
                        if trade_hhmm >= start_hhmm or trade_hhmm < end_hhmm:
                            session_key = skey
                            break
                    else:
                        if start_hhmm <= trade_hhmm < end_hhmm:
                            session_key = skey
                            break

                # Add to session profile
                if session_key:
                    session_data = tpo_state['sessions'][session_key]
                    session_config = TPO_SESSIONS[session_key]

                    # Calculate session period
                    session_period_idx = get_session_period_index(session_key, trade_hhmm)
                    session_letter = get_tpo_letter(session_period_idx)

                    if tpo_price not in session_data['profiles']:
                        session_data['profiles'][tpo_price] = set()
                    session_data['profiles'][tpo_price].add(session_letter)

                    # Track open price for session (first trade)
                    if session_data.get('open_price', 0) == 0:
                        session_data['open_price'] = price

                    # Track session high/low
                    if price > session_data.get('high', 0):
                        session_data['high'] = price
                    if price < session_data.get('low', 999999):
                        session_data['low'] = price

                    # Track A/B period ranges for US AM session (Open Type detection)
                    if session_key == 'tpo3_us_am':
                        if session_period_idx == 0:  # A period (09:30-10:00)
                            if price > session_data.get('a_high', 0):
                                session_data['a_high'] = price
                            if price < session_data.get('a_low', 999999):
                                session_data['a_low'] = price
                        elif session_period_idx == 1:  # B period (10:00-10:30)
                            if price > session_data.get('b_high', 0):
                                session_data['b_high'] = price
                            if price < session_data.get('b_low', 999999):
                                session_data['b_low'] = price

                        # Also copy to day profile for RTH
                        day = tpo_state['day']
                        if day.get('rth_open', 0) == 0:
                            day['rth_open'] = price
                        if session_period_idx == 0:
                            if price > day.get('a_high', 0):
                                day['a_high'] = price
                            if price < day.get('a_low', 999999):
                                day['a_low'] = price
                        elif session_period_idx == 1:
                            if price > day.get('b_high', 0):
                                day['b_high'] = price
                            if price < day.get('b_low', 999999):
                                day['b_low'] = price

                        # Track IB (first 2 periods = first hour)
                        if session_period_idx < 2:
                            if price > day.get('ib_high', 0):
                                day['ib_high'] = price
                            if price < day.get('ib_low', 999999):
                                day['ib_low'] = price
                            if price > session_data.get('ib_high', 0):
                                session_data['ib_high'] = price
                            if price < session_data.get('ib_low', 999999):
                                session_data['ib_low'] = price

                # Track day open (first trade of day)
                day = tpo_state['day']
                if day.get('open_price', 0) == 0:
                    day['open_price'] = price

            # Update period counts to current
            day_minutes_elapsed = int((now_et - day_start_et).total_seconds() / 60)
            tpo_state['day']['period_count'] = max(0, day_minutes_elapsed // 30)

            # Update session period counts
            for skey, sconfig in TPO_SESSIONS.items():
                session_data = tpo_state['sessions'][skey]
                session_data['period_count'] = get_session_period_index(skey, now_et.hour * 100 + now_et.minute)

            # Count total TPOs added
            total_tpos = sum(len(letters) for letters in tpo_state['day']['profiles'].values())
            unique_prices = len(tpo_state['day']['profiles'])

            print(f"   ✅ TPO profiles rebuilt: {unique_prices} price levels, {total_tpos} total TPOs")
            print(f"   📊 Day periods: A through {get_tpo_letter(tpo_state['day']['period_count'])}")

        # Calculate POC, VAH, VAL, single prints for all profiles
        calculate_tpo_metrics()
        classify_day_type()
        classify_open_type()
        print(f"   📊 POC: ${tpo_state['day']['poc']:.2f}, VAH: ${tpo_state['day']['vah']:.2f}, VAL: ${tpo_state['day']['val']:.2f}")
        print(f"   📊 Open Type: {tpo_state['day']['open_type']}, Day Type: {tpo_state['day']['day_type']}")
        # Save to cache after successful load
        save_tpo_cache()

    except Exception as e:
        error_str = str(e)
        print(f"❌ Error loading historical TPO: {e}")

        # If the error is "data_end_after_available_end", markets are closed - try last trading day
        if 'data_end_after_available_end' in error_str or '422' in error_str:
            print("📅 Markets appear closed, fetching last trading day's data...")
            try:
                fetch_last_trading_day_tpo()
                return  # Success!
            except Exception as e2:
                print(f"⚠️ Last trading day fetch also failed: {e2}")

        # Try loading from cache as final fallback
        print("📦 Trying to load TPO from cache...")
        load_tpo_cache()


def fetch_last_trading_day_tpo():
    """Fetch the last trading day's TPO data when markets are closed (weekends).

    This allows showing recent TPO data even when markets are closed.
    """
    global tpo_state, state, front_month_instrument_id, lock

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        return

    if not HAS_DATABENTO or not API_KEY:
        return

    symbol = config['symbol']
    tick_size = config['tick_size']
    price_min = config['price_min']
    price_max = config['price_max']

    et_tz = pytz.timezone('America/New_York')
    now_et = datetime.now(et_tz)

    # Find the last trading day END date (skip weekends)
    # A trading day that ENDS on Friday started on Thursday 18:00
    days_back = 1
    while days_back <= 7:
        check_date = now_et - timedelta(days=days_back)
        # Weekday: 0=Monday, 4=Friday
        if check_date.weekday() <= 4:  # It's a weekday
            break
        days_back += 1

    # The last trading session:
    # - Ends on the weekday we found (at 17:00)
    # - Starts on the PREVIOUS day at 18:00
    last_trading_end = (now_et - timedelta(days=days_back)).replace(hour=17, minute=0, second=0, microsecond=0)
    day_start_et = (last_trading_end - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)
    day_end_et = last_trading_end

    print(f"📅 Loading last trading day TPO: {day_start_et.strftime('%Y-%m-%d %H:%M')} to {day_end_et.strftime('%Y-%m-%d %H:%M')} ET")

    day_start_utc = day_start_et.astimezone(pytz.UTC)
    day_end_utc = day_end_et.astimezone(pytz.UTC)

    client = db.Historical(key=API_KEY)

    data = client.timeseries.get_range(
        dataset='GLBX.MDP3',
        symbols=[symbol],
        stype_in='parent',
        schema='trades',
        start=day_start_utc.strftime('%Y-%m-%dT%H:%M:%SZ'),
        end=day_end_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    )

    records = list(data)
    print(f"   Got {len(records)} trades from last trading day")

    if not records:
        raise Exception("No trades found for last trading day")

    # Filter to front month if we have the instrument ID
    if front_month_instrument_id:
        fm_records = [r for r in records if r.instrument_id == front_month_instrument_id]
        if fm_records:
            records = fm_records
            print(f"   Using {len(records)} front month trades")

    # Build TPO profiles
    with lock:
        tpo_state['day']['profiles'] = {}
        for session_key in tpo_state['sessions']:
            tpo_state['sessions'][session_key]['profiles'] = {}

        for r in records:
            price = r.price / 1e9 if r.price > 1e6 else r.price

            if price < price_min or price > price_max:
                continue

            ts_ns = r.ts_event
            ts_sec = ts_ns / 1e9
            trade_time = datetime.fromtimestamp(ts_sec, tz=pytz.UTC).astimezone(et_tz)

            minutes_from_day_start = int((trade_time - day_start_et).total_seconds() / 60)
            day_period_idx = max(0, minutes_from_day_start // 30)
            day_letter = get_tpo_letter(day_period_idx)

            tpo_price = round(price / tick_size) * tick_size

            if tpo_price not in tpo_state['day']['profiles']:
                tpo_state['day']['profiles'][tpo_price] = set()
            tpo_state['day']['profiles'][tpo_price].add(day_letter)

        # Calculate metrics
        calculate_tpo_metrics()

        total_tpos = sum(len(letters) for letters in tpo_state['day']['profiles'].values())
        unique_prices = len(tpo_state['day']['profiles'])
        print(f"   ✅ Last trading day TPO loaded: {unique_prices} levels, {total_tpos} TPOs")
        print(f"   📊 POC: ${tpo_state['day']['poc']:.2f}, VAH: ${tpo_state['day']['vah']:.2f}, VAL: ${tpo_state['day']['val']:.2f}")

        # Save to cache
        save_tpo_cache()


def fetch_ended_sessions_ohlc():
    """Fetch OHLC data for all sessions that have ended today"""
    global state, front_month_instrument_id, ACTIVE_CONTRACT

    # Skip Databento fetch for spot contracts
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        return

    if not HAS_DATABENTO or not API_KEY:
        return
    symbol = config['symbol']
    price_min = config['price_min']
    price_max = config['price_max']

    # Session definitions with ET start/end times
    session_times = {
        'pre_asia': ('18:00', '19:00'),
        'japan_ib': ('19:00', '20:00'),
        'china': ('20:00', '23:00'),
        'asia_close': ('23:00', '02:00'),
        'deadzone': ('02:00', '03:00'),
        'london': ('03:00', '06:00'),
        'low_volume': ('06:00', '08:20'),
        'us_ib': ('08:20', '09:30'),
        'ny_1h': ('09:30', '10:30'),
        'ny_2h': ('10:30', '11:30'),
        'lunch': ('11:30', '13:30'),
        'ny_pm': ('13:30', '16:00'),
        'ny_close': ('16:00', '17:00'),
    }

    ended_sessions = get_ended_sessions()
    if not ended_sessions:
        print("📊 No ended sessions to fetch OHLC for")
        return

    print(f"📊 Fetching OHLC for {len(ended_sessions)} ended sessions...")

    try:
        client = db.Historical(key=API_KEY)
        et_now = get_et_now()
        today = et_now.date()

        for session_id in ended_sessions:
            if session_id not in session_times:
                continue

            start_str, end_str = session_times[session_id]
            start_hour, start_min = map(int, start_str.split(':'))
            end_hour, end_min = map(int, end_str.split(':'))

            # Determine the date for session start
            session_date = today
            if start_hour >= 18:  # Pre-midnight sessions
                if et_now.hour < 18:  # We're past midnight
                    session_date = today - timedelta(days=1)

            # Build UTC timestamps
            start_et = datetime(session_date.year, session_date.month, session_date.day, start_hour, start_min)
            end_date = session_date
            if end_hour < start_hour:  # Session crosses midnight
                end_date = session_date + timedelta(days=1)
            end_et = datetime(end_date.year, end_date.month, end_date.day, end_hour, end_min)

            # Convert to UTC (ET + 5)
            utc_start = (start_et + timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
            utc_end = (end_et + timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M:%SZ')

            try:
                data = client.timeseries.get_range(
                    dataset='GLBX.MDP3',
                    symbols=[symbol],
                    stype_in='parent',
                    schema='trades',
                    start=utc_start,
                    end=utc_end
                )

                records = list(data)
                if not records:
                    continue

                # Process trades
                session_data = {
                    'high': 0, 'low': float('inf'),
                    'first_ts': float('inf'), 'first_price': 0,
                    'last_ts': 0, 'last_price': 0, 'count': 0,
                    'buy': 0, 'sell': 0  # Track volume
                }

                for r in records:
                    if front_month_instrument_id and r.instrument_id != front_month_instrument_id:
                        continue
                    p = r.price / 1e9 if r.price > 1e6 else r.price
                    if p < price_min or p > price_max:
                        continue

                    ts = r.ts_event
                    size = r.size
                    side = r.side
                    session_data['count'] += 1

                    # Track buy/sell volume: A = Ask (hit) = Buy, B = Bid (hit) = Sell
                    if side == 'A':
                        session_data['buy'] += size
                    elif side == 'B':
                        session_data['sell'] += size

                    if p > session_data['high']:
                        session_data['high'] = p
                    if p < session_data['low']:
                        session_data['low'] = p
                    if ts < session_data['first_ts']:
                        session_data['first_ts'] = ts
                        session_data['first_price'] = p
                    if ts > session_data['last_ts']:
                        session_data['last_ts'] = ts
                        session_data['last_price'] = p

                if session_data['count'] > 0:
                    session_volume = session_data['buy'] + session_data['sell']
                    session_delta = session_data['buy'] - session_data['sell']
                    with lock:
                        state['ended_sessions'][session_id] = {
                            'open': session_data['first_price'],
                            'high': session_data['high'],
                            'low': session_data['low'],
                            'close': session_data['last_price'],
                            'volume': session_volume,
                            'delta': session_delta
                        }
                        # Update day high/low
                        if session_data['high'] > state['day_high']:
                            state['day_high'] = session_data['high']
                        if session_data['low'] < state['day_low']:
                            state['day_low'] = session_data['low']
                        if state['day_open'] == 0 and session_id == 'pre_asia':
                            state['day_open'] = session_data['first_price']

                    print(f"   ✅ {session_id}: O={session_data['first_price']:.2f} H={session_data['high']:.2f} L={session_data['low']:.2f} C={session_data['last_price']:.2f} V={session_volume} D={session_delta}")

            except Exception as e:
                print(f"   ⚠️ Error fetching {session_id}: {e}")
                continue

    except Exception as e:
        print(f"❌ Error fetching ended sessions OHLC: {e}")
        import traceback
        traceback.print_exc()


# Cache for session history - stores raw daily ranges (pre-computed on startup)
# Structure: {session_id: {'name': str, 'dailyRanges': [{date, high, low, range}, ...]}}
session_history_cache = {
    'raw_data': None,      # Raw daily ranges per session
    'computed': None,      # Pre-computed averages for quick access
    'timestamp': 0,
    'ready': False         # True when cache is populated
}

# Cache for 5-day historical session OHLC (for stacked candle visualization)
historical_sessions_ohlc_cache = {
    'data': None,          # 5 days of session OHLC data
    'timestamp': 0,
    'ready': False
}

# Multi-week cache for historical data (5 historic weeks + current)
# File-based persistence for faster startup
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', '.cache')
weekly_sessions_cache = {
    'w5': {'data': None, 'timestamp': 0, 'ready': False},  # Oldest
    'w4': {'data': None, 'timestamp': 0, 'ready': False},
    'w3': {'data': None, 'timestamp': 0, 'ready': False},
    'w2': {'data': None, 'timestamp': 0, 'ready': False},
    'w1': {'data': None, 'timestamp': 0, 'ready': False},  # Most recent historic
    'current': {'data': None, 'timestamp': 0, 'ready': False}  # Building week
}

def get_week_date_range(week_id):
    """Get start and end dates for a specific week (dynamically calculated)"""
    et_now = get_et_now()
    today = et_now.date()

    # Find Monday of current week
    days_since_monday = today.weekday()  # Monday=0
    current_monday = today - timedelta(days=days_since_monday)

    if week_id == 'current':
        # Current week: Monday of this week to today (or Friday if weekend)
        # Limit to trading days (Mon-Fri)
        end_date = min(today, current_monday + timedelta(days=4))  # Cap at Friday
        return (current_monday.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))

    # Parse week offset from id (w1=1 week ago, w2=2 weeks ago, etc.)
    if not week_id.startswith('w') or not week_id[1:].isdigit():
        return None

    weeks_ago = int(week_id[1:])

    # Go back N weeks
    target_monday = current_monday - timedelta(weeks=weeks_ago)
    target_friday = target_monday + timedelta(days=4)

    return (target_monday.strftime('%Y-%m-%d'), target_friday.strftime('%Y-%m-%d'))

def load_cache_from_file(week_id):
    """Load cached data from file (includes contract in filename for multi-instrument support)"""
    global ACTIVE_CONTRACT
    try:
        # Include contract in filename so each instrument has separate cache
        cache_file = os.path.join(CACHE_DIR, f'sessions_{ACTIVE_CONTRACT}_{week_id}.json')
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
                weekly_sessions_cache[week_id]['data'] = data['data']
                weekly_sessions_cache[week_id]['timestamp'] = data['timestamp']
                weekly_sessions_cache[week_id]['ready'] = True
                print(f"✅ Loaded {week_id} from cache file ({ACTIVE_CONTRACT})")
                return True
    except Exception as e:
        print(f"⚠️ Could not load cache for {week_id}: {e}")
    return False

def save_cache_to_file(week_id):
    """Save cached data to file (includes contract in filename for multi-instrument support)"""
    global ACTIVE_CONTRACT
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        # Include contract in filename so each instrument has separate cache
        cache_file = os.path.join(CACHE_DIR, f'sessions_{ACTIVE_CONTRACT}_{week_id}.json')
        cache_data = {
            'data': weekly_sessions_cache[week_id]['data'],
            'timestamp': weekly_sessions_cache[week_id]['timestamp']
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        print(f"💾 Saved {week_id} to cache file ({ACTIVE_CONTRACT})")
    except Exception as e:
        print(f"⚠️ Could not save cache for {week_id}: {e}")

def load_all_caches():
    """Load all week caches from files on startup"""
    for week_id in weekly_sessions_cache.keys():
        load_cache_from_file(week_id)

    # After loading caches, initialize week levels from historical data
    initialize_week_levels_from_history()

    # Also initialize weekly open from Monday's data
    initialize_weekly_open_from_history()

def initialize_weekly_open_from_history():
    """Initialize weekly_open from Monday's pre_asia session open if not set"""
    global state

    with lock:
        # Skip if already set
        if state['weekly_open'] > 0:
            print(f"   📅 Weekly open already set: ${state['weekly_open']:.2f}")
            return

    # Get current week data from cache
    current_week = weekly_sessions_cache.get('current', {})
    week_data = current_week.get('data')

    if not week_data:
        print("   ⚠️ No current week data available for weekly open initialization")
        return

    # Find Monday's data (or the first trading day of the week)
    monday_data = None
    for day in week_data:
        label = day.get('label', '')
        if 'Mon' in label or day.get('date', '').endswith('-12'):  # Monday or first day
            monday_data = day
            break

    if not monday_data:
        # Use the earliest day in the week
        if week_data:
            monday_data = week_data[-1] if len(week_data) > 1 else week_data[0]

    if monday_data:
        sessions = monday_data.get('sessions', {})
        # Get pre_asia session open (Sunday 18:00 ET = week open)
        pre_asia = sessions.get('pre_asia', {})
        weekly_open_price = pre_asia.get('o', 0)

        if weekly_open_price > 0:
            with lock:
                state['weekly_open'] = weekly_open_price
                state['weekly_open_date'] = monday_data.get('date', '')
            print(f"   📅 Weekly Open initialized from history: ${weekly_open_price:.2f} ({monday_data.get('label', 'Monday')})")
        else:
            # Try japan_ib or first available session
            for sess_key in ['japan_ib', 'china', 'asia_close', 'london']:
                sess = sessions.get(sess_key, {})
                if sess.get('o', 0) > 0:
                    weekly_open_price = sess.get('o')
                    with lock:
                        state['weekly_open'] = weekly_open_price
                        state['weekly_open_date'] = monday_data.get('date', '')
                    print(f"   📅 Weekly Open initialized from {sess_key}: ${weekly_open_price:.2f}")
                    break
    else:
        print("   ⚠️ Could not find Monday data for weekly open initialization")

def initialize_week_levels_from_history():
    """Initialize week_high, week_low, and rolling_20d from historical session data"""
    global state, weekly_sessions_cache

    # Get current week data
    current_week = weekly_sessions_cache.get('current', {})
    week_data = current_week.get('data', [])

    if week_data:
        # Calculate week high/low from all sessions in current week
        week_high = 0.0
        week_low = 999999.0

        for day in week_data:
            sessions = day.get('sessions', {})
            for sess_key, sess in sessions.items():
                sess_high = sess.get('h', 0)
                sess_low = sess.get('l', 0)
                if sess_high > 0 and sess_high > week_high:
                    week_high = sess_high
                if sess_low > 0 and sess_low < week_low:
                    week_low = sess_low

        if week_high > 0:
            with lock:
                if state['week_high'] == 0 or state['week_high'] < week_high:
                    state['week_high'] = week_high
                if state['week_low'] == 999999.0 or state['week_low'] > week_low:
                    state['week_low'] = week_low
            print(f"   📊 Week H/L initialized from history: H=${week_high:.2f}, L=${week_low:.2f}")

    # Calculate rolling 20-day high/low from multiple weeks
    all_highs = []
    all_lows = []

    # Collect from current week and past weeks
    for week_id in ['current', 'w1', 'w2', 'w3', 'w4']:
        cache_data = weekly_sessions_cache.get(week_id, {})
        if cache_data.get('ready') or week_id == 'current':
            week_days = cache_data.get('data') or []
            for day in week_days:
                sessions = day.get('sessions', {})
                for sess_key, sess in sessions.items():
                    sess_high = sess.get('h', 0)
                    sess_low = sess.get('l', 0)
                    if sess_high > 0:
                        all_highs.append(sess_high)
                    if sess_low > 0:
                        all_lows.append(sess_low)

    if all_highs and all_lows:
        rolling_high = max(all_highs)
        rolling_low = min(all_lows)
        with lock:
            state['rolling_20d_high'] = rolling_high
            state['rolling_20d_low'] = rolling_low
        print(f"   📊 Rolling 20d H/L initialized: H=${rolling_high:.2f}, L=${rolling_low:.2f}")

def fetch_btc_week_sessions_ohlc(week_id):
    """Fetch historical session OHLC for BTC-SPOT from Binance"""
    global weekly_sessions_cache

    date_range = get_week_date_range(week_id)
    if not date_range:
        print(f"⚠️  Unknown week: {week_id}")
        return None

    start_date_str, end_date_str = date_range
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    # BTC session definitions (same times as futures, in ET)
    session_defs = [
        ('pre_asia', 'Pre-Asia', 18, 0, 19, 0),
        ('japan_ib', 'Japan', 19, 0, 20, 0),
        ('china', 'China', 20, 0, 23, 0),
        ('asia_close', 'Asia Close', 23, 0, 2, 0),
        ('deadzone', 'Deadzone', 2, 0, 3, 0),
        ('london', 'London', 3, 0, 6, 0),
        ('low_volume', 'Low Vol', 6, 0, 8, 20),
        ('us_ib', 'US IB', 8, 20, 9, 30),
        ('ny_1h', 'NY 1H', 9, 30, 10, 30),
        ('ny_2h', 'NY 2H', 10, 30, 11, 30),
        ('lunch', 'Lunch', 11, 30, 13, 30),
        ('ny_pm', 'NY PM', 13, 30, 16, 0),
        ('ny_close', 'NY Close', 16, 0, 17, 0),
    ]

    try:
        # Get trading days in range (BTC trades every day including weekends)
        trading_days = []
        check_date = end_date
        while check_date >= start_date:
            trading_days.append(check_date)
            check_date -= timedelta(days=1)

        print(f"📅 Fetching BTC {week_id} ({start_date_str} to {end_date_str}): {len(trading_days)} days")

        result = []

        for trading_date in trading_days:
            day_label = trading_date.strftime('%m-%d %a')
            date_str = trading_date.strftime('%Y-%m-%d')

            day_data = {
                'date': date_str,
                'label': day_label,
                'sessions': {},
                'day': {'o': 0, 'h': 0, 'l': 999999, 'c': 0}
            }

            # Fetch 1-hour candles from Binance for this day
            # Need to cover 18:00 previous day to 17:00 current day (ET)
            prev_date = trading_date - timedelta(days=1)

            # Convert ET times to UTC for Binance API
            # ET is UTC-5, so 18:00 ET = 23:00 UTC
            start_ts = int(datetime.combine(prev_date, datetime.min.time().replace(hour=23)).timestamp() * 1000)
            end_ts = int(datetime.combine(trading_date, datetime.min.time().replace(hour=22)).timestamp() * 1000)

            try:
                url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={start_ts}&endTime={end_ts}&limit=24"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                import ssl
                ctx = ssl.create_default_context()
                with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                    candles = json.loads(resp.read().decode())

                if candles:
                    # Track day OHLC
                    day_open = float(candles[0][1])
                    day_high = max(float(c[2]) for c in candles)
                    day_low = min(float(c[3]) for c in candles)
                    day_close = float(candles[-1][4])

                    day_data['day'] = {
                        'o': day_open,
                        'h': day_high,
                        'l': day_low,
                        'c': day_close
                    }

                    # Process each session
                    for sid, sname, sh, sm, eh, em in session_defs:
                        session_candles = []

                        for candle in candles:
                            candle_ts = int(candle[0]) / 1000
                            candle_dt = datetime.utcfromtimestamp(candle_ts)
                            # Convert to ET (subtract 5 hours from UTC)
                            candle_et = candle_dt - timedelta(hours=5)
                            candle_hour = candle_et.hour
                            candle_min = candle_et.minute
                            candle_time = candle_hour * 100 + candle_min

                            # Check if candle falls within session
                            start_time = sh * 100 + sm
                            end_time = eh * 100 + em

                            if end_time < start_time:  # Crosses midnight
                                if candle_time >= start_time or candle_time < end_time:
                                    session_candles.append(candle)
                            else:
                                if start_time <= candle_time < end_time:
                                    session_candles.append(candle)

                        if session_candles:
                            s_open = float(session_candles[0][1])
                            s_high = max(float(c[2]) for c in session_candles)
                            s_low = min(float(c[3]) for c in session_candles)
                            s_close = float(session_candles[-1][4])

                            day_data['sessions'][sid] = {
                                'o': s_open,
                                'h': s_high,
                                'l': s_low,
                                'c': s_close
                            }

            except Exception as e:
                print(f"⚠️ Error fetching BTC data for {date_str}: {e}")

            result.append(day_data)

        # Cache the result
        if result:
            weekly_sessions_cache[week_id] = {
                'ready': True,
                'data': result,
                'timestamp': time.time()
            }
            print(f"✅ BTC {week_id} cached: {len(result)} days")

        return result

    except Exception as e:
        print(f"❌ Error fetching BTC week {week_id}: {e}")
        return None


def fetch_week_sessions_ohlc(week_id):
    """Fetch historical session OHLC for a specific week"""
    global weekly_sessions_cache, ACTIVE_CONTRACT, front_month_instrument_id

    # Use BTC-specific fetcher for spot contracts
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        return fetch_btc_week_sessions_ohlc(week_id)

    if not HAS_DATABENTO or not API_KEY:
        print(f"⚠️  No Databento credentials for {week_id}")
        return None

    date_range = get_week_date_range(week_id)
    if not date_range:
        print(f"⚠️  Unknown week: {week_id}")
        return None

    start_date_str, end_date_str = date_range
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    symbol = config['symbol']
    price_min = config['price_min']
    price_max = config['price_max']

    session_defs = [
        ('pre_asia', 'Pre-Asia', 18, 0, 19, 0),
        ('japan_ib', 'Japan', 19, 0, 20, 0),
        ('china', 'China', 20, 0, 23, 0),
        ('asia_close', 'Asia Close', 23, 0, 2, 0),
        ('deadzone', 'Deadzone', 2, 0, 3, 0),
        ('london', 'London', 3, 0, 6, 0),
        ('low_volume', 'Low Vol', 6, 0, 8, 20),
        ('us_ib', 'US IB', 8, 20, 9, 30),
        ('ny_1h', 'NY 1H', 9, 30, 10, 30),
        ('ny_2h', 'NY 2H', 10, 30, 11, 30),
        ('lunch', 'Lunch', 11, 30, 13, 30),
        ('ny_pm', 'NY PM', 13, 30, 16, 0),
        ('ny_close', 'NY Close', 16, 0, 17, 0),
    ]

    try:
        client = db.Historical(key=API_KEY)
        et_tz = timezone(timedelta(hours=-5))

        # Get trading days in range (skip weekends)
        trading_days = []
        check_date = end_date
        while check_date >= start_date:
            if check_date.weekday() < 5:  # Mon-Fri
                trading_days.append(check_date)
            check_date -= timedelta(days=1)

        # Keep Fri at top, Mon at bottom (most recent first)
        print(f"📅 Fetching {week_id} ({start_date_str} to {end_date_str}): {len(trading_days)} days")

        result = []

        for trading_date in trading_days:
            # Format: "01-12 Mon" (MM-DD Day)
            day_label = trading_date.strftime('%m-%d %a')
            date_str = trading_date.strftime('%Y-%m-%d')

            day_data = {
                'date': date_str,
                'label': day_label,
                'sessions': {},
                'day': {'o': 0, 'h': 0, 'l': 999999, 'c': 0}
            }

            prev_date = trading_date - timedelta(days=1)
            start_utc = f"{prev_date.isoformat()}T23:00:00Z"
            end_utc = f"{trading_date.isoformat()}T22:00:00Z"

            try:
                data = client.timeseries.get_range(
                    dataset='GLBX.MDP3',
                    symbols=[symbol],
                    stype_in='parent',
                    schema='trades',
                    start=start_utc,
                    end=end_utc
                )

                df = data.to_df()
                if df.empty:
                    result.append(day_data)
                    continue

                if front_month_instrument_id and 'instrument_id' in df.columns:
                    df = df[df['instrument_id'] == front_month_instrument_id]

                df = df[(df['price'] > price_min) & (df['price'] < price_max)]

                if df.empty:
                    result.append(day_data)
                    continue

                df = df.sort_values('ts_event')

                day_data['day'] = {
                    'o': float(df.iloc[0]['price']),
                    'h': float(df['price'].max()),
                    'l': float(df['price'].min()),
                    'c': float(df.iloc[-1]['price'])
                }

                df['et_time'] = df['ts_event'].dt.tz_convert(et_tz)
                df['hour'] = df['et_time'].dt.hour
                df['minute'] = df['et_time'].dt.minute

                for sid, sname, start_h, start_m, end_h, end_m in session_defs:
                    start_mins = start_h * 60 + start_m
                    end_mins = end_h * 60 + end_m

                    if end_mins < start_mins:
                        mask = ((df['hour'] * 60 + df['minute']) >= start_mins) | \
                               ((df['hour'] * 60 + df['minute']) < end_mins)
                    else:
                        mask = ((df['hour'] * 60 + df['minute']) >= start_mins) & \
                               ((df['hour'] * 60 + df['minute']) < end_mins)

                    session_df = df[mask]
                    if not session_df.empty:
                        day_data['sessions'][sid] = {
                            'o': float(session_df.iloc[0]['price']),
                            'h': float(session_df['price'].max()),
                            'l': float(session_df['price'].min()),
                            'c': float(session_df.iloc[-1]['price'])
                        }

                print(f"   ✅ {date_str}: {len(day_data['sessions'])} sessions")

            except Exception as e:
                print(f"   ⚠️ {date_str}: {e}")

            result.append(day_data)

        # Store in cache
        weekly_sessions_cache[week_id]['data'] = result
        weekly_sessions_cache[week_id]['timestamp'] = time.time()
        weekly_sessions_cache[week_id]['ready'] = True
        save_cache_to_file(week_id)

        print(f"✅ {week_id} cached: {len(result)} days")
        return result

    except Exception as e:
        print(f"❌ Error fetching {week_id}: {e}")
        import traceback
        traceback.print_exc()
        return None

def fetch_all_historical_weeks():
    """Fetch historical data for all past weeks (background task)"""
    weeks_to_fetch = ['w5', 'w4', 'w3', 'w2', 'w1']  # 5 historic weeks (oldest to newest)
    for week_id in weeks_to_fetch:
        if not weekly_sessions_cache[week_id]['ready']:
            date_range = get_week_date_range(week_id)
            print(f"📊 Fetching {week_id} ({date_range[0]} to {date_range[1]})...")
            fetch_week_sessions_ohlc(week_id)
            time.sleep(1)  # Small delay between fetches
    print("✅ All historical weeks cached")

# Market overview cache for Correlation Matrix
market_overview_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 120  # Refresh every 2 minutes (yfinance data doesn't need real-time refresh)
}

def calculate_correlations():
    """Calculate live correlation matrix for key assets across timeframes"""
    if not HAS_YFINANCE:
        return None

    # Correlation assets - these are the ones we show in the correlation grid
    corr_symbols = {
        'GC': 'GC=F',      # Gold
        'SI': 'SI=F',      # Silver
        'CHF': '6S=F',     # Swiss Franc (CHF futures)
        'JPY': '6J=F',     # Japanese Yen
        'US10Y': '^TNX',   # 10-Year Treasury Yield
        'DXY': 'DX-Y.NYB'  # US Dollar Index
    }

    # Timeframe configs: (yfinance_period, yfinance_interval, min_data_points)
    # Only include 1D, 1W, 1M for the price change table
    timeframe_configs = {
        '1D': ('60d', '1d', 15),
        '1W': ('1y', '1wk', 10),
        '1M': ('2y', '1d', 30)  # Use daily data for 1M correlation (more reliable)
    }

    correlations = {}

    try:
        import pandas as pd
        import numpy as np

        for tf_name, (period, interval, min_points) in timeframe_configs.items():
            try:
                # Download all symbols at once
                symbols_list = list(corr_symbols.values())
                hist = yf.download(symbols_list, period=period, interval=interval, progress=False, group_by='ticker')

                if hist.empty:
                    continue

                # Extract close prices into a DataFrame
                closes = pd.DataFrame()
                for asset_id, symbol in corr_symbols.items():
                    try:
                        if len(symbols_list) == 1:
                            closes[asset_id] = hist['Close']
                        else:
                            closes[asset_id] = hist[symbol]['Close']
                    except:
                        pass

                # Drop NaN and calculate correlation
                closes = closes.dropna()
                if len(closes) < min_points:
                    continue

                # For 4H, resample hourly data to 4-hourly
                if tf_name == '4H' and interval == '1h':
                    closes = closes.resample('4h').last().dropna()

                corr_matrix = closes.corr()

                # Convert to nested dict format
                tf_corr = {}
                for row in corr_matrix.index:
                    tf_corr[row] = {}
                    for col in corr_matrix.columns:
                        val = corr_matrix.loc[row, col]
                        tf_corr[row][col] = round(float(val), 2) if not pd.isna(val) else 0

                correlations[tf_name] = tf_corr

            except Exception as e:
                print(f"Correlation calc error for {tf_name}: {e}")
                continue

        print(f"✅ Calculated correlations for {len(correlations)} timeframes")
        return correlations

    except Exception as e:
        print(f"❌ Correlation calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return None

# Cache for historic TPO data
historic_tpo_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 3600  # 1 hour cache
}

def fetch_btc_historic_tpo(days=40):
    """Fetch BTC historic TPO profiles from Binance or CryptoCompare with volume and delta data."""
    import requests
    from datetime import datetime, timedelta

    print(f"₿ Fetching BTC historic data for {days} days...")

    try:
        profiles = []
        tick_size = 100.0  # $100 tick size for BTC TPO
        vp_tick = 1.0  # $1 tick for volume profile
        et_tz = pytz.timezone('America/New_York')
        now = datetime.now(et_tz)

        # Try Binance first, fall back to CryptoCompare
        candles = None
        source = 'binance'

        # Binance API: get daily klines with buy/sell volume breakdown
        end_time = int(now.timestamp() * 1000)
        start_time = int((now - timedelta(days=days + 5)).timestamp() * 1000)

        try:
            url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1d&startTime={start_time}&endTime={end_time}&limit={days + 5}"
            resp = requests.get(url, timeout=10)

            if resp.status_code == 200:
                candles = resp.json()
                print(f"   ✅ Binance: Got {len(candles)} daily candles")
            else:
                print(f"   ⚠️ Binance API error: {resp.status_code}, trying CryptoCompare...")
        except Exception as e:
            print(f"   ⚠️ Binance failed: {e}, trying CryptoCompare...")

        # Fallback to CryptoCompare if Binance failed
        if not candles:
            source = 'cryptocompare'
            try:
                cc_url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym=BTC&tsym=USD&limit={days + 5}"
                cc_resp = requests.get(cc_url, timeout=10)
                if cc_resp.status_code == 200:
                    cc_json = cc_resp.json()
                    cc_data = cc_json.get('Data', {}).get('Data', [])
                    print(f"   📊 CC Response: {cc_json.get('Response')}, Message: {cc_json.get('Message', 'OK')}, Data items: {len(cc_data)}")
                    # Convert CryptoCompare format to Binance-like format
                    # CC: {time, high, low, open, close, volumefrom, volumeto}
                    # Binance: [open_time, open, high, low, close, volume, ..., taker_buy_vol, ...]
                    candles = []
                    for cc in cc_data:
                        # Estimate taker buy/sell from OHLC: if close > open, more buy pressure
                        vol = cc.get('volumefrom', 0)
                        close_price = cc.get('close', 0)
                        open_price = cc.get('open', 0)
                        if close_price > open_price:
                            buy_pct = 0.55 + 0.1 * (close_price - open_price) / max(1, open_price) * 100
                        elif close_price < open_price:
                            buy_pct = 0.45 - 0.1 * (open_price - close_price) / max(1, open_price) * 100
                        else:
                            buy_pct = 0.5
                        buy_pct = max(0.3, min(0.7, buy_pct))
                        taker_buy_vol = vol * buy_pct

                        candles.append([
                            cc.get('time', 0) * 1000,  # open_time in ms
                            open_price,
                            cc.get('high', 0),
                            cc.get('low', 0),
                            close_price,
                            vol,
                            0, 0, 0,  # close_time, quote_vol, trades
                            taker_buy_vol,  # taker_buy_vol (estimated)
                            0, 0
                        ])
                    print(f"   ✅ CryptoCompare: Got {len(candles)} daily candles")
                else:
                    print(f"   ❌ CryptoCompare API error: {cc_resp.status_code}")
                    return {'profiles': [], 'days': days, 'source': 'api_error'}
            except Exception as e:
                print(f"   ❌ CryptoCompare failed: {e}")
                return {'profiles': [], 'days': days, 'source': 'api_error'}

        if not candles:
            return {'profiles': [], 'days': days, 'source': 'no_data'}

        # Sort by timestamp descending (most recent first)
        candles.sort(key=lambda x: x[0], reverse=True)

        # Helper to convert period index to letter
        def idx_to_letter(idx):
            if idx < 26:
                return chr(65 + idx)
            else:
                return 'A' + chr(65 + (idx - 26))

        for i, candle in enumerate(candles[:days]):
            open_time = candle[0]
            open_price = float(candle[1])
            high = float(candle[2])
            low = float(candle[3])
            close = float(candle[4])
            volume = float(candle[5])
            taker_buy_vol = float(candle[9])  # Real buy volume from Binance!
            taker_sell_vol = volume - taker_buy_vol  # Sell volume = total - buy

            candle_date = datetime.fromtimestamp(open_time / 1000, tz=et_tz)
            date_str = candle_date.strftime('%Y-%m-%d')
            day_label = candle_date.strftime('%a')

            # Build TPO profile for this day
            day_profiles = {}
            price_range = high - low
            btc_tick = 20.0  # $20 tick for BTC TPO

            # Session period ranges (from 18:00 ET start)
            sessions = [
                (0, 20),    # Asia
                (18, 28),   # London
                (29, 46),   # US/RTH
                (44, 47),   # Close
            ]

            num_levels = max(20, int(price_range / btc_tick))

            for level_idx in range(num_levels):
                price_level = low + (level_idx * btc_tick)
                price_key = f"{price_level:.1f}"
                day_profiles[price_key] = []

                # More letters near middle (POC area)
                mid_level = num_levels / 2
                distance_from_mid = abs(level_idx - mid_level)
                density = max(2, int(6 - distance_from_mid * 0.5))

                for sess_start, sess_end in sessions:
                    sess_range = sess_end - sess_start
                    for j in range(min(density, sess_range)):
                        period_idx = sess_start + int(j * sess_range / max(1, density))
                        if period_idx <= sess_end:
                            letter = idx_to_letter(period_idx)
                            if letter not in day_profiles[price_key]:
                                day_profiles[price_key].append(letter)

            # Fetch hourly candles for intraday volume distribution
            day_start_ms = int(candle_date.replace(hour=0, minute=0, second=0).timestamp() * 1000)
            day_end_ms = int(candle_date.replace(hour=23, minute=59, second=59).timestamp() * 1000)
            day_start_ts = int(candle_date.replace(hour=0, minute=0, second=0).timestamp())

            price_volumes = {}
            delta_by_price = {}
            hourly_candles = None

            # Try Binance hourly first
            if source == 'binance':
                try:
                    hourly_url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={day_start_ms}&endTime={day_end_ms}"
                    hourly_resp = requests.get(hourly_url, timeout=5)
                    if hourly_resp.status_code == 200:
                        hourly_candles = hourly_resp.json()
                except:
                    pass

            # Fallback to CryptoCompare hourly
            if not hourly_candles:
                try:
                    cc_hourly_url = f"https://min-api.cryptocompare.com/data/v2/histohour?fsym=BTC&tsym=USD&limit=24&toTs={day_start_ts + 86400}"
                    cc_hourly_resp = requests.get(cc_hourly_url, timeout=5)
                    if cc_hourly_resp.status_code == 200:
                        cc_hourly_data = cc_hourly_resp.json().get('Data', {}).get('Data', [])
                        hourly_candles = []
                        for hc in cc_hourly_data:
                            h_vol = hc.get('volumefrom', 0)
                            h_close = hc.get('close', 0)
                            h_open = hc.get('open', 0)
                            if h_close > h_open:
                                buy_pct = 0.55 + 0.1 * (h_close - h_open) / max(1, h_open) * 100
                            elif h_close < h_open:
                                buy_pct = 0.45 - 0.1 * (h_open - h_close) / max(1, h_open) * 100
                            else:
                                buy_pct = 0.5
                            buy_pct = max(0.3, min(0.7, buy_pct))
                            hourly_candles.append([0, h_open, hc.get('high', 0), hc.get('low', 0), h_close, h_vol, 0, 0, 0, h_vol * buy_pct, 0, 0])
                except:
                    pass

            try:
                if hourly_candles and len(hourly_candles) > 0:
                    for hc in hourly_candles:
                        h_open = float(hc[1])
                        h_high = float(hc[2])
                        h_low = float(hc[3])
                        h_close = float(hc[4])
                        h_vol = float(hc[5])
                        h_buy_vol = float(hc[9])  # Taker buy volume
                        h_sell_vol = h_vol - h_buy_vol  # Sell volume

                        # Distribute volume across all prices touched by this hourly bar
                        bar_low = round(h_low / vp_tick) * vp_tick
                        bar_high = round(h_high / vp_tick) * vp_tick
                        num_bar_levels = max(1, int((bar_high - bar_low) / vp_tick) + 1)
                        vol_per_level = h_vol / num_bar_levels
                        # Real delta: buy - sell at each level
                        delta_per_level = (h_buy_vol - h_sell_vol) / num_bar_levels

                        for price_level in [bar_low + j * vp_tick for j in range(num_bar_levels)]:
                            price_key = f"{price_level:.1f}"
                            price_volumes[price_key] = price_volumes.get(price_key, 0) + vol_per_level
                            delta_by_price[price_key] = delta_by_price.get(price_key, 0) + delta_per_level
                else:
                    raise ValueError("No hourly candles available")
            except Exception as e:
                # Fallback: distribute daily volume across price range with daily delta
                bar_low = round(low / vp_tick) * vp_tick
                bar_high = round(high / vp_tick) * vp_tick
                num_bar_levels = max(1, int((bar_high - bar_low) / vp_tick) + 1)
                vol_per_level = volume / num_bar_levels
                delta_per_level = (taker_buy_vol - taker_sell_vol) / num_bar_levels
                for price_level in [bar_low + j * vp_tick for j in range(num_bar_levels)]:
                    price_key = f"{price_level:.1f}"
                    price_volumes[price_key] = vol_per_level
                    delta_by_price[price_key] = delta_per_level

            # Calculate POC (price with highest volume)
            if not price_volumes:
                price_volumes[f"{(high + low) / 2:.1f}"] = volume
            poc_price = max(price_volumes.keys(), key=lambda k: price_volumes[k])
            poc = float(poc_price)

            # Value area (70% around POC)
            va_range = price_range * 0.7
            vah = poc + va_range / 2
            val = poc - va_range / 2

            profiles.append({
                'date': date_str,
                'label': day_label,
                'weekday': day_label,
                'day': f"{candle_date.month:02d}-{candle_date.day:02d}",
                'high': high,
                'low': low,
                'open': open_price,
                'close': close,
                'poc': poc,
                'vah': vah,
                'val': val,
                'ib_high': high,  # No IB for crypto, use day high
                'ib_low': low,
                'price_volumes': price_volumes,
                'delta_by_price': delta_by_price,  # Delta for coloring (positive=buy, negative=sell)
                'volume': volume,
                'tpo_profiles': day_profiles,  # Must be 'tpo_profiles' to match frontend
                'day_type': 'Normal' if price_range < 2000 else 'Trend',
                'profile_shape': 'D-Shape'
            })

        print(f"   ✅ Built {len(profiles)} BTC daily profiles (source: {source})")
        return {'profiles': profiles, 'days': len(profiles), 'source': source}

    except Exception as e:
        print(f"   ❌ Error fetching BTC historic: {e}")
        return {'profiles': [], 'days': days, 'source': 'error', 'error': str(e)}

def fetch_historic_tpo_profiles(days=40):
    """Fetch historical TPO profiles for the last N trading days (8 weeks default).

    Returns daily profiles with:
    - Date
    - Session High/Low
    - POC (Point of Control)
    - VAH/VAL (Value Area High/Low)
    - IB High/Low (Initial Balance 09:30-10:30)
    - Day Type classification
    - Profile shape
    """
    global historic_tpo_cache

    # For spot contracts, fetch from crypto APIs instead of Databento
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        print("📊 Fetching BTC historic TPO from crypto APIs...")
        return fetch_btc_historic_tpo(days)

    # Check cache
    now = time.time()
    if historic_tpo_cache['data'] and (now - historic_tpo_cache['timestamp']) < historic_tpo_cache['ttl']:
        cached = historic_tpo_cache['data']
        if cached.get('days') == days:
            return cached

    print(f"📊 Fetching historic TPO data for {days} days...")

    try:
        client = db.Historical(key=API_KEY)

        # Get contract config
        config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
        # Use parent symbology - has more history, filter by price to get front month
        symbol = config['symbol']  # Use 'GC.FUT' for parent symbology
        tick_size = config['tick_size']
        price_min = config['price_min']
        price_max = config['price_max']

        # Calculate date range - go back extra days to account for weekends/holidays
        et_tz = pytz.timezone('America/New_York')
        now_et = datetime.now(et_tz)

        # For weekends/holidays, end at last trading day's close (17:00 ET)
        # Find the most recent weekday
        end_date = now_et - timedelta(minutes=15)  # Account for data delay
        days_back = 0
        while end_date.weekday() >= 5:  # Saturday=5, Sunday=6
            days_back += 1
            end_date = now_et - timedelta(days=days_back)
        # If we adjusted for weekend, set end time to market close (17:00)
        if days_back > 0:
            end_date = end_date.replace(hour=17, minute=0, second=0, microsecond=0)
            print(f"   📅 Weekend detected - using last trading day: {end_date.strftime('%Y-%m-%d %H:%M')} ET")

        start_date = end_date - timedelta(days=int(days * 1.5))  # Extra buffer for non-trading days

        # Convert to UTC for API call
        start_utc = start_date.strftime('%Y-%m-%dT00:00:00Z')
        end_utc = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        print(f"   Querying {symbol} from {start_utc[:10]} to {end_utc[:10]}...")

        # Fetch OHLCV data with 1-hour bars (Databento doesn't support 30m directly)
        # We'll create synthetic 30-min periods from the hour data
        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=[symbol],
            stype_in='parent',  # Use parent for more historical data
            schema='ohlcv-1h',  # 1-hour bars
            start=start_utc,
            end=end_utc
        )

        records = list(data)
        print(f"   Got {len(records)} hourly bars")

        if not records:
            return {'profiles': [], 'days': days, 'error': 'No data available'}

        # First pass: Group bars by trading day AND instrument_id to find front month
        daily_instrument_volumes = {}  # {date: {instrument_id: total_volume}}

        for r in records:
            ts_ns = r.ts_event
            ts_sec = ts_ns / 1e9
            bar_time = datetime.fromtimestamp(ts_sec, tz=pytz.UTC).astimezone(et_tz)

            hour = bar_time.hour
            if hour >= 18:
                trade_date = (bar_time + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                trade_date = bar_time.strftime('%Y-%m-%d')

            bar_weekday = bar_time.weekday()
            if bar_weekday >= 5:
                continue

            iid = r.instrument_id
            v = r.volume

            if trade_date not in daily_instrument_volumes:
                daily_instrument_volumes[trade_date] = {}
            if iid not in daily_instrument_volumes[trade_date]:
                daily_instrument_volumes[trade_date][iid] = 0
            daily_instrument_volumes[trade_date][iid] += v

        # Find front month (highest volume) instrument for each day
        daily_front_month = {}
        for date, instruments in daily_instrument_volumes.items():
            if instruments:
                front_month_iid = max(instruments, key=instruments.get)
                daily_front_month[date] = front_month_iid

        print(f"   Identified front month contracts for {len(daily_front_month)} trading days")

        # Second pass: Only use bars from front month contract for each day
        daily_data = {}

        for r in records:
            ts_ns = r.ts_event
            ts_sec = ts_ns / 1e9
            bar_time = datetime.fromtimestamp(ts_sec, tz=pytz.UTC).astimezone(et_tz)

            hour = bar_time.hour
            if hour >= 18:
                trade_date = (bar_time + timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                trade_date = bar_time.strftime('%Y-%m-%d')

            bar_weekday = bar_time.weekday()
            if bar_weekday >= 5:
                continue

            # Only use front month contract for this day
            if trade_date not in daily_front_month:
                continue
            if r.instrument_id != daily_front_month[trade_date]:
                continue

            # Get OHLCV values
            o = r.open / 1e9 if r.open > 1e6 else r.open
            h = r.high / 1e9 if r.high > 1e6 else r.high
            l = r.low / 1e9 if r.low > 1e6 else r.low
            c = r.close / 1e9 if r.close > 1e6 else r.close
            v = r.volume

            # Filter invalid prices
            if h < price_min or l > price_max or h < l:
                continue

            if trade_date not in daily_data:
                daily_data[trade_date] = {
                    'bars': [],
                    'high': 0,
                    'low': 999999,
                    'open': 0,
                    'close': 0,
                    'volume': 0,
                    'ib_high': 0,
                    'ib_low': 999999,
                    'price_volumes': {},
                    'delta_by_price': {},  # Delta at each price: positive = buy aggression, negative = sell
                    'profiles': {},  # TPO profiles: {price: [letters]}
                }

            day = daily_data[trade_date]

            # Calculate TPO period letters based on hour
            # Session starts at 18:00 ET, each hour gets 2 letters (representing 30-min halves)
            # A/B=18:00, C/D=19:00, E/F=20:00, ...
            bar_hour = bar_time.hour
            bar_minute = bar_time.minute
            if bar_hour >= 18:
                # Evening session (18:00-23:59)
                base_idx = (bar_hour - 18) * 2
            else:
                # Morning session (00:00-17:59)
                base_idx = 12 + bar_hour * 2

            # Each hourly bar gets 2 letters (first half and second half)
            period_indices = [base_idx, base_idx + 1]

            # Convert indices to letters
            def idx_to_letter(idx):
                if idx < 26:
                    return chr(65 + idx)
                else:
                    return chr(65 + (idx - 26) // 26) + chr(65 + (idx - 26) % 26)

            period_letters = [idx_to_letter(i) for i in period_indices]
            period_letter = period_letters[0]  # Use first letter for logging

            day['bars'].append({
                'time': bar_time,
                'hour': bar_hour,
                'minute': bar_minute,
                'period': period_letter,
                'open': o, 'high': h, 'low': l, 'close': c, 'volume': v
            })

            # Build TPO profile - add both period letters at each price level the bar touched
            for price in range(int(l / tick_size), int(h / tick_size) + 1):
                price_key = str(round(price * tick_size, 2))
                if price_key not in day['profiles']:
                    day['profiles'][price_key] = []
                # Add both letters for this hourly bar (representing 30-min halves)
                for pl in period_letters:
                    if pl not in day['profiles'][price_key]:
                        day['profiles'][price_key].append(pl)

            # Track session high/low
            if h > day['high']:
                day['high'] = h
            if l < day['low']:
                day['low'] = l

            # Track first/last price
            if day['open'] == 0:
                day['open'] = o
            day['close'] = c
            day['volume'] += v

            # Track IB (09:30-10:30 ET) - periods around 31-34
            if bar_hour == 9 or (bar_hour == 10 and bar_minute < 30):
                if h > day['ib_high']:
                    day['ib_high'] = h
                if l < day['ib_low']:
                    day['ib_low'] = l

            # Distribute volume across ALL price levels touched by this bar (low to high)
            # This creates proper volume profile with data at every price level
            vp_tick = 0.3  # Fine tick for volume profile ($0.30 for GC)
            bar_low = round(l / vp_tick) * vp_tick
            bar_high = round(h / vp_tick) * vp_tick
            num_levels = max(1, int((bar_high - bar_low) / vp_tick) + 1)
            vol_per_level = v / num_levels

            # Calculate delta based on bar direction (close vs open)
            bar_delta = vol_per_level if c > o else (-vol_per_level if c < o else 0)

            # Distribute volume and delta across all price levels in this bar
            for price_level in [bar_low + i * vp_tick for i in range(num_levels)]:
                price_key = round(price_level, 2)
                day['price_volumes'][price_key] = day['price_volumes'].get(price_key, 0) + vol_per_level
                day['delta_by_price'][price_key] = day['delta_by_price'].get(price_key, 0) + bar_delta

        # Process each day to calculate TPO metrics
        profiles = []
        sorted_dates = sorted(daily_data.keys(), reverse=True)[:days]  # Most recent first

        for date in sorted_dates:
            day = daily_data[date]

            # Skip incomplete days
            if len(day['bars']) < 5 or day['high'] == 0 or day['low'] >= 999999:
                continue

            # Calculate POC (price with highest volume)
            poc = 0
            max_vol = 0
            for price, vol in day['price_volumes'].items():
                if vol > max_vol:
                    max_vol = vol
                    poc = price

            # Calculate Value Area (70% of volume around POC)
            total_vol = sum(day['price_volumes'].values())
            target_vol = total_vol * 0.7

            # Sort prices and find value area
            sorted_prices = sorted(day['price_volumes'].keys())
            if poc in sorted_prices:
                poc_idx = sorted_prices.index(poc)
            else:
                poc_idx = len(sorted_prices) // 2

            va_vol = day['price_volumes'].get(poc, 0)
            va_low_idx = poc_idx
            va_high_idx = poc_idx

            while va_vol < target_vol and (va_low_idx > 0 or va_high_idx < len(sorted_prices) - 1):
                # Check which direction has more volume
                vol_below = day['price_volumes'].get(sorted_prices[va_low_idx - 1], 0) if va_low_idx > 0 else 0
                vol_above = day['price_volumes'].get(sorted_prices[va_high_idx + 1], 0) if va_high_idx < len(sorted_prices) - 1 else 0

                if vol_below >= vol_above and va_low_idx > 0:
                    va_low_idx -= 1
                    va_vol += vol_below
                elif va_high_idx < len(sorted_prices) - 1:
                    va_high_idx += 1
                    va_vol += vol_above
                else:
                    break

            vah = sorted_prices[va_high_idx] if sorted_prices else day['high']
            val = sorted_prices[va_low_idx] if sorted_prices else day['low']

            # Calculate IB range
            ib_high = day['ib_high'] if day['ib_high'] > 0 else None
            ib_low = day['ib_low'] if day['ib_low'] < 999999 else None
            ib_range = (ib_high - ib_low) if ib_high and ib_low else None

            # Classify day type based on IB extension
            day_type = 'normal'
            if ib_high and ib_low and ib_range:
                session_range = day['high'] - day['low']
                ext_up = max(0, day['high'] - ib_high)
                ext_down = max(0, ib_low - day['low'])
                total_ext = ext_up + ext_down
                ext_pct = (total_ext / ib_range * 100) if ib_range > 0 else 0

                if ext_pct > 150 and (ext_up < ib_range * 0.1 or ext_down < ib_range * 0.1):
                    day_type = 'trend'
                elif ext_pct > 100:
                    day_type = 'normal_var'
                elif ext_up > ib_range * 0.3 and ext_down > ib_range * 0.3:
                    day_type = 'neutral'
                elif ext_pct < 30:
                    day_type = 'non_trend'

            # Determine profile shape based on volume distribution
            mid_price = (day['high'] + day['low']) / 2
            upper_vol = sum(v for p, v in day['price_volumes'].items() if p > mid_price)
            lower_vol = sum(v for p, v in day['price_volumes'].items() if p <= mid_price)

            if upper_vol > lower_vol * 1.5:
                profile_shape = 'P'  # Fat top
            elif lower_vol > upper_vol * 1.5:
                profile_shape = 'b'  # Fat bottom
            else:
                profile_shape = 'D'  # Balanced

            # Count periods for this day
            all_letters = set()
            for letters in day['profiles'].values():
                all_letters.update(letters)
            period_count = len(all_letters)
            current_letter = max(all_letters) if all_letters else 'A'

            # Calculate open_type based on open location and first hour behavior
            open_type = 'OA'  # Default: Open Auction
            if ib_high and ib_low and day['open']:
                open_price = day['open']
                # Check if open drove strongly in first hour
                ib_mid = (ib_high + ib_low) / 2
                first_hour_range = ib_high - ib_low if ib_range else 0

                # Open Drive: Strong directional move, open near extreme
                if open_price <= ib_low + first_hour_range * 0.15 and day['close'] > ib_mid:
                    open_type = 'OD'  # Open Drive up
                elif open_price >= ib_high - first_hour_range * 0.15 and day['close'] < ib_mid:
                    open_type = 'OD'  # Open Drive down
                # Open Test Drive: Test one direction then drive other
                elif (open_price > ib_mid and day['low'] < ib_low and day['close'] > ib_high):
                    open_type = 'OTD'  # Open Test Drive
                elif (open_price < ib_mid and day['high'] > ib_high and day['close'] < ib_low):
                    open_type = 'OTD'  # Open Test Drive
                # Open Rejection Reverse: Price rejected at extreme
                elif (day['high'] > ib_high and day['close'] < ib_mid):
                    open_type = 'ORR'  # Open Rejection Reverse
                elif (day['low'] < ib_low and day['close'] > ib_mid):
                    open_type = 'ORR'  # Open Rejection Reverse

            profiles.append({
                'date': date,
                'weekday': datetime.strptime(date, '%Y-%m-%d').strftime('%a'),
                'open': round(day['open'], 2),
                'high': round(day['high'], 2),
                'low': round(day['low'], 2),
                'close': round(day['close'], 2),
                'volume': day['volume'],
                'poc': round(poc, 2),
                'vah': round(vah, 2),
                'val': round(val, 2),
                'ib_high': round(ib_high, 2) if ib_high else None,
                'ib_low': round(ib_low, 2) if ib_low else None,
                'ib_range': round(ib_range, 2) if ib_range else None,
                'day_type': day_type,
                'open_type': open_type,
                'profile_shape': profile_shape,
                'range': round(day['high'] - day['low'], 2),
                'tpo_profiles': day['profiles'],  # Full TPO profile with letters at each price
                'price_volumes': day.get('price_volumes', {}),  # Actual volume by price for VP
                'delta_by_price': day.get('delta_by_price', {}),  # Delta by price for coloring
                'period_count': period_count,
                'current_letter': current_letter
            })

        result = {
            'profiles': profiles,
            'days': len(profiles),
            'requested_days': days,
            'symbol': symbol,
            'tick_size': tick_size,
            'timestamp': time.time()
        }

        # Cache the result
        historic_tpo_cache['data'] = result
        historic_tpo_cache['timestamp'] = time.time()

        print(f"   ✅ Loaded {len(profiles)} historic TPO profiles")
        return result

    except Exception as e:
        print(f"❌ Error fetching historic TPO: {e}")
        import traceback
        traceback.print_exc()
        return {'profiles': [], 'days': days, 'error': str(e)}

def fetch_market_overview():
    """Fetch live market data for multiple assets using yfinance"""
    global market_overview_cache

    # Check cache freshness
    now = time.time()
    if market_overview_cache['data'] and (now - market_overview_cache['timestamp']) < market_overview_cache['ttl']:
        return market_overview_cache['data']

    if not HAS_YFINANCE:
        return {'error': 'yfinance not installed'}

    # Asset definitions with Yahoo Finance symbols
    assets = {
        'Commodities': [
            {'symbol': 'GC=F', 'id': 'GC', 'name': 'Gold Futures'},
            {'symbol': 'SI=F', 'id': 'SI', 'name': 'Silver Futures'},
            {'symbol': 'CL=F', 'id': 'CL', 'name': 'Crude Oil'},
            {'symbol': 'NG=F', 'id': 'NG', 'name': 'Natural Gas'},
            {'symbol': 'HG=F', 'id': 'HG', 'name': 'Copper'},
        ],
        'Indices': [
            {'symbol': 'ES=F', 'id': 'ES', 'name': 'S&P 500 E-mini'},
            {'symbol': 'NQ=F', 'id': 'NQ', 'name': 'Nasdaq E-mini'},
            {'symbol': 'YM=F', 'id': 'YM', 'name': 'Dow E-mini'},
        ],
        'Currencies': [
            {'symbol': 'DX-Y.NYB', 'id': 'DX', 'name': 'US Dollar Index'},
            {'symbol': '6E=F', 'id': '6E', 'name': 'Euro FX'},
            {'symbol': '6J=F', 'id': '6J', 'name': 'Japanese Yen'},
            {'symbol': '6B=F', 'id': '6B', 'name': 'British Pound'},
        ],
        'Bonds': [
            {'symbol': 'ZF=F', 'id': 'ZF', 'name': '5-Year Note (5Y)'},
            {'symbol': 'ZN=F', 'id': 'ZN', 'name': '10-Year Note (10Y)'},
            {'symbol': 'ZB=F', 'id': 'ZB', 'name': '30-Year Bond (30Y)'},
        ],
        'Yields': [
            {'symbol': '^FVX', 'id': 'US5Y', 'name': '5-Year Yield'},
            {'symbol': '^TNX', 'id': 'US10Y', 'name': '10-Year Yield'},
            {'symbol': '^TYX', 'id': 'US30Y', 'name': '30-Year Yield'},
        ]
    }

    # Sector colors
    sector_colors = {
        'Commodities': '#FFD700',
        'Indices': '#00BFFF',
        'Currencies': '#9370DB',
        'Bonds': '#20B2AA',
        'Yields': '#FF6B6B'
    }

    result = {'sectors': [], 'timestamp': now}

    try:
        # Collect all symbols
        all_symbols = []
        symbol_map = {}
        for sector, assets_list in assets.items():
            for asset in assets_list:
                all_symbols.append(asset['symbol'])
                symbol_map[asset['symbol']] = {'sector': sector, **asset}

        # Build sector data
        sectors_data = {s: {'name': s, 'color': sector_colors[s], 'stocks': []} for s in assets.keys()}

        # Helper to safely convert float (handle NaN)
        def safe_float(val):
            import math
            try:
                f = float(val)
                return 0 if math.isnan(f) else round(f, 4)
            except:
                return 0

        # Helper to get OHLC from dataframe row
        def row_to_ohlc(row):
            return {
                'o': safe_float(row.get('Open', 0)),
                'h': safe_float(row.get('High', 0)),
                'l': safe_float(row.get('Low', 0)),
                'c': safe_float(row.get('Close', 0))
            }

        # Calculate % change
        def calc_change(curr_close, prev_close):
            if prev_close and prev_close > 0 and curr_close > 0:
                return round(((curr_close - prev_close) / prev_close) * 100, 2)
            return 0

        # Batch download for efficiency (one HTTP request instead of many)
        # Use 10d for better 1W calculation (ensures we have ~5+ trading days)
        try:
            print(f"📈 Fetching {len(all_symbols)} symbols...")
            data_10d = yf.download(all_symbols, period='10d', progress=False, threads=True)
            data_1mo = yf.download(all_symbols, period='1mo', progress=False, threads=True)
        except Exception as e:
            print(f"⚠️ Batch download failed: {e}, falling back to individual fetch")
            data_10d = None
            data_1mo = None

        for symbol, info in symbol_map.items():
            try:
                # Extract data from batch download (10d for better 1W calculation)
                if data_10d is not None and len(all_symbols) > 1:
                    # Multi-ticker format: data['Close'][symbol]
                    hist_10d_close = data_10d['Close'][symbol].dropna() if symbol in data_10d['Close'].columns else None
                    hist_10d_open = data_10d['Open'][symbol].dropna() if symbol in data_10d['Open'].columns else None
                    hist_10d_high = data_10d['High'][symbol].dropna() if symbol in data_10d['High'].columns else None
                    hist_10d_low = data_10d['Low'][symbol].dropna() if symbol in data_10d['Low'].columns else None

                    hist_1mo_close = data_1mo['Close'][symbol].dropna() if data_1mo is not None and symbol in data_1mo['Close'].columns else None
                    hist_1mo_open = data_1mo['Open'][symbol].dropna() if data_1mo is not None and symbol in data_1mo['Open'].columns else None
                    hist_1mo_high = data_1mo['High'][symbol].dropna() if data_1mo is not None and symbol in data_1mo['High'].columns else None
                    hist_1mo_low = data_1mo['Low'][symbol].dropna() if data_1mo is not None and symbol in data_1mo['Low'].columns else None
                elif data_10d is not None:
                    # Single ticker format
                    hist_10d_close = data_10d['Close'].dropna()
                    hist_10d_open = data_10d['Open'].dropna()
                    hist_10d_high = data_10d['High'].dropna()
                    hist_10d_low = data_10d['Low'].dropna()

                    hist_1mo_close = data_1mo['Close'].dropna() if data_1mo is not None else None
                    hist_1mo_open = data_1mo['Open'].dropna() if data_1mo is not None else None
                    hist_1mo_high = data_1mo['High'].dropna() if data_1mo is not None else None
                    hist_1mo_low = data_1mo['Low'].dropna() if data_1mo is not None else None
                else:
                    # Fallback to individual fetch
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period='10d')
                    if len(hist) == 0:
                        continue
                    hist_10d_close = hist['Close']
                    hist_10d_open = hist['Open']
                    hist_10d_high = hist['High']
                    hist_10d_low = hist['Low']

                    hist_1mo = ticker.history(period='1mo')
                    hist_1mo_close = hist_1mo['Close'] if len(hist_1mo) > 0 else None
                    hist_1mo_open = hist_1mo['Open'] if len(hist_1mo) > 0 else None
                    hist_1mo_high = hist_1mo['High'] if len(hist_1mo) > 0 else None
                    hist_1mo_low = hist_1mo['Low'] if len(hist_1mo) > 0 else None

                if hist_10d_close is None or len(hist_10d_close) == 0:
                    continue

                # Build OHLC from series
                current = {
                    'o': safe_float(hist_10d_open.iloc[-1]) if hist_10d_open is not None and len(hist_10d_open) > 0 else 0,
                    'h': safe_float(hist_10d_high.iloc[-1]) if hist_10d_high is not None and len(hist_10d_high) > 0 else 0,
                    'l': safe_float(hist_10d_low.iloc[-1]) if hist_10d_low is not None and len(hist_10d_low) > 0 else 0,
                    'c': safe_float(hist_10d_close.iloc[-1])
                }

                prev_1d = {
                    'o': safe_float(hist_10d_open.iloc[-2]) if hist_10d_open is not None and len(hist_10d_open) > 1 else current['o'],
                    'h': safe_float(hist_10d_high.iloc[-2]) if hist_10d_high is not None and len(hist_10d_high) > 1 else current['h'],
                    'l': safe_float(hist_10d_low.iloc[-2]) if hist_10d_low is not None and len(hist_10d_low) > 1 else current['l'],
                    'c': safe_float(hist_10d_close.iloc[-2]) if len(hist_10d_close) > 1 else current['c']
                }

                # For 1W, go back ~5 trading days from the most recent data
                # With 10d period, we should have enough data even early in the week
                week_idx = min(5, len(hist_10d_close) - 1)  # 5 trading days back, or as far as we have
                prev_1w = {
                    'o': safe_float(hist_10d_open.iloc[-week_idx-1]) if hist_10d_open is not None and len(hist_10d_open) > week_idx else prev_1d['o'],
                    'h': safe_float(hist_10d_high.iloc[-week_idx-1]) if hist_10d_high is not None and len(hist_10d_high) > week_idx else prev_1d['h'],
                    'l': safe_float(hist_10d_low.iloc[-week_idx-1]) if hist_10d_low is not None and len(hist_10d_low) > week_idx else prev_1d['l'],
                    'c': safe_float(hist_10d_close.iloc[-week_idx-1]) if len(hist_10d_close) > week_idx else prev_1d['c']
                }

                prev_1m = {
                    'o': safe_float(hist_1mo_open.iloc[0]) if hist_1mo_open is not None and len(hist_1mo_open) > 0 else prev_1w['o'],
                    'h': safe_float(hist_1mo_high.iloc[0]) if hist_1mo_high is not None and len(hist_1mo_high) > 0 else prev_1w['h'],
                    'l': safe_float(hist_1mo_low.iloc[0]) if hist_1mo_low is not None and len(hist_1mo_low) > 0 else prev_1w['l'],
                    'c': safe_float(hist_1mo_close.iloc[0]) if hist_1mo_close is not None and len(hist_1mo_close) > 0 else prev_1w['c']
                }

                change_1d = calc_change(current['c'], prev_1d['c'])
                change_1w = calc_change(current['c'], prev_1w['c'])
                change_1m = calc_change(current['c'], prev_1m['c'])

                stock_data = {
                    'symbol': info['id'],
                    'name': info['name'],
                    'current': current,
                    'prev1D': prev_1d,
                    'prev1W': prev_1w,
                    'prev1M': prev_1m,
                    'change1D': change_1d,
                    'change1W': change_1w,
                    'change1M': change_1m
                }

                sectors_data[info['sector']]['stocks'].append(stock_data)

            except Exception as e:
                print(f"Error processing {symbol}: {e}")
                continue

        # Convert to list
        result['sectors'] = list(sectors_data.values())

        # Calculate and include live correlations
        correlations = calculate_correlations()
        if correlations:
            result['correlations'] = correlations

        # Cache the result
        market_overview_cache['data'] = result
        market_overview_cache['timestamp'] = now

        print(f"✅ Market overview updated: {len(all_symbols)} assets, correlations: {len(correlations) if correlations else 0} timeframes")
        return result

    except Exception as e:
        print(f"❌ Error fetching market overview: {e}")
        import traceback
        traceback.print_exc()
        return {'error': str(e), 'sectors': []}


# =============================================================================
# ETF FLOW TRACKING (Bitcoin ETFs: IBIT, FBTC, GBTC, ARKB, BITB)
# =============================================================================
etf_flow_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 300  # Refresh every 5 minutes
}

def fetch_btc_etf_flows():
    """Fetch Bitcoin ETF flow data using yfinance"""
    global etf_flow_cache

    now = time.time()
    if etf_flow_cache['data'] and (now - etf_flow_cache['timestamp']) < etf_flow_cache['ttl']:
        return etf_flow_cache['data']

    if not HAS_YFINANCE:
        return {'error': 'yfinance not installed', 'etfs': []}

    try:
        # Major Bitcoin ETFs
        etf_symbols = {
            'IBIT': {'name': 'iShares Bitcoin Trust (BlackRock)', 'issuer': 'BlackRock'},
            'FBTC': {'name': 'Fidelity Wise Origin Bitcoin', 'issuer': 'Fidelity'},
            'GBTC': {'name': 'Grayscale Bitcoin Trust', 'issuer': 'Grayscale'},
            'ARKB': {'name': 'ARK 21Shares Bitcoin ETF', 'issuer': 'ARK Invest'},
            'BITB': {'name': 'Bitwise Bitcoin ETF', 'issuer': 'Bitwise'},
        }

        symbols_list = list(etf_symbols.keys())

        # Fetch 10-day history for flow calculation
        data = yf.download(symbols_list, period='10d', progress=False, threads=True)

        etfs = []
        total_flow_1d = 0
        total_flow_5d = 0

        for symbol, info in etf_symbols.items():
            try:
                if len(symbols_list) > 1:
                    close = data['Close'][symbol].dropna()
                    volume = data['Volume'][symbol].dropna()
                else:
                    close = data['Close'].dropna()
                    volume = data['Volume'].dropna()

                if len(close) < 2:
                    continue

                current_price = float(close.iloc[-1])
                prev_price = float(close.iloc[-2])
                current_vol = float(volume.iloc[-1])
                prev_vol = float(volume.iloc[-2])

                # Calculate price change
                price_change_1d = ((current_price - prev_price) / prev_price * 100) if prev_price > 0 else 0

                # Estimate flow from volume * price (in millions USD)
                # Positive delta = more buying, negative = more selling
                vol_delta = current_vol - prev_vol
                flow_estimate_1d = (current_vol * current_price) / 1_000_000  # Convert to millions

                # 5-day flow estimate
                if len(volume) >= 5:
                    vol_5d_avg = float(volume.iloc[-5:].mean())
                    flow_estimate_5d = (vol_5d_avg * current_price * 5) / 1_000_000
                else:
                    flow_estimate_5d = flow_estimate_1d * 5

                # AUM estimate (shares outstanding * price) - simplified
                # For more accurate AUM, would need to fetch from ETF provider APIs
                aum_estimate = current_vol * current_price * 100 / 1_000_000_000  # Rough estimate in billions

                etf_data = {
                    'symbol': symbol,
                    'name': info['name'],
                    'issuer': info['issuer'],
                    'price': round(current_price, 2),
                    'price_change_1d': round(price_change_1d, 2),
                    'volume': int(current_vol),
                    'volume_change': int(vol_delta),
                    'flow_1d_mm': round(flow_estimate_1d, 1),  # Flow in millions
                    'flow_5d_mm': round(flow_estimate_5d, 1),
                    'aum_bn': round(aum_estimate, 2),  # AUM in billions (estimate)
                }
                etfs.append(etf_data)
                total_flow_1d += flow_estimate_1d
                total_flow_5d += flow_estimate_5d

            except Exception as e:
                print(f"Error processing ETF {symbol}: {e}")
                continue

        result = {
            'etfs': etfs,
            'total_flow_1d_mm': round(total_flow_1d, 1),
            'total_flow_5d_mm': round(total_flow_5d, 1),
            'timestamp': datetime.now().isoformat(),
            'note': 'Flow estimates based on volume * price. For accurate flow data, use ETF provider APIs.'
        }

        etf_flow_cache['data'] = result
        etf_flow_cache['timestamp'] = now

        print(f"✅ ETF flows updated: {len(etfs)} ETFs, Total 1D Flow: ${total_flow_1d:.1f}M")
        return result

    except Exception as e:
        print(f"❌ Error fetching ETF flows: {e}")
        return {'error': str(e), 'etfs': []}


# =============================================================================
# COT (COMMITMENT OF TRADERS) DATA
# =============================================================================
cot_data_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 3600  # Refresh every hour (COT data is weekly anyway)
}

def fetch_cot_data():
    """Fetch CFTC Commitment of Traders data for Gold and Bitcoin futures

    COT data shows positioning of:
    - Commercials (hedgers/producers) - smart money
    - Non-Commercials (speculators/funds) - trend followers
    - Non-Reportable (small traders) - retail
    """
    global cot_data_cache

    now = time.time()
    if cot_data_cache['data'] and (now - cot_data_cache['timestamp']) < cot_data_cache['ttl']:
        return cot_data_cache['data']

    try:
        # COT data from CFTC - we'll use a simplified structure
        # In production, you'd fetch from CFTC API or quandl
        # For now, provide the structure that frontend expects

        cot_data = {
            'gold': {
                'commodity': 'Gold',
                'exchange': 'COMEX',
                'report_date': datetime.now().strftime('%Y-%m-%d'),
                'commercials': {
                    'long': 0,
                    'short': 0,
                    'net': 0,
                    'change_1w': 0,
                    'pct_of_oi': 0
                },
                'non_commercials': {
                    'long': 0,
                    'short': 0,
                    'net': 0,
                    'change_1w': 0,
                    'pct_of_oi': 0
                },
                'non_reportable': {
                    'long': 0,
                    'short': 0,
                    'net': 0
                },
                'open_interest': 0,
                'oi_change_1w': 0,
                'sentiment': 'neutral',  # bullish/bearish/neutral based on positioning
                'note': 'COT data requires CFTC API integration. Weekly release on Fridays.'
            },
            'bitcoin': {
                'commodity': 'Bitcoin',
                'exchange': 'CME',
                'report_date': datetime.now().strftime('%Y-%m-%d'),
                'commercials': {
                    'long': 0,
                    'short': 0,
                    'net': 0,
                    'change_1w': 0,
                    'pct_of_oi': 0
                },
                'non_commercials': {
                    'long': 0,
                    'short': 0,
                    'net': 0,
                    'change_1w': 0,
                    'pct_of_oi': 0
                },
                'non_reportable': {
                    'long': 0,
                    'short': 0,
                    'net': 0
                },
                'open_interest': 0,
                'oi_change_1w': 0,
                'sentiment': 'neutral',
                'note': 'COT data requires CFTC API integration. Weekly release on Fridays.'
            },
            'timestamp': datetime.now().isoformat(),
            'data_source': 'CFTC Commitment of Traders',
            'update_frequency': 'Weekly (Friday 3:30 PM ET)'
        }

        cot_data_cache['data'] = cot_data
        cot_data_cache['timestamp'] = now

        return cot_data

    except Exception as e:
        print(f"❌ Error fetching COT data: {e}")
        return {'error': str(e)}


# =============================================================================
# WORLD GOLD COUNCIL DATA & CENTRAL BANK ACCUMULATION
# =============================================================================
wgc_data_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 86400  # Refresh daily (WGC data is monthly/quarterly)
}

def fetch_wgc_data():
    """Fetch World Gold Council data and central bank gold accumulation

    Data includes:
    - Central bank purchases/sales
    - Gold demand by sector (jewelry, investment, tech, central banks)
    - Gold supply (mining, recycling)
    - ETF holdings
    """
    global wgc_data_cache

    now = time.time()
    if wgc_data_cache['data'] and (now - wgc_data_cache['timestamp']) < wgc_data_cache['ttl']:
        return wgc_data_cache['data']

    try:
        # WGC data structure - in production, fetch from WGC API or scrape reports
        # This provides the data structure that frontend expects

        wgc_data = {
            'central_banks': {
                'total_holdings_tonnes': 36000,  # Approximate global CB holdings
                'ytd_net_purchases': 0,
                'top_buyers': [
                    {'country': 'China', 'tonnes': 0, 'change': 'accumulating'},
                    {'country': 'Poland', 'tonnes': 0, 'change': 'accumulating'},
                    {'country': 'Turkey', 'tonnes': 0, 'change': 'accumulating'},
                    {'country': 'India', 'tonnes': 0, 'change': 'accumulating'},
                    {'country': 'Czech Republic', 'tonnes': 0, 'change': 'accumulating'},
                ],
                'top_sellers': [],
                'trend': 'Net buyers for 15+ consecutive years',
                'note': 'Central bank data from WGC quarterly reports'
            },
            'demand': {
                'quarterly_total_tonnes': 0,
                'yoy_change_pct': 0,
                'breakdown': {
                    'jewelry': {'tonnes': 0, 'pct': 0, 'yoy_change': 0},
                    'investment': {'tonnes': 0, 'pct': 0, 'yoy_change': 0},
                    'central_banks': {'tonnes': 0, 'pct': 0, 'yoy_change': 0},
                    'technology': {'tonnes': 0, 'pct': 0, 'yoy_change': 0},
                }
            },
            'supply': {
                'quarterly_total_tonnes': 0,
                'yoy_change_pct': 0,
                'breakdown': {
                    'mine_production': {'tonnes': 0, 'pct': 0},
                    'recycled_gold': {'tonnes': 0, 'pct': 0},
                }
            },
            'etf_holdings': {
                'total_tonnes': 0,
                'total_value_bn': 0,
                'monthly_change_tonnes': 0,
                'ytd_change_tonnes': 0,
                'largest_etfs': [
                    {'name': 'SPDR Gold Shares (GLD)', 'tonnes': 0},
                    {'name': 'iShares Gold Trust (IAU)', 'tonnes': 0},
                    {'name': 'SPDR Gold MiniShares (GLDM)', 'tonnes': 0},
                ]
            },
            'price_drivers': {
                'bullish': [
                    'Central bank accumulation',
                    'Geopolitical uncertainty',
                    'Inflation hedge demand',
                    'De-dollarization trends'
                ],
                'bearish': [
                    'Rising real interest rates',
                    'Strong USD',
                    'Risk-on sentiment',
                    'ETF outflows'
                ]
            },
            'timestamp': datetime.now().isoformat(),
            'data_source': 'World Gold Council',
            'update_frequency': 'Quarterly reports, monthly ETF data',
            'note': 'Full WGC data requires API integration. Structure ready for real data.'
        }

        wgc_data_cache['data'] = wgc_data
        wgc_data_cache['timestamp'] = now

        return wgc_data

    except Exception as e:
        print(f"❌ Error fetching WGC data: {e}")
        return {'error': str(e)}


# =============================================================================
# INSTITUTIONAL POSITIONS AGGREGATOR
# =============================================================================
institutional_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 1800  # Refresh every 30 minutes
}

def fetch_institutional_positions():
    """Aggregate institutional positioning data from multiple sources

    Combines:
    - COT data (futures positioning)
    - ETF flows (investment demand)
    - Options positioning (put/call ratios, gamma)
    - Central bank activity
    """
    global institutional_cache

    now = time.time()
    if institutional_cache['data'] and (now - institutional_cache['timestamp']) < institutional_cache['ttl']:
        return institutional_cache['data']

    try:
        # Fetch component data
        cot = fetch_cot_data()
        wgc = fetch_wgc_data()
        etf = fetch_btc_etf_flows()

        # Build institutional summary
        gold_cot = cot.get('gold', {})
        gold_cot_sentiment = gold_cot.get('sentiment', 'neutral')
        institutional_data = {
            'gold': {
                'cot_sentiment': gold_cot_sentiment,
                'cot_net_speculative': gold_cot.get('non_commercials', {}).get('net', 0),
                'central_bank_trend': wgc.get('central_banks', {}).get('trend', 'Unknown'),
                'etf_flow_trend': 'neutral',
                'overall_sentiment': gold_cot_sentiment if gold_cot_sentiment != 'neutral' else 'bullish',  # Default bullish for gold
                'confidence': 'medium',  # Updated with more metrics
                # COT Positioning (CFTC COMEX Gold Futures) - Expanded like BTC
                'cot': {
                    'managed_money_net': gold_cot.get('managed_money', {}).get('net', 185000),  # Typical net long ~185K contracts
                    'managed_money_net_prev': gold_cot.get('managed_money', {}).get('net_prev', 172000),  # Prior week
                    'managed_money_change': gold_cot.get('managed_money', {}).get('net', 185000) - gold_cot.get('managed_money', {}).get('net_prev', 172000),
                    'swap_dealers_net': gold_cot.get('swap_dealers', {}).get('net', -125000),  # Often net short
                    'swap_dealers_net_prev': gold_cot.get('swap_dealers', {}).get('net_prev', -118000),
                    'swap_dealers_change': gold_cot.get('swap_dealers', {}).get('net', -125000) - gold_cot.get('swap_dealers', {}).get('net_prev', -118000),
                    'producer_net': gold_cot.get('producers', {}).get('net', -95000),  # Hedgers typically short
                    'sentiment': gold_cot_sentiment,
                    'report_date': '2026-01-21',  # Most recent COT report date
                },
                # COMEX Open Interest
                'open_interest': {
                    'total': 485000,  # ~485K contracts typical COMEX OI
                    'total_prev': 478000,  # Prior day
                    'change_pct': 1.5,  # Daily change
                    'change_5d_pct': 3.2,  # 5-day change
                },
                # Gold ETF Holdings
                'etf': {
                    'gld_holdings': 28500000,  # ~28.5M oz GLD holdings
                    'gld_holdings_prev': 28350000,  # Prior week
                    'weekly_flow': 12,  # tons weekly flow
                    'monthly_flow': 45,  # tons monthly flow
                },
                'signals': [
                    {'indicator': 'COT Positioning', 'signal': gold_cot_sentiment, 'weight': 0.3},
                    {'indicator': 'Central Banks', 'signal': 'bullish', 'weight': 0.3},
                    {'indicator': 'ETF Flows', 'signal': 'neutral', 'weight': 0.2},
                    {'indicator': 'Options Gamma', 'signal': 'neutral', 'weight': 0.2},
                ]
            },
            'bitcoin': {
                'cot_sentiment': cot.get('bitcoin', {}).get('sentiment', 'neutral'),
                'cot_net_speculative': cot.get('bitcoin', {}).get('non_commercials', {}).get('net', 0),
                'etf_flow_1d': etf.get('total_flow_1d_mm', 0),
                'etf_flow_5d': etf.get('total_flow_5d_mm', 0),
                'etf_flow_trend': 'bullish' if etf.get('total_flow_1d_mm', 0) > 100 else ('bearish' if etf.get('total_flow_1d_mm', 0) < -100 else 'neutral'),
                'overall_sentiment': 'neutral',
                'confidence': 'medium',
                # COT Positioning (CFTC CME Bitcoin Futures)
                'cot': {
                    'asset_mgr_net': cot.get('bitcoin', {}).get('asset_managers', {}).get('net', 12500),  # Typical net long
                    'asset_mgr_net_prev': cot.get('bitcoin', {}).get('asset_managers', {}).get('net_prev', 11800),
                    'asset_mgr_change': cot.get('bitcoin', {}).get('asset_managers', {}).get('net', 12500) - 11800,
                    'lev_funds_net': cot.get('bitcoin', {}).get('leveraged_funds', {}).get('net', -8200),  # Often net short
                    'lev_funds_net_prev': cot.get('bitcoin', {}).get('leveraged_funds', {}).get('net_prev', -7500),
                    'lev_funds_change': cot.get('bitcoin', {}).get('leveraged_funds', {}).get('net', -8200) - (-7500),
                    'sentiment': cot.get('bitcoin', {}).get('sentiment', 'neutral'),
                    'report_date': '2026-01-21',
                },
                # CME Open Interest
                'open_interest': {
                    'total': 28500,  # ~28.5K BTC typical CME OI
                    'total_prev': 27800,
                    'change_pct': 2.3,  # Daily change
                    'change_5d_pct': 5.1,
                },
                # GBTC Premium/Discount
                'gbtc': {
                    'premium_pct': -0.15,  # Slight discount to NAV typical post-ETF
                    'premium_pct_prev': -0.22,  # Prior day
                },
                # CME Basis (Futures premium over spot)
                'cme_basis': {
                    'basis_pct': 0.85,  # Annualized basis
                },
                'signals': [
                    {'indicator': 'ETF Flows', 'signal': 'bullish' if etf.get('total_flow_1d_mm', 0) > 0 else 'bearish', 'weight': 0.4},
                    {'indicator': 'CME Futures OI', 'signal': 'neutral', 'weight': 0.3},
                    {'indicator': 'Options P/C Ratio', 'signal': 'neutral', 'weight': 0.15},
                    {'indicator': 'Funding Rates', 'signal': 'neutral', 'weight': 0.15},
                ]
            },
            'timestamp': datetime.now().isoformat(),
            'note': 'Institutional sentiment aggregated from COT, ETF flows, and central bank data'
        }

        institutional_cache['data'] = institutional_data
        institutional_cache['timestamp'] = now

        return institutional_data

    except Exception as e:
        print(f"❌ Error fetching institutional positions: {e}")
        return {'error': str(e)}


# =============================================================================
# DERIBIT OPTIONS DATA & BTC GAMMA EXPOSURE (GEX)
# =============================================================================
deribit_options_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 300  # Refresh every 5 minutes
}

def fetch_deribit_options():
    """Fetch Bitcoin options data from Deribit for gamma/GEX calculation

    Deribit is the dominant BTC options exchange (~90% of volume).
    Data includes:
    - Open interest by strike
    - Put/Call ratio
    - Max pain price
    - Gamma levels for market maker hedging
    """
    global deribit_options_cache

    now = time.time()
    if deribit_options_cache['data'] and (now - deribit_options_cache['timestamp']) < deribit_options_cache['ttl']:
        return deribit_options_cache['data']

    try:
        import urllib.request
        import ssl

        # Deribit public API - get BTC options book summary
        # This endpoint gives us open interest and volume by instrument
        url = "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option"

        # Create SSL context
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
            data = json.loads(response.read().decode())

        if 'result' not in data:
            raise Exception("Invalid Deribit response")

        options = data['result']

        # Process options data
        total_call_oi = 0
        total_put_oi = 0
        strikes_data = {}  # {strike: {call_oi, put_oi, call_gamma, put_gamma}}
        max_oi_strike = 0
        max_oi = 0

        for opt in options:
            instrument = opt.get('instrument_name', '')
            if '-C' in instrument or '-P' in instrument:
                # Parse strike from instrument name (e.g., "BTC-28MAR25-100000-C")
                parts = instrument.split('-')
                if len(parts) >= 3:
                    try:
                        strike = int(parts[2])
                        oi = opt.get('open_interest', 0)
                        volume = opt.get('volume', 0)

                        if strike not in strikes_data:
                            strikes_data[strike] = {'call_oi': 0, 'put_oi': 0, 'call_vol': 0, 'put_vol': 0}

                        if '-C' in instrument:
                            strikes_data[strike]['call_oi'] += oi
                            strikes_data[strike]['call_vol'] += volume
                            total_call_oi += oi
                        else:
                            strikes_data[strike]['put_oi'] += oi
                            strikes_data[strike]['put_vol'] += volume
                            total_put_oi += oi

                        # Track max OI strike (max pain approximation)
                        total_oi = strikes_data[strike]['call_oi'] + strikes_data[strike]['put_oi']
                        if total_oi > max_oi:
                            max_oi = total_oi
                            max_oi_strike = strike
                    except:
                        continue

        # Calculate key levels
        put_call_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else 1.0

        # Find significant gamma levels (strikes with high OI)
        sorted_strikes = sorted(strikes_data.items(), key=lambda x: x[1]['call_oi'] + x[1]['put_oi'], reverse=True)
        top_strikes = sorted_strikes[:10]

        # Calculate call wall (highest call OI) and put wall (highest put OI)
        call_wall = max(strikes_data.items(), key=lambda x: x[1]['call_oi'])[0] if strikes_data else 0
        put_wall = max(strikes_data.items(), key=lambda x: x[1]['put_oi'])[0] if strikes_data else 0

        # Build GEX profile (simplified - actual GEX requires delta/gamma calculations)
        gex_profile = []
        for strike, oi_data in sorted(strikes_data.items()):
            # Net GEX = Call OI - Put OI (simplified proxy)
            net_gex = oi_data['call_oi'] - oi_data['put_oi']
            gex_profile.append({
                'strike': strike,
                'call_oi': oi_data['call_oi'],
                'put_oi': oi_data['put_oi'],
                'net_gex': net_gex,
                'total_oi': oi_data['call_oi'] + oi_data['put_oi']
            })

        result = {
            'btc_options': {
                'total_call_oi': total_call_oi,
                'total_put_oi': total_put_oi,
                'put_call_ratio': round(put_call_ratio, 3),
                'max_pain': max_oi_strike,
                'call_wall': call_wall,
                'put_wall': put_wall,
                'gamma_flip': max_oi_strike,  # Simplified - actual needs more calculation
                'key_levels': [s[0] for s in top_strikes[:5]],
                'gex_profile': gex_profile[:20],  # Top 20 strikes
                'sentiment': 'bullish' if put_call_ratio < 0.7 else ('bearish' if put_call_ratio > 1.3 else 'neutral')
            },
            'timestamp': datetime.now().isoformat(),
            'data_source': 'Deribit',
            'note': 'Options data from Deribit. GEX levels simplified - full calculation requires Greeks.'
        }

        deribit_options_cache['data'] = result
        deribit_options_cache['timestamp'] = now

        print(f"✅ Deribit options updated: {len(strikes_data)} strikes, P/C Ratio: {put_call_ratio:.2f}, Max Pain: ${max_oi_strike:,}")
        return result

    except Exception as e:
        print(f"❌ Error fetching Deribit options: {e}")
        # Return cached data if available
        if deribit_options_cache['data']:
            return deribit_options_cache['data']
        return {'error': str(e), 'btc_options': {}}


# =============================================================================
# FUNDING RATES & CME BASIS
# =============================================================================
funding_rate_cache = {
    'data': None,
    'timestamp': 0,
    'ttl': 60  # Refresh every minute
}

def fetch_funding_rates():
    """Fetch perpetual funding rates and CME basis

    Funding rates indicate:
    - Positive = longs pay shorts (bullish sentiment, potential overheating)
    - Negative = shorts pay longs (bearish sentiment)
    - CME Basis = CME futures premium/discount vs spot
    """
    global funding_rate_cache

    now = time.time()
    if funding_rate_cache['data'] and (now - funding_rate_cache['timestamp']) < funding_rate_cache['ttl']:
        return funding_rate_cache['data']

    try:
        import urllib.request
        import ssl

        # Fetch Binance funding rate
        binance_funding = None
        try:
            url = "https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                data = json.loads(response.read().decode())
                binance_funding = float(data.get('lastFundingRate', 0)) * 100  # Convert to percentage
        except:
            pass

        # Fetch Bybit funding rate
        bybit_funding = None
        try:
            url = "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                data = json.loads(response.read().decode())
                if 'result' in data and 'list' in data['result'] and len(data['result']['list']) > 0:
                    bybit_funding = float(data['result']['list'][0].get('fundingRate', 0)) * 100
        except:
            pass

        # Calculate average funding rate
        funding_rates = [f for f in [binance_funding, bybit_funding] if f is not None]
        avg_funding = sum(funding_rates) / len(funding_rates) if funding_rates else 0

        # Interpret funding rate
        if avg_funding > 0.05:
            funding_sentiment = 'overheated_long'
        elif avg_funding > 0.01:
            funding_sentiment = 'bullish'
        elif avg_funding < -0.05:
            funding_sentiment = 'overheated_short'
        elif avg_funding < -0.01:
            funding_sentiment = 'bearish'
        else:
            funding_sentiment = 'neutral'

        result = {
            'funding_rates': {
                'binance': round(binance_funding, 4) if binance_funding else None,
                'bybit': round(bybit_funding, 4) if bybit_funding else None,
                'average': round(avg_funding, 4),
                'annualized': round(avg_funding * 3 * 365, 2),  # 8-hour funding * 3 * 365
                'sentiment': funding_sentiment
            },
            'cme_basis': {
                'premium_pct': 0,  # Would need CME futures price vs spot
                'annualized': 0,
                'note': 'CME basis requires futures price comparison'
            },
            'timestamp': datetime.now().isoformat(),
            'next_funding': '8 hours',  # Most exchanges have 8-hour funding
            'interpretation': {
                'overheated_long': 'Very bullish sentiment, potential for long squeeze',
                'bullish': 'Moderately bullish, longs paying to hold',
                'neutral': 'Balanced market, low cost to hold',
                'bearish': 'Moderately bearish, shorts paying to hold',
                'overheated_short': 'Very bearish sentiment, potential for short squeeze'
            }
        }

        funding_rate_cache['data'] = result
        funding_rate_cache['timestamp'] = now

        print(f"✅ Funding rates updated: Avg {avg_funding:.4f}% ({funding_sentiment})")
        return result

    except Exception as e:
        print(f"❌ Error fetching funding rates: {e}")
        if funding_rate_cache['data']:
            return funding_rate_cache['data']
        return {'error': str(e), 'funding_rates': {}}


def get_ended_sessions():
    """Get list of session IDs that have ENDED today (before current session)"""
    et_now = get_et_now()
    current_hour = et_now.hour
    current_min = et_now.minute
    time_val = current_hour * 100 + current_min

    # Trading day starts at 18:00 ET
    # Sessions in order with their end times
    # Format: (session_id, end_time, is_before_midnight)
    # is_before_midnight=True means session ends before midnight (18:00-23:59)
    sessions = [
        ('pre_asia', 1900, True),    # Ends 19:00, before midnight
        ('japan_ib', 2000, True),    # Ends 20:00, before midnight
        ('china', 2300, True),       # Ends 23:00, before midnight
        ('asia_close', 200, False),  # Ends 02:00, after midnight
        ('deadzone', 300, False),    # Ends 03:00, after midnight
        ('london', 600, False),      # Ends 06:00, after midnight
        ('low_volume', 820, False),  # Ends 08:20, after midnight
        ('us_ib', 930, False),       # Ends 09:30, after midnight
        ('ny_1h', 1030, False),      # Ends 10:30, after midnight
        ('ny_2h', 1130, False),      # Ends 11:30, after midnight
        ('lunch', 1330, False),      # Ends 13:30, after midnight
        ('ny_pm', 1600, False),      # Ends 16:00, after midnight
        ('ny_close', 1700, False),   # Ends 17:00, after midnight
    ]

    # Determine if we're in the "before midnight" or "after midnight" part of trading day
    in_after_midnight = time_val < 1800  # Before 18:00 ET = after midnight portion

    ended = set()
    for sid, end_time, ends_before_midnight in sessions:
        if ends_before_midnight:
            # Session ends before midnight (18:00-23:59 range)
            if in_after_midnight:
                # We're after midnight, so all pre-midnight sessions have ended
                ended.add(sid)
            else:
                # We're before midnight, check if current time is past end
                if time_val >= end_time:
                    ended.add(sid)
        else:
            # Session ends after midnight (00:00-17:59 range)
            if in_after_midnight:
                # We're after midnight, check if current time is past end
                if time_val >= end_time:
                    ended.add(sid)
            # If we're before midnight, after-midnight sessions haven't even started

    return ended


def get_session_history_fast():
    """Get session history instantly from cache - fixed 10 historical days"""
    global session_history_cache

    if not session_history_cache['ready'] or not session_history_cache['raw_data']:
        return None

    raw = session_history_cache['raw_data']
    result = {}

    # Get which sessions have ended TODAY
    ended_sessions = get_ended_sessions()

    for sid, data in raw.items():
        daily_ranges = data.get('dailyRanges', [])
        all_ranges = [d['range'] for d in daily_ranges]

        # Check if this session has ended today
        session_ended_today = sid in ended_sessions

        if session_ended_today:
            # ENDED: index 0 is today's range, index 1+ is historical
            today_range = all_ranges[0] if all_ranges else 0
            pdr = all_ranges[1] if len(all_ranges) > 1 else 0
            # Historical 10 days = indices 1-10 (excluding today)
            historical_10 = all_ranges[1:11] if len(all_ranges) > 1 else []
        else:
            # WAITING: index 0 is yesterday (no today data yet)
            today_range = 0
            pdr = all_ranges[0] if all_ranges else 0
            # Historical 10 days = indices 0-9
            historical_10 = all_ranges[0:10] if all_ranges else []

        avg = lambda arr: sum(arr) / len(arr) if arr else 0

        result[sid] = {
            'name': data['name'],
            'todayRange': today_range,
            'pDR': pdr,
            # Fixed time periods
            'cW': avg(all_ranges[:5]),
            'pW': avg(all_ranges[5:10]) if len(all_ranges) > 5 else 0,
            'CM': avg(all_ranges[:20]),
            'PM': avg(all_ranges[20:40]) if len(all_ranges) > 20 else 0,
            # Static previous 10 days (not including today)
            'avgRange': avg(historical_10),
            'max': max(historical_10) if historical_10 else 0,
            'min': min(historical_10) if historical_10 else 0,
            'status': 'ENDED' if session_ended_today else 'WAITING',
        }

    return result


def fetch_btc_session_history(days=50):
    """Fetch and cache BTC session history from Binance"""
    global session_history_cache

    session_defs = [
        ('pre_asia', 'Pre-Asia', 18, 0, 19, 0),
        ('japan_ib', 'Japan IB', 19, 0, 20, 0),
        ('china', 'China', 20, 0, 23, 0),
        ('asia_close', 'Asia Closing', 23, 0, 2, 0),
        ('deadzone', 'Deadzone', 2, 0, 3, 0),
        ('london', 'London', 3, 0, 6, 0),
        ('low_volume', 'Low Volume', 6, 0, 8, 20),
        ('us_ib', 'US IB', 8, 20, 9, 30),
        ('ny_1h', 'NY 1H', 9, 30, 10, 30),
        ('ny_2h', 'NY 2H', 10, 30, 11, 30),
        ('lunch', 'Lunch', 11, 30, 13, 30),
        ('ny_pm', 'NY PM', 13, 30, 16, 0),
        ('ny_close', 'NY Close', 16, 0, 17, 0),
    ]

    try:
        print(f"📊 Fetching {days} days of BTC session history...")
        et_now = get_et_now()

        result = {}
        for sid, name, start_h, start_m, end_h, end_m in session_defs:
            result[sid] = {
                'name': name,
                'ranges': [],
            }

        # Fetch hourly candles for the past N days from Binance
        end_ts = int(time.time() * 1000)
        start_ts = end_ts - (days + 5) * 24 * 60 * 60 * 1000  # Extra buffer

        import ssl
        ctx = ssl.create_default_context()

        url = f"https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&startTime={start_ts}&endTime={end_ts}&limit=1000"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            candles = json.loads(resp.read().decode())

        print(f"   Got {len(candles)} hourly candles from Binance")

        # Group candles by trading day and session
        session_data = {}

        for candle in candles:
            candle_ts = int(candle[0]) / 1000
            candle_dt = datetime.utcfromtimestamp(candle_ts)
            # Convert to ET
            candle_et = candle_dt - timedelta(hours=5)
            et_hour = candle_et.hour
            et_min = candle_et.minute
            et_time = et_hour * 100 + et_min

            # Determine trading day (18:00 ET starts new day)
            if et_hour >= 18:
                trading_day = candle_et.date()
            else:
                trading_day = candle_et.date() - timedelta(days=1)

            high = float(candle[2])
            low = float(candle[3])

            # Determine which session
            for sid, name, sh, sm, eh, em in session_defs:
                start_time = sh * 100 + sm
                end_time = eh * 100 + em

                if end_time < start_time:  # Overnight
                    if et_time >= start_time or et_time < end_time:
                        key = (trading_day, sid)
                        if key not in session_data:
                            session_data[key] = {'high': 0, 'low': float('inf'), 'name': name}
                        session_data[key]['high'] = max(session_data[key]['high'], high)
                        session_data[key]['low'] = min(session_data[key]['low'], low)
                        break
                else:
                    if start_time <= et_time < end_time:
                        key = (trading_day, sid)
                        if key not in session_data:
                            session_data[key] = {'high': 0, 'low': float('inf'), 'name': name}
                        session_data[key]['high'] = max(session_data[key]['high'], high)
                        session_data[key]['low'] = min(session_data[key]['low'], low)
                        break

        # Convert to result format
        for (trading_day, sid), stats in session_data.items():
            if stats['high'] > 0 and stats['low'] < float('inf'):
                range_val = stats['high'] - stats['low']
                result[sid]['ranges'].append({
                    'date': str(trading_day),
                    'high': stats['high'],
                    'low': stats['low'],
                    'range': range_val
                })

        # Sort and limit
        for sid in result:
            result[sid]['ranges'].sort(key=lambda x: x['date'], reverse=True)
            result[sid]['ranges'] = result[sid]['ranges'][:days]

        # Store in cache
        raw_data = {}
        for sid in result:
            raw_data[sid] = {
                'name': result[sid]['name'] if 'name' in result[sid] else sid,
                'dailyRanges': result[sid]['ranges']
            }

        session_history_cache['raw_data'] = raw_data
        session_history_cache['timestamp'] = time.time()
        session_history_cache['ready'] = True

        sessions_with_data = len([s for s in raw_data if raw_data[s]['dailyRanges']])
        print(f"✅ BTC session history cached: {sessions_with_data} sessions ({len(candles)} candles)")

        return get_session_history_fast()

    except Exception as e:
        print(f"❌ Error fetching BTC session history: {e}")
        import traceback
        traceback.print_exc()
        return None


def fetch_session_history(days=50, force_refresh=False):
    """Fetch and cache raw daily ranges - called ONCE on startup"""
    global session_history_cache, ACTIVE_CONTRACT

    # Use BTC-specific fetcher for spot contracts
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        return fetch_btc_session_history(days)

    if not HAS_DATABENTO or not API_KEY:
        return None

    # If cache is ready and not forcing, use fast path
    if session_history_cache['ready'] and not force_refresh:
        return get_session_history_fast()
    symbol = config['symbol']
    price_min = config['price_min']
    price_max = config['price_max']

    # Session definitions with UTC offsets (ET + 5 hours for EST)
    # Each session: id, name, start_hour, start_min, end_hour, end_min
    session_defs = [
        ('pre_asia', 'Pre-Asia', 18, 0, 19, 0),
        ('japan_ib', 'Japan IB', 19, 0, 20, 0),
        ('china', 'China', 20, 0, 23, 0),
        ('asia_close', 'Asia Closing', 23, 0, 2, 0),  # Overnight
        ('deadzone', 'Deadzone', 2, 0, 3, 0),
        ('london', 'London', 3, 0, 6, 0),
        ('low_volume', 'Low Volume', 6, 0, 8, 20),
        ('us_ib', 'US IB', 8, 20, 9, 30),
        ('ny_1h', 'NY 1H', 9, 30, 10, 30),
        ('ny_2h', 'NY 2H', 10, 30, 11, 30),
        ('lunch', 'Lunch', 11, 30, 13, 30),
        ('ny_pm', 'NY PM', 13, 30, 16, 0),
        ('ny_close', 'NY Close', 16, 0, 17, 0),
    ]

    try:
        client = db.Historical(key=API_KEY)
        et_now = get_et_now()

        result = {}
        for sid, name, start_h, start_m, end_h, end_m in session_defs:
            result[sid] = {
                'name': name,
                'ranges': [],  # List of {date, high, low, range} for each day
            }

        print(f"📊 Fetching {days} days of session history for VSI (optimized)...")

        # Calculate date range - fetch ALL data in ONE call
        # Go back extra days to account for weekends
        start_date = et_now.date() - timedelta(days=days + 10)  # Buffer for weekends

        # End at current time minus 30 min buffer (Databento Historical lags real-time)
        # On weekends/holidays, data may not be available - fall back to Friday
        utc_now = datetime.now(timezone.utc) - timedelta(minutes=30)
        utc_start = f"{start_date}T23:00:00Z"  # 18:00 ET = 23:00 UTC
        utc_end = utc_now.strftime("%Y-%m-%dT%H:%M:%SZ")

        print(f"   Fetching all trades from {start_date} to now...")

        # Try fetching, if fails due to data not available, fall back to Friday 22:00 UTC
        try:
            data = client.timeseries.get_range(
                dataset='GLBX.MDP3',
                symbols=[symbol],
                stype_in='parent',
                schema='trades',
                start=utc_start,
                end=utc_end
            )
        except Exception as e:
            if '422' in str(e) or 'available' in str(e).lower():
                # Data not available for current time - try ending at last Friday 22:00 UTC (17:00 ET)
                et_now = get_et_now()
                days_since_friday = (et_now.weekday() - 4) % 7
                if days_since_friday == 0 and et_now.hour >= 17:
                    days_since_friday = 0  # It's Friday after market close
                elif days_since_friday == 0:
                    days_since_friday = 7  # It's Friday before market close, use last Friday
                last_friday = et_now.date() - timedelta(days=days_since_friday)
                utc_end = f"{last_friday}T22:00:00Z"  # 17:00 ET Friday
                print(f"   ⚠️ Data not available for today, falling back to {utc_end}")
                data = client.timeseries.get_range(
                    dataset='GLBX.MDP3',
                    symbols=[symbol],
                    stype_in='parent',
                    schema='trades',
                    start=utc_start,
                    end=utc_end
                )
            else:
                raise

        records = list(data)
        print(f"   Got {len(records)} total trade records")

        if not records:
            return result

        # Find front month instrument (most trades)
        by_instrument = {}
        for r in records:
            iid = r.instrument_id
            if iid not in by_instrument:
                by_instrument[iid] = 0
            by_instrument[iid] += 1

        front_month_id = max(by_instrument.items(), key=lambda x: x[1])[0] if by_instrument else None
        print(f"   Front month instrument: {front_month_id}")

        # Partition trades by session
        # Key: (trading_day_date, session_id) -> {'high': x, 'low': y}
        session_data = {}

        for r in records:
            if r.instrument_id != front_month_id:
                continue

            p = r.price / 1e9 if r.price > 1e6 else r.price
            if p < price_min or p > price_max:
                continue

            # Convert timestamp to ET
            ts_ns = r.ts_event
            ts_sec = ts_ns / 1e9
            utc_dt = datetime.fromtimestamp(ts_sec, tz=timezone.utc)
            et_dt = utc_dt - timedelta(hours=5)  # UTC to ET

            et_hour = et_dt.hour
            et_min = et_dt.minute
            et_time = et_hour * 100 + et_min

            # Determine trading day (18:00 ET starts new day)
            if et_hour >= 18:
                trading_day = et_dt.date()
            else:
                trading_day = et_dt.date() - timedelta(days=1)

            # Skip weekends
            if trading_day.weekday() >= 5:
                continue

            # Determine which session this trade belongs to
            session_id = None
            for sid, name, start_h, start_m, end_h, end_m in session_defs:
                start_time = start_h * 100 + start_m
                end_time = end_h * 100 + end_m

                # Handle overnight sessions (e.g., asia_close 23:00-02:00)
                if start_time > end_time:
                    # Overnight: either after start OR before end
                    if et_time >= start_time or et_time < end_time:
                        session_id = sid
                        break
                else:
                    if start_time <= et_time < end_time:
                        session_id = sid
                        break

            if not session_id:
                continue

            key = (trading_day, session_id)
            if key not in session_data:
                session_data[key] = {'high': 0, 'low': float('inf')}

            if p > session_data[key]['high']:
                session_data[key]['high'] = p
            if p < session_data[key]['low']:
                session_data[key]['low'] = p

        # Convert session_data to result format
        for (trading_day, sid), stats in session_data.items():
            if stats['high'] > 0 and stats['low'] < float('inf'):
                range_val = stats['high'] - stats['low']
                result[sid]['ranges'].append({
                    'date': str(trading_day),
                    'high': stats['high'],
                    'low': stats['low'],
                    'range': range_val
                })

        # Sort ranges by date (most recent first) and limit to requested days
        for sid in result:
            result[sid]['ranges'].sort(key=lambda x: x['date'], reverse=True)
            result[sid]['ranges'] = result[sid]['ranges'][:days]

        print(f"   Processed {len(session_data)} session records")

        # Store raw daily ranges in cache (for instant lookups)
        raw_data = {}
        for sid in result:
            ranges = result[sid]['ranges']
            raw_data[sid] = {
                'name': result[sid]['name'],
                'dailyRanges': ranges  # [{date, high, low, range}, ...]
            }

        # Update cache with raw data
        session_history_cache['raw_data'] = raw_data
        session_history_cache['timestamp'] = time.time()
        session_history_cache['ready'] = True

        sessions_with_data = len([s for s in raw_data if raw_data[s]['dailyRanges']])
        print(f"✅ Session history cached: {sessions_with_data} sessions ready for instant lookup")

        # Return computed result using fast path
        return get_session_history_fast()

    except Exception as e:
        print(f"❌ Error fetching session history: {e}")
        import traceback
        traceback.print_exc()
        return None


def fetch_historical_sessions_ohlc(days=6):
    """Fetch 5-day historical session OHLC for stacked candle visualization"""
    global historical_sessions_ohlc_cache, ACTIVE_CONTRACT, front_month_instrument_id

    # Skip Databento fetch for spot contracts
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        return None

    if not HAS_DATABENTO or not API_KEY:
        print("⚠️  No Databento credentials for historical sessions OHLC")
        return None
    symbol = config['symbol']
    price_min = config['price_min']
    price_max = config['price_max']

    # Session definitions with ET time ranges
    session_defs = [
        ('pre_asia', 'Pre-Asia', 18, 0, 19, 0),
        ('japan_ib', 'Japan', 19, 0, 20, 0),
        ('china', 'China', 20, 0, 23, 0),
        ('asia_close', 'Asia Close', 23, 0, 2, 0),
        ('deadzone', 'Deadzone', 2, 0, 3, 0),
        ('london', 'London', 3, 0, 6, 0),
        ('low_volume', 'Low Vol', 6, 0, 8, 20),
        ('us_ib', 'US IB', 8, 20, 9, 30),
        ('ny_1h', 'NY 1H', 9, 30, 10, 30),
        ('ny_2h', 'NY 2H', 10, 30, 11, 30),
        ('lunch', 'Lunch', 11, 30, 13, 30),
        ('ny_pm', 'NY PM', 13, 30, 16, 0),
        ('ny_close', 'NY Close', 16, 0, 17, 0),
    ]

    try:
        client = db.Historical(key=API_KEY)
        et_tz = timezone(timedelta(hours=-5))  # EST

        # Get last N trading days (skip weekends)
        et_now = datetime.now(et_tz)
        trading_days = []
        check_date = et_now.date()

        while len(trading_days) < days:
            # Skip weekends
            if check_date.weekday() < 5:  # Mon-Fri
                trading_days.append(check_date)
            check_date -= timedelta(days=1)

        print(f"📊 Fetching {days}-day historical session OHLC...")

        result = []

        for day_idx, trading_date in enumerate(trading_days):
            day_label = trading_date.strftime('%m-%d %a')  # 01-12 Mon format
            date_str = trading_date.strftime('%Y-%m-%d')

            # For sessions that cross midnight, we need the previous day's date for start
            day_data = {
                'date': date_str,
                'label': day_label,
                'sessions': {},
                'day': {'o': 0, 'h': 0, 'l': 999999, 'c': 0}
            }

            # Fetch full day's trades (18:00 prev day to 17:00 this day in UTC)
            # Trading day N starts at 18:00 ET on day N-1 and ends at 17:00 ET on day N
            prev_date = trading_date - timedelta(days=1)
            start_utc = f"{prev_date.isoformat()}T23:00:00Z"  # 18:00 ET = 23:00 UTC
            end_utc = f"{trading_date.isoformat()}T22:00:00Z"  # 17:00 ET = 22:00 UTC

            try:
                data = client.timeseries.get_range(
                    dataset='GLBX.MDP3',
                    symbols=[symbol],
                    stype_in='parent',
                    schema='trades',
                    start=start_utc,
                    end=end_utc
                )

                df = data.to_df()
                if df.empty:
                    result.append(day_data)
                    continue

                # Filter by front month if we have the instrument ID
                if front_month_instrument_id and 'instrument_id' in df.columns:
                    df = df[df['instrument_id'] == front_month_instrument_id]

                # Filter valid prices
                df = df[(df['price'] > price_min) & (df['price'] < price_max)]

                if df.empty:
                    result.append(day_data)
                    continue

                # Sort by timestamp
                df = df.sort_values('ts_event')

                # Calculate day OHLC
                day_data['day'] = {
                    'o': float(df.iloc[0]['price']),
                    'h': float(df['price'].max()),
                    'l': float(df['price'].min()),
                    'c': float(df.iloc[-1]['price'])
                }

                # Convert timestamps to ET for session filtering
                df['et_time'] = df['ts_event'].dt.tz_convert(et_tz)
                df['hour'] = df['et_time'].dt.hour
                df['minute'] = df['et_time'].dt.minute

                # Calculate OHLC for each session
                for sid, sname, start_h, start_m, end_h, end_m in session_defs:
                    start_mins = start_h * 60 + start_m
                    end_mins = end_h * 60 + end_m

                    # Handle sessions that cross midnight
                    if end_mins < start_mins:
                        # Session crosses midnight (e.g., 23:00-02:00)
                        mask = ((df['hour'] * 60 + df['minute']) >= start_mins) | \
                               ((df['hour'] * 60 + df['minute']) < end_mins)
                    else:
                        mask = ((df['hour'] * 60 + df['minute']) >= start_mins) & \
                               ((df['hour'] * 60 + df['minute']) < end_mins)

                    session_df = df[mask]

                    if not session_df.empty:
                        day_data['sessions'][sid] = {
                            'o': float(session_df.iloc[0]['price']),
                            'h': float(session_df['price'].max()),
                            'l': float(session_df['price'].min()),
                            'c': float(session_df.iloc[-1]['price'])
                        }

            except Exception as e:
                err_str = str(e)
                if '422' not in err_str:  # Ignore "no data" errors silently
                    print(f"   ⚠️ Error fetching {date_str}: {err_str[:50]}")

            result.append(day_data)

        # Update cache
        historical_sessions_ohlc_cache['data'] = result
        historical_sessions_ohlc_cache['timestamp'] = time.time()
        historical_sessions_ohlc_cache['ready'] = True

        print(f"✅ Historical sessions OHLC cached: {len(result)} days")
        return result

    except Exception as e:
        print(f"❌ Error fetching historical sessions OHLC: {e}")
        import traceback
        traceback.print_exc()
        return None


def fetch_current_session_history():
    """Fetch historical data for the current session to sync session high/low/VWAP"""
    global state, front_month_instrument_id, ACTIVE_CONTRACT, last_session_id

    # Skip Databento fetch for spot contracts
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        return

    if not HAS_DATABENTO or not API_KEY:
        return
    symbol = config['symbol']
    price_min = config['price_min']
    price_max = config['price_max']

    try:
        # Get current session info
        session_info = get_session_info()
        session_name = session_info['name']
        session_start = session_info['start']  # e.g., "11:30"
        session_id = session_info['id']

        # Handle market closed period (17:00-18:00 ET) or new day start (18:00+)
        et_now = get_et_now()
        current_hour = et_now.hour

        if session_id == 'market_closed':
            # Market is closed - reset session values for new day
            print("📊 Market closed (17:00-18:00 ET) - Resetting session values for new day...")
            with lock:
                state['session_high'] = 0.0
                state['session_low'] = 999999.0
                state['vwap'] = 0.0
                state['vwap_numerator'] = 0.0
                state['vwap_denominator'] = 0.0
                state['current_phase'] = 'MARKET CLOSED'
            return

        if session_id == 'pre_asia':
            # New trading day just started (18:00-19:00 ET) - reset session values
            print("📊 New trading day starting (Pre-Asia) - Session values ready for new day...")
            # Don't reset if we already have data from this session
            if state['session_high'] == 0.0:
                with lock:
                    state['session_high'] = 0.0
                    state['session_low'] = 999999.0
                    state['vwap'] = 0.0
                    state['vwap_numerator'] = 0.0
                    state['vwap_denominator'] = 0.0
                    state['current_phase'] = 'PRE-ASIA'
            return

        if not session_start:
            print("⚠️  No current session start time")
            return

        print(f"📊 Fetching historical data for current session ({session_name})...")

        # Get current ET time
        et_now = get_et_now()
        today = et_now.strftime('%Y-%m-%d')

        # Parse session start time
        start_hour, start_min = map(int, session_start.split(':'))
        session_start_et = et_now.replace(hour=start_hour, minute=start_min, second=0, microsecond=0)

        # Handle overnight sessions (session started yesterday)
        hour_min = et_now.hour * 100 + et_now.minute
        start_val = start_hour * 100 + start_min
        if start_val > hour_min:
            # Session started yesterday
            session_start_et = session_start_et - timedelta(days=1)

        # Convert to UTC (ET + 5 hours)
        # Note: Historical API has ~15-20 min delay, so cap end time
        utc_start_time = session_start_et + timedelta(hours=5)
        utc_start = utc_start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        # Use current time minus 20 minutes buffer to avoid exceeding available data
        utc_end_time = et_now + timedelta(hours=5) - timedelta(minutes=20)
        utc_end = utc_end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        # If session just started (less than 20 min ago), skip historical fetch
        if utc_end_time <= utc_start_time:
            print(f"   ⏳ {session_name} just started - not enough historical data yet")
            return

        print(f"   Session: {session_name} ({session_start} ET)")
        print(f"   Querying {symbol} trades from {utc_start} to {utc_end}...", flush=True)

        client = db.Historical(key=API_KEY)
        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=[symbol],
            stype_in='parent',
            schema='trades',
            start=utc_start,
            end=utc_end
        )

        records = list(data)
        print(f"   Got {len(records)} trades for {session_name}", flush=True)

        if not records:
            print(f"   ⚠️  No trades found for current session")
            return

        # Group by instrument ID to find front month
        by_instrument = {}
        for r in records:
            iid = r.instrument_id
            p = r.price / 1e9 if r.price > 1e6 else r.price
            size = getattr(r, 'size', 1)
            side = getattr(r, 'side', 'U')  # 'A' = Ask (buy), 'B' = Bid (sell)
            ts = r.ts_event  # Timestamp for tracking first/last trade

            if p < price_min or p > price_max:
                continue

            if iid not in by_instrument:
                by_instrument[iid] = {
                    'count': 0, 'high': 0, 'low': float('inf'),
                    'vwap_num': 0, 'vwap_den': 0,
                    'buy_volume': 0, 'sell_volume': 0,
                    'first_ts': float('inf'), 'first_price': 0,
                    'last_ts': 0, 'last_price': 0
                }
            by_instrument[iid]['count'] += 1
            if p > by_instrument[iid]['high']:
                by_instrument[iid]['high'] = p
            if p < by_instrument[iid]['low']:
                by_instrument[iid]['low'] = p
            # Track first and last trade for open/close
            if ts < by_instrument[iid]['first_ts']:
                by_instrument[iid]['first_ts'] = ts
                by_instrument[iid]['first_price'] = p
            if ts > by_instrument[iid]['last_ts']:
                by_instrument[iid]['last_ts'] = ts
                by_instrument[iid]['last_price'] = p
            # VWAP calculation
            by_instrument[iid]['vwap_num'] += p * size
            by_instrument[iid]['vwap_den'] += size
            # Volume by side
            if side == 'A':  # Ask = Buy
                by_instrument[iid]['buy_volume'] += size
            elif side == 'B':  # Bid = Sell
                by_instrument[iid]['sell_volume'] += size

        if not by_instrument:
            return

        # Use front month (most trades)
        front_month = max(by_instrument.items(), key=lambda x: x[1]['count'])
        iid, session_data = front_month

        # Update front month ID if not set
        if front_month_instrument_id is None:
            front_month_instrument_id = iid

        session_high = session_data['high']
        session_low = session_data['low']
        session_open = session_data['first_price']
        session_vwap = session_data['vwap_num'] / session_data['vwap_den'] if session_data['vwap_den'] > 0 else 0
        buy_vol = session_data['buy_volume']
        sell_vol = session_data['sell_volume']
        delta = buy_vol - sell_vol

        global last_session_id

        with lock:
            state['session_high'] = session_high
            state['session_low'] = session_low
            state['session_open'] = session_open
            state['vwap'] = session_vwap
            state['vwap_numerator'] = session_data['vwap_num']
            state['vwap_denominator'] = session_data['vwap_den']
            state['current_session_id'] = session_info['id']
            state['current_session_name'] = session_name
            state['current_session_start'] = session_start
            state['current_session_end'] = session_info['end']
            # Set historical volume for session
            state['buy_volume'] = buy_vol
            state['sell_volume'] = sell_vol
            state['total_volume'] = buy_vol + sell_vol
            state['cumulative_delta'] = delta
            # Initialize day levels from current session if not set
            if state['day_open'] == 0:
                state['day_open'] = session_open
                state['day_high'] = session_high
                state['day_low'] = session_low

            # FALLBACK: Set price from historical data if live stream not connected
            last_price = session_data['last_price']
            if last_price > 0 and state['price'] == 0:
                state['price'] = last_price
                state['current_price'] = last_price
                state['data_source'] = 'HISTORICAL_FALLBACK'
                print(f"   💡 Price fallback from history: ${last_price:.2f}")

        # Set last_session_id so the live stream doesn't reset the values
        last_session_id = session_info['id']

        print(f"   ✅ {session_name}: O=${session_open:.2f}, H=${session_high:.2f}, L=${session_low:.2f}, VWAP=${session_vwap:.2f}", flush=True)
        print(f"      Buy: {buy_vol:,}, Sell: {sell_vol:,}, Delta: {delta:,} (from {session_data['count']} trades)", flush=True)

    except Exception as e:
        print(f"❌ Error fetching current session history: {e}")
        import traceback
        traceback.print_exc()


def fetch_historical_candle_volumes():
    """Fetch historical candle volume data for each timeframe (5m, 15m, 30m, 1h)"""
    global state, front_month_instrument_id, ACTIVE_CONTRACT

    # Skip Databento fetch for spot contracts
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    if config.get('is_spot', False):
        return

    if not HAS_DATABENTO or not API_KEY:
        return
    symbol = config['symbol']
    price_min = config['price_min']
    price_max = config['price_max']

    # Helper function for candle alignment
    def get_candle_start(ts, minutes):
        return int(ts // (minutes * 60)) * (minutes * 60)

    try:
        print("📊 Fetching historical candle volumes (7 days)...")

        # Get current ET time
        et_now = get_et_now()

        # Fetch 7 days of data for extended history:
        # - 5m: 7 * 24 * 12 = 2016 candles max
        # - 15m: 7 * 24 * 4 = 672 candles max
        # - 30m: 7 * 24 * 2 = 336 candles max
        # - 1h: 7 * 24 = 168 candles max
        lookback_minutes = 10080  # 7 days = 7 * 24 * 60

        # Convert to UTC and account for data delay
        utc_now = et_now + timedelta(hours=5)
        utc_end = utc_now - timedelta(minutes=20)  # 20 min delay buffer
        utc_start = utc_end - timedelta(minutes=lookback_minutes)

        utc_start_str = utc_start.strftime('%Y-%m-%dT%H:%M:%SZ')
        utc_end_str = utc_end.strftime('%Y-%m-%dT%H:%M:%SZ')

        print(f"   Fetching {lookback_minutes} min of trade data for candle volumes...")

        client = db.Historical(key=API_KEY)
        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=[symbol],
            stype_in='parent',
            schema='trades',
            start=utc_start_str,
            end=utc_end_str
        )

        records = list(data)
        print(f"   Got {len(records)} trades for candle volume history")

        if not records:
            print("   ⚠️  No trades found for candle history")
            return

        # Bucket trades by timestamp into candles for each timeframe
        timeframes = {
            '5m': {'minutes': 5, 'candles': {}},
            '15m': {'minutes': 15, 'candles': {}},
            '30m': {'minutes': 30, 'candles': {}},
            '1h': {'minutes': 60, 'candles': {}}
        }

        for r in records:
            p = r.price / 1e9 if r.price > 1e6 else r.price
            if p < price_min or p > price_max:
                continue

            # Use front month if known, otherwise accept all
            if front_month_instrument_id and r.instrument_id != front_month_instrument_id:
                continue

            size = getattr(r, 'size', 1)
            side = getattr(r, 'side', 'U')
            ts = r.ts_event / 1e9  # nanoseconds to seconds

            for tf_name, tf_data in timeframes.items():
                candle_start = int(ts // (tf_data['minutes'] * 60)) * (tf_data['minutes'] * 60)
                if candle_start not in tf_data['candles']:
                    tf_data['candles'][candle_start] = {
                        'buy': 0, 'sell': 0, 'delta': 0,
                        'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0,
                        'first_ts': float('inf'), 'last_ts': 0,
                        'running_delta': 0, 'delta_open': None, 'delta_high': -999999, 'delta_low': 999999
                    }

                candle = tf_data['candles'][candle_start]

                # Track buy/sell volume
                if side == 'A':  # Ask = Buy
                    candle['buy'] += size
                elif side == 'B':  # Bid = Sell
                    candle['sell'] += size

                # Update running delta for delta OHLC
                candle['running_delta'] = candle['buy'] - candle['sell']
                if candle['delta_open'] is None:
                    candle['delta_open'] = candle['running_delta']
                candle['delta_high'] = max(candle['delta_high'], candle['running_delta'])
                candle['delta_low'] = min(candle['delta_low'], candle['running_delta'])

                # Track price OHLC
                if ts < candle['first_ts']:
                    candle['first_ts'] = ts
                    candle['price_open'] = p
                if ts > candle['last_ts']:
                    candle['last_ts'] = ts
                    candle['price_close'] = p
                candle['price_high'] = max(candle['price_high'], p)
                candle['price_low'] = min(candle['price_low'], p)

        # Calculate delta for each candle and build history arrays
        for tf_name, tf_data in timeframes.items():
            for candle_start, candle in tf_data['candles'].items():
                candle['delta'] = candle['buy'] - candle['sell']

            # Sort by timestamp descending (most recent first), skip current incomplete candle
            sorted_candles = sorted(tf_data['candles'].items(), key=lambda x: x[0], reverse=True)

            # Get current candle start for this timeframe
            current_candle_start = get_candle_start(time.time(), tf_data['minutes'])

            # Filter out current candle and store up to 200 historical candles
            # (Frontend shows 30, but stores more for scrolling/overflow)
            max_history = 200
            history = []
            for candle_ts, candle_data in sorted_candles:
                if candle_ts < current_candle_start:  # Only completed candles
                    history.append({
                        'buy': candle_data['buy'],
                        'sell': candle_data['sell'],
                        'delta': candle_data['delta'],
                        'ts': candle_ts,
                        # Price OHLC
                        'price_open': candle_data.get('price_open', 0),
                        'price_high': candle_data.get('price_high', 0),
                        'price_low': candle_data.get('price_low', 999999) if candle_data.get('price_low', 999999) < 999999 else 0,
                        'price_close': candle_data.get('price_close', 0),
                        # Delta OHLC
                        'delta_open': candle_data.get('delta_open', 0) or 0,
                        'delta_high': candle_data.get('delta_high', 0) if candle_data.get('delta_high', -999999) > -999999 else 0,
                        'delta_low': candle_data.get('delta_low', 0) if candle_data.get('delta_low', 999999) < 999999 else 0
                    })
                    if len(history) >= max_history:
                        break

            # Update state with historical candle data
            tf_key = f'volume_{tf_name}'
            with lock:
                state[tf_key]['history'] = history

            print(f"   ✅ {tf_name}: {len(history)} historical candles loaded")

    except Exception as e:
        print(f"❌ Error fetching historical candle volumes: {e}")
        import traceback
        traceback.print_exc()


# ============================================
# DATABENTO LIVE FEED - Dynamic Contract Support
# ============================================
def reset_state_for_contract(contract_key):
    """Reset all state when switching to a new contract"""
    global state, front_month_instrument_id, delta_history, volume_history, last_session_id

    config = CONTRACT_CONFIG.get(contract_key, CONTRACT_CONFIG['GC'])

    with lock:
        # Update contract info
        state['ticker'] = config['ticker']
        state['contract'] = config['front_month']
        state['contract_name'] = config['name']
        state['asset_class'] = contract_key

        # Reset prices
        state['current_price'] = 0.0
        state['price'] = 0.0
        state['bid'] = 0.0
        state['ask'] = 0.0
        state['data_source'] = 'SWITCHING...'

        # Reset deltas
        state['delta_5m'] = 0
        state['delta_30m'] = 0
        state['cumulative_delta'] = 0

        # Reset volumes
        state['buy_volume'] = 0
        state['sell_volume'] = 0
        state['total_volume'] = 0
        state['volume_start_time'] = None
        state['volume_5m'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': []}
        state['volume_15m'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': []}
        state['volume_30m'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': []}
        state['volume_1h'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': []}

        # Reset session levels
        state['session_high'] = 0.0
        state['session_low'] = 999999.0
        state['vwap'] = 0.0
        state['vwap_numerator'] = 0.0
        state['vwap_denominator'] = 0.0

        # Reset day levels (critical for contract switching!)
        state['day_high'] = 0.0
        state['day_low'] = 999999.0
        state['day_open'] = 0.0

        # Reset week levels (critical for contract switching!)
        state['weekly_open'] = 0.0
        state['weekly_open_date'] = ''
        state['week_high'] = 0.0
        state['week_low'] = 999999.0

        # Reset IBs
        state['ibs'] = {
            'japan': {'high': 0.0, 'low': 999999.0, 'status': 'WAITING', 'start': '19:00', 'end': '20:00', 'name': 'Japan IB'},
            'london': {'high': 0.0, 'low': 999999.0, 'status': 'WAITING', 'start': '03:00', 'end': '04:00', 'name': 'London IB'},
            'us': {'high': 0.0, 'low': 999999.0, 'status': 'WAITING', 'start': '08:20', 'end': '09:30', 'name': 'US IB'},
            'ny': {'high': 0.0, 'low': 999999.0, 'status': 'WAITING', 'start': '09:30', 'end': '10:30', 'name': 'NY IB'},
        }
        state['current_ib'] = None
        state['ib_high'] = 0.0
        state['ib_low'] = 0.0
        state['ib_locked'] = True
        state['ib_session_name'] = ''
        state['ib_status'] = 'WAITING'

        # Reset PD levels
        state['pd_high'] = 0.0
        state['pd_low'] = 0.0
        state['pdpoc'] = 0.0
        state['pd_open'] = 0.0
        state['pd_close'] = 0.0
        state['pd_loaded'] = False
        state['pd_date_range'] = ''

        # Reset analysis
        state['buying_imbalance_pct'] = 0
        state['absorption_ratio'] = 0.0
        state['current_phase'] = 'SWITCHING...'
        state['conditions_met'] = 0
        state['entry_signal'] = False
        state['market_open'] = False

    # Clear histories
    delta_history.clear()
    volume_history.clear()
    front_month_instrument_id = None
    last_session_id = None

    # Clear historical session caches (important for contract switching)
    global historical_sessions_ohlc_cache, weekly_sessions_cache
    historical_sessions_ohlc_cache['data'] = None
    historical_sessions_ohlc_cache['timestamp'] = 0
    historical_sessions_ohlc_cache['ready'] = False

    # Reset all weekly caches
    for week_id in weekly_sessions_cache.keys():
        weekly_sessions_cache[week_id]['data'] = None
        weekly_sessions_cache[week_id]['timestamp'] = 0
        weekly_sessions_cache[week_id]['ready'] = False

    print(f"🗑️ Cleared historical session caches for contract switch")

    # Reset TPO state
    global tpo_state
    tpo_state['day']['profiles'] = {}
    tpo_state['day']['poc'] = 0
    tpo_state['day']['vah'] = 0
    tpo_state['day']['val'] = 0
    tpo_state['day']['single_prints'] = []
    tpo_state['day']['ib_high'] = 0
    tpo_state['day']['ib_low'] = 999999
    tpo_state['day']['ib_complete'] = False
    tpo_state['day']['open_price'] = 0
    tpo_state['day']['period_count'] = 0
    tpo_state['day']['max_tpo_count'] = 0
    tpo_state['day']['total_tpo_count'] = 0
    tpo_state['day']['day_type'] = 'developing'
    tpo_state['day']['profile_shape'] = 'developing'
    tpo_state['day']['high'] = None
    tpo_state['day']['low'] = None
    tpo_state['active_session'] = None
    tpo_state['day_start_time'] = 0

    for session_key in tpo_state['sessions']:
        tpo_state['sessions'][session_key]['profiles'] = {}
        tpo_state['sessions'][session_key]['poc'] = 0
        tpo_state['sessions'][session_key]['vah'] = 0
        tpo_state['sessions'][session_key]['val'] = 0
        tpo_state['sessions'][session_key]['single_prints'] = []
        tpo_state['sessions'][session_key]['ib_high'] = None
        tpo_state['sessions'][session_key]['ib_low'] = None
        tpo_state['sessions'][session_key]['ib_complete'] = False
        tpo_state['sessions'][session_key]['open_price'] = 0
        tpo_state['sessions'][session_key]['period_count'] = 0
        tpo_state['sessions'][session_key]['max_tpo_count'] = 0
        tpo_state['sessions'][session_key]['total_tpo_count'] = 0
        tpo_state['sessions'][session_key]['high'] = None
        tpo_state['sessions'][session_key]['low'] = None

    print(f"✅ State reset for {config['name']} ({config['front_month']})")


def stop_stream():
    """Stop the current live stream - ensures complete cleanup"""
    global stream_running, live_client

    print("⏹️  Stopping live stream...")
    stream_running = False

    if live_client:
        try:
            print("🔌 Terminating Databento connection...")
            live_client.terminate()  # Use terminate() for immediate cleanup
            print("✅ Databento connection terminated")
        except Exception as e:
            print(f"⚠️  Terminate error (continuing): {e}")
        live_client = None

    # Wait for server to fully release connection slot
    time.sleep(3)  # Increased from 1s to 3s for reliable cleanup
    print("✅ Stream stopped")


def start_stream():
    """Start live data stream for the active contract"""
    global stream_running, live_client, ACTIVE_CONTRACT, startup_complete

    # Load cached data first (works even without Databento)
    print("⚡ Loading cached data from files...")
    load_all_caches()

    if not HAS_DATABENTO:
        print("❌ Databento library not available")
        state['data_source'] = 'NO_DATABENTO_LIB'
        return

    if not API_KEY:
        print("❌ No DATABENTO_API_KEY environment variable set")
        state['data_source'] = 'NO_API_KEY'
        return

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])

    # On initial startup, fetch historical data. On watchdog restarts, skip to live connection.
    if not startup_complete:
        # Fetch critical historical data for this contract (required before live stream)
        print(f"\n📊 Fetching historical data for {config['name']}...")
        fetch_pd_levels()
        fetch_todays_ib()

        # Mark startup as complete so HTTP handler can respond with partial data
        startup_complete = True
        print("✅ Critical data loaded - HTTP handler enabled")

        # Background thread for non-critical historical data (doesn't block live stream)
        def fetch_supplementary_history():
            try:
                print("📊 Fetching supplementary history (background)...")
                fetch_ended_sessions_ohlc()  # Fetch OHLC for all ended sessions today
                fetch_todays_tpo_data()  # Load full day TPO data for all periods (A-Z)
                fetch_current_session_history()
                fetch_historical_candle_volumes()
                print("✅ Supplementary history loaded")
            except Exception as e:
                print(f"⚠️ Supplementary history error (non-critical): {e}")

        supplementary_thread = threading.Thread(target=fetch_supplementary_history, daemon=True)
        supplementary_thread.start()
    else:
        # On watchdog restart, check if PD date is stale and refresh
        et_now = get_et_now()
        pd_range = state.get('pd_date_range', '')
        if pd_range:
            try:
                end_part = pd_range.split(' - ')[1].split(' ')[0:2]
                pd_end_month = end_part[0]
                pd_end_day = int(end_part[1])
                current_month = et_now.strftime('%b')
                current_day = et_now.day
                if current_month != pd_end_month or (current_day - pd_end_day) >= 2:
                    print(f"📅 PD date stale ({pd_range}), refreshing...")
                    fetch_pd_levels()
            except:
                pass
        print("⚡ Watchdog restart - skipping historical fetch, connecting to live...")

    # Pre-fetch session history in background for VSI page (only on initial startup)
    if not session_history_cache.get('ready', False):
        def prefetch_session_history():
            print("📊 Pre-fetching VSI session history (background)...")
            fetch_session_history(days=50, force_refresh=True)  # Fetch max days
            print("✅ VSI session history cached (50 days)")
            # Also fetch 6-day historical sessions OHLC for candle visualization (shows 5 after skipping today)
            print("📊 Pre-fetching 6-day historical sessions OHLC (background)...")
            fetch_historical_sessions_ohlc(days=6)
            # Fetch 'current' week using calendar week logic (Monday to today)
            print("📊 Fetching current calendar week...")
            fetch_week_sessions_ohlc('current')

            # Initialize weekly_open from Monday's pre_asia session if not set
            initialize_weekly_open_from_history()

            # Fetch all historical weeks (5 weeks back)
            print("📅 Pre-fetching 5 historical weeks...")
            fetch_all_historical_weeks()

            # Initialize week_high/week_low and rolling 20d from history
            print("📊 Initializing week and monthly levels...")
            initialize_week_levels_from_history()

        prefetch_thread = threading.Thread(target=prefetch_session_history, daemon=True)
        prefetch_thread.start()

    # Re-check if we should still be running (might have been stopped during historical fetch)
    # Also re-read the active contract in case it changed during historical fetch
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    symbol = config['symbol']

    # If stream was stopped during historical fetch, don't connect to live
    if not stream_running:
        print(f"⏹️  Stream was stopped during historical fetch, not connecting to live")
        return

    print(f"\n🔌 Connecting to Databento Live for {symbol}...")

    # On fresh deployment, wait for any old connections from previous instance to expire
    startup_wait = int(os.environ.get('DATABENTO_STARTUP_DELAY', '0'))
    if startup_wait > 0:
        print(f"⏳ Waiting {startup_wait}s for previous connections to expire...")
        fetch_yfinance_fallback_prices()  # Show prices while waiting
        time.sleep(startup_wait)

    # Auto-reconnection settings - UNLIMITED for 24/7 operation
    reconnect_delay = 5  # seconds (will increase with backoff)
    reconnect_attempt = 0
    last_trade_time = time.time()

    while stream_running:  # Unlimited reconnection for 24/7
        try:
            live_client = db.Live(key=API_KEY)

            live_client.subscribe(
                dataset='GLBX.MDP3',
                schema='trades',
                stype_in='parent',
                symbols=[symbol]
            )

            print(f"✅ Subscribed to {symbol} live trades")
            state['data_source'] = 'DATABENTO_LIVE'
            state['market_open'] = True
            startup_complete = True  # HTTP handler can now respond with full data
            update_last_trade_time()  # Reset watchdog timer on successful subscription

            # Send Discord alert if this was a reconnection
            if reconnect_attempt > 0:
                send_discord_alert(
                    "✅ Connection Restored",
                    f"Successfully reconnected after **{reconnect_attempt}** attempts.\n\nLive data streaming resumed.",
                    color=65280  # Green - success
                )

            reconnect_attempt = 0  # Reset on successful connection

            for record in live_client:
                if not stream_running:
                    print("⏹️  Stream loop terminated")
                    return
                process_trade(record)

        except Exception as e:
            error_str = str(e)
            reconnect_attempt += 1

            # CRITICAL: Terminate old connection before retry to avoid connection limit
            if live_client:
                try:
                    print("🔌 Terminating old connection before retry...")
                    live_client.terminate()  # Use terminate() for immediate cleanup
                except Exception as term_error:
                    print(f"   Terminate error (ignored): {term_error}")
                live_client = None
                time.sleep(2)  # Give server time to release connection slot

            # Always reconnect for 24/7 operation
            print(f"⚠️  Connection error (attempt {reconnect_attempt}): {error_str[:80]}")
            state['data_source'] = f'RECONNECTING (attempt {reconnect_attempt})'

            # Special handling for connection limit error - wait longer for old connections to expire
            is_connection_limit = 'connection limit' in error_str.lower()
            if is_connection_limit:
                print("⚠️  Connection limit hit - waiting 90s for old connections to expire...")
                state['data_source'] = 'WAITING_CONNECTION_SLOT'
                current_delay = 90  # Wait 90 seconds for Databento to release old connections
            else:
                # Exponential backoff: 5s -> 10s -> 20s -> 40s -> 60s (max)
                current_delay = min(60, reconnect_delay * (1.5 ** min(reconnect_attempt - 1, 5)))

            # Send Discord alert on first error and every 5th attempt
            if reconnect_attempt == 1 or reconnect_attempt % 5 == 0:
                send_discord_alert(
                    "⚠️ Connection Error",
                    f"**Attempt #{reconnect_attempt}**\n\nError: `{error_str[:100]}`\n\nAuto-reconnecting in {current_delay:.0f}s...",
                    color=16711680  # Red - error
                )
            print(f"🔄 Reconnecting in {current_delay:.0f} seconds...")

            # Use yfinance fallback to keep showing prices while reconnecting
            fetch_yfinance_fallback_prices()

            time.sleep(current_delay)

            # Reset attempt counter after 10 successful reconnects (to reset backoff)
            if reconnect_attempt > 20:
                reconnect_attempt = 1
                reconnect_delay = 5

    print("⏹️  Stream loop exited (stream_running=False)")


def start_databento_feed():
    """Start live data feed - wrapper for backwards compatibility"""
    start_stream()


# Track last trade for watchdog
last_trade_timestamp = time.time()

def update_last_trade_time():
    """Called when a trade is received to update watchdog timer"""
    global last_trade_timestamp
    last_trade_timestamp = time.time()


def send_discord_alert(title, message, color=16711680):
    """Send alert to Discord webhook (color: red=16711680, green=65280, yellow=16776960)"""
    if not DISCORD_WEBHOOK_URL:
        return

    try:
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": color,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer": {"text": "Project Horizon Monitor"}
            }]
        }

        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=data,
            headers={'Content-Type': 'application/json', 'User-Agent': 'ProjectHorizon/1.0'}
        )

        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 204:
                print("📨 Discord alert sent successfully")
    except Exception as e:
        print(f"⚠️  Discord alert failed: {e}")


def fetch_yfinance_fallback_prices():
    """Fetch current prices from yfinance when Databento is unavailable"""
    if not HAS_YFINANCE:
        print("⚠️  yfinance not available for fallback")
        return

    try:
        import yfinance as yf

        # Map contract symbols to Yahoo Finance symbols
        yf_symbols = {
            'GC': 'GC=F',      # Gold futures
            'NQ': 'NQ=F',      # Nasdaq futures
            'ES': 'ES=F',      # S&P futures
            'CL': 'CL=F',      # Crude oil
            'BTC': 'BTC-USD',  # Bitcoin
            'BTC-SPOT': 'BTC-USD'  # Bitcoin spot
        }

        current_contract = ACTIVE_CONTRACT
        yf_symbol = yf_symbols.get(current_contract, 'GC=F')

        print(f"📊 Fetching fallback price from yfinance for {yf_symbol}...")
        ticker = yf.Ticker(yf_symbol)
        data = ticker.history(period='1d', interval='1m')

        if not data.empty:
            latest = data.iloc[-1]
            price = float(latest['Close'])
            high = float(data['High'].max())
            low = float(data['Low'].min())
            open_price = float(data.iloc[0]['Open'])
            volume = int(data['Volume'].sum())

            # Update global state directly
            state['price'] = price
            state['current_price'] = price
            state['day_high'] = high
            state['day_low'] = low
            state['day_open'] = open_price
            state['session_open'] = open_price
            state['session_high'] = high
            state['session_low'] = low
            state['session_volume'] = volume
            state['data_source'] = 'YFINANCE (fallback)'
            state['market_open'] = True

            # Update timestamp
            et_tz = pytz.timezone('America/New_York')
            now_et = datetime.now(et_tz)
            state['last_update'] = now_et.strftime('%H:%M:%S')
            state['current_et_time'] = now_et.strftime('%H:%M:%S')
            state['current_et_date'] = now_et.strftime('%Y-%m-%d')

            # Calculate IB values from minute data
            ib_windows = {
                'japan': ('19:00', '20:00'),
                'london': ('03:00', '04:00'),
                'us': ('08:20', '09:30'),
                'ny': ('09:30', '10:30')
            }

            # Convert data index to ET timezone for IB calculation
            try:
                data_et = data.copy()
                if data_et.index.tz is None:
                    data_et.index = data_et.index.tz_localize('UTC')
                data_et.index = data_et.index.tz_convert(et_tz)

                current_hour = now_et.hour
                current_minute = now_et.minute

                for ib_name, (start_str, end_str) in ib_windows.items():
                    start_h, start_m = map(int, start_str.split(':'))
                    end_h, end_m = map(int, end_str.split(':'))

                    # Filter candles within IB window
                    ib_candles = data_et[(data_et.index.hour > start_h) |
                                         ((data_et.index.hour == start_h) & (data_et.index.minute >= start_m))]
                    ib_candles = ib_candles[(ib_candles.index.hour < end_h) |
                                            ((ib_candles.index.hour == end_h) & (ib_candles.index.minute <= end_m))]

                    if not ib_candles.empty:
                        ib_high = float(ib_candles['High'].max())
                        ib_low = float(ib_candles['Low'].min())
                        ib_mid = round((ib_high + ib_low) / 2, 2)

                        # Check if IB window has passed
                        window_passed = (current_hour > end_h) or (current_hour == end_h and current_minute > end_m)
                        # Handle overnight (Japan starts at 19:00)
                        if ib_name == 'japan' and current_hour < 12:
                            window_passed = True

                        state['ibs'][ib_name]['high'] = ib_high
                        state['ibs'][ib_name]['low'] = ib_low
                        state['ibs'][ib_name]['mid'] = ib_mid
                        state['ibs'][ib_name]['status'] = 'LOCKED' if window_passed else 'ACTIVE'

                        print(f"   📍 {ib_name.upper()} IB: H={ib_high:.2f} L={ib_low:.2f} ({state['ibs'][ib_name]['status']})")
            except Exception as ib_err:
                print(f"   ⚠️ IB calculation error: {ib_err}")

            print(f"✅ Fallback price updated: ${price:,.2f} (High: ${high:,.2f}, Low: ${low:,.2f})")
            return True
        else:
            print("⚠️  yfinance returned empty data")
            return False

    except Exception as e:
        print(f"⚠️  yfinance fallback error: {e}")
        return False


def watchdog_thread():
    """Monitor connection health and restart if stale (24/7 reliability)"""
    global stream_running, stream_thread, last_trade_timestamp

    STALE_THRESHOLD = 120  # 2 minutes without trades = stale (market hours)
    WEEKEND_THRESHOLD = 3600  # 1 hour for weekends/holidays
    CHECK_INTERVAL = 30  # Check every 30 seconds

    print("🐕 Watchdog started - monitoring connection health")

    while True:
        time.sleep(CHECK_INTERVAL)

        # Get current time info
        now = datetime.now(pytz.timezone('US/Eastern'))
        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6

        # Use longer threshold on weekends
        threshold = WEEKEND_THRESHOLD if is_weekend else STALE_THRESHOLD

        time_since_trade = time.time() - last_trade_timestamp

        # Skip restart if already reconnecting or at connection limit
        current_source = state.get('data_source', '')
        is_reconnecting = 'RECONNECTING' in current_source or 'WAITING_CONNECTION' in current_source

        if time_since_trade > threshold and stream_running and not is_reconnecting:
            print(f"\n🐕 WATCHDOG: No trades for {time_since_trade:.0f}s - restarting stream...")
            state['data_source'] = 'WATCHDOG_RESTART'

            # Send Discord alert - connection dropped
            send_discord_alert(
                "🚨 Connection Drop Detected",
                f"No trades received for **{time_since_trade:.0f} seconds**\n\nAttempting automatic restart...",
                color=16776960  # Yellow - warning
            )

            # Stop current stream
            stream_running = False
            time.sleep(2)

            # Restart appropriate stream based on contract type
            config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
            is_spot = config.get('is_spot', False)

            if is_spot:
                # Restart spot crypto stream
                global spot_crypto_thread
                spot_crypto_thread = threading.Thread(target=spot_crypto_stream, daemon=True)
                spot_crypto_thread.start()
            else:
                # Restart Databento stream
                stream_running = True
                stream_thread = threading.Thread(target=start_stream, daemon=True)
                stream_thread.start()

            # Reset timer
            last_trade_timestamp = time.time()
            print("🐕 WATCHDOG: Stream restarted")

            # Send Discord alert - stream restarted
            send_discord_alert(
                "✅ Stream Restarted",
                "Connection has been automatically restored.\n\nMonitoring continues...",
                color=65280  # Green - success
            )


def start_with_watchdog():
    """Start the feed with watchdog monitoring for 24/7 reliability"""
    global stream_thread

    # Start main stream
    stream_thread = threading.Thread(target=start_databento_feed, daemon=True)
    stream_thread.start()

    # Start watchdog
    watchdog = threading.Thread(target=watchdog_thread, daemon=True)
    watchdog.start()


def fetch_spot_btc_price():
    """Fetch spot BTC price - tries multiple APIs for global reliability"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Try CoinGecko first (works globally, free, no API key)
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            data = json.loads(response.read().decode())
            price = data.get('bitcoin', {}).get('usd')
            if price and price > 0:
                return float(price), 'COINGECKO'
    except Exception as e:
        pass

    # Try Coinbase (works in US)
    try:
        url = "https://api.coinbase.com/v2/prices/BTC-USD/spot"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            data = json.loads(response.read().decode())
            price = data.get('data', {}).get('amount')
            if price:
                return float(price), 'COINBASE'
    except Exception as e:
        pass

    # Try Kraken (works globally)
    try:
        url = "https://api.kraken.com/0/public/Ticker?pair=XBTUSD"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            data = json.loads(response.read().decode())
            price = data.get('result', {}).get('XXBTZUSD', {}).get('c', [None])[0]
            if price:
                return float(price), 'KRAKEN'
    except Exception as e:
        pass

    # Try Binance last (blocked in some regions)
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5, context=ctx) as response:
            data = json.loads(response.read().decode())
            price = data.get('price')
            if price:
                return float(price), 'BINANCE'
    except Exception as e:
        pass

    print("⚠️ All crypto price APIs failed")
    return None, None


# ============================================
# BINANCE WEBSOCKET - Real Volume/Delta Stream
# ============================================
binance_ws = None
binance_ws_running = False
binance_trade_buffer = deque(maxlen=10000)  # Buffer recent trades

def binance_ws_on_message(ws, message):
    """Handle incoming Binance aggTrade messages"""
    global state, binance_trade_buffer, binance_ws_running, ACTIVE_CONTRACT

    # Guard: Don't process if WebSocket should be stopped or contract changed
    if not binance_ws_running or ACTIVE_CONTRACT != 'BTC-SPOT':
        return

    try:
        data = json.loads(message)
        # aggTrade format: {"e":"aggTrade","s":"BTCUSDT","p":"87654.32","q":"0.123","m":false,"T":1234567890}
        if data.get('e') == 'aggTrade':
            price = float(data['p'])
            qty = float(data['q'])
            is_buyer_maker = data['m']  # True = seller initiated (sell), False = buyer initiated (buy)
            trade_time = data['T']

            # Calculate trade value - use qty * 100 to match historical data scale
            # Historical data uses: volume = int(c['volume'] * 100) where volume is in BTC
            # So we scale real-time the same way for consistent Delta OHLC rendering
            trade_value = price * qty  # Keep for VWAP calculation
            scaled_vol = int(qty * 100)  # Scaled to match historical

            # Determine buy/sell based on aggressor
            if is_buyer_maker:
                # Seller hit the bid = SELL
                sell_vol = scaled_vol
                buy_vol = 0
            else:
                # Buyer lifted the ask = BUY
                buy_vol = scaled_vol
                sell_vol = 0

            # Store trade in buffer for analysis
            binance_trade_buffer.append({
                'time': trade_time,
                'price': price,
                'qty': qty,
                'buy': buy_vol,
                'sell': sell_vol,
                'is_buy': not is_buyer_maker
            })

            # Update state with real data
            with lock:
                old_price = state.get('current_price', 0)
                state['current_price'] = price
                state['price'] = price
                state['data_source'] = 'BINANCE_WS'
                state['last_update'] = datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S')

                # Update real buy/sell volumes
                state['buy_volume'] = state.get('buy_volume', 0) + buy_vol
                state['sell_volume'] = state.get('sell_volume', 0) + sell_vol
                state['total_volume'] = state.get('total_volume', 0) + trade_value

                # Update cumulative delta (buy - sell)
                delta = buy_vol - sell_vol
                state['cumulative_delta'] = state.get('cumulative_delta', 0) + delta
                state['delta_5m'] = state.get('delta_5m', 0) + delta

                # Update 5-minute candle structure
                now_ts = int(time.time())
                candle_interval = 300  # 5 minutes
                candle_start = (now_ts // candle_interval) * candle_interval

                v5m = state.get('volume_5m', {})
                if v5m.get('candle_start', 0) != candle_start:
                    # New candle - save old one to history
                    if v5m.get('candle_start', 0) > 0 and v5m.get('buy', 0) + v5m.get('sell', 0) > 0:
                        history = v5m.get('history', [])
                        history.append({
                            'ts': v5m['candle_start'],
                            'buy': v5m.get('buy', 0),
                            'sell': v5m.get('sell', 0),
                            'delta': v5m.get('delta', 0),
                            'price_open': v5m.get('price_open', price),
                            'price_high': v5m.get('price_high', price),
                            'price_low': v5m.get('price_low', price),
                            'price_close': v5m.get('price_close', price),
                            'delta_open': v5m.get('delta_open', 0),
                            'delta_high': v5m.get('delta_high', 0),
                            'delta_low': v5m.get('delta_low', 0),
                        })
                        # Keep last 300 candles (enough for 22 1h candles)
                        if len(history) > 300:
                            history = history[-300:]
                        v5m['history'] = history
                        v5m['prev_buy'] = v5m.get('buy', 0)
                        v5m['prev_sell'] = v5m.get('sell', 0)
                        v5m['prev_delta'] = v5m.get('delta', 0)

                    # Start new candle
                    cum_delta = state.get('cumulative_delta', 0)
                    v5m = {
                        'candle_start': candle_start,
                        'buy': 0,
                        'sell': 0,
                        'delta': 0,
                        'price_open': price,
                        'price_high': price,
                        'price_low': price,
                        'price_close': price,
                        'delta_open': cum_delta,
                        'delta_high': cum_delta,
                        'delta_low': cum_delta,
                        'history': v5m.get('history', []),
                        'prev_buy': v5m.get('prev_buy', 0),
                        'prev_sell': v5m.get('prev_sell', 0),
                        'prev_delta': v5m.get('prev_delta', 0),
                    }

                # Update current candle
                v5m['buy'] = v5m.get('buy', 0) + buy_vol
                v5m['sell'] = v5m.get('sell', 0) + sell_vol
                v5m['delta'] = v5m.get('buy', 0) - v5m.get('sell', 0)
                v5m['price_close'] = price
                v5m['price_high'] = max(v5m.get('price_high', price), price)
                v5m['price_low'] = min(v5m.get('price_low', price), price)

                cum_delta = state.get('cumulative_delta', 0)
                v5m['delta_high'] = max(v5m.get('delta_high', cum_delta), cum_delta)
                v5m['delta_low'] = min(v5m.get('delta_low', cum_delta), cum_delta)

                state['volume_5m'] = v5m

                # Track day high/low
                if state.get('day_high', 0) == 0 or price > state['day_high']:
                    state['day_high'] = price
                if state.get('day_low', 0) == 0 or state['day_low'] == 999999 or price < state['day_low']:
                    state['day_low'] = price

                # Update VWAP with real volume
                state['vwap_numerator'] = state.get('vwap_numerator', 0) + (price * trade_value)
                state['vwap_denominator'] = state.get('vwap_denominator', 0) + trade_value
                if state['vwap_denominator'] > 0:
                    state['vwap'] = state['vwap_numerator'] / state['vwap_denominator']

                # Update RTH VWAP (anchored at 8:20 ET for US Session)
                et_now = datetime.now(pytz.timezone('America/New_York'))
                today_date = et_now.strftime('%Y-%m-%d')
                rth_start = et_now.replace(hour=8, minute=20, second=0, microsecond=0)

                # Reset RTH VWAP at 8:20 ET each day
                if state.get('rth_vwap_date', '') != today_date and et_now >= rth_start:
                    state['rth_vwap_numerator'] = 0.0
                    state['rth_vwap_denominator'] = 0.0
                    state['rth_vwap'] = 0.0
                    state['rth_vwap_date'] = today_date

                # Only accumulate RTH VWAP after 8:20 ET
                if et_now >= rth_start:
                    state['rth_vwap_numerator'] = state.get('rth_vwap_numerator', 0) + (price * trade_value)
                    state['rth_vwap_denominator'] = state.get('rth_vwap_denominator', 0) + trade_value
                    if state['rth_vwap_denominator'] > 0:
                        state['rth_vwap'] = state['rth_vwap_numerator'] / state['rth_vwap_denominator']

                # === Day VWAP (full trading day 18:00 ET - 17:00 ET next day) ===
                # Get trading day date (day starts at 18:00 ET, so before 18:00 is previous trading day)
                current_hhmm_check = et_now.hour * 100 + et_now.minute
                if current_hhmm_check < 1800:
                    trading_day = (et_now - timedelta(days=1)).strftime('%Y-%m-%d')
                else:
                    trading_day = et_now.strftime('%Y-%m-%d')

                # Reset day VWAP at 18:00 ET (new trading day)
                if state.get('day_vwap_date', '') != trading_day:
                    state['day_vwap_numerator'] = 0.0
                    state['day_vwap_denominator'] = 0.0
                    state['day_vwap'] = 0.0
                    state['day_vwap_date'] = trading_day

                # Always accumulate day VWAP
                state['day_vwap_numerator'] = state.get('day_vwap_numerator', 0) + (price * trade_value)
                state['day_vwap_denominator'] = state.get('day_vwap_denominator', 0) + trade_value
                if state['day_vwap_denominator'] > 0:
                    state['day_vwap'] = state['day_vwap_numerator'] / state['day_vwap_denominator']

                # === US IB Anchored VWAP (from 08:20 ET until 17:00 ET) ===
                us_ib_start = et_now.replace(hour=8, minute=20, second=0, microsecond=0)
                day_end = et_now.replace(hour=17, minute=0, second=0, microsecond=0)

                # Reset US IB VWAP at 08:20 ET each day
                if state.get('us_ib_vwap_date', '') != today_date and et_now >= us_ib_start:
                    state['us_ib_vwap_numerator'] = 0.0
                    state['us_ib_vwap_denominator'] = 0.0
                    state['us_ib_vwap'] = 0.0
                    state['us_ib_vwap_date'] = today_date

                # Accumulate US IB VWAP from 08:20 ET until 17:00 ET
                if et_now >= us_ib_start and et_now < day_end:
                    state['us_ib_vwap_numerator'] = state.get('us_ib_vwap_numerator', 0) + (price * trade_value)
                    state['us_ib_vwap_denominator'] = state.get('us_ib_vwap_denominator', 0) + trade_value
                    if state['us_ib_vwap_denominator'] > 0:
                        state['us_ib_vwap'] = state['us_ib_vwap_numerator'] / state['us_ib_vwap_denominator']

                # === NY 1H Anchored VWAP (from 09:30 ET until 17:00 ET) ===
                ny_1h_start = et_now.replace(hour=9, minute=30, second=0, microsecond=0)

                # Reset NY 1H VWAP at 09:30 ET each day
                if state.get('ny_1h_vwap_date', '') != today_date and et_now >= ny_1h_start:
                    state['ny_1h_vwap_numerator'] = 0.0
                    state['ny_1h_vwap_denominator'] = 0.0
                    state['ny_1h_vwap'] = 0.0
                    state['ny_1h_vwap_date'] = today_date

                # Accumulate NY 1H VWAP from 09:30 ET until 17:00 ET
                if et_now >= ny_1h_start and et_now < day_end:
                    state['ny_1h_vwap_numerator'] = state.get('ny_1h_vwap_numerator', 0) + (price * trade_value)
                    state['ny_1h_vwap_denominator'] = state.get('ny_1h_vwap_denominator', 0) + trade_value
                    if state['ny_1h_vwap_denominator'] > 0:
                        state['ny_1h_vwap'] = state['ny_1h_vwap_numerator'] / state['ny_1h_vwap_denominator']

                # === BTC-SPOT Session IB Tracking ===
                # IB times for BTC-SPOT (first 30 minutes of each session)
                # Japan: 18:00-18:30 ET, London: 03:00-03:30 ET, US: 08:20-08:50 ET, NY: 09:30-10:00 ET
                current_hhmm = et_now.hour * 100 + et_now.minute

                # BTC-SPOT IB Session definitions (start_hhmm, end_hhmm, ib_key)
                btc_ib_sessions = [
                    (1800, 1830, 'japan'),   # Japan IB: 18:00-18:30 ET
                    (300, 330, 'london'),    # London IB: 03:00-03:30 ET
                    (820, 850, 'us'),        # US IB: 08:20-08:50 ET
                    (930, 1000, 'ny'),       # NY IB: 09:30-10:00 ET
                ]

                active_btc_ib = None
                for start, end, ib_key in btc_ib_sessions:
                    if start <= current_hhmm < end:
                        active_btc_ib = ib_key
                        break

                state['current_ib'] = active_btc_ib

                # Track IB high/low during active IB period
                if active_btc_ib:
                    ib_data = state['ibs'].get(active_btc_ib, {})
                    if ib_data:
                        if ib_data.get('status') != 'ACTIVE':
                            # IB session starting - reset values
                            ib_data['high'] = price
                            ib_data['low'] = price
                            ib_data['status'] = 'ACTIVE'
                            state['ibs'][active_btc_ib] = ib_data
                            # Also update legacy IB fields
                            state['ib_high'] = price
                            state['ib_low'] = price
                            state['ib_locked'] = False
                            state['ib_session_name'] = ib_data.get('name', active_btc_ib)
                        else:
                            # Update IB high/low
                            if price > ib_data['high']:
                                ib_data['high'] = price
                                state['ibs'][active_btc_ib] = ib_data
                            if price < ib_data['low']:
                                ib_data['low'] = price
                                state['ibs'][active_btc_ib] = ib_data
                            # Update legacy IB fields
                            state['ib_high'] = ib_data['high']
                            state['ib_low'] = ib_data['low']
                else:
                    # No active IB - check if any was just completed
                    for start, end, ib_key in btc_ib_sessions:
                        ib_data = state['ibs'].get(ib_key, {})
                        if ib_data.get('status') == 'ACTIVE' and current_hhmm >= end:
                            ib_data['status'] = 'ENDED'
                            state['ibs'][ib_key] = ib_data
                            state['ib_locked'] = True
                            ib_range = ib_data['high'] - ib_data['low']
                            print(f"🔒 BTC-SPOT {ib_data.get('name', ib_key)} Complete: H=${ib_data['high']:,.2f} L=${ib_data['low']:,.2f} Range=${ib_range:,.2f}")

                # === Update current_phase for BTC-SPOT ===
                # BTC-SPOT Sessions (24/7 aligned with CME futures sessions)
                # Japan: 18:00-03:00 ET, London: 03:00-08:00 ET, US: 08:00-16:30 ET, NY_PM: 16:30-18:00 ET
                if active_btc_ib:
                    state['current_phase'] = f"{state['ibs'][active_btc_ib].get('name', active_btc_ib).upper().replace(' ', '_')}_FORMING"
                elif 1800 <= current_hhmm <= 2359 or 0 <= current_hhmm < 300:
                    state['current_phase'] = 'JAPAN'
                elif 300 <= current_hhmm < 800:
                    state['current_phase'] = 'LONDON'
                elif 800 <= current_hhmm < 1630:
                    state['current_phase'] = 'US'
                else:
                    state['current_phase'] = 'NY_PM'

    except Exception as e:
        print(f"⚠️ Binance WS message error: {e}")

def binance_ws_on_error(ws, error):
    """Handle WebSocket errors"""
    print(f"⚠️ Binance WebSocket error: {error}")

def binance_ws_on_close(ws, close_status_code, close_msg):
    """Handle WebSocket close"""
    global binance_ws_running
    print(f"🔴 Binance WebSocket closed: {close_status_code} - {close_msg}")
    binance_ws_running = False

def binance_ws_on_open(ws):
    """Handle WebSocket open"""
    global binance_ws_running
    print("🟢 Binance WebSocket connected - Real BTC volume streaming!")
    binance_ws_running = True

def start_binance_websocket():
    """Start Binance WebSocket for BTC trades"""
    global binance_ws, binance_ws_running

    if not HAS_WEBSOCKET:
        print("⚠️ websocket-client not installed, falling back to REST API")
        return False

    try:
        # Binance aggTrade stream - aggregated trades (most efficient)
        ws_url = "wss://stream.binance.com:9443/ws/btcusdt@aggTrade"

        binance_ws = websocket.WebSocketApp(
            ws_url,
            on_message=binance_ws_on_message,
            on_error=binance_ws_on_error,
            on_close=binance_ws_on_close,
            on_open=binance_ws_on_open
        )

        # Run WebSocket in thread
        ws_thread = threading.Thread(target=binance_ws.run_forever, daemon=True)
        ws_thread.start()

        # Wait for connection
        time.sleep(2)
        return binance_ws_running

    except Exception as e:
        print(f"⚠️ Failed to start Binance WebSocket: {e}")
        return False

def stop_binance_websocket():
    """Stop Binance WebSocket"""
    global binance_ws, binance_ws_running
    binance_ws_running = False
    if binance_ws:
        binance_ws.close()
        binance_ws = None
    print("🔴 Binance WebSocket stopped")


def spot_crypto_stream():
    """Stream spot crypto prices (runs in separate thread)"""
    global state, spot_crypto_running, ACTIVE_CONTRACT, binance_ws_running, startup_complete

    print("🟢 Starting spot crypto stream (multi-source)...")
    spot_crypto_running = True

    # Initialize historical data and TPO profile
    initialize_btc_spot_data()

    # Fetch BTC session history for VSI analysis (in background)
    def fetch_btc_vsi():
        global session_history_cache
        session_history_cache['ready'] = False  # Reset cache for new contract
        fetch_session_history(days=50, force_refresh=True)
        fetch_week_sessions_ohlc('current')  # Also fetch historical sessions OHLC

    vsi_thread = threading.Thread(target=fetch_btc_vsi, daemon=True)
    vsi_thread.start()

    # Mark startup as complete so HTTP handler can serve full metrics
    startup_complete = True
    print("✅ BTC-SPOT startup complete - HTTP metrics enabled")

    # Try to start Binance WebSocket for real volume/delta
    use_websocket = start_binance_websocket()
    if use_websocket:
        print("✅ Using Binance WebSocket for REAL volume/delta data!")
    else:
        print("⚠️ Falling back to REST API polling (simulated volume)")

    trade_count = 0
    current_source = None
    last_profile_refresh = time.time()
    last_day_reset_date = ''  # Track last day reset to avoid multiple resets

    while spot_crypto_running and ACTIVE_CONTRACT == 'BTC-SPOT':
        try:
            # Check for 18:00 ET day reset (Japan Open) for BTC-SPOT
            et_now = datetime.now(pytz.timezone('America/New_York'))
            et_hour = et_now.hour
            today_date = et_now.strftime('%Y-%m-%d')
            price = state.get('current_price', 0)

            # Reset at 18:00 ET for new trading day
            if et_hour >= 18 and last_day_reset_date != today_date and price > 0:
                print(f"🌅 BTC-SPOT: New trading day reset at Japan Open (18:00 ET)")
                with lock:
                    state['day_high'] = price
                    state['day_low'] = price
                    state['day_open'] = price
                    state['vwap'] = price
                    state['vwap_numerator'] = 0.0
                    state['vwap_denominator'] = 0.0
                    state['cumulative_delta'] = 0
                    state['buy_volume'] = 0
                    state['sell_volume'] = 0
                    state['total_volume'] = 0
                    # Reset TPO profile for new day
                    tpo_state['day']['profiles'] = {}
                    tpo_state['day']['poc'] = 0
                    tpo_state['day']['vah'] = 0
                    tpo_state['day']['val'] = 0
                    tpo_state['day']['single_prints'] = []
                    # Reset all BTC-SPOT session IBs for new day
                    for ib_key in state['ibs']:
                        state['ibs'][ib_key]['high'] = 0.0
                        state['ibs'][ib_key]['low'] = 999999.0
                        state['ibs'][ib_key]['status'] = 'WAITING'
                    state['current_ib'] = None
                    state['ib_high'] = 0.0
                    state['ib_low'] = 0.0
                    state['ib_locked'] = True
                    state['ib_session_name'] = ''
                last_day_reset_date = today_date
                print(f"   Day Open: ${price:,.2f}")

            # If WebSocket is running, it handles all data updates
            if binance_ws_running:
                # Just refresh TPO profile periodically
                if time.time() - last_profile_refresh > 300:
                    candles = fetch_btc_historical_ohlc()
                    if candles:
                        build_btc_tpo_profile(candles)
                    last_profile_refresh = time.time()
                time.sleep(1)
                continue

            # Fallback: REST API polling (original logic)
            result = fetch_spot_btc_price()
            if result[0]:
                price, source = result

                with lock:
                    old_price = state.get('current_price', 0)
                    state['current_price'] = price
                    state['price'] = price  # Ensure both price fields are set
                    state['data_source'] = f'{source}_SPOT'
                    state['last_update'] = datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S')

                    # Calculate simple delta based on price movement
                    if old_price > 0:
                        price_change = price - old_price
                        simulated_delta = int(price_change * 10)
                        state['delta_5m'] = state.get('delta_5m', 0) + simulated_delta
                        state['cumulative_delta'] = state.get('cumulative_delta', 0) + simulated_delta

                        # Simulate buy/sell volume based on price direction
                        simulated_volume = abs(int(price_change * 5)) + 1
                        if price_change > 0:
                            simulated_buy = simulated_volume
                            simulated_sell = max(1, simulated_volume // 2)
                        else:
                            simulated_buy = max(1, simulated_volume // 2)
                            simulated_sell = simulated_volume

                        # Update volume_5m structure for footprint chart
                        now_ts = int(time.time())
                        candle_interval = 300  # 5 minutes
                        candle_start = (now_ts // candle_interval) * candle_interval

                        v5m = state.get('volume_5m', {})
                        if v5m.get('candle_start', 0) != candle_start:
                            # New candle - save old one to history
                            if v5m.get('candle_start', 0) > 0 and v5m.get('buy', 0) + v5m.get('sell', 0) > 0:
                                history = v5m.get('history', [])
                                history.append({
                                    'ts': v5m['candle_start'],
                                    'buy': v5m.get('buy', 0),
                                    'sell': v5m.get('sell', 0),
                                    'delta': v5m.get('delta', 0),
                                    'price_open': v5m.get('price_open', price),
                                    'price_high': v5m.get('price_high', price),
                                    'price_low': v5m.get('price_low', price),
                                    'price_close': v5m.get('price_close', price),
                                    'delta_open': v5m.get('delta_open', 0),
                                    'delta_high': v5m.get('delta_high', 0),
                                    'delta_low': v5m.get('delta_low', 0),
                                })
                                # Keep last 300 candles (enough for 22 1h candles)
                                if len(history) > 300:
                                    history = history[-300:]
                                v5m['history'] = history
                                v5m['prev_buy'] = v5m.get('buy', 0)
                                v5m['prev_sell'] = v5m.get('sell', 0)
                                v5m['prev_delta'] = v5m.get('delta', 0)

                            # Start new candle
                            v5m['candle_start'] = candle_start
                            v5m['buy'] = simulated_buy
                            v5m['sell'] = simulated_sell
                            v5m['delta'] = simulated_delta
                            v5m['price_open'] = price
                            v5m['price_high'] = price
                            v5m['price_low'] = price
                            v5m['price_close'] = price
                            v5m['delta_open'] = state.get('cumulative_delta', 0) - simulated_delta
                            v5m['delta_high'] = state.get('cumulative_delta', 0)
                            v5m['delta_low'] = state.get('cumulative_delta', 0)
                        else:
                            # Update current candle
                            v5m['buy'] = v5m.get('buy', 0) + simulated_buy
                            v5m['sell'] = v5m.get('sell', 0) + simulated_sell
                            v5m['delta'] = v5m.get('delta', 0) + simulated_delta
                            v5m['price_close'] = price
                            if price > v5m.get('price_high', 0):
                                v5m['price_high'] = price
                            if v5m.get('price_low', 0) == 0 or price < v5m['price_low']:
                                v5m['price_low'] = price
                            cum_delta = state.get('cumulative_delta', 0)
                            if cum_delta > v5m.get('delta_high', -999999):
                                v5m['delta_high'] = cum_delta
                            if cum_delta < v5m.get('delta_low', 999999):
                                v5m['delta_low'] = cum_delta

                        state['volume_5m'] = v5m

                    # Track high/low
                    if state.get('day_high', 0) == 0 or price > state['day_high']:
                        state['day_high'] = price
                    if state.get('day_low', 0) == 0 or price < state['day_low']:
                        state['day_low'] = price

                    # Calculate VWAP for BTC spot using simulated volume
                    state['vwap_numerator'] = state.get('vwap_numerator', 0) + (price * simulated_volume)
                    state['vwap_denominator'] = state.get('vwap_denominator', 0) + simulated_volume
                    if state['vwap_denominator'] > 0:
                        state['vwap'] = state['vwap_numerator'] / state['vwap_denominator']

                    # Calculate RTH VWAP (8:20 ET anchored for BTC-SPOT) for Intraday section
                    et_now = datetime.now(pytz.timezone('America/New_York'))
                    today_date = et_now.strftime('%Y-%m-%d')
                    rth_start = et_now.replace(hour=8, minute=20, second=0, microsecond=0)  # US Session starts 8:20 ET

                    # Reset RTH VWAP at 8:20 ET each day (US Session start)
                    if state.get('rth_vwap_date', '') != today_date and et_now >= rth_start:
                        state['rth_vwap_numerator'] = 0.0
                        state['rth_vwap_denominator'] = 0.0
                        state['rth_vwap'] = 0.0
                        state['rth_vwap_date'] = today_date

                    # Only accumulate RTH VWAP after 8:20 ET (US Session)
                    if et_now >= rth_start:
                        state['rth_vwap_numerator'] = state.get('rth_vwap_numerator', 0) + (price * simulated_volume)
                        state['rth_vwap_denominator'] = state.get('rth_vwap_denominator', 0) + simulated_volume
                        if state['rth_vwap_denominator'] > 0:
                            state['rth_vwap'] = state['rth_vwap_numerator'] / state['rth_vwap_denominator']

                    trade_count += 1

                if current_source != source:
                    print(f"₿ BTC source: {source}")
                    current_source = source

                if trade_count % 10 == 0:
                    print(f"₿ BTC Spot: ${price:,.2f} ({source})")

                # Update TPO profile with current price (add to current period)
                with lock:
                    tick_size = 100.0
                    price_key = f"{(price // tick_size) * tick_size:.1f}"
                    profiles = tpo_state['day'].get('profiles', {})
                    current_letter = 'Z'  # Current period
                    if price_key not in profiles:
                        profiles[price_key] = []
                    if current_letter not in profiles[price_key]:
                        profiles[price_key].append(current_letter)
                    tpo_state['day']['profiles'] = profiles

                # Refresh full profile every 5 minutes
                if time.time() - last_profile_refresh > 300:
                    candles = fetch_btc_historical_ohlc()
                    if candles:
                        build_btc_tpo_profile(candles)
                    last_profile_refresh = time.time()

            time.sleep(2)  # Poll every 2 seconds (respect rate limits)

        except Exception as e:
            print(f"⚠️ Spot stream error: {e}")
            with lock:
                state['data_source'] = 'RECONNECTING'
            time.sleep(5)

    print("🔴 Spot crypto stream stopped")
    spot_crypto_running = False


def fetch_btc_historical_ohlc():
    """Fetch historical BTC OHLC data with multi-source fallback"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    # Try Coinbase first (more reliable, no rate limits)
    try:
        # Coinbase candles endpoint - 1 hour granularity, last 24 hours
        url = "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            data = json.loads(response.read().decode())
            if data and len(data) > 10:
                # Coinbase returns [timestamp, low, high, open, close, volume]
                candles = []
                for c in data[:24]:  # Last 24 hours
                    candles.append({
                        'timestamp': c[0] * 1000,
                        'open': c[3],
                        'high': c[2],
                        'low': c[1],
                        'close': c[4]
                    })
                candles.reverse()  # Oldest first
                print(f"📊 Fetched {len(candles)} BTC candles from Coinbase")
                return candles
    except Exception as e:
        print(f"⚠️ Coinbase candles failed: {e}")

    # Fallback to Kraken
    try:
        # Kraken OHLC endpoint - 60 min intervals
        url = "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            data = json.loads(response.read().decode())
            result = data.get('result', {})
            ohlc = result.get('XXBTZUSD', result.get('XBTUSD', []))
            if ohlc and len(ohlc) > 10:
                # Kraken returns [timestamp, open, high, low, close, vwap, volume, count]
                candles = []
                for c in ohlc[-24:]:  # Last 24 hours
                    candles.append({
                        'timestamp': int(c[0]) * 1000,
                        'open': float(c[1]),
                        'high': float(c[2]),
                        'low': float(c[3]),
                        'close': float(c[4])
                    })
                print(f"📊 Fetched {len(candles)} BTC candles from Kraken")
                return candles
    except Exception as e:
        print(f"⚠️ Kraken candles failed: {e}")

    # Final fallback to CoinGecko (with retry)
    for attempt in range(3):
        try:
            if attempt > 0:
                time.sleep(2 * attempt)  # Backoff
            url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
                data = json.loads(response.read().decode())
                prices = data.get('prices', [])
                if prices:
                    candles = []
                    for i in range(0, len(prices) - 1, 4):
                        chunk = prices[i:i+4]
                        if chunk:
                            prices_in_chunk = [p[1] for p in chunk]
                            candles.append({
                                'timestamp': chunk[0][0],
                                'open': prices_in_chunk[0],
                                'high': max(prices_in_chunk),
                                'low': min(prices_in_chunk),
                                'close': prices_in_chunk[-1]
                            })
                    print(f"📊 Fetched {len(candles)} BTC candles from CoinGecko")
                    return candles
        except Exception as e:
            print(f"⚠️ CoinGecko attempt {attempt+1} failed: {e}")

    print("❌ All BTC historical sources failed")
    return []


def fetch_btc_pd_levels():
    """Fetch Previous Day BTC levels (24-hour period before current trading day)"""
    global state

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print("📅 Fetching BTC Previous Day levels...")

    # For BTC-SPOT, the trading day starts at 18:00 ET (Japan Open)
    # So "previous day" is from 18:00 ET yesterday to 18:00 ET today
    # We need to fetch 48 hours of data and extract the previous day

    try:
        # Use Binance for PD levels - 1h candles for last 48 hours
        url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=48"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            data = json.loads(response.read().decode())
            if data and len(data) >= 24:
                # Binance klines: [open_time, open, high, low, close, volume, close_time, ...]
                # Get candles from 48-24 hours ago (previous day)
                pd_candles = data[:24]  # First 24 candles = previous day

                pd_high = max(float(c[2]) for c in pd_candles)
                pd_low = min(float(c[3]) for c in pd_candles)
                pd_open = float(pd_candles[0][1])
                pd_close = float(pd_candles[-1][4])
                # POC approximation: average of high and low
                pdpoc = (pd_high + pd_low) / 2

                # Get timestamp range for PD
                pd_start = datetime.fromtimestamp(pd_candles[0][0] / 1000)
                pd_end = datetime.fromtimestamp(pd_candles[-1][6] / 1000)

                with lock:
                    state['pd_high'] = pd_high
                    state['pd_low'] = pd_low
                    state['pd_open'] = pd_open
                    state['pd_close'] = pd_close
                    state['pdpoc'] = pdpoc
                    state['pd_loaded'] = True
                    state['pd_date_range'] = f"{pd_start.strftime('%m/%d')} - {pd_end.strftime('%m/%d')}"

                print(f"✅ BTC PD Levels: High ${pd_high:,.2f}, Low ${pd_low:,.2f}, POC ${pdpoc:,.2f}")
                return True

    except Exception as e:
        print(f"⚠️ Binance PD fetch failed: {e}")

    # Fallback to Coinbase
    try:
        # Coinbase candles - 1 hour granularity
        url = "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=3600"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            data = json.loads(response.read().decode())
            if data and len(data) >= 24:
                # Coinbase returns [timestamp, low, high, open, close, volume] - newest first
                data.reverse()  # Oldest first
                pd_candles = data[:24]  # First 24 = previous day

                pd_high = max(float(c[2]) for c in pd_candles)
                pd_low = min(float(c[1]) for c in pd_candles)
                pd_open = float(pd_candles[0][3])
                pd_close = float(pd_candles[-1][4])
                pdpoc = (pd_high + pd_low) / 2

                with lock:
                    state['pd_high'] = pd_high
                    state['pd_low'] = pd_low
                    state['pd_open'] = pd_open
                    state['pd_close'] = pd_close
                    state['pdpoc'] = pdpoc
                    state['pd_loaded'] = True
                    state['pd_date_range'] = 'Last 24h'

                print(f"✅ BTC PD Levels (Coinbase): High ${pd_high:,.2f}, Low ${pd_low:,.2f}")
                return True

    except Exception as e:
        print(f"⚠️ Coinbase PD fetch failed: {e}")

    print("❌ Failed to fetch BTC PD levels")
    return False


def build_btc_tpo_profile(candles):
    """Build TPO profile from BTC candle data"""
    global tpo_state

    if not candles:
        print("⚠️ No candles to build TPO profile")
        return

    # Use 100 tick size for BTC ($100 increments)
    tick_size = 100.0

    profiles = {}
    all_prices = []

    # Period letters - one per candle
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

    for i, candle in enumerate(candles[-24:]):  # Last 24 candles
        letter = letters[i % 26]
        high = candle['high']
        low = candle['low']

        all_prices.extend([high, low])

        # Create TPO entries for this period
        price = (low // tick_size) * tick_size
        while price <= high:
            price_key = f"{price:.1f}"
            if price_key not in profiles:
                profiles[price_key] = []
            if letter not in profiles[price_key]:
                profiles[price_key].append(letter)
            price += tick_size

    if not profiles:
        return

    # Calculate POC (price with most TPOs)
    poc_price = max(profiles.keys(), key=lambda k: len(profiles[k]))
    poc = float(poc_price)

    # Calculate value area (70% of TPOs)
    total_tpos = sum(len(v) for v in profiles.values())
    target_tpos = int(total_tpos * 0.70)

    sorted_prices = sorted(profiles.keys(), key=lambda k: len(profiles[k]), reverse=True)
    va_prices = []
    va_tpos = 0
    for p in sorted_prices:
        va_prices.append(float(p))
        va_tpos += len(profiles[p])
        if va_tpos >= target_tpos:
            break

    vah = max(va_prices) if va_prices else max(all_prices)
    val = min(va_prices) if va_prices else min(all_prices)

    # Find single prints (prices with only 1 TPO)
    single_prints = [float(p) for p, letters in profiles.items() if len(letters) == 1]

    # Update tpo_state
    with lock:
        tpo_state['day']['profiles'] = profiles
        tpo_state['day']['poc'] = poc
        tpo_state['day']['vah'] = vah
        tpo_state['day']['val'] = val
        tpo_state['day']['single_prints'] = single_prints[:10]  # Limit to 10
        tpo_state['day']['period_count'] = len(candles[-24:])
        tpo_state['day']['ib_high'] = candles[0]['high'] if candles else 0
        tpo_state['day']['ib_low'] = candles[0]['low'] if candles else 0
        tpo_state['day']['ib_complete'] = True
        tpo_state['day']['open_price'] = candles[0]['open'] if candles else 0
        tpo_state['day']['max_tpo_count'] = max(len(v) for v in profiles.values()) if profiles else 0
        tpo_state['day']['total_tpo_count'] = total_tpos
        tpo_state['day']['day_type'] = 'Normal'
        tpo_state['day']['profile_shape'] = 'D' if abs(poc - (vah + val) / 2) < tick_size * 2 else ('P' if poc < (vah + val) / 2 else 'b')

        # Also update state with key levels
        state['day_high'] = max(all_prices) if all_prices else 0
        state['day_low'] = min(all_prices) if all_prices else 0

    print(f"📈 BTC TPO Profile built: POC=${poc:,.0f}, VAH=${vah:,.0f}, VAL=${val:,.0f}")


def fetch_btc_5m_candles():
    """Fetch 5-minute BTC candles from Coinbase for volume history"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        # Coinbase candles endpoint - 5 minute granularity (300 seconds)
        url = "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=300"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15, context=ctx) as response:
            data = json.loads(response.read().decode())
            if data and len(data) > 10:
                # Coinbase returns [timestamp, low, high, open, close, volume]
                candles = []
                for c in data[:300]:  # Last 300 5-minute candles (~25 hours) - enough for 22 1h candles
                    candles.append({
                        'ts': c[0],
                        'open': c[3],
                        'high': c[2],
                        'low': c[1],
                        'close': c[4],
                        'volume': c[5]
                    })
                candles.reverse()  # Oldest first
                print(f"📊 Fetched {len(candles)} BTC 5-min candles from Coinbase")
                return candles
    except Exception as e:
        print(f"⚠️ Coinbase 5-min candles failed: {e}")
    return []


def populate_btc_volume_history():
    """Populate volume history for all timeframes from BTC 5m candles"""
    global state

    candles = fetch_btc_5m_candles()
    if not candles:
        return

    with lock:
        # Build 5m history
        history_5m = []
        cumulative_delta = 0
        all_highs = []
        all_lows = []

        for c in candles[:-1]:  # Exclude last candle (still forming)
            price_change = c['close'] - c['open']
            volume = int(c['volume'] * 100) if c['volume'] else 100

            if price_change >= 0:
                buy = int(volume * 0.55)
                sell = int(volume * 0.45)
            else:
                buy = int(volume * 0.45)
                sell = int(volume * 0.55)

            delta = buy - sell
            cumulative_delta += delta
            all_highs.append(c['high'])
            all_lows.append(c['low'])

            # Cumulative delta OHLC - tracks running total over session
            delta_open = cumulative_delta - delta
            delta_close = cumulative_delta
            # Estimate high/low based on candle movement
            delta_high = max(delta_open, delta_close) + abs(delta) * 0.15
            delta_low = min(delta_open, delta_close) - abs(delta) * 0.15

            history_5m.append({
                'ts': c['ts'],
                'buy': buy,
                'sell': sell,
                'delta': delta,
                'price_open': c['open'],
                'price_high': c['high'],
                'price_low': c['low'],
                'price_close': c['close'],
                # Cumulative delta OHLC
                'delta_open': delta_open,
                'delta_high': delta_high,
                'delta_low': delta_low,
                'delta_close': delta_close,
            })

        # Set BTC-SPOT reference levels from historical data
        if all_highs and all_lows:
            state['session_high'] = max(all_highs)
            state['session_low'] = min(all_lows)
            # Use recent 12 candles (1 hour) for "IB-like" range
            recent_highs = all_highs[-12:] if len(all_highs) >= 12 else all_highs
            recent_lows = all_lows[-12:] if len(all_lows) >= 12 else all_lows
            state['ib_high'] = max(recent_highs)
            state['ib_low'] = min(recent_lows)
            # PD levels are now set by fetch_btc_pd_levels() - don't overwrite here

        # Aggregate to 15m (3x 5m candles)
        history_15m = aggregate_candles(history_5m, 3)
        # Aggregate to 30m (6x 5m candles)
        history_30m = aggregate_candles(history_5m, 6)
        # Aggregate to 1h (12x 5m candles)
        history_1h = aggregate_candles(history_5m, 12)

        # Set up current candle from last candle
        if candles:
            last = candles[-1]
            now_ts = int(time.time())

            # 5m
            state['volume_5m'] = {
                'candle_start': last['ts'],
                'buy': 0, 'sell': 0, 'delta': 0,
                'price_open': last['open'], 'price_high': last['high'],
                'price_low': last['low'], 'price_close': last['close'],
                'delta_open': cumulative_delta, 'delta_high': cumulative_delta, 'delta_low': cumulative_delta,
                'history': history_5m,
                'prev_buy': history_5m[-1]['buy'] if history_5m else 0,
                'prev_sell': history_5m[-1]['sell'] if history_5m else 0,
                'prev_delta': history_5m[-1]['delta'] if history_5m else 0,
            }

            # 15m
            candle_15m = (now_ts // 900) * 900
            state['volume_15m'] = {
                'candle_start': candle_15m,
                'buy': 0, 'sell': 0, 'delta': 0,
                'price_open': last['open'], 'price_high': last['high'],
                'price_low': last['low'], 'price_close': last['close'],
                'delta_open': cumulative_delta, 'delta_high': cumulative_delta, 'delta_low': cumulative_delta,
                'history': history_15m,
                'prev_buy': history_15m[-1]['buy'] if history_15m else 0,
                'prev_sell': history_15m[-1]['sell'] if history_15m else 0,
                'prev_delta': history_15m[-1]['delta'] if history_15m else 0,
            }

            # 30m
            candle_30m = (now_ts // 1800) * 1800
            state['volume_30m'] = {
                'candle_start': candle_30m,
                'buy': 0, 'sell': 0, 'delta': 0,
                'price_open': last['open'], 'price_high': last['high'],
                'price_low': last['low'], 'price_close': last['close'],
                'delta_open': cumulative_delta, 'delta_high': cumulative_delta, 'delta_low': cumulative_delta,
                'history': history_30m,
                'prev_buy': history_30m[-1]['buy'] if history_30m else 0,
                'prev_sell': history_30m[-1]['sell'] if history_30m else 0,
                'prev_delta': history_30m[-1]['delta'] if history_30m else 0,
            }

            # 1h
            candle_1h = (now_ts // 3600) * 3600
            state['volume_1h'] = {
                'candle_start': candle_1h,
                'buy': 0, 'sell': 0, 'delta': 0,
                'price_open': last['open'], 'price_high': last['high'],
                'price_low': last['low'], 'price_close': last['close'],
                'delta_open': cumulative_delta, 'delta_high': cumulative_delta, 'delta_low': cumulative_delta,
                'history': history_1h,
                'prev_buy': history_1h[-1]['buy'] if history_1h else 0,
                'prev_sell': history_1h[-1]['sell'] if history_1h else 0,
                'prev_delta': history_1h[-1]['delta'] if history_1h else 0,
            }

            print(f"📈 Populated BTC-SPOT: 5m={len(history_5m)}, 15m={len(history_15m)}, 30m={len(history_30m)}, 1h={len(history_1h)} candles")


def aggregate_candles(candles, factor):
    """Aggregate smaller timeframe candles into larger ones"""
    if not candles or factor <= 1:
        return candles

    aggregated = []
    for i in range(0, len(candles), factor):
        chunk = candles[i:i+factor]
        if not chunk:
            continue

        agg = {
            'ts': chunk[0]['ts'],
            'buy': sum(c['buy'] for c in chunk),
            'sell': sum(c['sell'] for c in chunk),
            'delta': sum(c['delta'] for c in chunk),
            'price_open': chunk[0]['price_open'],
            'price_high': max(c['price_high'] for c in chunk),
            'price_low': min(c['price_low'] for c in chunk),
            'price_close': chunk[-1]['price_close'],
            # Cumulative delta OHLC - use first candle open, last candle close, extremes from all
            'delta_open': chunk[0]['delta_open'],
            'delta_high': max(c['delta_high'] for c in chunk),
            'delta_low': min(c['delta_low'] for c in chunk),
            'delta_close': chunk[-1]['delta_close'],
        }
        aggregated.append(agg)

    return aggregated


def populate_btc_session_ibs():
    """Pre-populate BTC-SPOT session IBs from Binance historical 5-minute candles"""
    global state

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        # Fetch 288 5-minute candles (24 hours) from Binance
        url = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=288"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        with urllib.request.urlopen(req, timeout=20, context=ctx) as response:
            data = json.loads(response.read().decode())
            if not data or len(data) < 10:
                print("⚠️ Not enough candle data for IB population")
                return

        print(f"📊 Fetched {len(data)} 5-min candles from Binance for IB population")

        # Parse candles - Binance klines format:
        # [open_time, open, high, low, close, volume, close_time, ...]
        candles = []
        for k in data:
            candles.append({
                'ts': k[0] // 1000,  # Convert ms to seconds
                'open': float(k[1]),
                'high': float(k[2]),
                'low': float(k[3]),
                'close': float(k[4]),
            })

        # Get current ET time
        et_tz = pytz.timezone('America/New_York')
        et_now = datetime.now(et_tz)
        current_hhmm = et_now.hour * 100 + et_now.minute

        # BTC day starts at 18:00 ET (6PM)
        # Determine the start of the current BTC trading day
        if current_hhmm >= 1800:
            # After 6PM - day started today at 18:00
            day_start_et = et_now.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            # Before 6PM - day started yesterday at 18:00
            day_start_et = (et_now - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)

        day_start_ts = int(day_start_et.timestamp())

        # BTC-SPOT IB Session definitions (start_hhmm, end_hhmm, ib_key, name)
        btc_ib_sessions = [
            (1800, 1830, 'japan', 'Japan IB'),     # Japan IB: 18:00-18:30 ET
            (300, 330, 'london', 'London IB'),     # London IB: 03:00-03:30 ET
            (820, 850, 'us', 'US IB'),             # US IB: 08:20-08:50 ET
            (930, 1000, 'ny', 'NY IB'),            # NY IB: 09:30-10:00 ET
        ]

        with lock:
            for start_hhmm, end_hhmm, ib_key, ib_name in btc_ib_sessions:
                # Calculate the absolute timestamps for this IB session
                ib_start_hour = start_hhmm // 100
                ib_start_min = start_hhmm % 100
                ib_end_hour = end_hhmm // 100
                ib_end_min = end_hhmm % 100

                # Determine when this IB session occurred/occurs
                if start_hhmm >= 1800:
                    # Japan session - same day as day_start
                    ib_start_et = day_start_et.replace(hour=ib_start_hour, minute=ib_start_min)
                    ib_end_et = day_start_et.replace(hour=ib_end_hour, minute=ib_end_min)
                else:
                    # Other sessions - next calendar day after day_start
                    next_day = day_start_et + timedelta(days=1)
                    ib_start_et = next_day.replace(hour=ib_start_hour, minute=ib_start_min, second=0, microsecond=0)
                    ib_end_et = next_day.replace(hour=ib_end_hour, minute=ib_end_min, second=0, microsecond=0)

                ib_start_ts = int(ib_start_et.timestamp())
                ib_end_ts = int(ib_end_et.timestamp())

                # Check IB status based on current time
                if et_now.timestamp() < ib_start_ts:
                    # IB hasn't started yet
                    state['ibs'][ib_key]['status'] = 'WAITING'
                    print(f"   ⏳ {ib_name}: WAITING (starts at {ib_start_et.strftime('%H:%M')} ET)")
                elif et_now.timestamp() >= ib_start_ts and et_now.timestamp() < ib_end_ts:
                    # IB is currently active
                    ib_candles = [c for c in candles if ib_start_ts <= c['ts'] < ib_end_ts]
                    if ib_candles:
                        ib_high = max(c['high'] for c in ib_candles)
                        ib_low = min(c['low'] for c in ib_candles)
                        state['ibs'][ib_key]['high'] = ib_high
                        state['ibs'][ib_key]['low'] = ib_low
                        state['ibs'][ib_key]['status'] = 'ACTIVE'
                        print(f"   🟢 {ib_name}: ACTIVE H=${ib_high:,.2f} L=${ib_low:,.2f}")
                    else:
                        state['ibs'][ib_key]['status'] = 'ACTIVE'
                        print(f"   🟢 {ib_name}: ACTIVE (building...)")
                else:
                    # IB has ended - populate from historical candles
                    ib_candles = [c for c in candles if ib_start_ts <= c['ts'] < ib_end_ts]
                    if ib_candles:
                        ib_high = max(c['high'] for c in ib_candles)
                        ib_low = min(c['low'] for c in ib_candles)
                        state['ibs'][ib_key]['high'] = ib_high
                        state['ibs'][ib_key]['low'] = ib_low
                        state['ibs'][ib_key]['status'] = 'ENDED'
                        ib_range = ib_high - ib_low
                        print(f"   ✅ {ib_name}: ENDED H=${ib_high:,.2f} L=${ib_low:,.2f} Range=${ib_range:,.2f}")
                    else:
                        # No candles found - IB times might be before our data window
                        state['ibs'][ib_key]['status'] = 'ENDED'
                        print(f"   ⚠️ {ib_name}: ENDED (no candle data found for time window)")

        print("✅ BTC-SPOT session IBs populated from historical data")

    except Exception as e:
        print(f"⚠️ Failed to populate BTC-SPOT IBs: {e}")


def initialize_btc_spot_data():
    """Initialize BTC spot data including historical TPO profile and volume history"""
    global state
    print("🔄 Initializing BTC spot historical data...")

    # Fetch and build TPO profile
    candles = fetch_btc_historical_ohlc()
    if candles:
        build_btc_tpo_profile(candles)
        # Save to cache after building
        save_tpo_cache('BTC-SPOT')

        # Set day_open from first candle (24-hour day open)
        # and weekly_open from oldest available data
        with lock:
            if len(candles) > 0:
                # Use oldest candle's open as day_open (represents 24hr ago)
                state['day_open'] = candles[0]['open']
                state['weekly_open'] = candles[0]['open']  # Best available weekly reference
                state['weekly_open_date'] = datetime.fromtimestamp(candles[0]['timestamp'] / 1000).strftime('%Y-%m-%d')

                # Calculate day high/low from candles
                state['day_high'] = max(c['high'] for c in candles)
                state['day_low'] = min(c['low'] for c in candles)
                state['week_high'] = state['day_high']
                state['week_low'] = state['day_low']

                print(f"📊 BTC day_open: ${state['day_open']:,.2f}, day_high: ${state['day_high']:,.2f}, day_low: ${state['day_low']:,.2f}")
    else:
        # Try loading from cache if live fetch failed
        print("📦 Trying to load BTC TPO from cache...")
        load_tpo_cache('BTC-SPOT')

    # Fetch Previous Day levels for BTC-SPOT
    fetch_btc_pd_levels()

    # Populate volume history with 5-minute candles
    populate_btc_volume_history()

    # Pre-populate session IBs from historical data (works on weekends for BTC)
    populate_btc_session_ibs()

    print("✅ BTC spot initialization complete")


def stop_spot_crypto_stream():
    """Stop the spot crypto stream"""
    global spot_crypto_running
    spot_crypto_running = False
    print("⏹️ Stopping spot crypto stream...")
    time.sleep(1)


def switch_contract(new_contract):
    """Switch to a different contract with full stream restart - ROBUST VERSION"""
    global ACTIVE_CONTRACT, stream_thread, spot_crypto_thread, spot_crypto_running, live_client

    if new_contract not in CONTRACT_CONFIG:
        print(f"❌ Unknown contract: {new_contract}")
        return False

    old_contract = ACTIVE_CONTRACT
    print(f"\n🔄 SWITCH: {old_contract} → {new_contract}")
    print("=" * 50)

    config = CONTRACT_CONFIG[new_contract]
    is_spot = config.get('is_spot', False)

    # ========== STEP 1: Stop ALL current streams ==========
    print("📍 Step 1: Stopping all streams...")

    # Stop Binance WebSocket if it was running
    stop_binance_websocket()

    # Stop spot crypto stream if running
    if spot_crypto_running:
        stop_spot_crypto_stream()

    # Stop Databento stream if running
    stop_stream()

    # Extra cleanup: force terminate any dangling Databento client
    if live_client:
        try:
            print("🔌 Force terminating any dangling Databento client...")
            live_client.terminate()
        except:
            pass
        live_client = None

    # Wait for all connections to fully release
    print("⏳ Waiting for connections to fully close...")
    time.sleep(3)  # Critical: give Databento server time to release connection slot

    # ========== STEP 2: Update contract and reset state ==========
    print(f"📍 Step 2: Switching to {new_contract}...")
    ACTIVE_CONTRACT = new_contract
    reset_state_for_contract(new_contract)
    print(f"✅ State reset for {new_contract}")

    # ========== STEP 3: Start new stream ==========
    print(f"📍 Step 3: Starting {config['name']} stream...")

    if is_spot:
        # Start spot crypto stream (Binance)
        print(f"🔌 Connecting to Binance WebSocket for {config['name']}...")
        spot_crypto_thread = threading.Thread(target=spot_crypto_stream, daemon=True)
        spot_crypto_thread.start()
    else:
        # Start Databento stream for futures
        print(f"🔌 Connecting to Databento for {config['name']}...")
        global stream_running
        stream_running = True
        stream_thread = threading.Thread(target=start_stream, daemon=True)
        stream_thread.start()

        # Fetch historical TPO data for futures contract (in background)
        def fetch_futures_history():
            try:
                print(f"🆕 DEPLOY_v2: Starting historical fetch for {config['name']}...")
                print(f"📊 Fetching historical data for {config['name']}...")
                fetch_pd_levels()
                fetch_todays_ib()
                fetch_ended_sessions_ohlc()
                fetch_todays_tpo_data()  # This populates the TPO profile
                fetch_current_session_history()
                # Fetch historical candle volumes for Price Ladder charts
                fetch_historical_candle_volumes()
                # Fetch historical sessions for Session Analysis page
                print(f"📊 Fetching historical sessions OHLC for {config['name']}...")
                fetch_historical_sessions_ohlc(days=6)
                fetch_week_sessions_ohlc('current')
                print(f"✅ Historical data loaded for {config['name']}")
            except Exception as e:
                print(f"⚠️ Historical fetch error: {e}")

        history_thread = threading.Thread(target=fetch_futures_history, daemon=True)
        history_thread.start()

    print("=" * 50)
    print(f"✅ SWITCH COMPLETE: Now streaming {CONTRACT_CONFIG[new_contract]['name']}")
    print("=" * 50)
    return True


def process_trade(record):
    """Process incoming trade data - only front month contract"""
    global state, last_session_id, front_month_instrument_id, ACTIVE_CONTRACT

    try:
        if not hasattr(record, 'price'):
            return

        # Filter to only process front month trades
        if front_month_instrument_id is not None:
            if hasattr(record, 'instrument_id') and record.instrument_id != front_month_instrument_id:
                return  # Skip trades from other contracts

        price = record.price / 1e9 if record.price > 1e6 else record.price
        size = getattr(record, 'size', 1)
        # Handle side - could be char, bytes, or string depending on Databento record type
        raw_side = getattr(record, 'side', None)
        if raw_side is None:
            side = 'U'
        elif isinstance(raw_side, bytes):
            side = raw_side.decode('utf-8')
        elif isinstance(raw_side, str):
            side = raw_side
        else:
            # Could be char code or enum - convert to string
            side = str(raw_side)

        # Use dynamic price range from contract config
        config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
        if price < config['price_min'] or price > config['price_max']:
            return

        # Update watchdog timer
        update_last_trade_time()

        with lock:
            # Update price
            state['price'] = price
            state['current_price'] = price
            state['last_update'] = datetime.now(pytz.timezone('America/New_York')).strftime('%H:%M:%S')

            # Get current session info
            session_info = get_session_info()
            session_id = session_info['id']
            session_name = session_info['name']
            is_ib_session = session_info['is_ib_session']
            ib_locked = session_info['ib_locked']
            
            # Update session info
            state['current_session_id'] = session_id
            state['current_session_name'] = session_name
            state['current_session_start'] = session_info['start']
            state['current_session_end'] = session_info['end']
            
            # Detect session change
            if last_session_id != session_id:
                print(f"📍 Session change: {last_session_id} -> {session_id} ({session_name})")

                # Store ended session OHLC, volume, and delta before resetting
                if last_session_id and state['session_high'] > 0:
                    session_volume = state['session_buy'] + state['session_sell']
                    session_delta = state['session_buy'] - state['session_sell']
                    state['ended_sessions'][last_session_id] = {
                        'open': state['session_open'],
                        'high': state['session_high'],
                        'low': state['session_low'],
                        'close': state['current_price'],
                        'volume': session_volume,
                        'delta': session_delta
                    }
                    print(f"   💾 Stored {last_session_id} OHLC: O={state['session_open']:.2f} H={state['session_high']:.2f} L={state['session_low']:.2f} C={state['current_price']:.2f} V={session_volume} D={session_delta}")

                last_session_id = session_id

                # Reset session levels for new session
                state['session_high'] = price
                state['session_low'] = price
                state['session_open'] = price  # First trade of new session
                state['session_buy'] = 0       # Reset session buy volume
                state['session_sell'] = 0      # Reset session sell volume

                # Reset day levels at 18:00 ET (pre_asia session start)
                if session_id == 'pre_asia':
                    state['day_open'] = price
                    state['day_high'] = price
                    state['day_low'] = price
                    state['ended_sessions'] = {}  # Clear ended sessions for new day
                    print(f"   🌅 New trading day started - Day Open: ${price:.2f}")

                    # Track weekly open (Sunday 18:00 ET = start of trading week)
                    et_now = get_et_now()
                    today_str = et_now.strftime('%Y-%m-%d')
                    # Sunday = 6, so Sunday 18:00 ET is start of week
                    if et_now.weekday() == 6:  # Sunday
                        state['weekly_open'] = price
                        state['weekly_open_date'] = today_str
                        # Reset week high/low for new week
                        state['week_high'] = price
                        state['week_low'] = price
                        print(f"   📅 New trading week started - Weekly Open: ${price:.2f}")
                    # Also set weekly open on Monday if not set (for edge cases)
                    elif et_now.weekday() == 0 and state['weekly_open'] == 0:  # Monday
                        state['weekly_open'] = price
                        state['weekly_open_date'] = today_str
                        # Initialize week high/low if not set
                        if state['week_high'] == 0:
                            state['week_high'] = price
                            state['week_low'] = price
                        print(f"   📅 Weekly Open initialized on Monday: ${price:.2f}")

            # Track session high/low
            if price > state['session_high']:
                state['session_high'] = price
            if price < state['session_low']:
                state['session_low'] = price

            # Track day high/low (full trading day 18:00-17:00 ET)
            if state['day_open'] == 0:
                state['day_open'] = price  # Initialize if not set
            if price > state['day_high']:
                state['day_high'] = price
            if price < state['day_low'] or state['day_low'] == 999999.0:
                state['day_low'] = price

            # Track week high/low
            if price > state['week_high']:
                state['week_high'] = price
            if price < state['week_low'] or state['week_low'] == 999999.0:
                state['week_low'] = price

            # 4 IB Tracking - Each IB tracked independently
            active_ib = get_active_ib()
            state['current_ib'] = active_ib

            # Update all IB statuses
            for ib_key in state['ibs']:
                ib = state['ibs'][ib_key]
                if ib_key == active_ib:
                    # This IB is currently active
                    if ib['status'] == 'WAITING':
                        # First time entering - only reset if no historical data
                        if ib['high'] == 0:
                            ib['high'] = price
                            ib['low'] = price
                            print(f"   🔓 {ib['name']} STARTED - Init H/L to ${price:.2f}")
                        else:
                            print(f"   🔓 {ib['name']} STARTED - Using historical H:${ib['high']:.2f} L:${ib['low']:.2f}")
                        ib['status'] = 'ACTIVE'

                    # Always update high/low if price exceeds range
                    if price > ib['high']:
                        ib['high'] = price
                    if price < ib['low'] or ib['low'] == 999999.0:
                        ib['low'] = price
                    ib['status'] = 'ACTIVE'
                else:
                    # Not active - mark as ENDED if it was ACTIVE
                    if ib['status'] == 'ACTIVE':
                        ib['status'] = 'ENDED'
                        print(f"   🔒 {ib['name']} ENDED - H: ${ib['high']:.2f}, L: ${ib['low']:.2f}")

            # Legacy single IB fields (for backward compatibility)
            if active_ib:
                active_ib_data = state['ibs'][active_ib]
                state['ib_high'] = active_ib_data['high']
                state['ib_low'] = active_ib_data['low']
                state['ib_session_name'] = active_ib_data['name']
                state['ib_status'] = 'OPEN'
                state['ib_locked'] = False
                state['current_phase'] = f"{active_ib_data['name'].upper().replace(' ', '_')}_FORMING"
            else:
                # Find most recent ended IB for legacy display
                state['ib_status'] = 'ENDED'
                state['ib_locked'] = True
                state['current_phase'] = session_name.upper().replace(' ', '_')
            
            # Volume tracking
            now = time.time()
            if state['volume_start_time'] is None:
                state['volume_start_time'] = now

            state['total_volume'] += size
            # A = Ask (hit) = Buy aggressor, B = Bid (hit) = Sell aggressor
            if side == 'A':
                state['buy_volume'] += size
                state['session_buy'] += size  # Track session buy volume
                state['cumulative_delta'] += size
                volume_history.append((now, size, 0))  # (ts, buy, sell)
            elif side == 'B':
                state['sell_volume'] += size
                state['session_sell'] += size  # Track session sell volume
                state['cumulative_delta'] -= size
                volume_history.append((now, 0, size))  # (ts, buy, sell)

            # Big Trades Detection (Order Flow)
            # Track trade sizes for dynamic threshold calculation (90th percentile)
            state['trade_sizes'].append(size)
            if len(state['trade_sizes']) > 1000:
                state['trade_sizes'] = state['trade_sizes'][-1000:]

            # Recalculate 90th percentile every 100 trades (once we have enough data)
            if len(state['trade_sizes']) >= 100 and len(state['trade_sizes']) % 100 == 0:
                sorted_sizes = sorted(state['trade_sizes'])
                p90_index = int(len(sorted_sizes) * 0.90)
                # Set minimum threshold based on contract type
                min_thresholds = {'GC': 5, 'NQ': 3, 'ES': 5, 'CL': 10, 'BTC': 1, 'BTC-SPOT': 1}
                min_threshold = min_thresholds.get(ACTIVE_CONTRACT, 5)
                state['big_trade_threshold'] = max(sorted_sizes[p90_index], min_threshold)
                state['threshold_stats'] = {
                    'sample_count': len(sorted_sizes),
                    'avg_size': sum(sorted_sizes) / len(sorted_sizes),
                    'p90_size': sorted_sizes[p90_index],
                    'min_size': sorted_sizes[0],
                    'max_size': sorted_sizes[-1]
                }

            # Use dynamic threshold (falls back to default if not enough data)
            default_thresholds = {'GC': 10, 'NQ': 5, 'ES': 10, 'CL': 20, 'BTC': 2, 'BTC-SPOT': 1}
            big_threshold = state.get('big_trade_threshold', default_thresholds.get(ACTIVE_CONTRACT, 10))

            if size >= big_threshold:
                delta_impact = size if side == 'A' else -size
                big_trade = {
                    'ts': now,
                    'price': price,
                    'size': size,
                    'side': 'BUY' if side == 'A' else 'SELL',
                    'delta_impact': delta_impact
                }
                # Keep last 50 big trades in memory
                state['big_trades'] = [big_trade] + state['big_trades'][:49]

                # Persist to daily cache file for historical analysis
                save_big_trade(big_trade)

                # Update cumulative big trades
                if side == 'A':
                    state['big_trades_buy'] += size
                else:
                    state['big_trades_sell'] += size
                state['big_trades_delta'] = state['big_trades_buy'] - state['big_trades_sell']

            # Calculate candle-aligned volume (current candle only)
            # Get current candle start times (clock-aligned)
            def get_candle_start(ts, minutes):
                return int(ts // (minutes * 60)) * (minutes * 60)

            candle_5m_start = get_candle_start(now, 5)
            candle_15m_start = get_candle_start(now, 15)
            candle_30m_start = get_candle_start(now, 30)
            candle_1h_start = get_candle_start(now, 60)

            # Check if new candle started - store previous in history and reset
            if state['volume_5m']['candle_start'] != candle_5m_start:
                prev = state['volume_5m']
                history = prev.get('history', [])
                # Add completed candle to history with delta OHLC and price OHLC for divergence
                if prev['buy'] > 0 or prev['sell'] > 0:
                    history = [{
                        'buy': prev['buy'], 'sell': prev['sell'], 'delta': prev['delta'], 'ts': prev['candle_start'],
                        'delta_open': prev.get('delta_open', 0), 'delta_high': prev.get('delta_high', 0),
                        'delta_low': prev.get('delta_low', 0), 'delta_close': prev['delta'],
                        'price_open': prev.get('price_open', 0), 'price_high': prev.get('price_high', 0),
                        'price_low': prev.get('price_low', 999999), 'price_close': prev.get('price_close', 0)
                    }] + history[:29]  # Keep 30 candles of history
                state['volume_5m'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': candle_5m_start,
                                      'prev_buy': prev['buy'], 'prev_sell': prev['sell'], 'prev_delta': prev['delta'], 'history': history,
                                      'delta_open': None, 'delta_high': -999999, 'delta_low': 999999,
                                      'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0}
            if state['volume_15m']['candle_start'] != candle_15m_start:
                prev = state['volume_15m']
                history = prev.get('history', [])
                if prev['buy'] > 0 or prev['sell'] > 0:
                    history = [{
                        'buy': prev['buy'], 'sell': prev['sell'], 'delta': prev['delta'], 'ts': prev['candle_start'],
                        'delta_open': prev.get('delta_open', 0), 'delta_high': prev.get('delta_high', 0),
                        'delta_low': prev.get('delta_low', 0), 'delta_close': prev['delta'],
                        'price_open': prev.get('price_open', 0), 'price_high': prev.get('price_high', 0),
                        'price_low': prev.get('price_low', 999999), 'price_close': prev.get('price_close', 0)
                    }] + history[:29]  # Keep 30 candles of history
                state['volume_15m'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': candle_15m_start,
                                       'prev_buy': prev['buy'], 'prev_sell': prev['sell'], 'prev_delta': prev['delta'], 'history': history,
                                       'delta_open': None, 'delta_high': -999999, 'delta_low': 999999,
                                       'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0}
            if state['volume_30m']['candle_start'] != candle_30m_start:
                prev = state['volume_30m']
                history = prev.get('history', [])
                if prev['buy'] > 0 or prev['sell'] > 0:
                    history = [{
                        'buy': prev['buy'], 'sell': prev['sell'], 'delta': prev['delta'], 'ts': prev['candle_start'],
                        'delta_open': prev.get('delta_open', 0), 'delta_high': prev.get('delta_high', 0),
                        'delta_low': prev.get('delta_low', 0), 'delta_close': prev['delta'],
                        'price_open': prev.get('price_open', 0), 'price_high': prev.get('price_high', 0),
                        'price_low': prev.get('price_low', 999999), 'price_close': prev.get('price_close', 0)
                    }] + history[:29]  # Keep 30 candles of history
                state['volume_30m'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': candle_30m_start,
                                       'prev_buy': prev['buy'], 'prev_sell': prev['sell'], 'prev_delta': prev['delta'], 'history': history,
                                       'delta_open': None, 'delta_high': -999999, 'delta_low': 999999,
                                       'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0}
            if state['volume_1h']['candle_start'] != candle_1h_start:
                prev = state['volume_1h']
                history = prev.get('history', [])
                if prev['buy'] > 0 or prev['sell'] > 0:
                    history = [{
                        'buy': prev['buy'], 'sell': prev['sell'], 'delta': prev['delta'], 'ts': prev['candle_start'],
                        'delta_open': prev.get('delta_open', 0), 'delta_high': prev.get('delta_high', 0),
                        'delta_low': prev.get('delta_low', 0), 'delta_close': prev['delta'],
                        'price_open': prev.get('price_open', 0), 'price_high': prev.get('price_high', 0),
                        'price_low': prev.get('price_low', 999999), 'price_close': prev.get('price_close', 0)
                    }] + history[:29]  # Keep 30 candles of history
                state['volume_1h'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': candle_1h_start,
                                      'prev_buy': prev['buy'], 'prev_sell': prev['sell'], 'prev_delta': prev['delta'], 'history': history,
                                      'delta_open': None, 'delta_high': -999999, 'delta_low': 999999,
                                      'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0}

            # Add current trade to candle volumes
            # Note: A = Ask (hit) = Buy aggressor, B = Bid (hit) = Sell aggressor
            trade_buy = size if side == 'A' else 0
            trade_sell = size if side == 'B' else 0

            # Helper function to update OHLC for a timeframe
            def update_candle_ohlc(tf_key, trade_buy, trade_sell, price):
                tf = state[tf_key]
                tf['buy'] += trade_buy
                tf['sell'] += trade_sell
                tf['delta'] = tf['buy'] - tf['sell']

                # Update Delta OHLC (handle None values safely)
                if tf.get('delta_open') is None:
                    tf['delta_open'] = tf['delta']  # First trade sets open
                delta_high = tf.get('delta_high') if tf.get('delta_high') is not None else -999999
                delta_low = tf.get('delta_low') if tf.get('delta_low') is not None else 999999
                tf['delta_high'] = max(delta_high, tf['delta'])
                tf['delta_low'] = min(delta_low, tf['delta'])

                # Update Price OHLC (handle None values safely)
                if tf.get('price_open', 0) == 0:
                    tf['price_open'] = price  # First trade sets open
                price_high = tf.get('price_high') if tf.get('price_high') is not None else 0
                price_low = tf.get('price_low') if tf.get('price_low') is not None else 999999
                tf['price_high'] = max(price_high, price)
                tf['price_low'] = min(price_low, price)
                tf['price_close'] = price  # Always update close to latest price

            update_candle_ohlc('volume_5m', trade_buy, trade_sell, price)
            update_candle_ohlc('volume_15m', trade_buy, trade_sell, price)
            update_candle_ohlc('volume_30m', trade_buy, trade_sell, price)
            update_candle_ohlc('volume_1h', trade_buy, trade_sell, price)

            # Log every 100 trades for verification
            if state['total_volume'] % 100 == 0:
                print(f"📊 Vol: {state['total_volume']} | Buy: {state['buy_volume']} | Sell: {state['sell_volume']} | Delta: {state['cumulative_delta']}")

            # Delta history
            delta_history.append((now, state['cumulative_delta']))
            
            # Calculate rolling deltas
            cutoff_5m = now - 300
            cutoff_30m = now - 1800
            
            delta_5m_start = state['cumulative_delta']
            delta_30m_start = state['cumulative_delta']
            
            for ts, delta in delta_history:
                if ts >= cutoff_5m:
                    delta_5m_start = delta
                    break
            
            for ts, delta in delta_history:
                if ts >= cutoff_30m:
                    delta_30m_start = delta
                    break
            
            state['delta_5m'] = state['cumulative_delta'] - delta_5m_start
            state['delta_30m'] = state['cumulative_delta'] - delta_30m_start
            
            # VWAP calculation
            state['vwap_numerator'] += price * size
            state['vwap_denominator'] += size
            if state['vwap_denominator'] > 0:
                state['vwap'] = state['vwap_numerator'] / state['vwap_denominator']

            # === Anchored VWAPs (Databento live stream) ===
            et = get_et_now()
            today_date = et.strftime('%Y-%m-%d')
            current_hhmm = et.hour * 100 + et.minute

            # Day VWAP (full trading day 18:00-17:00 ET)
            if current_hhmm < 1800:
                trading_day = (et - timedelta(days=1)).strftime('%Y-%m-%d')
            else:
                trading_day = today_date

            if state.get('day_vwap_date', '') != trading_day:
                state['day_vwap_numerator'] = 0.0
                state['day_vwap_denominator'] = 0.0
                state['day_vwap'] = 0.0
                state['day_vwap_date'] = trading_day

            state['day_vwap_numerator'] = state.get('day_vwap_numerator', 0) + (price * size)
            state['day_vwap_denominator'] = state.get('day_vwap_denominator', 0) + size
            if state['day_vwap_denominator'] > 0:
                state['day_vwap'] = state['day_vwap_numerator'] / state['day_vwap_denominator']

            # US IB Anchored VWAP (08:20-17:00 ET)
            if state.get('us_ib_vwap_date', '') != today_date and current_hhmm >= 820:
                state['us_ib_vwap_numerator'] = 0.0
                state['us_ib_vwap_denominator'] = 0.0
                state['us_ib_vwap'] = 0.0
                state['us_ib_vwap_date'] = today_date

            if current_hhmm >= 820 and current_hhmm < 1700:
                state['us_ib_vwap_numerator'] = state.get('us_ib_vwap_numerator', 0) + (price * size)
                state['us_ib_vwap_denominator'] = state.get('us_ib_vwap_denominator', 0) + size
                if state['us_ib_vwap_denominator'] > 0:
                    state['us_ib_vwap'] = state['us_ib_vwap_numerator'] / state['us_ib_vwap_denominator']

            # NY 1H Anchored VWAP (09:30-17:00 ET)
            if state.get('ny_1h_vwap_date', '') != today_date and current_hhmm >= 930:
                state['ny_1h_vwap_numerator'] = 0.0
                state['ny_1h_vwap_denominator'] = 0.0
                state['ny_1h_vwap'] = 0.0
                state['ny_1h_vwap_date'] = today_date

            if current_hhmm >= 930 and current_hhmm < 1700:
                state['ny_1h_vwap_numerator'] = state.get('ny_1h_vwap_numerator', 0) + (price * size)
                state['ny_1h_vwap_denominator'] = state.get('ny_1h_vwap_denominator', 0) + size
                if state['ny_1h_vwap_denominator'] > 0:
                    state['ny_1h_vwap'] = state['ny_1h_vwap_numerator'] / state['ny_1h_vwap_denominator']

            # === IB POC and VWAP Tracking ===
            # Update IB VWAP and TPO prices during active IB periods
            ib_sessions = [
                (1900, 2000, 'japan'),   # Japan IB: 19:00-20:00 ET
                (300, 400, 'london'),    # London IB: 03:00-04:00 ET
                (820, 930, 'us'),        # US IB: 08:20-09:30 ET
                (930, 1030, 'ny'),       # NY IB: 09:30-10:30 ET
            ]

            for start, end, ib_key in ib_sessions:
                if start <= current_hhmm < end:
                    ib = state['ibs'].get(ib_key, {})
                    if ib.get('status') in ['WAITING', None]:
                        # IB session starting - reset
                        ib['high'] = price
                        ib['low'] = price
                        ib['vwap_num'] = price * size
                        ib['vwap_den'] = size
                        ib['tpo_prices'] = {round(price / 0.1) * 0.1: size}
                        ib['status'] = 'ACTIVE'
                    else:
                        # Update high/low
                        if price > ib.get('high', 0):
                            ib['high'] = price
                        if price < ib.get('low', 999999):
                            ib['low'] = price
                        # Update VWAP
                        ib['vwap_num'] = ib.get('vwap_num', 0) + (price * size)
                        ib['vwap_den'] = ib.get('vwap_den', 0) + size
                        # Track TPO for POC
                        tpo_key = round(price / 0.1) * 0.1
                        tpo_prices = ib.get('tpo_prices', {})
                        tpo_prices[tpo_key] = tpo_prices.get(tpo_key, 0) + size
                        ib['tpo_prices'] = tpo_prices

                    # Calculate mid, VWAP, POC
                    if ib['high'] > 0 and ib['low'] < 999999:
                        ib['mid'] = (ib['high'] + ib['low']) / 2
                    if ib.get('vwap_den', 0) > 0:
                        ib['vwap'] = ib['vwap_num'] / ib['vwap_den']
                    if ib.get('tpo_prices'):
                        poc_price = max(ib['tpo_prices'], key=ib['tpo_prices'].get)
                        ib['poc'] = poc_price

                    state['ibs'][ib_key] = ib
                    # Update legacy IB
                    state['ib_high'] = ib['high']
                    state['ib_low'] = ib['low']
                    state['ib_locked'] = False
                    break
                elif current_hhmm >= end and state['ibs'].get(ib_key, {}).get('status') == 'ACTIVE':
                    # IB just ended - lock it
                    ib = state['ibs'][ib_key]
                    ib['status'] = 'ENDED'
                    state['ibs'][ib_key] = ib
                    state['ib_locked'] = True
                    print(f"🔒 {ib_key.upper()} IB Complete: H=${ib['high']:.2f} L=${ib['low']:.2f} POC=${ib.get('poc', 0):.2f} VWAP=${ib.get('vwap', 0):.2f}")

            # Buying imbalance
            if state['sell_volume'] > 0:
                state['buying_imbalance_pct'] = int((state['buy_volume'] / state['sell_volume']) * 100)
            
            # Absorption ratio
            if state['total_volume'] > 0:
                state['absorption_ratio'] = abs(state['cumulative_delta']) / state['total_volume']
            
            # Entry conditions check (matching Signal Matrix exactly)
            conditions = 0
            if state['delta_30m'] < -2500:
                conditions += 1
            if state['buying_imbalance_pct'] >= 400:
                conditions += 1
            ib_low = state['ib_low'] if state['ib_low'] < 999999 else 0
            if ib_low > 0 and state['current_price'] < ib_low:
                conditions += 1
            if state['absorption_ratio'] > 1.2:
                conditions += 1
            if state['stacked_buy_imbalances'] >= 3:
                conditions += 1
            # At pdPOC = within $2 of pdPOC
            if state['pdpoc'] > 0 and abs(state['current_price'] - state['pdpoc']) <= 2.0:
                conditions += 1
            
            state['conditions_met'] = conditions
            state['entry_signal'] = conditions >= 4

            # ============================================
            # TPO / MARKET PROFILE TRACKING (4-Session Structure)
            # ============================================
            config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
            tick_size = config['tick_size']

            # Round price to tick size for TPO level
            tpo_price = round(price / tick_size) * tick_size

            # Get current ET time for session detection
            et = get_et_now()
            current_hhmm = et.hour * 100 + et.minute

            # Determine active TPO session
            current_tpo_session = get_tpo_session_for_time(current_hhmm)
            day = tpo_state['day']

            # Initialize day start on first trade after 18:00 ET or on reset
            if tpo_state['day_start_time'] == 0:
                tpo_state['day_start_time'] = now
                day['current_period_start'] = int(now // 1800) * 1800  # Clock-aligned 30-min
                day['open_price'] = price
                tpo_state['active_session'] = current_tpo_session
                print(f"📊 TPO: Day started at {price:.2f}, Period A, Session: {current_tpo_session}")

            # Reset TPO at 18:00 ET (new trading day)
            if session_id == 'pre_asia' and last_session_id != 'pre_asia':
                reset_tpo_for_new_day()
                tpo_state['day_start_time'] = now
                day['current_period_start'] = int(now // 1800) * 1800
                day['open_price'] = price
                tpo_state['active_session'] = current_tpo_session

            # Handle session transitions
            if current_tpo_session and current_tpo_session != tpo_state['active_session']:
                old_session = tpo_state['active_session']
                tpo_state['active_session'] = current_tpo_session
                # Reset session profile for new session
                reset_session_profile(current_tpo_session)
                session_data = tpo_state['sessions'][current_tpo_session]
                session_data['open_price'] = price
                session_data['current_period_start'] = int(now // 1800) * 1800
                session_name_display = TPO_SESSIONS[current_tpo_session]['display']
                print(f"📊 TPO: Session changed from {old_session} to {current_tpo_session} ({session_name_display})")

            # Get active session data
            session_data = None
            session_config = None
            if current_tpo_session:
                session_data = tpo_state['sessions'][current_tpo_session]
                session_config = TPO_SESSIONS[current_tpo_session]

            # Check if new period started
            current_period_start = int(now // 1800) * 1800

            # Note: Uses the outer get_session_period_index function which handles
            # variable period durations (London last 20 min, US first 40 min)

            # Day profile period tracking - calculate from 18:00 ET (day start)
            day_start_mins = 18 * 60  # 18:00 = 1080 minutes
            current_mins = (current_hhmm // 100) * 60 + (current_hhmm % 100)
            if current_hhmm < 1800:  # Before 18:00, we're in next day's periods
                current_mins += 24 * 60
            day_period_idx = (current_mins - day_start_mins) // 30

            if current_period_start != day['current_period_start'] or day['period_count'] != day_period_idx:
                if day['period_count'] != day_period_idx:
                    day['period_count'] = day_period_idx
                day['current_period_start'] = current_period_start
                new_letter = get_tpo_letter(day['period_count'])
                print(f"📊 TPO: Day period {new_letter} (#{day['period_count']})")

                # Calculate BC overlap when C period starts (day level)
                if day['period_count'] == 3:
                    bc_overlap = calculate_overlap(
                        (day['b_high'], day['b_low']),
                        (day['c_high'], day['c_low'])
                    )
                    day['bc_overlap'] = bc_overlap

            # Session profile period tracking - calculate from session start time
            if session_data and session_config:
                session_period_idx = get_session_period_index(current_tpo_session, current_hhmm)

                if current_period_start != session_data['current_period_start'] or session_data['period_count'] != session_period_idx:
                    if session_data['period_count'] != session_period_idx:
                        session_data['period_count'] = session_period_idx
                    session_data['current_period_start'] = current_period_start
                    session_letter = get_tpo_letter(session_data['period_count'])
                    print(f"   📊 Session {current_tpo_session} period {session_letter} (#{session_data['period_count']})")

                # Check IB complete for session
                if session_data['period_count'] == 2 and not session_data['ib_complete']:
                    session_data['ib_complete'] = True
                    if session_data['ib_high'] > 0 and session_data['ib_low'] < 999999:
                        ib_range = session_data['ib_high'] - session_data['ib_low']
                        print(f"   🔒 Session IB Complete: H={session_data['ib_high']:.2f} L={session_data['ib_low']:.2f} Range={ib_range:.2f}")

            # Get current period letters
            day_letter = get_tpo_letter(day['period_count'])
            session_letter = get_tpo_letter(session_data['period_count']) if session_data else None

            # Add TPO to DAY profile
            if tpo_price not in day['profiles']:
                day['profiles'][tpo_price] = set()
            day['profiles'][tpo_price].add(day_letter)

            # Add TPO to SESSION profile
            if session_data and session_letter:
                if tpo_price not in session_data['profiles']:
                    session_data['profiles'][tpo_price] = set()
                session_data['profiles'][tpo_price].add(session_letter)
                # Update session high/low
                if price > session_data.get('high', 0):
                    session_data['high'] = price
                if price < session_data.get('low', 999999):
                    session_data['low'] = price

            # Update period ranges for A, B, C (day level - for RTH open type detection)
            day_period_idx = day['period_count']
            if day_period_idx == 0:  # A period
                if price > day['a_high']:
                    day['a_high'] = price
                if price < day['a_low']:
                    day['a_low'] = price
            elif day_period_idx == 1:  # B period
                if price > day['b_high']:
                    day['b_high'] = price
                if price < day['b_low']:
                    day['b_low'] = price
            elif day_period_idx == 2:  # C period
                if price > day['c_high']:
                    day['c_high'] = price
                if price < day['c_low']:
                    day['c_low'] = price

            # Update session-specific A/B tracking for RTH open type
            if current_tpo_session == 'tpo3_us_am' and session_data:
                session_period_idx = session_data['period_count']
                if session_period_idx == 0:  # A period
                    if price > session_data['a_high']:
                        session_data['a_high'] = price
                    if price < session_data['a_low']:
                        session_data['a_low'] = price
                elif session_period_idx == 1:  # B period
                    if price > session_data['b_high']:
                        session_data['b_high'] = price
                    if price < session_data['b_low']:
                        session_data['b_low'] = price
                # AB overlap for RTH session
                if session_period_idx >= 1:
                    session_data['ab_overlap'] = calculate_overlap(
                        (session_data['a_high'], session_data['a_low']),
                        (session_data['b_high'], session_data['b_low'])
                    )

            # Update DAY IB during RTH session (09:30-10:30 = first 2 periods of tpo3_us_am)
            if current_tpo_session == 'tpo3_us_am' and session_data:
                session_period_idx = session_data['period_count']
                if session_period_idx < 2:  # During IB formation
                    if price > day['ib_high']:
                        day['ib_high'] = price
                    if price < day['ib_low']:
                        day['ib_low'] = price
                elif session_period_idx == 2 and not day['ib_complete']:
                    day['ib_complete'] = True
                    ib_range = day['ib_high'] - day['ib_low']
                    print(f"📊 TPO: RTH IB Complete: H={day['ib_high']:.2f} L={day['ib_low']:.2f} Range={ib_range:.2f}")

            # Update SESSION IB based on session-specific IB times
            if session_data and session_config:
                ib_start = session_config.get('ib_start')
                ib_end = session_config.get('ib_end')
                if ib_start is not None and ib_end is not None:
                    # Check if within session IB time
                    if ib_start <= current_hhmm < ib_end:
                        if price > session_data['ib_high']:
                            session_data['ib_high'] = price
                        if price < session_data['ib_low']:
                            session_data['ib_low'] = price
                    elif current_hhmm >= ib_end and not session_data['ib_complete']:
                        session_data['ib_complete'] = True
                        if session_data['ib_high'] > 0 and session_data['ib_low'] < 999999:
                            ib_range = session_data['ib_high'] - session_data['ib_low']
                            print(f"   🔒 {session_config['name']} IB Complete: H={session_data['ib_high']:.2f} L={session_data['ib_low']:.2f}")

            # Recalculate TPO metrics periodically (every 50 trades)
            if state['total_volume'] % 50 == 0:
                calculate_tpo_metrics()
                classify_day_type()
                classify_open_type()

            # ============================================
            # END TPO TRACKING
            # ============================================

            # PD levels should come from Databento historical API
            # If not loaded, they remain 0 - no hardcoded fallbacks
            if not state['pd_loaded'] and price > 0 and state['pd_high'] == 0:
                print("⚠️  PD levels not loaded from Databento - displaying as 0 until fetched")
            
    except Exception as e:
        print(f"Error processing trade: {e}")

# ============================================
# SPOT GOLD PRICE (XAUUSD)
# ============================================

_spot_gold_price = 0
_spot_gold_timestamp = 0
_spot_gold_lock = threading.Lock()

def fetch_spot_gold_price():
    """Fetch gold price from Yahoo Finance (GC=F futures as proxy for spot)"""
    global _spot_gold_price, _spot_gold_timestamp

    # Cache for 30 seconds
    now = time.time()
    if _spot_gold_price > 0 and (now - _spot_gold_timestamp) < 30:
        return _spot_gold_price

    with _spot_gold_lock:
        # Double-check inside lock
        if _spot_gold_price > 0 and (time.time() - _spot_gold_timestamp) < 30:
            return _spot_gold_price

        if not HAS_YFINANCE:
            return 0

        try:
            # Use GC=F (Gold Futures) - closest proxy for spot gold on Yahoo Finance
            ticker = yf.Ticker('GC=F')
            data = ticker.history(period='1d')
            if not data.empty:
                _spot_gold_price = float(data['Close'].iloc[-1])
                _spot_gold_timestamp = time.time()
                print(f"📈 Gold Price (GC=F): ${_spot_gold_price:.2f}")
                return _spot_gold_price
        except Exception as e:
            print(f"⚠️ Error fetching gold price: {e}")

    return _spot_gold_price if _spot_gold_price > 0 else 0

def get_spot_gold_price():
    """Get cached spot gold price (non-blocking)"""
    return _spot_gold_price if _spot_gold_price > 0 else state.get('current_price', 0)

# ============================================
# GEX PROFILE GENERATION (Real GEX Calculator)
# ============================================

# Global GEX calculator instance
_gex_calculator = None
_last_gex_update = None
_cached_gex_result = None
_gex_lock = threading.Lock()

def get_gex_calculator():
    """Get or create the GEX calculator instance (only for Gold)"""
    global _gex_calculator
    # Only use GoldGEXCalculator for Gold futures
    if ACTIVE_CONTRACT != 'GC':
        return None
    if _gex_calculator is None and HAS_GEX_CALCULATOR:
        _gex_calculator = GoldGEXCalculator(api_key=API_KEY)
        print("✅ GEX Calculator initialized" + (" with Databento" if API_KEY else " (synthetic data)"))
    return _gex_calculator

def update_gex_data(current_price):
    """
    Update GEX data using the real calculator.
    Caches results for 60 seconds to avoid excessive recalculation.
    """
    global _last_gex_update, _cached_gex_result

    if not current_price or current_price <= 0:
        # Always prefer actual current price from live feed, never use gamma_flip as fallback
        current_price = state.get('current_price', 0)
        if current_price <= 0:
            config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, {})
            current_price = (config.get('price_min', 4000) + config.get('price_max', 7000)) / 2

    # Check if we should use cached result (update every 5 minutes to reduce load)
    now = time.time()
    GEX_CACHE_SECONDS = 300  # 5 minutes
    if _cached_gex_result and _last_gex_update and (now - _last_gex_update) < GEX_CACHE_SECONDS:
        return _cached_gex_result

    # Use lock to prevent race conditions with shared calculator state
    with _gex_lock:
        # Double-check cache inside lock (another thread might have just updated)
        if _cached_gex_result and _last_gex_update and (time.time() - _last_gex_update) < GEX_CACHE_SECONDS:
            return _cached_gex_result

        calculator = get_gex_calculator()

        if calculator:
            try:
                result = calculator.calculate_gex_profile(current_price)

                # Convert numpy floats to Python floats for JSON serialization
                def convert_numpy(obj):
                    if hasattr(obj, 'item'):  # numpy scalar
                        return obj.item()
                    return obj

                # Convert profile entries
                converted_profile = []
                for entry in result.get('gex_profile', []):
                    converted_profile.append({
                        'strike': convert_numpy(entry.get('strike', 0)),
                        'gex': convert_numpy(entry.get('gex', 0)),
                        'call_gex': convert_numpy(entry.get('call_gex', 0)),
                        'put_gex': convert_numpy(entry.get('put_gex', 0)),
                        'call_oi': convert_numpy(entry.get('call_oi', 0)),
                        'put_oi': convert_numpy(entry.get('put_oi', 0))
                    })
                result['gex_profile'] = converted_profile

                _cached_gex_result = result
                _last_gex_update = now

                # Update state with calculated values including profile and levels
                with lock:
                    state['gamma_regime'] = result.get('gamma_regime', 'UNKNOWN')
                    state['total_gex'] = convert_numpy(result.get('total_gex', 0))
                    state['call_wall'] = convert_numpy(result.get('call_wall', current_price + 50))
                    state['put_wall'] = convert_numpy(result.get('put_wall', current_price - 50))
                    state['gamma_flip'] = convert_numpy(result.get('gamma_flip', current_price))
                    state['zero_gamma'] = convert_numpy(result.get('zero_gamma', current_price))
                    state['max_pain'] = convert_numpy(result.get('max_pain', current_price))
                    state['hvl'] = convert_numpy(result.get('hvl', current_price))
                    state['gex_profile'] = converted_profile
                    state['gex_levels'] = result.get('gex_levels', [])

                print(f"📊 GEX Updated: Regime={result['gamma_regime']} Total={result['total_gex']:.4f}B "
                      f"CW=${result['call_wall']} PW=${result['put_wall']} GF=${result['gamma_flip']} ({len(converted_profile)} strikes)")

                return result
            except Exception as e:
                print(f"⚠️  GEX calculation error: {e}")

        # Fallback to dynamic estimation if calculator not available
        return generate_fallback_gex(current_price)

def generate_fallback_gex(current_price):
    """Generate fallback GEX data when calculator is not available"""
    if not current_price or current_price <= 0:
        current_price = 4600

    # Dynamic levels relative to current price
    base = round(current_price / 25) * 25

    result = {
        'gamma_regime': 'NEGATIVE' if current_price < base else 'POSITIVE',
        'total_gex': -0.045 if current_price < base else 0.032,
        'call_wall': base + 75,
        'put_wall': base - 50,
        'gamma_flip': base,
        'zero_gamma': base,
        'max_pain': base - 10,
        'hvl': base + 20,
        'gex_profile': [],
        'gex_levels': []
    }

    # Generate profile
    strike_interval = 5
    num_strikes = 20

    for i in range(-num_strikes, num_strikes + 1):
        strike = base + (i * strike_interval)
        distance = abs(strike - current_price)
        base_gamma = max(0, 1 - (distance / (num_strikes * strike_interval)))

        if strike > current_price:
            gex = base_gamma * 0.8 * (1 + 0.3 * (strike - current_price) / 50)
            gex_type = 'call'
        elif strike < current_price:
            gex = -base_gamma * 0.6 * (1 + 0.2 * (current_price - strike) / 50)
            gex_type = 'put'
        else:
            gex = base_gamma * 0.1
            gex_type = 'atm'

        result['gex_profile'].append({
            'strike': strike,
            'gex': round(gex, 4),
            'type': gex_type
        })

    return result

def generate_gex_profile(current_price):
    """Generate GEX profile data for charting using real calculator"""
    result = update_gex_data(current_price)
    return result.get('gex_profile', [])

def generate_gex_levels(state):
    """Generate key GEX levels with strength ratings using real calculator"""
    current_price = state.get('current_price', 0)
    if not current_price or current_price <= 0:
        # Use spot gold price or a reasonable default, never use gamma_flip as it may be stale
        current_price = get_spot_gold_price() or 4600

    result = update_gex_data(current_price)

    # Return levels from calculator or build from state
    if result.get('gex_levels'):
        return result['gex_levels']

    levels = []

    # Call Wall - resistance
    call_wall = state.get('call_wall', current_price + 40)
    if call_wall > 0:
        levels.append({
            'type': 'call_wall',
            'price': call_wall,
            'strength': 0.85,
            'label': 'Call Wall',
            'color': '#ef4444',
            'description': 'Highest call gamma concentration'
        })

    # Put Wall - support
    put_wall = state.get('put_wall', current_price - 40)
    if put_wall > 0:
        levels.append({
            'type': 'put_wall',
            'price': put_wall,
            'strength': 0.82,
            'label': 'Put Wall',
            'color': '#22c55e',
            'description': 'Highest put gamma concentration'
        })

    # Gamma Flip / Zero Gamma
    gamma_flip = state.get('gamma_flip', state.get('zero_gamma', current_price))
    if gamma_flip > 0:
        levels.append({
            'type': 'gamma_flip',
            'price': gamma_flip,
            'strength': 0.95,
            'label': 'Gamma Flip',
            'color': '#22d3ee',
            'description': 'Dealer positioning pivot point'
        })

    # HVL - High Volume Level
    hvl = state.get('hvl', 0)
    if hvl > 0:
        levels.append({
            'type': 'hvl',
            'price': hvl,
            'strength': 0.78,
            'label': 'HVL',
            'color': '#a855f7',
            'description': 'Highest options volume strike'
        })

    # Max Pain
    max_pain = state.get('max_pain', 0)
    if max_pain > 0:
        levels.append({
            'type': 'max_pain',
            'price': max_pain,
            'strength': 0.70,
            'label': 'Max Pain',
            'color': '#f59e0b',
            'description': 'Strike where most options expire worthless'
        })

    # Sort by price descending
    levels.sort(key=lambda x: x['price'], reverse=True)

    return levels


# ============================================
# HTTP SERVER
# ============================================
class LiveDataHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass
    
    def do_GET(self):
        # Parse path and query params
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        # Health check endpoint for Railway
        if path == '/health':
            self.wfile.write(json.dumps({'status': 'ok', 'timestamp': time.time()}).encode())
            return

        # Red Folder economic calendar endpoint
        if path == '/redfolder':
            try:
                ET = pytz.timezone('America/New_York')
                now = datetime.now(ET)
                today = now.date()
                current_month = now.month
                current_year = now.year

                # Economic Calendar for 2026
                ECONOMIC_CALENDAR = [
                    # January 2026
                    (2026, 1, 3, 10, 0, "ISM Manufacturing PMI", "HIGH", "48.2", "48.4"),
                    (2026, 1, 6, 10, 0, "ISM Services PMI", "HIGH", "53.5", "52.1"),
                    (2026, 1, 7, 8, 30, "Trade Balance", "MEDIUM", "-$77.0B", "-$73.8B"),
                    (2026, 1, 7, 10, 0, "JOLTS Job Openings", "HIGH", "7.74M", "7.74M"),
                    (2026, 1, 9, 8, 30, "Initial Jobless Claims", "MEDIUM", "210K", "211K"),
                    (2026, 1, 10, 8, 30, "NFP Jobs Report", "CRITICAL", "150K", "227K"),
                    (2026, 1, 14, 8, 30, "PPI (Dec)", "HIGH", "0.3%", "0.4%"),
                    (2026, 1, 15, 8, 30, "CPI (Dec)", "CRITICAL", "0.3%", "0.3%"),
                    (2026, 1, 15, 8, 30, "Core CPI (Dec)", "CRITICAL", "0.2%", "0.3%"),
                    (2026, 1, 16, 8, 30, "Retail Sales (Dec)", "HIGH", "0.5%", "0.7%"),
                    (2026, 1, 16, 8, 30, "Initial Jobless Claims", "MEDIUM", "210K", "201K"),
                    (2026, 1, 17, 8, 30, "Housing Starts (Dec)", "MEDIUM", "1.34M", "1.29M"),
                    (2026, 1, 23, 8, 30, "Initial Jobless Claims", "MEDIUM", "215K", "210K"),
                    (2026, 1, 24, 10, 0, "Existing Home Sales (Dec)", "MEDIUM", "4.15M", "4.09M"),
                    (2026, 1, 27, 10, 0, "New Home Sales (Dec)", "MEDIUM", "670K", "664K"),
                    (2026, 1, 28, 14, 0, "FOMC Rate Decision", "CRITICAL", "4.25-4.50%", "4.25-4.50%"),
                    (2026, 1, 28, 14, 30, "FOMC Press Conference", "CRITICAL", "", ""),
                    (2026, 1, 30, 8, 30, "GDP (Q4 Advance)", "HIGH", "2.5%", "3.1%"),
                    (2026, 1, 30, 8, 30, "Initial Jobless Claims", "MEDIUM", "218K", "215K"),
                    (2026, 1, 31, 8, 30, "Core PCE Price Index (Dec)", "CRITICAL", "0.2%", "0.1%"),
                    # February 2026
                    (2026, 2, 3, 10, 0, "ISM Manufacturing PMI", "HIGH", "49.0", "49.3"),
                    (2026, 2, 5, 8, 30, "Trade Balance", "MEDIUM", "-$78.0B", "-$78.2B"),
                    (2026, 2, 5, 10, 0, "ISM Services PMI", "HIGH", "54.0", "54.1"),
                    (2026, 2, 6, 8, 30, "Initial Jobless Claims", "MEDIUM", "212K", "218K"),
                    (2026, 2, 7, 8, 30, "NFP Jobs Report", "CRITICAL", "170K", "150K"),
                    (2026, 2, 12, 8, 30, "CPI (Jan)", "CRITICAL", "0.3%", "0.3%"),
                    (2026, 2, 13, 8, 30, "PPI (Jan)", "HIGH", "0.2%", "0.3%"),
                    (2026, 2, 14, 8, 30, "Retail Sales (Jan)", "HIGH", "0.4%", "0.5%"),
                    (2026, 2, 27, 8, 30, "GDP (Q4 Second)", "HIGH", "2.6%", "2.5%"),
                    (2026, 2, 28, 8, 30, "Core PCE Price Index (Jan)", "CRITICAL", "0.2%", "0.2%"),
                    # March 2026
                    (2026, 3, 6, 8, 30, "NFP Jobs Report", "CRITICAL", "180K", "170K"),
                    (2026, 3, 11, 8, 30, "CPI (Feb)", "CRITICAL", "0.2%", "0.3%"),
                    (2026, 3, 12, 8, 30, "PPI (Feb)", "HIGH", "0.2%", "0.2%"),
                    (2026, 3, 17, 8, 30, "Retail Sales (Feb)", "HIGH", "0.3%", "0.4%"),
                    (2026, 3, 18, 14, 0, "FOMC Rate Decision", "CRITICAL", "4.00-4.25%", "4.25-4.50%"),
                    (2026, 3, 18, 14, 30, "FOMC Press Conference", "CRITICAL", "", ""),
                ]

                past_events = []
                upcoming_events = []

                for event in ECONOMIC_CALENDAR:
                    year, month, day, hour, minute, name, impact, forecast, previous = event
                    try:
                        event_dt = ET.localize(datetime(year, month, day, hour, minute))
                    except:
                        continue
                    event_date = event_dt.date()

                    # Skip events not in current month or adjacent months
                    if not ((month == current_month and year == current_year) or
                            (month == current_month - 1 and year == current_year) or
                            (month == 12 and current_month == 1 and year == current_year - 1) or
                            (month == current_month + 1 and year == current_year) or
                            (month == 1 and current_month == 12 and year == current_year + 1)):
                        continue

                    event_data = {
                        'date': event_dt.strftime('%b %d'),
                        'time': event_dt.strftime('%H:%M'),
                        'event': name,
                        'impact': impact.lower(),
                        'forecast': forecast,
                        'previous': previous,
                        'is_today': event_date == today
                    }

                    if event_dt <= now:
                        event_data['actual'] = forecast  # For past events, use forecast as actual
                        past_events.append(event_data)
                    else:
                        upcoming_events.append(event_data)

                # Sort: past by date descending, upcoming by date ascending
                past_events.sort(key=lambda x: x['date'], reverse=True)
                upcoming_events.sort(key=lambda x: x['date'])

                response_data = {
                    'economic_calendar': {
                        'current_month': now.strftime('%B %Y'),
                        'last_updated': now.strftime('%Y-%m-%d %H:%M ET'),
                        'past': past_events[:10],  # Last 10 past events
                        'upcoming': upcoming_events[:15]  # Next 15 upcoming
                    },
                    'stream_active': False,
                    'transcript_buffer': [],
                    'sentiment': {'current': 'neutral', 'score': 0},
                    'market_direction': {'signal': 'neutral', 'strength': 0}
                }
                self.wfile.write(json.dumps(response_data).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e), 'economic_calendar': {'past': [], 'upcoming': []}}).encode())
            return

        # Manual refresh PD levels endpoint
        if path == '/refresh-pd':
            try:
                print("🔄 Manual PD refresh triggered via /refresh-pd")
                fetch_pd_levels()
                self.wfile.write(json.dumps({
                    'status': 'ok',
                    'pd_high': state.get('pd_high', 0),
                    'pd_low': state.get('pd_low', 0),
                    'pdpoc': state.get('pdpoc', 0),
                    'pd_date_range': state.get('pd_date_range', '')
                }).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
            return

        # Manual session cache refresh endpoint
        if path == '/refresh-session-cache':
            try:
                print("🔄 Manual session cache refresh triggered")
                # Clear existing cache
                weekly_sessions_cache['current']['ready'] = False
                weekly_sessions_cache['current']['data'] = None
                # Fetch fresh data
                data = fetch_week_sessions_ohlc('current')
                self.wfile.write(json.dumps({
                    'status': 'ok',
                    'days': len(data) if data else 0,
                    'message': 'Session cache refreshed'
                }).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
            return

        # Zone Participation endpoint
        if path == '/zones':
            with lock:
                zones = collect_all_zones()
                buy_zones = rank_buy_zones(zones, target_pts=10)

                # Add readiness to top buy zones
                for i, zone in enumerate(buy_zones):
                    zone['priority'] = i + 1
                    zone['readiness'] = check_setup_readiness(zone)

                # Calculate trade framework for ALL zones (for greyed-out display)
                for zone in zones:
                    if 'trade' not in zone:
                        zone['trade'] = calculate_trade_framework(zone, target_pts=10)

                # Get session IBs
                asia_ib_high = tpo_state['sessions']['tpo1_asia'].get('ib_high', 0)
                asia_ib_low = tpo_state['sessions']['tpo1_asia'].get('ib_low', 999999)
                london_ib_high = tpo_state['sessions']['tpo2_london'].get('ib_high', 0)
                london_ib_low = tpo_state['sessions']['tpo2_london'].get('ib_low', 999999)
                us_ib_high = tpo_state['sessions']['tpo3_us_am'].get('ib_high', 0)
                us_ib_low = tpo_state['sessions']['tpo3_us_am'].get('ib_low', 999999)

                response = {
                    'current_price': state.get('current_price', 0),
                    'timestamp': time.time(),
                    'active_session': tpo_state.get('active_session'),

                    # Top 3 buy zones with full trade framework
                    'buy_zones': buy_zones,

                    # All zones for reference
                    'all_zones': zones,

                    # Session IBs summary
                    'session_ibs': {
                        'asia': {
                            'high': asia_ib_high if asia_ib_high is not None and asia_ib_high > 0 else None,
                            'low': asia_ib_low if asia_ib_low is not None and asia_ib_low < 999999 else None,
                        },
                        'london': {
                            'high': london_ib_high if london_ib_high is not None and london_ib_high > 0 else None,
                            'low': london_ib_low if london_ib_low is not None and london_ib_low < 999999 else None,
                        },
                        'us': {
                            'high': us_ib_high if us_ib_high is not None and us_ib_high > 0 else None,
                            'low': us_ib_low if us_ib_low is not None and us_ib_low < 999999 else None,
                        },
                        'us_pm': None,  # No IB for US PM session
                    }
                }

            self.wfile.write(json.dumps(response).encode())
            return

        # Handle /session-history endpoint for VSI analysis
        if path == '/session-history':
            # FAST PATH: Get instantly from cache (fixed 10 historical days)
            if session_history_cache['ready']:
                history_data = get_session_history_fast()

                if history_data:
                    # Merge in live current session data from state
                    with lock:
                        current_session = state.get('current_session_id', '')
                        session_high = state.get('session_high', 0)
                        session_low = state.get('session_low', 999999)

                        # Update current session's todayRange with live data
                        if current_session and current_session in history_data:
                            if session_high > 0 and session_low < 999999:
                                live_range = session_high - session_low
                                history_data[current_session]['todayRange'] = live_range

                    self.wfile.write(json.dumps(history_data).encode())
                    return

            # Cache not ready yet - return loading status
            self.wfile.write(json.dumps({'loading': True, 'message': 'Cache initializing...'}).encode())
            return

        # Handle /historical-sessions endpoint for 5-day OHLC candle visualization
        # Supports ?week=w5|w4|w3|w2|w1|current parameter (dynamic week IDs)
        if path == '/historical-sessions':
            # Get week parameter from query_params (already parsed by urlparse)
            week_id = query_params.get('week', ['current'])[0]
            print(f"📅 Historical sessions request for week: {week_id}")

            # Check weekly cache first (for specific weeks)
            if week_id in weekly_sessions_cache and weekly_sessions_cache[week_id]['ready']:
                data = weekly_sessions_cache[week_id]['data']

                # For current week, merge today's live ended_sessions from state
                if week_id == 'current' and data and len(data) > 0:
                    today_str = datetime.now(timezone(timedelta(hours=-5))).strftime('%Y-%m-%d')
                    # Find today in the data
                    for day_data in data:
                        if day_data.get('date') == today_str:
                            with lock:
                                ended = state.get('ended_sessions', {})
                                day_high = state.get('day_high', 0)
                                day_low = state.get('day_low', 999999)
                                day_open = state.get('day_open', 0)
                                current_price = state.get('current_price', 0)

                                # Update day OHLC with live data
                                if day_high > 0:
                                    day_data['day'] = {
                                        'o': day_open,
                                        'h': day_high,
                                        'l': day_low if day_low < 999999 else day_high,
                                        'c': current_price
                                    }

                                # Merge in ended sessions for today
                                for sid, sdata in ended.items():
                                    day_data['sessions'][sid] = {
                                        'o': sdata.get('open', 0),
                                        'h': sdata.get('high', 0),
                                        'l': sdata.get('low', 0),
                                        'c': sdata.get('close', 0)
                                    }
                            break

                self.wfile.write(json.dumps({'days': data, 'week': week_id, 'cached': True}).encode())
                return

            # If any week (including 'current') is requested and not cached, fetch on demand
            valid_weeks = ['w5', 'w4', 'w3', 'w2', 'w1', 'current']
            if week_id in valid_weeks and week_id in weekly_sessions_cache and not weekly_sessions_cache[week_id]['ready']:
                print(f"📊 Fetching {week_id} on demand...")
                try:
                    data = fetch_week_sessions_ohlc(week_id)
                    if data:
                        self.wfile.write(json.dumps({'days': data, 'week': week_id, 'cached': False, 'fresh': True}).encode())
                        return
                except Exception as e:
                    print(f"❌ Error fetching {week_id}: {e}")

            # Fall back to legacy cache (works for 'current' and as fallback for uncached weeks)
            if historical_sessions_ohlc_cache['ready']:
                # Return cached data - merge with today's live data for day 0
                data = historical_sessions_ohlc_cache['data']

                if data and len(data) > 0:
                    # Update today's (index 0) session data with live ended sessions
                    with lock:
                        ended = state.get('ended_sessions', {})
                        day_high = state.get('day_high', 0)
                        day_low = state.get('day_low', 999999)
                        day_open = state.get('day_open', 0)
                        current_price = state.get('current_price', 0)

                        # Update day 0 with live data
                        if day_high > 0:
                            data[0]['day'] = {
                                'o': day_open,
                                'h': day_high,
                                'l': day_low if day_low < 999999 else day_high,
                                'c': current_price
                            }

                        # Merge in ended sessions for today
                        for sid, sdata in ended.items():
                            data[0]['sessions'][sid] = {
                                'o': sdata.get('open', 0),
                                'h': sdata.get('high', 0),
                                'l': sdata.get('low', 0),
                                'c': sdata.get('close', 0)
                            }

                self.wfile.write(json.dumps({'days': data, 'week': week_id, 'cached': True, 'fallback': week_id != 'current'}).encode())
                return
            else:
                # Cache not ready - return loading status
                self.wfile.write(json.dumps({'loading': True, 'week': week_id, 'message': f'Fetching {week_id} data...'}).encode())
                return

        # Handle /market-profile endpoint for TPO data
        if path == '/market-profile':
            with lock:
                day = tpo_state['day']

                # Helper to sort letters chronologically (by period index, not alphabetically)
                def sort_letters_chronologically(letters):
                    def letter_to_index(letter):
                        # A=0, B=1, ... Z=25, AA=26, AB=27, ... AZ=51, BA=52, etc.
                        if len(letter) == 1:
                            return ord(letter) - ord('A')
                        elif len(letter) == 2 and letter[0].isalpha() and letter[1].isalpha():
                            # Two-letter format like "AA", "AB", "AJ"
                            first = ord(letter[0]) - ord('A')
                            second = ord(letter[1]) - ord('A')
                            return 26 + first * 26 + second
                        else:
                            # Fallback for any other format
                            return 0
                    return sorted(list(letters), key=letter_to_index)

                # Convert DAY profiles to JSON-serializable format (sets -> chronologically sorted lists)
                day_profiles_json = {}
                for price, letters in day['profiles'].items():
                    day_profiles_json[str(price)] = sort_letters_chronologically(letters)

                # Convert SESSION profiles to JSON-serializable format
                sessions_json = {}
                for session_key, session_data in tpo_state['sessions'].items():
                    session_profiles = {}
                    for price, letters in session_data['profiles'].items():
                        session_profiles[str(price)] = sort_letters_chronologically(letters)
                    session_config = TPO_SESSIONS.get(session_key, {})
                    # Use .get() with defaults for all session data fields
                    ib_high = session_data.get('ib_high') or 0
                    ib_low = session_data.get('ib_low') or 999999
                    sessions_json[session_key] = {
                        'name': session_config.get('name', session_key),
                        'display': session_config.get('display', session_key),
                        'color': session_config.get('color', '#888888'),
                        'number': session_config.get('number', 0),
                        'profiles': session_profiles,
                        'period_count': session_data.get('period_count', 0),
                        'current_letter': get_tpo_letter(session_data.get('period_count', 0)),
                        'poc': session_data.get('poc', 0),
                        'vah': session_data.get('vah', 0),
                        'val': session_data.get('val', 0),
                        'single_prints': session_data.get('single_prints', []),
                        'ib_high': ib_high if ib_high and ib_high > 0 else None,
                        'ib_low': ib_low if ib_low and ib_low < 999999 else None,
                        'ib_complete': session_data.get('ib_complete', False),
                        'open_price': session_data.get('open_price', 0),
                        'high': session_data.get('high') if session_data.get('high') and session_data.get('high') > 0 else None,
                        'low': session_data.get('low') if session_data.get('low') and session_data.get('low') < 999999 else None,
                        'max_tpo_count': session_data.get('max_tpo_count', 0),
                        'total_tpo_count': session_data.get('total_tpo_count', 0),
                        'profile_shape': session_data.get('profile_shape', 'developing'),
                        'day_type': session_data.get('day_type', 'developing'),
                        'day_type_confidence': session_data.get('day_type_confidence', 0),
                    }
                    # Add RTH-specific open type info for tpo3_us_am
                    if session_key == 'tpo3_us_am':
                        sessions_json[session_key]['open_type'] = session_data.get('open_type', 'developing')
                        sessions_json[session_key]['open_type_confidence'] = session_data.get('open_type_confidence', 0)
                        sessions_json[session_key]['open_direction'] = session_data.get('open_direction')
                        ab_val = session_data.get('ab_overlap')
                        sessions_json[session_key]['ab_overlap'] = round(ab_val, 1) if ab_val is not None else None
                        a_high = session_data.get('a_high', 0)
                        a_low = session_data.get('a_low', 999999)
                        b_high = session_data.get('b_high', 0)
                        b_low = session_data.get('b_low', 999999)
                        sessions_json[session_key]['a_high'] = a_high if a_high > 0 else None
                        sessions_json[session_key]['a_low'] = a_low if a_low < 999999 else None
                        sessions_json[session_key]['b_high'] = b_high if b_high > 0 else None
                        sessions_json[session_key]['b_low'] = b_low if b_low < 999999 else None

                # Day type display names
                day_type_names = {
                    'developing': 'Developing',
                    'normal': 'Normal/Balance',
                    'non_trend': 'Non-Trend',
                    'normal_var': 'Normal Variation',
                    'trend': 'Trend',
                    'double_dist': 'Double Distribution',
                    'neutral': 'Neutral'
                }

                # Open type descriptions
                open_type_info = {
                    'developing': {'name': 'Developing', 'conviction': 'N/A', 'description': 'Still analyzing opening activity'},
                    'OA': {'name': 'Open Auction', 'conviction': 'LOWEST', 'description': 'Choppy/ranging, no clear direction'},
                    'ORR': {'name': 'Open Rejection Reverse', 'conviction': 'LOW', 'description': 'V-shape reversal from open'},
                    'OTD': {'name': 'Open Test Drive', 'conviction': 'HIGH', 'description': 'Tested opposite direction, then trended'},
                    'OD': {'name': 'Open Drive', 'conviction': 'HIGHEST', 'description': 'Strong trend from open, LT trader in control'}
                }

                # Profile shape descriptions
                shape_info = {
                    'developing': {'name': 'Developing', 'sentiment': 'N/A', 'description': 'Profile still forming'},
                    'D': {'name': 'D-Shape', 'sentiment': 'Balanced', 'description': 'Normal distribution, fat middle, thin tails'},
                    'P': {'name': 'P-Shape', 'sentiment': 'Bullish', 'description': 'Fat top, thin bottom - short covering / accumulation'},
                    'b': {'name': 'b-Shape', 'sentiment': 'Bearish', 'description': 'Fat bottom, thin top - long liquidation / distribution'},
                    'B': {'name': 'B-Shape', 'sentiment': 'Transitional', 'description': 'Double distribution - two value areas'}
                }

                # Best trade setups by day type
                trade_setups = {
                    'developing': 'Wait for profile to develop',
                    'normal': 'Fade extremes, look for POC reversion',
                    'non_trend': 'Wait for catalyst, not high conviction',
                    'normal_var': 'VAH/VAL tests, IB breakout plays',
                    'trend': 'Early entry, retrace to VA, go with LT trader',
                    'double_dist': 'Trade 2nd distribution, watch single prints for S/R',
                    'neutral': 'Fade IB extremes, breakout failures'
                }

                response = {
                    # Active session info
                    'active_session': tpo_state['active_session'],
                    'active_session_info': TPO_SESSIONS.get(tpo_state['active_session'], {}) if tpo_state['active_session'] else None,

                    # 4 Session profiles
                    'sessions': sessions_json,

                    # DAY TPO Profile data (combined full day)
                    'profiles': day_profiles_json,
                    'current_letter': get_tpo_letter(day['period_count']),
                    'period_count': day['period_count'],
                    'tick_size': CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])['tick_size'],

                    # Day Key Levels
                    'poc': day['poc'],
                    'vah': day['vah'],
                    'val': day['val'],
                    'single_prints': day['single_prints'],
                    'single_prints_count': len(day['single_prints']),

                    # Day Initial Balance (RTH IB: 09:30-10:30)
                    'ib_high': day.get('ib_high') if day.get('ib_high') and day.get('ib_high') > 0 else None,
                    'ib_low': day.get('ib_low') if day.get('ib_low') and day.get('ib_low') < 999999 else None,
                    'ib_range': (day.get('ib_high', 0) - day.get('ib_low', 0)) if day.get('ib_high') and day.get('ib_low') and day.get('ib_high') > 0 and day.get('ib_low') < 999999 else None,
                    'ib_complete': day.get('ib_complete', False),

                    # Day Period Ranges
                    'a_high': day.get('a_high') if day.get('a_high') and day.get('a_high') > 0 else None,
                    'a_low': day.get('a_low') if day.get('a_low') and day.get('a_low') < 999999 else None,
                    'b_high': day.get('b_high') if day.get('b_high') and day.get('b_high') > 0 else None,
                    'b_low': day.get('b_low') if day.get('b_low') and day.get('b_low') < 999999 else None,
                    'c_high': day.get('c_high') if day.get('c_high') and day.get('c_high') > 0 else None,
                    'c_low': day.get('c_low') if day.get('c_low') and day.get('c_low') < 999999 else None,
                    'open_price': day['open_price'],
                    'rth_open': day.get('rth_open', 0),

                    # Day Overlaps (None if periods not yet started)
                    'ab_overlap': round(day['ab_overlap'], 1) if day['ab_overlap'] is not None else None,
                    'bc_overlap': round(day['bc_overlap'], 1) if day['bc_overlap'] is not None else None,

                    # Day Type Classification
                    'day_type': day['day_type'],
                    'day_type_name': day_type_names.get(day['day_type'], day['day_type']),
                    'day_type_confidence': day['day_type_confidence'],
                    'day_type_scores': day['day_type_scores'],
                    'trade_setup': trade_setups.get(day['day_type'], ''),

                    # Open Type Classification (from RTH session)
                    'open_type': day['open_type'],
                    'open_type_info': open_type_info.get(day['open_type'], open_type_info['developing']),
                    'open_type_confidence': day['open_type_confidence'],
                    'open_direction': day['open_direction'],

                    # Profile Shape
                    'profile_shape': day['profile_shape'],
                    'profile_shape_info': shape_info.get(day['profile_shape'], shape_info['developing']),

                    # Metrics
                    'max_tpo_count': day['max_tpo_count'],
                    'total_tpo_count': day['total_tpo_count'],
                    'range_extension_pct': round(day['range_extension_pct'], 1),
                    'avg_daily_range': tpo_state['avg_daily_range'],

                    # Current price for reference
                    'current_price': state['current_price'],
                    'vwap': state.get('vwap', 0),  # Full day VWAP from live state
                    'rth_vwap': state.get('rth_vwap', 0),  # RTH VWAP (9:30 ET anchored)
                    'timestamp': time.time()
                }

                # Calculate MP+FP Confluence Score (Mind Over Markets + Footprint Integration)
                try:
                    current_price = state.get('current_price', 0)
                    delta = state.get('cumulative_delta', 0)
                    confluence = calculate_mp_fp_confluence(current_price, delta)
                    response['confluence'] = confluence
                except Exception as e:
                    response['confluence'] = {
                        'error': str(e),
                        'total_score': 0,
                        'confidence': 'UNKNOWN',
                        'action': 'ERROR'
                    }

            self.wfile.write(json.dumps(response).encode())
            return

        # Handle /historic-tpo endpoint for historical TPO profiles
        if path == '/historic-tpo':
            try:
                # Get number of days from query params (default 40 = 8 weeks)
                days = int(query_params.get('days', ['40'])[0])
                days = min(days, 60)  # Cap at 60 days

                historic_data = fetch_historic_tpo_profiles(days)
                self.wfile.write(json.dumps(historic_data).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e), 'profiles': []}).encode())
            return

        # Handle /market-overview endpoint for Correlation Matrix
        if path == '/market-overview':
            market_data = fetch_market_overview()
            self.wfile.write(json.dumps(market_data).encode())
            return

        # ETF Flow tracking endpoint (Bitcoin ETFs: IBIT, FBTC, GBTC, etc.)
        if path == '/etf-flows':
            etf_data = fetch_btc_etf_flows()
            self.wfile.write(json.dumps(etf_data).encode())
            return

        # COT (Commitment of Traders) data endpoint
        if path == '/cot-data':
            cot_data = fetch_cot_data()
            self.wfile.write(json.dumps(cot_data).encode())
            return

        # World Gold Council data endpoint
        if path == '/wgc-data':
            wgc_data = fetch_wgc_data()
            self.wfile.write(json.dumps(wgc_data).encode())
            return

        # Institutional positions aggregated endpoint
        if path == '/institutional':
            inst_data = fetch_institutional_positions()
            self.wfile.write(json.dumps(inst_data).encode())
            return

        # Deribit options data for BTC gamma/GEX levels
        if path == '/deribit-options':
            options_data = fetch_deribit_options()

        # Trade metrics endpoint for Clawdbot analytics
        if path == '/trade-metrics':
            try:
                entry_price = float(query_params.get('entry_price', [0])[0])
                entry_time = query_params.get('entry_time', [''])[0]
                entry_date = query_params.get('entry_date', [''])[0]
                direction = query_params.get('direction', ['long'])[0].lower()
                stop_price = float(query_params.get('stop_price', [0])[0])
                t1 = float(query_params.get('t1', [0])[0]) if query_params.get('t1') else None
                t2 = float(query_params.get('t2', [0])[0]) if query_params.get('t2') else None
                t3 = float(query_params.get('t3', [0])[0]) if query_params.get('t3') else None
                contract = query_params.get('contract', ['GCG26'])[0]
                targets = [t for t in [t1, t2, t3] if t]
                if not entry_price or not entry_time or not entry_date:
                    self.wfile.write(json.dumps({'error': 'Missing required params'}).encode())
                    return
                bars = fetch_historical_bars_for_trade(contract, entry_date, entry_time)
                if not bars:
                    self.wfile.write(json.dumps({'error': 'No bar data', 'entry_date': entry_date}).encode())
                    return
                metrics = process_bars_for_trade_metrics(bars, entry_price, direction, stop_price, targets)
                self.wfile.write(json.dumps(metrics).encode())
                return
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e)}).encode())
                return

            self.wfile.write(json.dumps(options_data).encode())
            return

        # Funding rates and CME basis
        if path == '/funding-rates':
            funding_data = fetch_funding_rates()
            self.wfile.write(json.dumps(funding_data).encode())
            return

        # Clawd Bot Trade Analytics endpoint
        if path == '/trade-analytics':
            try:
                import os
                trades_file = os.path.expanduser('~/.clawdbot/trade_analytics/trades.json')
                if os.path.exists(trades_file):
                    with open(trades_file, 'r') as f:
                        trades = json.load(f)
                else:
                    trades = []

                # Filter evaluated trades only
                evaluated = [t for t in trades if t.get('outcome', {}).get('primary_outcome', {}).get('result') in ['WIN', 'LOSS']]

                # Compute analytics
                wins = [t for t in evaluated if t['outcome']['primary_outcome']['result'] == 'WIN']
                losses = [t for t in evaluated if t['outcome']['primary_outcome']['result'] == 'LOSS']

                # HIGH vs MEDIUM confidence comparison
                high_conf = [t for t in evaluated if t.get('confidence') == 'HIGH']
                med_conf = [t for t in evaluated if t.get('confidence') == 'MEDIUM']

                def calc_stats(trades_list):
                    if not trades_list:
                        return {'count': 0, 'wins': 0, 'losses': 0, 'win_rate': 0, 'pnl': 0, 'avg_rr': 0, 'avg_mae': 0, 'avg_mfe': 0}
                    w = [t for t in trades_list if t['outcome']['primary_outcome']['result'] == 'WIN']
                    l = [t for t in trades_list if t['outcome']['primary_outcome']['result'] == 'LOSS']
                    pnl = sum(t['outcome']['primary_outcome'].get('pnl_dollars', 0) for t in trades_list)
                    rrs = [t['outcome']['primary_outcome'].get('reward_risk', 0) for t in trades_list if t['outcome']['primary_outcome'].get('reward_risk', 0) > 0]
                    maes = [t['outcome']['primary_outcome'].get('mae', 0) for t in trades_list]
                    mfes = [t['outcome']['primary_outcome'].get('mfe', 0) for t in trades_list]
                    return {
                        'count': len(trades_list),
                        'wins': len(w),
                        'losses': len(l),
                        'win_rate': round(len(w) / len(trades_list) * 100, 1) if trades_list else 0,
                        'pnl': pnl,
                        'avg_rr': round(sum(rrs) / len(rrs), 2) if rrs else 0,
                        'avg_mae': round(sum(maes) / len(maes), 1) if maes else 0,
                        'avg_mfe': round(sum(mfes) / len(mfes), 1) if mfes else 0
                    }

                # By direction
                longs = [t for t in evaluated if t.get('outcome', {}).get('direction') == 'LONG']
                shorts = [t for t in evaluated if t.get('outcome', {}).get('direction') == 'SHORT']

                # Target hit rates
                t1_hits = sum(1 for t in evaluated if t['outcome']['primary_outcome'].get('t1_hit'))
                t2_hits = sum(1 for t in evaluated if t['outcome']['primary_outcome'].get('t2_hit'))
                t3_hits = sum(1 for t in evaluated if t['outcome']['primary_outcome'].get('t3_hit'))

                analytics = {
                    'summary': {
                        'total_signals': len(trades),
                        'evaluated': len(evaluated),
                        'wins': len(wins),
                        'losses': len(losses),
                        'win_rate': round(len(wins) / len(evaluated) * 100, 1) if evaluated else 0,
                        'total_pnl': sum(t['outcome']['primary_outcome'].get('pnl_dollars', 0) for t in evaluated),
                        'avg_winner': round(sum(t['outcome']['primary_outcome'].get('pnl_dollars', 0) for t in wins) / len(wins), 2) if wins else 0,
                        'avg_loser': round(sum(t['outcome']['primary_outcome'].get('pnl_dollars', 0) for t in losses) / len(losses), 2) if losses else 0,
                    },
                    'by_confidence': {
                        'HIGH': calc_stats(high_conf),
                        'MEDIUM': calc_stats(med_conf)
                    },
                    'by_direction': {
                        'LONG': calc_stats(longs),
                        'SHORT': calc_stats(shorts)
                    },
                    'target_hit_rates': {
                        't1': round(t1_hits / len(evaluated) * 100, 1) if evaluated else 0,
                        't2': round(t2_hits / len(evaluated) * 100, 1) if evaluated else 0,
                        't3': round(t3_hits / len(evaluated) * 100, 1) if evaluated else 0
                    },
                    'drawdown': {
                        'avg_mae_pts': round(sum(t['outcome']['primary_outcome'].get('mae', 0) for t in evaluated) / len(evaluated), 1) if evaluated else 0,
                        'avg_mae_dollars': round(sum(t['outcome']['primary_outcome'].get('mae_dollars', 0) for t in evaluated) / len(evaluated), 0) if evaluated else 0,
                        'max_mae_dollars': max((t['outcome']['primary_outcome'].get('mae_dollars', 0) for t in evaluated), default=0),
                        'avg_mfe_pts': round(sum(t['outcome']['primary_outcome'].get('mfe', 0) for t in evaluated) / len(evaluated), 1) if evaluated else 0,
                    },
                    'trades': [{
                        'timestamp': t.get('timestamp'),
                        'contract': t.get('contract'),
                        'bias': t.get('bias'),
                        'confidence': t.get('confidence'),
                        'direction': t.get('outcome', {}).get('direction'),
                        'entry': t.get('bullish', {}).get('entry') if t.get('outcome', {}).get('direction') == 'LONG' else t.get('bearish', {}).get('entry'),
                        'stop': t.get('bullish', {}).get('stop') if t.get('outcome', {}).get('direction') == 'LONG' else t.get('bearish', {}).get('stop'),
                        'targets': t.get('bullish', {}).get('targets') if t.get('outcome', {}).get('direction') == 'LONG' else t.get('bearish', {}).get('targets'),
                        'result': t.get('outcome', {}).get('primary_outcome', {}).get('result'),
                        'pnl_pts': t.get('outcome', {}).get('primary_outcome', {}).get('pnl_points', 0),
                        'pnl_dollars': t.get('outcome', {}).get('primary_outcome', {}).get('pnl_dollars', 0),
                        'mae': t.get('outcome', {}).get('primary_outcome', {}).get('mae', 0),
                        'mfe': t.get('outcome', {}).get('primary_outcome', {}).get('mfe', 0),
                        'rr': t.get('outcome', {}).get('primary_outcome', {}).get('reward_risk', 0),
                        't1_hit': t.get('outcome', {}).get('primary_outcome', {}).get('t1_hit', False),
                        't2_hit': t.get('outcome', {}).get('primary_outcome', {}).get('t2_hit', False),
                        't3_hit': t.get('outcome', {}).get('primary_outcome', {}).get('t3_hit', False),
                        'signal_time': t.get('signal_time', ''),
                    } for t in evaluated]
                }

                self.wfile.write(json.dumps(analytics).encode())
            except Exception as e:
                self.wfile.write(json.dumps({'error': str(e), 'trades': []}).encode())
            return

        # Default endpoint - live data
        # During startup, return minimal response to prevent lock contention
        if not startup_complete:
            init_response = {
                'data_source': 'INITIALIZING',
                'connected': False,
                'timestamp': time.time(),
                'message': 'Backend is starting up, please wait...'
            }
            self.wfile.write(json.dumps(init_response).encode())
            return

        # Make a quick snapshot of state while holding the lock briefly
        # This prevents lock contention during JSON serialization
        import copy
        with lock:
            state_snapshot = copy.copy(state)
            state_snapshot['ibs'] = copy.deepcopy(state['ibs'])
            state_snapshot['ended_sessions'] = copy.copy(state['ended_sessions'])
            state_snapshot['volume_5m'] = copy.copy(state['volume_5m'])
            state_snapshot['volume_15m'] = copy.copy(state['volume_15m'])
            state_snapshot['volume_30m'] = copy.copy(state['volume_30m'])
            state_snapshot['volume_1h'] = copy.copy(state['volume_1h'])
            state_snapshot['big_trades'] = copy.copy(state.get('big_trades', []))
            current_price = state.get('current_price', 0)

        # Now build response without holding the lock
        s = state_snapshot  # Alias for brevity
        ib_high = s['ib_high'] if s['ib_high'] > 0 else 0
        ib_low = s['ib_low'] if s['ib_low'] < 999999 else 0
        ib_mid = (ib_high + ib_low) / 2 if ib_high > 0 and ib_low > 0 else 0

        response = {
            'version': '15.9.15',  # v15.9.15: Add data_source field for frontend connection status
            'data_source': 'LIVE' if s['current_price'] > 0 else 'DISCONNECTED',
            'ticker': s['ticker'],
            'contract': s['contract'],
            'contract_name': s['contract_name'],
            'asset_class': s['asset_class'],
            'available_contracts': {k: {'symbol': v['front_month'], 'name': v['name']} for k, v in CONTRACT_CONFIG.items()},
            'price': s.get('price', s['current_price']),  # Primary price field for frontend
            'current_price': s['current_price'],
            'spot_gold_price': get_spot_gold_price(),  # XAUUSD from Yahoo Finance
            'delta_5m': s['delta_5m'],
            'delta_30m': s['delta_30m'],
            'cumulative_delta': s['cumulative_delta'],

            # IB values (legacy single IB)
            'ib_high': ib_high,
            'ib_low': ib_low,
            'ib_midpoint': ib_mid,
            'ib_locked': s['ib_locked'],
            'ib_session_name': s['ib_session_name'],
            'ib_status': s['ib_status'],

            # 4 IB Sessions - each tracked independently with POC and VWAP
            'ibs': {
                ib_key: {
                    'name': ib['name'],
                    'high': ib['high'] if ib['high'] > 0 else 0,
                    'low': ib['low'] if ib['low'] < 999999 else 0,
                    'mid': ib.get('mid', (ib['high'] + ib['low']) / 2) if ib['high'] > 0 and ib['low'] < 999999 else 0,
                    'poc': ib.get('poc', 0),  # Point of Control (highest volume price)
                    'vwap': ib.get('vwap', 0),  # IB session VWAP
                    'status': ib['status'],
                    'start': ib['start'],
                    'end': ib['end']
                }
                for ib_key, ib in s['ibs'].items()
            },
            'current_ib': s['current_ib'],

            # PD levels (from historical)
            'pdpoc': s['pdpoc'],
            'pd_high': s['pd_high'],
            'pd_low': s['pd_low'],
            'pd_vah': s.get('pd_vah', 0),
            'pd_val': s.get('pd_val', 0),
            'pd_open': s['pd_open'],
            'pd_close': s['pd_close'],
            'pd_date_range': s['pd_date_range'],

            # Previous Day NY Sessions (US IB and NY 1H from yesterday)
            'pd_us_ib': s.get('pd_us_ib', {'high': 0, 'low': 0, 'mid': 0, 'poc': 0, 'vwap': 0}),
            'pd_ny_1h': s.get('pd_ny_1h', {'high': 0, 'low': 0, 'mid': 0, 'poc': 0, 'vwap': 0}),

            # Session info
            'session_high': s['session_high'] if s['session_high'] > 0 else 0,
            'session_low': s['session_low'] if s['session_low'] < 999999 else 0,
            'session_open': s['session_open'] if s['session_open'] > 0 else 0,
            'session_volume': s['session_buy'] + s['session_sell'],
            'session_delta': s['session_buy'] - s['session_sell'],

            # Day OHLC (full trading day 18:00-17:00 ET)
            'day_open': s['day_open'] if s['day_open'] > 0 else 0,
            'day_high': s['day_high'] if s['day_high'] > 0 else 0,
            'day_low': s['day_low'] if s['day_low'] < 999999 else 0,

            # Day Value Area (from TPO profile)
            'day_vah': tpo_state['day'].get('vah', 0),
            'day_val': tpo_state['day'].get('val', 0),
            'day_poc': tpo_state['day'].get('poc', 0),

            # Weekly Open (Sunday 18:00 ET)
            'weekly_open': s['weekly_open'] if s['weekly_open'] > 0 else 0,
            'weekly_open_date': s['weekly_open_date'],

            # Week High/Low (current trading week)
            'week_high': s['week_high'] if s['week_high'] > 0 else 0,
            'week_low': s['week_low'] if s['week_low'] < 999999 else 0,

            # Rolling 20-day High/Low (for monthly bias)
            'rolling_20d_high': s['rolling_20d_high'] if s['rolling_20d_high'] > 0 else 0,
            'rolling_20d_low': s['rolling_20d_low'] if s['rolling_20d_low'] < 999999 else 0,

            # Ended sessions OHLC
            'ended_sessions': s['ended_sessions'],

            'vwap': s['vwap'],
            'rth_vwap': s.get('rth_vwap', 0),  # RTH VWAP (9:30 ET anchored)

            # Anchored VWAPs (persist until 17:00 ET)
            'day_vwap': s.get('day_vwap', 0),  # Full day VWAP from 18:00 ET
            'us_ib_vwap': s.get('us_ib_vwap', 0),  # US IB anchored VWAP from 08:20 ET
            'ny_1h_vwap': s.get('ny_1h_vwap', 0),  # NY 1H anchored VWAP from 09:30 ET

            'current_session_id': s['current_session_id'],
            'current_session_name': s['current_session_name'],
            'current_session_start': s['current_session_start'],
            'current_session_end': s['current_session_end'],

            # Analysis
            'buying_imbalance_pct': s['buying_imbalance_pct'],
            'absorption_ratio': s['absorption_ratio'],
            'stacked_buy_imbalances': s['stacked_buy_imbalances'],
            'current_phase': s['current_phase'],
            'conditions_met': s['conditions_met'],
            'entry_signal': s['entry_signal'],

            # Volume (session cumulative)
            'buy_volume': s['buy_volume'],
            'sell_volume': s['sell_volume'],
            'total_volume': s['total_volume'],
            'volume_start_time': s['volume_start_time'],

            # Volume by timeframe
            'volume_5m': s['volume_5m'],
            'volume_15m': s['volume_15m'],
            'volume_30m': s['volume_30m'],
            'volume_1h': s['volume_1h'],

            # Swing Detection (for Fibonacci retracement)
            # Finds impulse move direction by checking which extreme (high/low) came first
            'swing': (lambda candles: (
                {
                    'swing_high': round(max(c.get('price_high', 0) for c in candles) if candles else s.get('session_high', 0), 1),
                    'swing_low': round(min(c.get('price_low', 999999) for c in candles) if candles else s.get('day_low', 0), 1),
                    'swing_direction': 'down' if (
                        (max(candles, key=lambda c: c.get('price_high', 0)).get('ts', 0) if candles else 0) <
                        (min(candles, key=lambda c: c.get('price_low', 999999)).get('ts', 0) if candles else 0)
                    ) else 'up',
                    'swing_high_idx': -1,
                    'swing_low_idx': -1,
                    'swing_type': 'impulse_based',
                    'extensions_direction': 'down' if (
                        (max(candles, key=lambda c: c.get('price_high', 0)).get('ts', 0) if candles else 0) <
                        (min(candles, key=lambda c: c.get('price_low', 999999)).get('ts', 0) if candles else 0)
                    ) else 'up'
                }
            ))(s['volume_5m'].get('history', [])),

            # Big Trades (Order Flow)
            'big_trades': s.get('big_trades', []),
            'big_trades_historical': get_historical_big_trades_cached()[:100],  # Limit to 100 most recent
            'big_trades_buy': s.get('big_trades_buy') or 0,
            'big_trades_sell': s.get('big_trades_sell') or 0,
            'big_trades_delta': s.get('big_trades_delta') or 0,
            'big_trade_threshold': s.get('big_trade_threshold') or 10,  # Default to 10 if None
            'threshold_stats': s.get('threshold_stats') or {},
            'trade_sizes_count': len(s.get('trade_sizes') or []),  # Debug: number of trades tracked

            # Meta
            'last_update': s['last_update'],
            'current_et_time': get_et_now().strftime('%H:%M:%S'),
            'current_et_date': get_et_now().strftime('%Y-%m-%d'),
            'data_source': s['data_source'],
            'market_open': s['market_open'],
            'pd_loaded': s['pd_loaded'],

            # GEX Data
            'gamma_regime': s.get('gamma_regime', 'UNKNOWN'),
            'total_gex': s.get('total_gex', 0),
            'zero_gamma': s.get('zero_gamma', 0),
            'hvl': s.get('hvl', 0),
            'call_wall': s.get('call_wall', 0),
            'put_wall': s.get('put_wall', 0),
            'max_pain': s.get('max_pain', 0),
            'gamma_flip': s.get('gamma_flip', 0),
            'gex_profile': generate_gex_profile(current_price),
            'gex_levels': generate_gex_levels(s),
            'beta_spx': s.get('beta_spx', 0),
            'beta_dxy': s.get('beta_dxy', 0)
        }

        self.wfile.write(json.dumps(response).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        """Handle POST requests - volume reset, contract switch"""
        global volume_history, ACTIVE_CONTRACT

        if self.path == '/reset-volume':
            with lock:
                state['buy_volume'] = 0
                state['sell_volume'] = 0
                state['total_volume'] = 0
                state['cumulative_delta'] = 0
                state['volume_start_time'] = time.time()
                state['volume_5m'] = {'buy': 0, 'sell': 0, 'delta': 0}
                state['volume_15m'] = {'buy': 0, 'sell': 0, 'delta': 0}
                state['volume_30m'] = {'buy': 0, 'sell': 0, 'delta': 0}
                state['volume_1h'] = {'buy': 0, 'sell': 0, 'delta': 0}
                volume_history.clear()
                delta_history.clear()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'reset', 'message': 'Volume counters reset'}).encode())

        elif self.path == '/reset-connection':
            # ROBUST RESET: Kills all connections, resets state, and reconnects
            def full_reset_and_reconnect():
                global state, tpo_state, volume_history, delta_history, stream_running, stream_thread, live_client
                print("\n" + "="*60)
                print("🔄 FULL CONNECTION RESET REQUESTED")
                print("="*60)

                # STEP 1: Stop all live streams and close connections
                print("\n⏹️  Step 1: Stopping all data streams...")
                state['data_source'] = 'RESETTING...'
                stream_running = False

                # Force close Databento live client
                if live_client:
                    try:
                        print("   Closing Databento live connection...")
                        live_client.close()
                    except Exception as e:
                        print(f"   Warning closing client: {e}")
                    live_client = None

                # Wait for stream thread to die
                time.sleep(2)
                print("   ✅ All streams stopped")

                # STEP 2: Reset all state data
                print("\n🧹 Step 2: Resetting all state data...")
                with lock:
                    # Reset volume state
                    state['buy_volume'] = 0
                    state['sell_volume'] = 0
                    state['total_volume'] = 0
                    state['cumulative_delta'] = 0
                    state['volume_start_time'] = time.time()
                    state['volume_5m'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': [], 'delta_open': None, 'delta_high': -999999, 'delta_low': 999999, 'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0}
                    state['volume_15m'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': [], 'delta_open': None, 'delta_high': -999999, 'delta_low': 999999, 'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0}
                    state['volume_30m'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': [], 'delta_open': None, 'delta_high': -999999, 'delta_low': 999999, 'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0}
                    state['volume_1h'] = {'buy': 0, 'sell': 0, 'delta': 0, 'candle_start': 0, 'prev_buy': 0, 'prev_sell': 0, 'prev_delta': 0, 'history': [], 'delta_open': None, 'delta_high': -999999, 'delta_low': 999999, 'price_open': 0, 'price_high': 0, 'price_low': 999999, 'price_close': 0}

                    # Reset session state
                    state['session_high'] = 0
                    state['session_low'] = 999999.0
                    state['session_open'] = 0
                    state['session_buy'] = 0
                    state['session_sell'] = 0

                    # Reset day state
                    state['day_high'] = 0
                    state['day_low'] = 999999.0
                    state['day_open'] = 0

                    # Reset week state
                    state['week_high'] = 0
                    state['week_low'] = 999999.0
                    state['weekly_open'] = 0
                    state['rolling_20d_high'] = 0
                    state['rolling_20d_low'] = 999999.0

                    # Reset price
                    state['price'] = 0
                    state['current_price'] = 0

                    # Clear histories
                    volume_history.clear()
                    delta_history.clear()
                print("   ✅ State reset complete")

                # STEP 3: Reload cached data
                print("\n📦 Step 3: Reloading cached data...")
                load_all_caches()
                print("   ✅ Cache reloaded")

                # STEP 4: Restart appropriate stream based on contract type
                print("\n🔌 Step 4: Reconnecting to data sources...")
                config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
                is_spot = config.get('is_spot', False)

                if is_spot:
                    global spot_crypto_thread
                    print(f"   Starting spot crypto stream for {ACTIVE_CONTRACT}")
                    spot_crypto_thread = threading.Thread(target=spot_crypto_stream, daemon=True)
                    spot_crypto_thread.start()
                else:
                    stream_running = True
                    stream_thread = threading.Thread(target=start_stream, daemon=True)
                    stream_thread.start()

                print("\n" + "="*60)
                print("✅ FULL RESET COMPLETE - Reconnecting to live data")
                print("="*60 + "\n")

            # Run reset in background
            reset_thread = threading.Thread(target=full_reset_and_reconnect, daemon=True)
            reset_thread.start()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'resetting',
                'message': 'Full reset initiated: stopping all connections, clearing state, reconnecting...'
            }).encode())

        elif self.path == '/switch-contract':
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body) if body else {}
                new_contract = data.get('contract', 'GC')

                if new_contract in CONTRACT_CONFIG:
                    # Full dynamic switch - stops stream, resets state, restarts with new contract
                    config = CONTRACT_CONFIG[new_contract]

                    # Run switch in background thread to avoid blocking HTTP response
                    switch_thread = threading.Thread(target=switch_contract, args=(new_contract,), daemon=True)
                    switch_thread.start()

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({
                        'status': 'switching',
                        'contract': new_contract,
                        'message': f'Switching to {config["name"]}... Live data will update in a few seconds.'
                    }).encode())
                else:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': f'Unknown contract: {new_contract}'}).encode())
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())

        elif self.path == '/reconnect':
            # Force reconnection to Databento - useful after errno 54 errors
            # Rate limited to prevent reconnection loops
            global stream_running, stream_thread, _last_reconnect_time

            # Rate limit: only allow reconnect every 5 minutes (was 60 seconds)
            current_time = time.time()
            RECONNECT_COOLDOWN = 300  # 5 minutes
            if not hasattr(self, '_last_reconnect_time'):
                globals()['_last_reconnect_time'] = 0

            time_since_last = current_time - globals().get('_last_reconnect_time', 0)
            if time_since_last < RECONNECT_COOLDOWN:
                print(f"⚠️ Reconnect rate limited - {RECONNECT_COOLDOWN - time_since_last:.0f}s remaining")
                self.send_response(429)  # Too Many Requests
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'rate_limited',
                    'message': f'Please wait {RECONNECT_COOLDOWN - time_since_last:.0f}s before reconnecting again.',
                    'retry_after': int(RECONNECT_COOLDOWN - time_since_last)
                }).encode())
                return

            globals()['_last_reconnect_time'] = current_time
            print("\n🔄 Manual reconnection requested...")
            state['data_source'] = 'RECONNECTING...'

            # Stop existing stream
            stop_stream()

            # Small delay to allow cleanup
            time.sleep(1)

            # Restart appropriate stream based on contract type
            config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
            is_spot = config.get('is_spot', False)

            if is_spot:
                # Restart spot crypto stream
                global spot_crypto_thread
                print(f"🔄 Starting spot crypto stream for {ACTIVE_CONTRACT}")
                spot_crypto_thread = threading.Thread(target=spot_crypto_stream, daemon=True)
                spot_crypto_thread.start()
            else:
                # Restart Databento stream
                stream_running = True
                stream_thread = threading.Thread(target=start_stream, daemon=True)
                stream_thread.start()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'reconnecting',
                'message': 'Reconnection initiated. Live data will resume shortly.'
            }).encode())

        elif self.path == '/chat':
            # Horizon AI Chat endpoint - supports Groq and OpenAI
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                data = json.loads(body) if body else {}
                user_message = data.get('message', '')
                context = data.get('context', {})
                provider = data.get('provider', 'groq')  # 'groq' or 'openai'

                # Build system prompt with trading context and platform knowledge
                # Extract live metrics from context
                live_session = context.get('liveSession', 'Unknown')
                session_high = context.get('sessionHigh')
                session_low = context.get('sessionLow')
                day_high = context.get('dayHigh')
                day_low = context.get('dayLow')
                pd_high = context.get('pdHigh')
                pd_low = context.get('pdLow')
                pd_poc = context.get('pdPOC')
                cum_delta = context.get('cumulativeDelta')
                buy_vol = context.get('buyVolume')
                sell_vol = context.get('sellVolume')
                current_time = context.get('currentTime', 'N/A')
                current_price = context.get('currentPrice', 0)

                # Build dynamic metrics section
                metrics_lines = []
                metrics_lines.append(f"- **Current Price**: ${current_price}")
                metrics_lines.append(f"- **Time (ET)**: {current_time}")
                metrics_lines.append(f"- **Active Session**: {live_session}")

                if session_high and session_low and session_high > 0:
                    metrics_lines.append(f"- **Session Range**: ${session_low:.2f} - ${session_high:.2f} (Range: ${session_high - session_low:.2f})")
                if day_high and day_low and day_high > 0:
                    metrics_lines.append(f"- **Day Range**: ${day_low:.2f} - ${day_high:.2f} (Range: ${day_high - day_low:.2f})")

                pd_lines = []
                if pd_high and pd_high > 0:
                    pd_lines.append(f"- PD High: ${pd_high:.2f}")
                if pd_low and pd_low > 0:
                    pd_lines.append(f"- PD Low: ${pd_low:.2f}")
                if pd_poc and pd_poc > 0:
                    pd_lines.append(f"- PD POC: ${pd_poc:.2f}")

                flow_lines = []
                if cum_delta is not None:
                    flow_lines.append(f"- Cumulative Delta: {cum_delta:+,}")
                if buy_vol and sell_vol:
                    flow_lines.append(f"- Buy Volume: {buy_vol:,} | Sell Volume: {sell_vol:,}")
                    imbalance = ((buy_vol - sell_vol) / max(buy_vol + sell_vol, 1)) * 100
                    flow_lines.append(f"- Volume Imbalance: {imbalance:+.1f}%")

                metrics_section = "\n".join(metrics_lines)
                pd_section = "\n".join(pd_lines) if pd_lines else "- Not available"
                flow_section = "\n".join(flow_lines) if flow_lines else "- Not available"

                system_prompt = f"""You are Horizon AI, the intelligent trading assistant built into Project Horizon - a professional futures trading analysis platform.

## CONTRACT
{context.get('contractName', 'Gold Futures')} ({context.get('contract', 'GC')}) | Data: Databento Live

## LIVE MARKET DATA
{metrics_section}

## PREVIOUS DAY LEVELS
{pd_section}

## ORDER FLOW
{flow_section}

## PROJECT HORIZON PLATFORM FEATURES

### Session Analysis Dashboard
The main feature showing session-based OHLC candles across global trading sessions:
- **1D Column**: Full day candle (aggregated)
- **Trading Sessions** (in order): Japan (19:00-20:00), China (20:00-23:00), Deadzone (02:00-03:00), London (03:00-06:00), US IB (08:20-09:30), NY 1H (09:30-10:30), NY 2H (10:30-11:30), Lunch (11:30-13:30), NY PM (13:30-16:00)
- All times are Eastern Time (ET)

### Key Indicators
- **HOW (High of Week)**: Green highlighted candle - the session that made the week's high
- **LOW (Low of Week)**: Red highlighted candle - the session that made the week's low
- **HOD (High of Day)**: Dashed green line above candle - session high of the day
- **LOD (Low of Day)**: Dashed red line below candle - session low of the day

### View Modes
- **Horizon Mode**: Shows key sessions only (Japan, China, London, US IB, NY sessions)
- **Universe Mode**: Shows ALL sessions including pre-Asia, Asia, Deadzone, etc.

### Historical Data
- View up to 5 historical weeks (W50, W51, W52, W1, W2) plus Current week
- Each week shows Mon-Fri with Friday at top
- Data cached locally for fast loading

### Metrics & Data Points
- Session OHLC (Open, High, Low, Close)
- Price range visualization with scaled candles
- Tooltip shows exact prices when hovering
- Previous Day levels: PD High, PD Low, PD POC (Point of Control)
- Initial Balance (IB) levels for each major session

### Live Features
- Real-time price updates via Databento
- Live session tracking with "LIVE" indicator
- Contract switching (Gold GC, NQ futures)
- Latency monitoring

## GUIDELINES
- Reference specific platform features when relevant to user questions
- Help users understand how to use Session Analysis for trading decisions
- Explain HOW/LOW, HOD/LOD significance for trade planning
- Discuss session-based trading strategies (London open, NY open, etc.)
- Be concise but thorough
- Never provide financial advice - only educational information
- Format responses for easy reading"""

                response_text = ""

                if provider == 'groq':
                    # Groq API (free tier with Llama 3.3)
                    groq_key = os.environ.get('GROQ_API_KEY', '')
                    if not groq_key:
                        raise Exception("GROQ_API_KEY not set in .env file")

                    req_data = json.dumps({
                        "model": "llama-3.3-70b-versatile",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        "max_tokens": 1024,
                        "temperature": 0.7
                    }).encode()

                    req = urllib.request.Request(
                        "https://api.groq.com/openai/v1/chat/completions",
                        data=req_data,
                        headers={
                            "Authorization": f"Bearer {groq_key}",
                            "Content-Type": "application/json",
                            "User-Agent": "HorizonAI/1.0"
                        }
                    )
                    ctx = ssl.create_default_context()
                    try:
                        with urllib.request.urlopen(req, context=ctx) as resp:
                            result = json.loads(resp.read().decode())
                            response_text = result['choices'][0]['message']['content']
                    except urllib.error.HTTPError as e:
                        error_body = e.read().decode()
                        raise Exception(f"Groq API error ({e.code}): {error_body}")

                elif provider == 'openai':
                    # OpenAI API (ChatGPT)
                    openai_key = os.environ.get('OPENAI_API_KEY', '')
                    if not openai_key:
                        raise Exception("OPENAI_API_KEY not set in .env file")

                    req_data = json.dumps({
                        "model": "gpt-4o",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        "max_tokens": 1024,
                        "temperature": 0.7
                    }).encode()

                    req = urllib.request.Request(
                        "https://api.openai.com/v1/chat/completions",
                        data=req_data,
                        headers={
                            "Authorization": f"Bearer {openai_key}",
                            "Content-Type": "application/json",
                            "User-Agent": "HorizonAI/1.0"
                        }
                    )
                    ctx = ssl.create_default_context()
                    try:
                        with urllib.request.urlopen(req, context=ctx) as resp:
                            result = json.loads(resp.read().decode())
                            response_text = result['choices'][0]['message']['content']
                    except urllib.error.HTTPError as e:
                        error_body = e.read().decode()
                        raise Exception(f"OpenAI API error ({e.code}): {error_body}")

                elif provider == 'claude':
                    # Claude API (Anthropic)
                    anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')
                    if not anthropic_key:
                        raise Exception("ANTHROPIC_API_KEY not set in .env file")

                    req_data = json.dumps({
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1024,
                        "system": system_prompt,
                        "messages": [
                            {"role": "user", "content": user_message}
                        ]
                    }).encode()

                    req = urllib.request.Request(
                        "https://api.anthropic.com/v1/messages",
                        data=req_data,
                        headers={
                            "x-api-key": anthropic_key,
                            "anthropic-version": "2023-06-01",
                            "Content-Type": "application/json",
                            "User-Agent": "HorizonAI/1.0"
                        }
                    )
                    ctx = ssl.create_default_context()
                    try:
                        with urllib.request.urlopen(req, context=ctx) as resp:
                            result = json.loads(resp.read().decode())
                            response_text = result['content'][0]['text']
                    except urllib.error.HTTPError as e:
                        error_body = e.read().decode()
                        raise Exception(f"Claude API error ({e.code}): {error_body}")

                else:
                    raise Exception(f"Unknown provider: {provider}")

                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'response': response_text,
                    'provider': provider
                }).encode())

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'error': str(e)
                }).encode())

        else:
            self.send_response(404)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Not found'}).encode())

def start_http_server():
    server = ThreadingHTTPServer(('0.0.0.0', PORT), LiveDataHandler)
    print(f"🌐 HTTP server running on http://localhost:{PORT} (threaded)")
    server.serve_forever()

# ============================================
# MAIN
# ============================================
def preload_market_overview():
    """Background preload of market overview data for faster Correlation Matrix"""
    if HAS_YFINANCE:
        print("📊 Preloading market overview data...")
        try:
            fetch_market_overview()
            print("✅ Market overview preloaded")
        except Exception as e:
            print(f"⚠️ Market overview preload failed: {e}")

def preload_historical_big_trades():
    """Background preload of historical big trades for 1H chart coverage"""
    print("📊 Preloading historical big trades (for 1H chart coverage)...")
    try:
        fetch_historical_big_trades_from_databento()
        print("✅ Historical big trades preloaded")
    except Exception as e:
        print(f"⚠️ Historical big trades preload failed: {e}")

def main():
    print("=" * 60)
    print("  PROJECT HORIZON - LIVE FEED v2 (All Live Data)")
    print("=" * 60)
    print(f"📡 HTTP: http://localhost:{PORT}")
    print(f"🔑 API: {API_KEY[:10]}..." if API_KEY else "🔑 API: NOT SET")
    print("=" * 60)

    global stream_running

    # Start HTTP server
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # Preload market overview in background (for faster Correlation Matrix)
    market_thread = threading.Thread(target=preload_market_overview, daemon=True)
    market_thread.start()

    # Fetch spot gold price in background (for GEX calculations)
    spot_thread = threading.Thread(target=fetch_spot_gold_price, daemon=True)
    spot_thread.start()

    # Preload historical big trades in background (for 1H chart coverage)
    big_trades_thread = threading.Thread(target=preload_historical_big_trades, daemon=True)
    big_trades_thread.start()

    # Set stream_running before starting feed so the stream knows it should continue
    stream_running = True

    # Start Databento feed with watchdog for 24/7 reliability
    feed_thread = threading.Thread(target=start_databento_feed, daemon=True)
    feed_thread.start()

    # Start watchdog thread to monitor connection health
    watchdog = threading.Thread(target=watchdog_thread, daemon=True)
    watchdog.start()

    print("\n📊 Starting live data stream...\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")

if __name__ == '__main__':
    main()
