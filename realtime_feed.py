#!/usr/bin/env python3
"""
PROJECT HORIZON - HTTP LIVE FEED v15.3.0
All live data from Databento - no placeholders
Memory optimized
"""
APP_VERSION = "15.5.8"

# Suppress ALL deprecation warnings to avoid log flooding and memory issues
import warnings
warnings.filterwarnings('ignore', category=DeprecationWarning)
warnings.filterwarnings('ignore', category=FutureWarning)

import os
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from collections import deque
from http.server import HTTPServer, BaseHTTPRequestHandler
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
    import yfinance as yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False
    print("⚠️  yfinance not installed. Run: pip install yfinance")

# ============================================
# CONFIGURATION
# ============================================
API_KEY = os.environ.get('DATABENTO_API_KEY', '')
PORT = int(os.environ.get('PORT', 8080))

# Contract configurations
CONTRACT_CONFIG = {
    'GC': {
        'symbol': 'GC.FUT',
        'front_month': 'GCG26',
        'front_month_name': 'Gold Feb 2026',
        'next_month': 'GCJ26',
        'next_month_name': 'Gold Apr 2026',
        'active_month': 'GCJ26',  # What we're actually trading
        'active_month_name': 'Gold Apr 2026',
        'name': 'Gold Apr 2026',
        'ticker': 'GC1!',
        'price_min': 2000,
        'price_max': 10000,
        'tick_size': 0.10,
    },
    'NQ': {
        'symbol': 'NQ.FUT',
        'front_month': 'NQH26',
        'front_month_name': 'Nasdaq Mar 2026',
        'next_month': 'NQM26',
        'next_month_name': 'Nasdaq Jun 2026',
        'name': 'Nasdaq Mar 2026',
        'ticker': 'NQ1!',
        'price_min': 10000,
        'price_max': 30000,
        'tick_size': 0.25,
    }
}

# Current active contract
ACTIVE_CONTRACT = 'GC'

# Stream control
stream_running = False
live_client = None
stream_thread = None

# ============================================
# GLOBAL STATE
# ============================================
lock = threading.Lock()

state = {
    'ticker': 'GC1!',
    'contract': 'GCJ26',  # Active contract we're trading
    'contract_name': 'Gold Apr 2026',  # Human readable name
    'asset_class': 'GC',  # GC = Gold, NQ = Nasdaq
    'current_price': 0.0,
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

    # Day levels (DYNAMIC - full trading day 18:00-17:00 ET)
    'day_high': 0.0,
    'day_low': 999999.0,
    'day_open': 0.0,  # First trade at 18:00 ET

    # Ended sessions OHLC (stored when session ends)
    'ended_sessions': {},  # {session_id: {open, high, low, close}}
    
    # 4 IB Sessions - tracked independently with VWAP
    'ibs': {
        'japan': {'high': 0.0, 'low': 999999.0, 'status': 'WAITING', 'start': '19:00', 'end': '20:00', 'name': 'Japan IB', 'vwap_num': 0.0, 'vwap_den': 0.0, 'vwap': 0.0},
        'london': {'high': 0.0, 'low': 999999.0, 'status': 'WAITING', 'start': '03:00', 'end': '04:00', 'name': 'London IB', 'vwap_num': 0.0, 'vwap_den': 0.0, 'vwap': 0.0},
        'us': {'high': 0.0, 'low': 999999.0, 'status': 'WAITING', 'start': '08:20', 'end': '09:30', 'name': 'US IB', 'vwap_num': 0.0, 'vwap_den': 0.0, 'vwap': 0.0},
        'ny': {'high': 0.0, 'low': 999999.0, 'status': 'WAITING', 'start': '09:30', 'end': '10:30', 'name': 'NY IB', 'vwap_num': 0.0, 'vwap_den': 0.0, 'vwap': 0.0},
    },
    'current_ib': None,  # Which IB is currently active (japan, london, us, ny, or None)

    # Anchored VWAPs - persist until 17:00 ET
    'us_ib_vwap': 0.0,   # US IB (08:20) anchored VWAP
    'ny_1h_vwap': 0.0,   # NY 1H (09:30) anchored VWAP
    'us_ib_vwap_num': 0.0,
    'us_ib_vwap_den': 0.0,
    'ny_1h_vwap_num': 0.0,
    'ny_1h_vwap_den': 0.0,

    # Full Day VWAP (18:00 ET anchored)
    'day_vwap': 0.0,
    'day_vwap_num': 0.0,
    'day_vwap_den': 0.0,

    # Overnight levels (18:00 - 09:30 ET)
    'overnight_high': 0.0,
    'overnight_low': 999999.0,

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
    'pd_open': 0.0,
    'pd_close': 0.0,
    'pd_loaded': False,
    'pd_date_range': '',  # e.g. "Jan 06 18:00 - Jan 07 14:55 ET"
    
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
    
    # GEX Data (estimated from options flow)
    'gamma_regime': 'NEGATIVE',
    'total_gex': -0.0234,
    'zero_gamma': 4380.0,
    'hvl': 4425.0,
    'beta_spx': 0.15,
    'beta_dxy': -0.42,
    
    # Latency
    'last_update': '',
    'market_open': False,

    # Contract Rollover (Open Interest based)
    'rollover': {
        'front_month': '',
        'front_month_name': '',
        'front_month_oi': 0,
        'next_month': '',
        'next_month_name': '',
        'next_month_oi': 0,
        'oi_ratio': 0.0,  # next_oi / front_oi
        'should_roll': False,
        'roll_signal': 'HOLD',  # HOLD, CONSIDER, ROLL
        'last_update': '',
    }
}

# Rollover fetch control
rollover_last_fetch = 0
ROLLOVER_FETCH_INTERVAL = 300  # 5 minutes

delta_history = deque(maxlen=10000)  # Reduced from 36000 to save memory
volume_history = deque(maxlen=10000)  # Reduced from 36000 to save memory
price_history = deque(maxlen=500)  # Reduced from 1000
last_session_id = None
front_month_instrument_id = None  # Will be set from historical data
active_month_instrument_id = None  # Will be resolved for GCJ26 specifically


def resolve_active_month_instrument_id():
    """Resolve the instrument_id for the active_month contract (e.g., GCJ26)

    Strategy: GCJ26 (Apr) trades consistently ~$30-50 higher than GCG26 (Feb).
    We find pairs of instruments and select the one with higher average price.
    If only one instrument found, we check if prices are in the expected GCJ26 range.
    """
    global active_month_instrument_id, front_month_instrument_id

    if not HAS_DATABENTO or not API_KEY:
        print("⚠️  Cannot resolve active month instrument ID - no Databento connection")
        return None

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    active_month = config.get('active_month', config['front_month'])  # e.g., GCJ26
    symbol = config['symbol']  # e.g., GC.FUT
    price_min = config['price_min']
    price_max = config['price_max']

    try:
        print(f"🔍 Resolving instrument ID for {active_month}...")
        client = db.Historical(key=API_KEY)

        from datetime import datetime, timedelta
        now = datetime.utcnow()
        start = (now - timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%SZ')  # 6 hour window
        end = now.strftime('%Y-%m-%dT%H:%M:%SZ')

        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=[symbol],
            stype_in='parent',
            schema='trades',
            start=start,
            end=end
        )

        # Group trades by instrument_id
        instrument_stats = {}
        all_prices = []
        for r in data:
            iid = r.instrument_id
            price = r.price / 1e9 if r.price > 1e6 else r.price
            if price < price_min or price > price_max:
                continue
            all_prices.append(price)
            if iid not in instrument_stats:
                instrument_stats[iid] = {'prices': [], 'count': 0}
            instrument_stats[iid]['prices'].append(price)
            instrument_stats[iid]['count'] += 1

        if not instrument_stats:
            print(f"⚠️  No trades found")
            return None

        # Calculate stats
        for iid, info in instrument_stats.items():
            info['avg'] = sum(info['prices']) / len(info['prices'])
            info['max'] = max(info['prices'])
            info['min'] = min(info['prices'])
            print(f"   ID {iid}: {info['count']} trades, avg ${info['avg']:.2f}, range ${info['min']:.2f}-${info['max']:.2f}")

        # Sort by average price (GCJ26 should have higher avg)
        sorted_instruments = sorted(instrument_stats.items(), key=lambda x: x[1]['avg'], reverse=True)

        if len(sorted_instruments) >= 2:
            # Check spread between top 2 instruments
            top = sorted_instruments[0]
            second = sorted_instruments[1]
            spread = top[1]['avg'] - second[1]['avg']
            print(f"   Spread between top instruments: ${spread:.2f}")

            # If spread is $20+, confidently select the higher one as GCJ26
            if spread >= 20:
                active_month_instrument_id = top[0]
                front_month_instrument_id = top[0]
                print(f"✅ Selected {active_month} (higher avg by ${spread:.2f}): ID {active_month_instrument_id}")
                return active_month_instrument_id

        # Fallback: use the instrument with highest average
        top_instrument = sorted_instruments[0]
        active_month_instrument_id = top_instrument[0]
        front_month_instrument_id = top_instrument[0]
        print(f"✅ Selected {active_month} (highest avg): ID {active_month_instrument_id}, avg ${top_instrument[1]['avg']:.2f}")
        return active_month_instrument_id

    except Exception as e:
        print(f"⚠️  Error resolving instrument ID: {e}")
        return None


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
        'ib_start': 930,   # US/NY IB starts 09:30
        'ib_end': 1030,    # NY IB ends 10:30
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
        'ab_overlap': 0.0,
        'bc_overlap': 0.0,
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
            'ab_overlap': 0.0,
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
    """Get TPO letter for period index (A=0, B=1, ... Z=25, then cycles A2, B2...)"""
    cycle = period_index // 26
    letter_idx = period_index % 26
    letter = TPO_LETTERS[letter_idx]
    if cycle > 0:
        return f"{letter}{cycle+1}"  # A2, B2, etc. for second cycle
    return letter

def get_session_period_index(session_key, current_hhmm):
    """Calculate which 30-min period we're in for a session.
    session_key: TPO session key (e.g., 'tpo1_asia')
    current_hhmm: Current time in HHMM format (e.g., 1430 for 14:30)
    Returns: Period index (0 = A, 1 = B, etc.)
    """
    config = TPO_SESSIONS.get(session_key)
    if not config:
        return 0
    session_start = config['start']  # HHMM format

    # Convert HHMM to minutes from midnight
    start_mins = (session_start // 100) * 60 + (session_start % 100)
    current_mins = (current_hhmm // 100) * 60 + (current_hhmm % 100)

    # Handle overnight sessions (like Asia 18:00-03:00)
    if config['end'] < config['start']:  # Overnight
        if current_hhmm < config['end']:  # After midnight
            current_mins += 24 * 60

    # Minutes since session start
    mins_elapsed = current_mins - start_mins
    if mins_elapsed < 0:
        mins_elapsed += 24 * 60  # Wrap around

    # Period index (0 = A, 1 = B, etc.)
    return mins_elapsed // 30

def calculate_overlap(range1, range2):
    """Calculate overlap percentage between two price ranges
    range1, range2: tuples of (high, low)
    Returns: overlap percentage (0-100)
    """
    h1, l1 = range1
    h2, l2 = range2

    if h1 <= 0 or l1 >= 999999 or h2 <= 0 or l2 >= 999999:
        return 0.0

    overlap_high = min(h1, h2)
    overlap_low = max(l1, l2)
    overlap = max(0, overlap_high - overlap_low)

    range1_size = h1 - l1
    range2_size = h2 - l2

    if range1_size <= 0 or range2_size <= 0:
        return 0.0

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
    if ab_overlap > 60:
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
    if ab_overlap > 50:
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
    if ab_overlap > 50:
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
    """Classify open type based on first 2-3 periods of RTH (TPO #3 US AM)"""
    global tpo_state

    # Open type is specifically for US AM session (RTH)
    us_am = tpo_state['sessions']['tpo3_us_am']
    day = tpo_state['day']

    if us_am['period_count'] < 1:
        us_am['open_type'] = 'developing'
        day['open_type'] = 'developing'
        return

    open_price = us_am['open_price']
    a_high, a_low = us_am.get('a_high', 0), us_am.get('a_low', 999999)
    b_high, b_low = us_am.get('b_high', 0), us_am.get('b_low', 999999)

    if open_price <= 0 or a_high <= 0 or a_low >= 999999:
        return

    # Calculate AB overlap
    if b_high > 0 and b_low < 999999:
        ab_overlap = calculate_overlap((a_high, a_low), (b_high, b_low))
        us_am['ab_overlap'] = ab_overlap
        day['ab_overlap'] = ab_overlap
    else:
        ab_overlap = 100  # Still in A period

    # Determine dominant direction
    current_mid = (a_high + a_low) / 2
    if b_high > 0:
        current_mid = (b_high + b_low) / 2

    dominant_dir = 'up' if current_mid > open_price else 'down'

    # Count TPOs opposite to dominant direction
    profiles = us_am['profiles']
    tpos_opposite = 0
    for price, letters in profiles.items():
        if dominant_dir == 'up' and price < open_price:
            tpos_opposite += len(letters)
        elif dominant_dir == 'down' and price > open_price:
            tpos_opposite += len(letters)

    # Did B period cross the open?
    b_crossed_open = b_low < open_price < b_high if b_high > 0 else False

    # Classify open type
    if tpos_opposite == 0 and ab_overlap < 40:
        open_type = 'OD'  # Open Drive
        confidence = 85
    elif tpos_opposite <= 3 and ab_overlap < 50:
        open_type = 'OTD'  # Open Test Drive
        confidence = 75
    elif b_crossed_open and ab_overlap > 50:
        open_type = 'OA'  # Open Auction
        confidence = 70
        dominant_dir = None
    else:
        open_type = 'ORR'  # Open Rejection Reverse
        confidence = 65

    # Update both US AM session and day profile
    us_am['open_type'] = open_type
    us_am['open_type_confidence'] = confidence
    us_am['open_direction'] = dominant_dir
    day['open_type'] = open_type
    day['open_type_confidence'] = confidence
    day['open_direction'] = dominant_dir

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
        session['ab_overlap'] = 0.0

def reset_tpo_for_new_day():
    """Reset TPO data for new trading day (18:00 ET)"""
    global tpo_state

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
    day['ab_overlap'] = 0.0
    day['bc_overlap'] = 0.0
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
# FETCH CONTRACT ROLLOVER (OPEN INTEREST) DATA
# ============================================
def fetch_rollover_data():
    """Fetch Open Interest for front and next month contracts to determine rollover timing"""
    global state, rollover_last_fetch, ACTIVE_CONTRACT

    if not HAS_DATABENTO or not API_KEY:
        print("⚠️  Cannot fetch rollover data - no Databento connection")
        return

    # Throttle fetches to avoid API rate limits
    current_time = time.time()
    if current_time - rollover_last_fetch < ROLLOVER_FETCH_INTERVAL:
        return  # Skip if fetched recently

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    front_month = config['front_month']
    next_month = config['next_month']
    front_month_name = config.get('front_month_name', config['name'])
    next_month_name = config.get('next_month_name', '')

    # Initialize with defaults immediately so state is always valid
    with lock:
        if 'rollover' not in state or not state['rollover'].get('front_month'):
            state['rollover'] = {
                'front_month': front_month,
                'front_month_name': front_month_name,
                'front_month_oi': 0,
                'next_month': next_month,
                'next_month_name': next_month_name,
                'next_month_oi': 0,
                'oi_ratio': 0.0,
                'should_roll': False,
                'roll_signal': 'HOLD',
                'last_update': get_et_now().strftime('%Y-%m-%d %H:%M:%S ET'),
            }

    try:
        print(f"📊 Fetching Open Interest for rollover: {front_month} vs {next_month}...")

        client = db.Historical(key=API_KEY)
        et_tz = pytz.timezone('America/New_York')
        et_now = datetime.now(et_tz)

        # Fetch last 7 days to ensure we get the most recent OI data (OI only published at daily settlement)
        start_date = (et_now - timedelta(days=7)).strftime('%Y-%m-%d')
        end_date = (et_now + timedelta(days=1)).strftime('%Y-%m-%d')  # Include today

        front_oi = 0
        next_oi = 0

        # Use daily OHLCV to get volume (correlates with OI during rollover)
        # Volume is a reliable proxy when OI data isn't available
        try:
            # Fetch daily bars for front month
            front_data = client.timeseries.get_range(
                dataset='GLBX.MDP3',
                schema='ohlcv-1d',
                stype_in='parent',
                symbols=[front_month],
                start=start_date,
                end=end_date
            )

            # Get cumulative volume as proxy for activity/OI
            total_volume = 0
            for record in front_data:
                if hasattr(record, 'volume') and record.volume > 0:
                    total_volume += record.volume
                # Also check for open_interest if available
                if hasattr(record, 'open_interest') and record.open_interest > 0:
                    front_oi = record.open_interest

            # Use volume as OI proxy if no OI found
            if front_oi == 0 and total_volume > 0:
                front_oi = total_volume

            print(f"   📈 {front_month}: Vol/OI={front_oi:,}")

        except Exception as e:
            print(f"   ⚠️ Front month fetch error: {str(e)[:80]}")

        try:
            # Fetch daily bars for next month
            next_data = client.timeseries.get_range(
                dataset='GLBX.MDP3',
                schema='ohlcv-1d',
                stype_in='parent',
                symbols=[next_month],
                start=start_date,
                end=end_date
            )

            # Get cumulative volume as proxy for activity/OI
            total_volume = 0
            for record in next_data:
                if hasattr(record, 'volume') and record.volume > 0:
                    total_volume += record.volume
                if hasattr(record, 'open_interest') and record.open_interest > 0:
                    next_oi = record.open_interest

            # Use volume as OI proxy if no OI found
            if next_oi == 0 and total_volume > 0:
                next_oi = total_volume

            print(f"   📈 {next_month}: Vol/OI={next_oi:,}")

        except Exception as e:
            print(f"   ⚠️ Next month fetch error: {str(e)[:80]}")

        # Calculate rollover metrics
        oi_ratio = 0.0
        should_roll = False
        roll_signal = 'HOLD'

        if front_oi > 0:
            oi_ratio = next_oi / front_oi

            # Rollover signals based on OI ratio
            if oi_ratio >= 1.0:
                should_roll = True
                roll_signal = 'ROLL'
            elif oi_ratio >= 0.75:
                should_roll = False
                roll_signal = 'CONSIDER'
            else:
                should_roll = False
                roll_signal = 'HOLD'

        # Update state with fetched values
        with lock:
            state['rollover'] = {
                'front_month': front_month,
                'front_month_name': front_month_name,
                'front_month_oi': front_oi,
                'next_month': next_month,
                'next_month_name': next_month_name,
                'next_month_oi': next_oi,
                'oi_ratio': round(oi_ratio, 3),
                'should_roll': should_roll,
                'roll_signal': roll_signal,
                'last_update': get_et_now().strftime('%Y-%m-%d %H:%M:%S ET'),
            }

        rollover_last_fetch = current_time

        print(f"   ✅ Rollover: {front_month} OI={front_oi:,} | {next_month} OI={next_oi:,} | Ratio={oi_ratio:.2f} | Signal={roll_signal}")

    except Exception as e:
        print(f"❌ Rollover fetch error: {e}")
        # Keep default state on error


# ============================================
# FETCH PREVIOUS DAY LEVELS FROM DATABENTO
# ============================================
def fetch_pd_levels():
    """Fetch previous day OHLC from Databento historical API using trade data"""
    global state, front_month_instrument_id, ACTIVE_CONTRACT

    if not HAS_DATABENTO or not API_KEY:
        print("⚠️  Cannot fetch PD levels - no Databento connection")
        return

    # Get contract config for active contract
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    # Use active_month (specific contract like GCJ26) for accurate data
    symbol = config['symbol']  # Parent symbol like GC.FUT
    price_min = config['price_min']
    price_max = config['price_max']

    try:
        print(f"📊 Fetching Previous Day levels for {symbol} ({config['name']}) from Databento...")

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

        # Fetch TRADES for specific contract (active_month)
        print(f"   Querying {symbol} trades for session {session_start_date} to {session_end_date}...")
        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=[symbol],
            stype_in='parent',  # Use raw_symbol for specific contracts like GCJ26
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

        # Use front_month_instrument_id if already set (GCJ26), otherwise pick by volume
        if front_month_instrument_id and front_month_instrument_id in by_instrument:
            iid = front_month_instrument_id
            data = by_instrument[iid]
            print(f"   Using pre-set instrument ID: {iid}")
        else:
            # Fallback: find front month = instrument with most trades
            front_month = max(by_instrument.items(), key=lambda x: x[1]['count'])
            iid, data = front_month
            # Set front month ID for live trade filtering (if not already set)
            if front_month_instrument_id is None:
                front_month_instrument_id = iid
                print(f"   🎯 Auto-detected front month instrument ID: {iid}")

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

        print(f"   Front month (ID {iid}): {data['count']} trades")

        with lock:
            state['pd_high'] = pd_high
            state['pd_low'] = pd_low
            state['pd_open'] = pd_open
            state['pd_close'] = pd_close
            state['pdpoc'] = pdpoc
            state['pd_loaded'] = True
            state['pd_date_range'] = f"{session_start_date.strftime('%b %d')} 18:00 - {session_end_date.strftime('%b %d')} 17:00 ET"

        print(f"✅ PD Levels loaded: High=${pd_high:.2f}, Low=${pd_low:.2f}, POC=${pdpoc:.2f}")

    except Exception as e:
        print(f"❌ Error fetching PD levels: {e}")
        import traceback
        traceback.print_exc()

def fetch_all_ibs():
    """Fetch historical data for all 4 IBs that have already ended in current trading day"""
    global state, front_month_instrument_id, ACTIVE_CONTRACT

    if not HAS_DATABENTO or not API_KEY:
        return

    # Get contract config for active contract
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    # Use active_month (specific contract like GCJ26) for accurate data
    symbol = config['symbol']  # Parent symbol like GC.FUT
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
                    elif hour_min >= ib_def['et_start']:
                        # Japan IB is active now
                        should_fetch = True
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
                elif hour_min >= ib_def['et_start'] and hour_min < ib_def['et_end']:
                    should_fetch = True
                    print(f"   🔄 {ib_def['name']} is ACTIVE - fetching historical to sync...")
                elif ib_key == 'japan':
                    # Japan IB from yesterday evening (before current time)
                    should_fetch = True
                else:
                    print(f"   ⏳ {ib_def['name']} hasn't started yet")
                    continue

            if not should_fetch:
                continue

            # Get UTC time range
            utc_start = ib_def['utc_start']
            utc_end = ib_def['utc_end']

            # For active sessions, use current time as end (data only available up to now)
            if hour_min >= ib_def['et_start'] and hour_min < ib_def['et_end']:
                # Currently in this IB session - query up to current time
                current_utc = (et_now + timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
                utc_end = current_utc
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

                # Use front_month_instrument_id if already set (GCJ26), otherwise pick by volume
                if front_month_instrument_id and front_month_instrument_id in by_instrument:
                    iid = front_month_instrument_id
                    ib_data = by_instrument[iid]
                else:
                    # Fallback: use instrument with most trades
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

                        # Fetch A and B period data separately for AB Overlap calculation
                        try:
                            # A period: 09:30-10:00 ET = 14:30-15:00 UTC
                            a_data = client.timeseries.get_range(
                                dataset='GLBX.MDP3',
                                symbols=[symbol],
                                stype_in='parent',
                                schema='trades',
                                start=f"{today}T14:30:00Z",
                                end=f"{today}T15:00:00Z"
                            )
                            a_records = list(a_data)
                            if a_records:
                                a_high, a_low = 0, float('inf')
                                for r in a_records:
                                    if front_month_instrument_id and r.instrument_id != front_month_instrument_id:
                                        continue
                                    p = r.price / 1e9 if r.price > 1e6 else r.price
                                    if p < price_min or p > price_max:
                                        continue
                                    if p > a_high:
                                        a_high = p
                                    if p < a_low:
                                        a_low = p
                                if a_high > 0:
                                    tpo_state['day']['a_high'] = a_high
                                    tpo_state['day']['a_low'] = a_low
                                    tpo_state['sessions']['tpo3_us_am']['a_high'] = a_high
                                    tpo_state['sessions']['tpo3_us_am']['a_low'] = a_low
                                    print(f"   📊 A period (09:30-10:00): H=${a_high:.2f}, L=${a_low:.2f}")

                            # B period: 10:00-10:30 ET = 15:00-15:30 UTC
                            b_data = client.timeseries.get_range(
                                dataset='GLBX.MDP3',
                                symbols=[symbol],
                                stype_in='parent',
                                schema='trades',
                                start=f"{today}T15:00:00Z",
                                end=f"{today}T15:30:00Z"
                            )
                            b_records = list(b_data)
                            if b_records:
                                b_high, b_low = 0, float('inf')
                                for r in b_records:
                                    if front_month_instrument_id and r.instrument_id != front_month_instrument_id:
                                        continue
                                    p = r.price / 1e9 if r.price > 1e6 else r.price
                                    if p < price_min or p > price_max:
                                        continue
                                    if p > b_high:
                                        b_high = p
                                    if p < b_low:
                                        b_low = p
                                if b_high > 0:
                                    tpo_state['day']['b_high'] = b_high
                                    tpo_state['day']['b_low'] = b_low
                                    tpo_state['sessions']['tpo3_us_am']['b_high'] = b_high
                                    tpo_state['sessions']['tpo3_us_am']['b_low'] = b_low
                                    print(f"   📊 B period (10:00-10:30): H=${b_high:.2f}, L=${b_low:.2f}")

                            # Calculate AB Overlap if both periods have data
                            if tpo_state['day'].get('a_high', 0) > 0 and tpo_state['day'].get('b_high', 0) > 0:
                                ab_overlap = calculate_overlap(
                                    (tpo_state['day']['a_high'], tpo_state['day']['a_low']),
                                    (tpo_state['day']['b_high'], tpo_state['day']['b_low'])
                                )
                                tpo_state['day']['ab_overlap'] = ab_overlap
                                tpo_state['sessions']['tpo3_us_am']['ab_overlap'] = ab_overlap
                                print(f"   📊 AB Overlap: {ab_overlap:.1f}%")
                        except Exception as ab_err:
                            print(f"   ⚠️ Could not fetch A/B period data: {ab_err}")

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


def fetch_full_day_data():
    """Fetch full day's trade data (18:00 ET to now) and calculate:
    - True day_high and day_low
    - Overnight high/low (18:00-09:30)
    - Anchored VWAPs: us_ib_vwap (08:20+), ny_1h_vwap (09:30+), day_vwap (18:00+)
    """
    global state, front_month_instrument_id, lock

    if not HAS_DATABENTO or not API_KEY:
        print("⚠️  Databento not available for full day data")
        return

    try:
        config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
        symbol = config['symbol']  # Parent symbol like GC.FUT
        price_min = config['price_min']
        price_max = config['price_max']

        # Calculate trading day start (18:00 ET)
        et_tz = pytz.timezone('America/New_York')
        now_et = datetime.now(et_tz)
        current_hour = now_et.hour

        if current_hour >= 18:
            # After 18:00, trading day started today
            day_start_et = now_et.replace(hour=18, minute=0, second=0, microsecond=0)
        else:
            # Before 18:00, trading day started yesterday
            day_start_et = (now_et - timedelta(days=1)).replace(hour=18, minute=0, second=0, microsecond=0)

        # Convert to UTC
        utc_start = (day_start_et + timedelta(hours=5)).strftime('%Y-%m-%dT%H:%M:%SZ')
        # Use current time minus 25 min buffer for data delay (Databento has ~20 min delay)
        utc_end_time = now_et + timedelta(hours=5) - timedelta(minutes=25)
        utc_end = utc_end_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        print(f"📊 Fetching full day data (18:00 ET to now)...")
        print(f"   Range: {utc_start} to {utc_end}")

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
        print(f"   Got {len(records)} trades for full day")

        if not records:
            print("   ⚠️ No trades found for today")
            return

        # Initialize tracking variables
        day_high = 0
        day_low = float('inf')
        day_open = 0
        day_vwap_num = 0.0
        day_vwap_den = 0.0

        # Overnight: 18:00 - 08:20 ET (23:00 - 13:20 UTC)
        overnight_high = 0
        overnight_low = float('inf')

        # US IB VWAP: 08:20+ ET (13:20+ UTC)
        us_ib_vwap_num = 0.0
        us_ib_vwap_den = 0.0

        # NY 1H VWAP: 09:30+ ET (14:30+ UTC)
        ny_1h_vwap_num = 0.0
        ny_1h_vwap_den = 0.0

        first_ts = float('inf')
        first_price = 0

        # Get current day in UTC for time comparisons
        today = now_et.strftime('%Y-%m-%d')

        # Calculate UTC times for boundaries
        # 08:20 ET = 13:20 UTC
        us_ib_start_utc = datetime.strptime(f"{today}T13:20:00Z", '%Y-%m-%dT%H:%M:%SZ')
        # 09:30 ET = 14:30 UTC
        ny_start_utc = datetime.strptime(f"{today}T14:30:00Z", '%Y-%m-%dT%H:%M:%SZ')

        for r in records:
            # Only use front month if known
            if front_month_instrument_id and r.instrument_id != front_month_instrument_id:
                continue

            p = r.price / 1e9 if r.price > 1e6 else r.price
            size = getattr(r, 'size', 1)
            ts = r.ts_event

            if p < price_min or p > price_max:
                continue

            # Track first trade for day open
            if ts < first_ts:
                first_ts = ts
                first_price = p

            # Day high/low
            if p > day_high:
                day_high = p
            if p < day_low:
                day_low = p

            # Day VWAP (full day from 18:00 ET)
            day_vwap_num += p * size
            day_vwap_den += size

            # Get trade time in UTC for VWAP calculations
            trade_utc = datetime.fromtimestamp(ts / 1e9, tz=timezone.utc)
            trade_hhmm_utc = trade_utc.hour * 100 + trade_utc.minute

            # Overnight (18:00-08:20 ET = before 13:20 UTC on same day or after 23:00 UTC previous day)
            if trade_hhmm_utc < 1320 or trade_hhmm_utc >= 2300:
                if p > overnight_high:
                    overnight_high = p
                if p < overnight_low:
                    overnight_low = p

            # US IB VWAP (08:20+ ET = 13:20+ UTC)
            if trade_hhmm_utc >= 1320:
                us_ib_vwap_num += p * size
                us_ib_vwap_den += size

            # NY 1H VWAP (09:30+ ET = 14:30+ UTC)
            if trade_hhmm_utc >= 1430:
                ny_1h_vwap_num += p * size
                ny_1h_vwap_den += size

        # Calculate VWAPs
        day_vwap = day_vwap_num / day_vwap_den if day_vwap_den > 0 else 0
        us_ib_vwap = us_ib_vwap_num / us_ib_vwap_den if us_ib_vwap_den > 0 else 0
        ny_1h_vwap = ny_1h_vwap_num / ny_1h_vwap_den if ny_1h_vwap_den > 0 else 0

        # Update state with full day values
        with lock:
            state['day_high'] = day_high if day_high > 0 else state['day_high']
            state['day_low'] = day_low if day_low < float('inf') else state['day_low']
            if first_price > 0 and state['day_open'] == 0:
                state['day_open'] = first_price

            # Set day VWAP (this is the full day VWAP from 18:00 ET)
            state['day_vwap'] = day_vwap
            state['day_vwap_num'] = day_vwap_num
            state['day_vwap_den'] = day_vwap_den

            # Set overnight high/low
            if overnight_high > 0:
                state['overnight_high'] = overnight_high
            if overnight_low < float('inf'):
                state['overnight_low'] = overnight_low

            # Set anchored VWAPs
            if us_ib_vwap > 0:
                state['us_ib_vwap'] = us_ib_vwap
                state['us_ib_vwap_num'] = us_ib_vwap_num
                state['us_ib_vwap_den'] = us_ib_vwap_den
            if ny_1h_vwap > 0:
                state['ny_1h_vwap'] = ny_1h_vwap
                state['ny_1h_vwap_num'] = ny_1h_vwap_num
                state['ny_1h_vwap_den'] = ny_1h_vwap_den

        print(f"   ✅ Day: O=${first_price:.2f}, H=${day_high:.2f}, L=${day_low:.2f}")
        print(f"   ✅ Day VWAP: ${day_vwap:.2f}")
        if overnight_high > 0:
            print(f"   ✅ Overnight: H=${overnight_high:.2f}, L=${overnight_low:.2f}")
        if us_ib_vwap > 0:
            print(f"   ✅ US IB VWAP (08:20+): ${us_ib_vwap:.2f}")
        if ny_1h_vwap > 0:
            print(f"   ✅ NY 1H VWAP (09:30+): ${ny_1h_vwap:.2f}")

    except Exception as e:
        print(f"❌ Error fetching full day data: {e}")
        import traceback
        traceback.print_exc()


def fetch_todays_tpo_data():
    """Fetch full day's trade data and rebuild TPO profiles from session start.

    This ensures all TPO periods (A-Z) are populated even when backend starts mid-session.
    """
    global tpo_state, state, front_month_instrument_id, lock

    if not HAS_DATABENTO or not API_KEY:
        print("⚠️  Databento not available for historical TPO load")
        return

    try:
        config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
        symbol = config['symbol']  # Parent symbol like GC.FUT  # Specific contract like GCJ26
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

        # Convert to UTC (subtract 15 minutes to account for data delay)
        day_start_utc = day_start_et.astimezone(pytz.UTC)
        now_utc = (now_et - timedelta(minutes=15)).astimezone(pytz.UTC)

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
                        # Calculate IB period index relative to RTH IB start (09:30), not session start (08:20)
                        ib_start_mins = 9 * 60 + 30  # 09:30 = 570 mins from midnight
                        trade_time_mins = (trade_hhmm // 100) * 60 + (trade_hhmm % 100)
                        ib_mins_elapsed = trade_time_mins - ib_start_mins
                        ib_period_idx = ib_mins_elapsed // 30 if ib_mins_elapsed >= 0 else -1

                        if ib_period_idx == 0:  # A period (09:30-10:00)
                            if price > session_data.get('a_high', 0):
                                session_data['a_high'] = price
                            if price < session_data.get('a_low', 999999):
                                session_data['a_low'] = price
                        elif ib_period_idx == 1:  # B period (10:00-10:30)
                            if price > session_data.get('b_high', 0):
                                session_data['b_high'] = price
                            if price < session_data.get('b_low', 999999):
                                session_data['b_low'] = price

                        # Also copy to day profile for RTH
                        day = tpo_state['day']
                        if day.get('rth_open', 0) == 0 and ib_period_idx >= 0:
                            day['rth_open'] = price
                        if ib_period_idx == 0:
                            if price > day.get('a_high', 0):
                                day['a_high'] = price
                            if price < day.get('a_low', 999999):
                                day['a_low'] = price
                        elif ib_period_idx == 1:
                            if price > day.get('b_high', 0):
                                day['b_high'] = price
                            if price < day.get('b_low', 999999):
                                day['b_low'] = price

                        # Track IB (first 2 periods = first hour from 09:30)
                        if ib_period_idx >= 0 and ib_period_idx < 2:
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

    except Exception as e:
        print(f"❌ Error loading historical TPO: {e}")
        import traceback
        traceback.print_exc()


def fetch_ended_sessions_ohlc():
    """Fetch OHLC data for all sessions that have ended today"""
    global state, front_month_instrument_id, ACTIVE_CONTRACT

    if not HAS_DATABENTO or not API_KEY:
        return

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    symbol = config['symbol']  # Parent symbol like GC.FUT
    price_min = config['price_min']
    price_max = config['price_max']

    # Session definitions with ET start/end times
    # CME Globex Gold futures: 18:00 ET Sunday to 17:00 ET Friday
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
    """Load cached data from file"""
    try:
        cache_file = os.path.join(CACHE_DIR, f'sessions_{week_id}.json')
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
                weekly_sessions_cache[week_id]['data'] = data['data']
                weekly_sessions_cache[week_id]['timestamp'] = data['timestamp']
                weekly_sessions_cache[week_id]['ready'] = True
                print(f"✅ Loaded {week_id} from cache file")
                return True
    except Exception as e:
        print(f"⚠️ Could not load cache for {week_id}: {e}")
    return False

def save_cache_to_file(week_id):
    """Save cached data to file"""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        cache_file = os.path.join(CACHE_DIR, f'sessions_{week_id}.json')
        cache_data = {
            'data': weekly_sessions_cache[week_id]['data'],
            'timestamp': weekly_sessions_cache[week_id]['timestamp']
        }
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        print(f"💾 Saved {week_id} to cache file")
    except Exception as e:
        print(f"⚠️ Could not save cache for {week_id}: {e}")

def load_all_caches():
    """Load all week caches from files on startup"""
    for week_id in weekly_sessions_cache.keys():
        load_cache_from_file(week_id)

def fetch_week_sessions_ohlc(week_id):
    """Fetch historical session OHLC for a specific week"""
    global weekly_sessions_cache, ACTIVE_CONTRACT, front_month_instrument_id

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

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    symbol = config['symbol']  # Parent symbol like GC.FUT
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
            day_label = trading_date.strftime('%a')
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
    'ttl': 30  # Refresh every 30 seconds
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
        # Use specific contract symbol (active_month like GCJ26)
        symbol = config['symbol']  # Parent symbol like GC.FUT
        tick_size = config['tick_size']
        price_min = config['price_min']
        price_max = config['price_max']

        # Calculate date range - go back extra days to account for weekends/holidays
        et_tz = pytz.timezone('America/New_York')
        end_date = datetime.now(et_tz) - timedelta(minutes=15)  # Account for data delay
        start_date = end_date - timedelta(days=int(days * 1.5))  # Extra buffer for non-trading days

        # Convert to UTC for API call
        start_utc = start_date.strftime('%Y-%m-%dT00:00:00Z')
        end_utc = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        print(f"   Querying {symbol} from {start_utc[:10]} to {end_utc[:10]}...")

        # Fetch OHLCV data with 1-hour bars for TPO calculation
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
                }

            day = daily_data[trade_date]
            day['bars'].append({
                'time': bar_time,
                'hour': hour,
                'open': o, 'high': h, 'low': l, 'close': c, 'volume': v
            })

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

            # Track IB (09:30-10:30 ET) - hours 9 and 10
            if hour in [9, 10]:
                if h > day['ib_high']:
                    day['ib_high'] = h
                if l < day['ib_low']:
                    day['ib_low'] = l

            # Accumulate volume at price levels for POC
            price_level = round(((h + l) / 2) / tick_size) * tick_size
            day['price_volumes'][price_level] = day['price_volumes'].get(price_level, 0) + v

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
                'profile_shape': profile_shape,
                'range': round(day['high'] - day['low'], 2)
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

        for symbol, info in symbol_map.items():
            try:
                # Fetch data for each ticker individually (more reliable)
                ticker = yf.Ticker(symbol)

                # Get history for different periods
                hist_5d = ticker.history(period='5d')
                hist_1mo = ticker.history(period='1mo')

                if len(hist_5d) == 0:
                    continue

                # Current = latest row
                current = row_to_ohlc(hist_5d.iloc[-1])

                # Previous day = second to last row (if available)
                prev_1d = row_to_ohlc(hist_5d.iloc[-2]) if len(hist_5d) > 1 else current

                # Previous week = 5 trading days ago
                prev_1w = row_to_ohlc(hist_5d.iloc[0]) if len(hist_5d) >= 5 else prev_1d

                # Previous month = first row of monthly data
                prev_1m = row_to_ohlc(hist_1mo.iloc[0]) if len(hist_1mo) > 0 else prev_1w

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
                print(f"Error fetching {symbol}: {e}")
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


def fetch_session_history(days=50, force_refresh=False):
    """Fetch and cache raw daily ranges - called ONCE on startup"""
    global session_history_cache, ACTIVE_CONTRACT

    if not HAS_DATABENTO or not API_KEY:
        return None

    # If cache is ready and not forcing, use fast path
    if session_history_cache['ready'] and not force_refresh:
        return get_session_history_fast()

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    symbol = config['symbol']  # Parent symbol like GC.FUT
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

    if not HAS_DATABENTO or not API_KEY:
        print("⚠️  No Databento credentials for historical sessions OHLC")
        return None

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    symbol = config['symbol']  # Parent symbol like GC.FUT
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
            day_label = trading_date.strftime('%a')  # Mon, Tue, etc.
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

    if not HAS_DATABENTO or not API_KEY:
        return

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    symbol = config['symbol']  # Parent symbol like GC.FUT
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

        # Use front_month_instrument_id if already set (GCJ26), otherwise pick by volume
        if front_month_instrument_id and front_month_instrument_id in by_instrument:
            iid = front_month_instrument_id
            session_data = by_instrument[iid]
        else:
            # Fallback: use front month (most trades)
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

    if not HAS_DATABENTO or not API_KEY:
        return

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    symbol = config['symbol']  # Parent symbol like GC.FUT
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
        state['contract'] = config.get('active_month', config['front_month'])
        state['contract_name'] = config.get('active_month_name', config['name'])
        state['asset_class'] = contract_key

        # Reset prices
        state['current_price'] = 0.0
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

    print(f"✅ State reset for {config['name']} ({config['front_month']})")


def stop_stream():
    """Stop the current live stream"""
    global stream_running, live_client

    print("⏹️  Stopping live stream...")
    stream_running = False

    if live_client:
        try:
            live_client.close()
        except:
            pass
        live_client = None

    time.sleep(1)  # Give time for stream to stop
    print("✅ Stream stopped")


def start_stream():
    """Start live data stream for the active contract"""
    global stream_running, live_client, ACTIVE_CONTRACT

    if not HAS_DATABENTO:
        print("❌ Databento library not available")
        state['data_source'] = 'NO_DATABENTO_LIB'
        return

    if not API_KEY:
        print("❌ No DATABENTO_API_KEY environment variable set")
        state['data_source'] = 'NO_API_KEY'
        return

    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])

    # Resolve the active_month instrument ID first (for GCJ26 filtering)
    print(f"\n🎯 Resolving active month instrument ID...")
    resolve_active_month_instrument_id()

    # Fetch historical data for this contract
    print(f"\n📊 Fetching historical data for {config['name']}...")
    fetch_pd_levels()
    fetch_todays_ib()
    fetch_full_day_data()  # Fetch full day for day_high/low, VWAPs, overnight
    fetch_ended_sessions_ohlc()  # Fetch OHLC for all ended sessions today
    fetch_todays_tpo_data()  # Load full day TPO data for all periods (A-Z)
    fetch_current_session_history()
    fetch_historical_candle_volumes()
    # Rollover data fetched in background to not block startup

    # Load cached data from files first (instant startup)
    print("⚡ Loading cached data from files...")
    load_all_caches()

    # Pre-fetch session history in background for VSI page (so it's cached)
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
        # Fetch all historical weeks (5 weeks back)
        print("📅 Pre-fetching 5 historical weeks...")
        fetch_all_historical_weeks()

    prefetch_thread = threading.Thread(target=prefetch_session_history, daemon=True)
    prefetch_thread.start()

    # Periodic rollover data refresh (Open Interest updates typically at settlement)
    def periodic_rollover_fetch():
        global stream_running
        # Fetch immediately on startup, then every 5 minutes
        time.sleep(5)  # Short delay to let main data load first
        fetch_rollover_data()
        while stream_running:
            time.sleep(300)  # Check every 5 minutes
            if stream_running:
                fetch_rollover_data()

    rollover_thread = threading.Thread(target=periodic_rollover_fetch, daemon=True)
    rollover_thread.start()

    # Re-check if we should still be running (might have been stopped during historical fetch)
    # Also re-read the active contract in case it changed during historical fetch
    config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
    # Use active_month (specific contract like GCJ26) instead of parent symbol (GC.FUT)
    # This ensures we get the exact contract we're trading
    symbol = config['symbol']  # Parent symbol like GC.FUT

    # If stream was stopped during historical fetch, don't connect to live
    if not stream_running:
        print(f"⏹️  Stream was stopped during historical fetch, not connecting to live")
        return

    print(f"\n🔌 Connecting to Databento Live for {symbol}...")

    # Auto-reconnection settings
    max_reconnect_attempts = 10
    reconnect_delay = 5  # seconds
    reconnect_attempt = 0

    while stream_running and reconnect_attempt < max_reconnect_attempts:
        try:
            live_client = db.Live(key=API_KEY)

            live_client.subscribe(
                dataset='GLBX.MDP3',
                schema='trades',
                stype_in='parent',  # Use raw_symbol for specific contracts like GCJ26
                symbols=[symbol]
            )

            print(f"✅ Subscribed to {symbol} live trades")
            state['data_source'] = 'DATABENTO_LIVE'
            state['market_open'] = True
            reconnect_attempt = 0  # Reset on successful connection

            for record in live_client:
                if not stream_running:
                    print("⏹️  Stream loop terminated")
                    return
                process_trade(record)

        except Exception as e:
            error_str = str(e)
            reconnect_attempt += 1

            # Check if it's a connection reset error (errno 54)
            is_connection_reset = 'Errno 54' in error_str or 'Connection reset' in error_str or \
                                  'ECONNRESET' in error_str or 'BrokenPipe' in error_str

            if is_connection_reset and reconnect_attempt < max_reconnect_attempts:
                print(f"⚠️  Connection reset (attempt {reconnect_attempt}/{max_reconnect_attempts}): {error_str[:50]}")
                state['data_source'] = f'RECONNECTING ({reconnect_attempt}/{max_reconnect_attempts})'
                print(f"🔄 Reconnecting in {reconnect_delay} seconds...")
                time.sleep(reconnect_delay)
                # Increase delay with each attempt (exponential backoff, max 60s)
                reconnect_delay = min(60, reconnect_delay * 1.5)
            else:
                print(f"❌ Databento error: {e}")
                state['data_source'] = f'ERROR: {error_str[:30]}'
                print("\n⚠️  Running in offline mode - no live data\n")
                break

    stream_running = False


def start_databento_feed():
    """Start live data feed - wrapper for backwards compatibility"""
    start_stream()


def switch_contract(new_contract):
    """Switch to a different contract with full stream restart"""
    global ACTIVE_CONTRACT, stream_thread

    if new_contract not in CONTRACT_CONFIG:
        print(f"❌ Unknown contract: {new_contract}")
        return False

    print(f"\n🔄 Switching from {ACTIVE_CONTRACT} to {new_contract}...")

    # Stop current stream
    stop_stream()

    # Reset state for new contract
    ACTIVE_CONTRACT = new_contract
    reset_state_for_contract(new_contract)

    # Set stream_running BEFORE starting new thread so the new stream knows it should continue
    global stream_running
    stream_running = True

    # Start new stream in background thread
    stream_thread = threading.Thread(target=start_stream, daemon=True)
    stream_thread.start()

    print(f"✅ Switched to {CONTRACT_CONFIG[new_contract]['name']}")
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
        side = getattr(record, 'side', 'U')

        # Use dynamic price range from contract config
        config = CONTRACT_CONFIG.get(ACTIVE_CONTRACT, CONTRACT_CONFIG['GC'])
        if price < config['price_min'] or price > config['price_max']:
            return
        
        with lock:
            # Update price
            state['current_price'] = price
            state['last_update'] = datetime.now().strftime('%H:%M:%S')
            
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

                # Update Delta OHLC
                if tf['delta_open'] is None:
                    tf['delta_open'] = tf['delta']  # First trade sets open
                tf['delta_high'] = max(tf['delta_high'], tf['delta'])
                tf['delta_low'] = min(tf['delta_low'], tf['delta'])

                # Update Price OHLC
                if tf['price_open'] == 0:
                    tf['price_open'] = price  # First trade sets open
                tf['price_high'] = max(tf['price_high'], price)
                tf['price_low'] = min(tf['price_low'], price)
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

            # Anchored VWAPs - US IB (08:20) and NY 1H (09:30) - persist until 17:00 ET
            et_now = get_et_now()
            current_hhmm = et_now.hour * 100 + et_now.minute

            # US IB VWAP: Anchor at 08:20, accumulate until 17:00
            if current_hhmm >= 820 and current_hhmm < 1700:
                state['us_ib_vwap_num'] += price * size
                state['us_ib_vwap_den'] += size
                if state['us_ib_vwap_den'] > 0:
                    state['us_ib_vwap'] = state['us_ib_vwap_num'] / state['us_ib_vwap_den']

            # NY 1H VWAP: Anchor at 09:30, accumulate until 17:00
            if current_hhmm >= 930 and current_hhmm < 1700:
                state['ny_1h_vwap_num'] += price * size
                state['ny_1h_vwap_den'] += size
                if state['ny_1h_vwap_den'] > 0:
                    state['ny_1h_vwap'] = state['ny_1h_vwap_num'] / state['ny_1h_vwap_den']

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

            # Check if new 30-min period started (clock-aligned)
            current_period_start = int(now // 1800) * 1800

            # Calculate session period based on session start time (not backend start)
            def get_session_period_index(session_key, current_hhmm):
                """Calculate which 30-min period we're in for a session"""
                config = TPO_SESSIONS.get(session_key)
                if not config:
                    return 0
                session_start = config['start']  # HHMM format

                # Convert HHMM to minutes from midnight
                start_mins = (session_start // 100) * 60 + (session_start % 100)
                current_mins = (current_hhmm // 100) * 60 + (current_hhmm % 100)

                # Handle overnight sessions (like Asia 18:00-03:00)
                if config['end'] < config['start']:  # Overnight
                    if current_hhmm < config['end']:  # After midnight
                        current_mins += 24 * 60

                # Minutes since session start
                mins_elapsed = current_mins - start_mins
                if mins_elapsed < 0:
                    mins_elapsed += 24 * 60  # Wrap around

                # Period index (0 = A, 1 = B, etc.)
                return mins_elapsed // 30

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

            # Update period ranges for A, B, C (relative to RTH IB start 09:30, not day start)
            # Calculate IB period index relative to RTH IB start (09:30)
            et_now = get_et_now()
            current_hhmm = et_now.hour * 100 + et_now.minute
            ib_start_mins = 9 * 60 + 30  # 09:30 = 570 mins from midnight
            current_mins = (current_hhmm // 100) * 60 + (current_hhmm % 100)
            ib_mins_elapsed = current_mins - ib_start_mins
            ib_period_idx = ib_mins_elapsed // 30 if ib_mins_elapsed >= 0 else -1

            if ib_period_idx == 0:  # A period (09:30-10:00)
                if price > day['a_high']:
                    day['a_high'] = price
                if price < day['a_low']:
                    day['a_low'] = price
            elif ib_period_idx == 1:  # B period (10:00-10:30)
                if price > day['b_high']:
                    day['b_high'] = price
                if price < day['b_low']:
                    day['b_low'] = price
            elif ib_period_idx == 2:  # C period (10:30-11:00)
                if price > day['c_high']:
                    day['c_high'] = price
                if price < day['c_low']:
                    day['c_low'] = price

            # Update session-specific A/B tracking for RTH open type
            if current_tpo_session == 'tpo3_us_am' and session_data:
                if ib_period_idx == 0:  # A period (09:30-10:00)
                    if price > session_data['a_high']:
                        session_data['a_high'] = price
                    if price < session_data['a_low']:
                        session_data['a_low'] = price
                elif ib_period_idx == 1:  # B period (10:00-10:30)
                    if price > session_data['b_high']:
                        session_data['b_high'] = price
                    if price < session_data['b_low']:
                        session_data['b_low'] = price
                # AB overlap for RTH session
                if ib_period_idx >= 1:
                    session_data['ab_overlap'] = calculate_overlap(
                        (session_data['a_high'], session_data['a_low']),
                        (session_data['b_high'], session_data['b_low'])
                    )

            # Update DAY IB during RTH session (09:30-10:30 = first 2 periods from 09:30)
            if current_tpo_session == 'tpo3_us_am' and session_data:
                if ib_period_idx >= 0 and ib_period_idx < 2:  # During IB formation (09:30-10:30)
                    if price > day['ib_high']:
                        day['ib_high'] = price
                    if price < day['ib_low']:
                        day['ib_low'] = price
                elif ib_period_idx == 2 and not day['ib_complete']:
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
                        # A=0, B=1, ... Z=25, A2=26, B2=27, etc.
                        if len(letter) == 1:
                            return ord(letter) - ord('A')
                        else:
                            # Has cycle number like "A2", "B2"
                            base_letter = letter[0]
                            cycle = int(letter[1:]) - 1  # "2" means cycle 1
                            return cycle * 26 + (ord(base_letter) - ord('A'))
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
                    ib_high = session_data.get('ib_high', 0)
                    ib_low = session_data.get('ib_low', 999999)
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
                        'ib_high': ib_high if ib_high > 0 else None,
                        'ib_low': ib_low if ib_low < 999999 else None,
                        'ib_complete': session_data.get('ib_complete', False),
                        'open_price': session_data.get('open_price', 0),
                        'high': session_data.get('high', 0) if session_data.get('high', 0) > 0 else None,
                        'low': session_data.get('low', 999999) if session_data.get('low', 999999) < 999999 else None,
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
                        sessions_json[session_key]['ab_overlap'] = round(session_data.get('ab_overlap', 0), 1)
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
                    'ib_high': day['ib_high'] if day['ib_high'] > 0 else None,
                    'ib_low': day['ib_low'] if day['ib_low'] < 999999 else None,
                    'ib_range': (day['ib_high'] - day['ib_low']) if day['ib_high'] > 0 and day['ib_low'] < 999999 else None,
                    'ib_complete': day['ib_complete'],

                    # Day Period Ranges
                    'a_high': day['a_high'] if day['a_high'] > 0 else None,
                    'a_low': day['a_low'] if day['a_low'] < 999999 else None,
                    'b_high': day['b_high'] if day['b_high'] > 0 else None,
                    'b_low': day['b_low'] if day['b_low'] < 999999 else None,
                    'c_high': day['c_high'] if day['c_high'] > 0 else None,
                    'c_low': day['c_low'] if day['c_low'] < 999999 else None,
                    'open_price': day['open_price'],
                    'rth_open': day.get('rth_open', 0),

                    # Day Overlaps
                    'ab_overlap': round(day['ab_overlap'], 1),
                    'bc_overlap': round(day['bc_overlap'], 1),

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
                    'timestamp': time.time()
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

        # Handle /red-folder endpoint for Fed event scheduler
        if path == '/red-folder' or path == '/redfolder':
            # Check scheduled Fed events
            from datetime import datetime, timedelta
            now = datetime.utcnow()  # Server uses UTC

            # High impact events in UTC (ET + 5 hours)
            # Powell speaking Jan 29, 2026 - FOMC day
            # Event window: all day on Jan 28-29, 2026
            FED_EVENTS = [
                (2026, 1, 29, 12, 0, "Fed Chair Powell Speaks - FOMC", "CRITICAL"),  # noon UTC
            ]

            scheduler_data = {'active': False, 'event_active': False}

            for event in FED_EVENTS:
                year, month, day, hour, minute, event_name, impact = event
                event_time = datetime(year, month, day, hour, minute)
                window_start = event_time - timedelta(hours=12)  # 12 hours before
                window_end = event_time + timedelta(hours=12)    # 12 hours after

                if window_start <= now <= window_end:
                    scheduler_data = {
                        'active': True,
                        'event_active': True,
                        'event_name': event_name,
                        'impact_level': impact,
                        'scheduled_time': event_time.strftime('%Y-%m-%d %H:%M ET'),
                        'status': 'in_progress' if now >= event_time else 'upcoming'
                    }
                    break

            if path == '/red-folder' or path == '/redfolder':
                # Simulated Powell transcript when event is active
                transcript_buffer = []
                current_segment = None
                sentiment = {'score': 0.0, 'label': 'neutral'}

                if scheduler_data.get('active'):
                    # Add simulated transcript segments for Powell speaking
                    transcript_buffer = [
                        {'timestamp': '14:02:15', 'text': 'Good afternoon. The Federal Open Market Committee concluded its meeting today.', 'is_final': True},
                        {'timestamp': '14:02:45', 'text': 'We decided to maintain the target range for the federal funds rate.', 'is_final': True},
                        {'timestamp': '14:03:20', 'text': 'Inflation has continued to ease but remains somewhat elevated.', 'is_final': True},
                        {'timestamp': '14:03:55', 'text': 'The labor market remains strong with solid job gains.', 'is_final': True},
                        {'timestamp': '14:04:30', 'text': 'We are committed to returning inflation to our 2 percent objective.', 'is_final': True},
                    ]
                    current_segment = 'Economic activity has been expanding at a solid pace...'
                    sentiment = {'score': 0.12, 'label': 'slightly_hawkish'}

                self.wfile.write(json.dumps({
                    'status': 'ok',
                    'is_speaking': scheduler_data.get('active', False),
                    'scheduler': scheduler_data,
                    'transcript_buffer': transcript_buffer,
                    'current_segment': current_segment,
                    'sentiment': sentiment,
                    'transcription': {'segments': transcript_buffer, 'full_text': ' '.join([s['text'] for s in transcript_buffer])},
                    'speaker_detection': {'current_speaker': 'Powell' if scheduler_data.get('active') else None}
                }).encode())
                return

        # Default endpoint - live data
        with lock:
            ib_high = state['ib_high'] if state['ib_high'] > 0 else 0
            ib_low = state['ib_low'] if state['ib_low'] < 999999 else 0
            ib_mid = (ib_high + ib_low) / 2 if ib_high > 0 and ib_low > 0 else 0
            
            response = {
                'version': APP_VERSION,
                'ticker': state['ticker'],
                'contract': state['contract'],
                'contract_name': state['contract_name'],
                'asset_class': state['asset_class'],
                'available_contracts': {k: {'symbol': v['front_month'], 'name': v['name']} for k, v in CONTRACT_CONFIG.items()},
                'current_price': state['current_price'],
                'delta_5m': state['delta_5m'],
                'delta_30m': state['delta_30m'],
                'cumulative_delta': state['cumulative_delta'],
                
                # IB values (legacy single IB)
                'ib_high': ib_high,
                'ib_low': ib_low,
                'ib_midpoint': ib_mid,
                'ib_locked': state['ib_locked'],
                'ib_session_name': state['ib_session_name'],
                'ib_status': state['ib_status'],

                # 4 IB Sessions - each tracked independently
                'ibs': {
                    ib_key: {
                        'name': ib['name'],
                        'high': ib['high'] if ib['high'] > 0 else 0,
                        'low': ib['low'] if ib['low'] < 999999 else 0,
                        'mid': (ib['high'] + ib['low']) / 2 if ib['high'] > 0 and ib['low'] < 999999 else 0,
                        'status': ib['status'],
                        'start': ib['start'],
                        'end': ib['end']
                    }
                    for ib_key, ib in state['ibs'].items()
                },
                'current_ib': state['current_ib'],
                
                # PD levels (from historical)
                'pdpoc': state['pdpoc'],
                'pd_high': state['pd_high'],
                'pd_low': state['pd_low'],
                'pd_open': state['pd_open'],
                'pd_close': state['pd_close'],
                'pd_date_range': state['pd_date_range'],

                # Session info
                'session_high': state['session_high'] if state['session_high'] > 0 else 0,
                'session_low': state['session_low'] if state['session_low'] < 999999 else 0,
                'session_open': state['session_open'] if state['session_open'] > 0 else 0,
                'session_volume': state['session_buy'] + state['session_sell'],  # Current session volume
                'session_delta': state['session_buy'] - state['session_sell'],   # Current session delta

                # Day OHLC (full trading day 18:00-17:00 ET)
                'day_open': state['day_open'] if state['day_open'] > 0 else 0,
                'day_high': state['day_high'] if state['day_high'] > 0 else 0,
                'day_low': state['day_low'] if state['day_low'] < 999999 else 0,
                'day_vwap': state['day_vwap'] if state['day_vwap'] > 0 else 0,

                # Overnight (18:00 - 9:30 ET) from full day fetch
                'overnight_high': state['overnight_high'] if state['overnight_high'] > 0 else 0,
                'overnight_low': state['overnight_low'] if state['overnight_low'] < 999999 else 0,

                # Ended sessions OHLC
                'ended_sessions': state['ended_sessions'],

                'vwap': state['vwap'],
                # Anchored VWAPs (persist until 17:00 ET)
                'us_ib_vwap': state['us_ib_vwap'] if state['us_ib_vwap'] > 0 else 0,
                'ny_1h_vwap': state['ny_1h_vwap'] if state['ny_1h_vwap'] > 0 else 0,
                'current_session_id': state['current_session_id'],
                'current_session_name': state['current_session_name'],
                'current_session_start': state['current_session_start'],
                'current_session_end': state['current_session_end'],
                
                # Analysis
                'buying_imbalance_pct': state['buying_imbalance_pct'],
                'absorption_ratio': state['absorption_ratio'],
                'stacked_buy_imbalances': state['stacked_buy_imbalances'],
                'current_phase': state['current_phase'],
                'conditions_met': state['conditions_met'],
                'entry_signal': state['entry_signal'],
                
                # Volume (session cumulative)
                'buy_volume': state['buy_volume'],
                'sell_volume': state['sell_volume'],
                'total_volume': state['total_volume'],
                'volume_start_time': state['volume_start_time'],

                # Volume by timeframe
                'volume_5m': state['volume_5m'],
                'volume_15m': state['volume_15m'],
                'volume_30m': state['volume_30m'],
                'volume_1h': state['volume_1h'],

                # Meta
                'last_update': state['last_update'],
                'current_et_time': get_et_now().strftime('%H:%M:%S'),
                'current_et_date': get_et_now().strftime('%Y-%m-%d'),
                'data_source': state['data_source'],
                'market_open': state['market_open'],
                'pd_loaded': state['pd_loaded'],
                
                # GEX Data
                'gamma_regime': state.get('gamma_regime', 'UNKNOWN'),
                'total_gex': state.get('total_gex', 0),
                'zero_gamma': state.get('zero_gamma', 0),
                'hvl': state.get('hvl', 0),
                'beta_spx': state.get('beta_spx', 0),
                'beta_dxy': state.get('beta_dxy', 0),

                # TPO/Market Profile Data - POC, VAH, VAL (from tpo_state)
                'tpo_poc': tpo_state['day'].get('poc', 0),
                'tpo_vah': tpo_state['day'].get('vah', 0),
                'tpo_val': tpo_state['day'].get('val', 0),

                # Contract Rollover Indicator (Open Interest based)
                'rollover': state.get('rollover', {})
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
            global stream_running, stream_thread

            print("\n🔄 Manual reconnection requested...")
            state['data_source'] = 'RECONNECTING...'

            # Stop existing stream
            stop_stream()

            # Small delay to allow cleanup
            time.sleep(1)

            # Restart stream
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
    server = HTTPServer(('0.0.0.0', PORT), LiveDataHandler)
    print(f"🌐 HTTP server running on http://localhost:{PORT}")
    server.serve_forever()

# ============================================
# MAIN
# ============================================
def main():
    print("=" * 60)
    print(f"  PROJECT HORIZON - LIVE FEED v{APP_VERSION}")
    print("=" * 60)
    print(f"📡 HTTP: http://localhost:{PORT}")
    print(f"🔑 API: {API_KEY[:10]}..." if API_KEY else "🔑 API: NOT SET")
    print("=" * 60)
    
    global stream_running

    # Start HTTP server
    http_thread = threading.Thread(target=start_http_server, daemon=True)
    http_thread.start()

    # Set stream_running before starting feed so the stream knows it should continue
    stream_running = True

    # Start Databento feed (includes PD fetch)
    feed_thread = threading.Thread(target=start_databento_feed, daemon=True)
    feed_thread.start()
    
    print("\n📊 Starting live data stream...\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")

if __name__ == '__main__':
    main()
