"""
Trade Metrics Helper Functions for Project Horizon
"""
from datetime import datetime, timedelta
import pytz
import os

def process_bars_for_trade_metrics(bars, entry_price, direction, stop_price, targets):
    """Process bar data to calculate trade metrics."""
    is_long = direction.lower() == "long"
    
    entry_triggered = False
    entry_time = None
    exit_triggered = False
    exit_reason = None
    exit_price = None
    exit_time = None
    
    max_favorable = 0
    max_adverse = 0
    mfe_price = entry_price
    mae_price = entry_price
    mae_time = None
    
    time_in_profit_secs = 0
    last_bar_time = None
    
    t1_time = t2_time = t3_time = None
    t1_hit = t2_hit = t3_hit = False
    
    for bar in bars:
        bar_time = bar.get('timestamp')
        if isinstance(bar_time, str):
            try:
                bar_time = datetime.fromisoformat(bar_time.replace('Z', '+00:00'))
            except:
                pass
        bar_high = bar['high']
        bar_low = bar['low']
        bar_close = bar['close']
        
        if not entry_triggered:
            if is_long:
                if bar_low <= entry_price:
                    entry_triggered = True
                    entry_time = bar_time
            else:
                if bar_high >= entry_price:
                    entry_triggered = True
                    entry_time = bar_time
            continue
        
        if entry_triggered and not exit_triggered:
            if is_long:
                if bar_high - entry_price > max_favorable:
                    max_favorable = bar_high - entry_price
                    mfe_price = bar_high
                if entry_price - bar_low > max_adverse:
                    max_adverse = entry_price - bar_low
                    mae_price = bar_low
                    mae_time = bar_time
                if bar_low <= stop_price:
                    exit_triggered = True
                    exit_reason = "stop"
                    exit_price = stop_price
                    exit_time = bar_time
                if not t1_hit and len(targets) > 0 and bar_high >= targets[0]:
                    t1_hit = True
                    t1_time = bar_time
                if not t2_hit and len(targets) > 1 and bar_high >= targets[1]:
                    t2_hit = True
                    t2_time = bar_time
                if not t3_hit and len(targets) > 2 and bar_high >= targets[2]:
                    t3_hit = True
                    t3_time = bar_time
                    if not exit_triggered:
                        exit_triggered = True
                        exit_reason = "t3"
                        exit_price = targets[2]
                        exit_time = bar_time
                if bar_close > entry_price and last_bar_time:
                    time_in_profit_secs += 60
            else:
                if entry_price - bar_low > max_favorable:
                    max_favorable = entry_price - bar_low
                    mfe_price = bar_low
                if bar_high - entry_price > max_adverse:
                    max_adverse = bar_high - entry_price
                    mae_price = bar_high
                    mae_time = bar_time
                if bar_high >= stop_price:
                    exit_triggered = True
                    exit_reason = "stop"
                    exit_price = stop_price
                    exit_time = bar_time
                if not t1_hit and len(targets) > 0 and bar_low <= targets[0]:
                    t1_hit = True
                    t1_time = bar_time
                if not t2_hit and len(targets) > 1 and bar_low <= targets[1]:
                    t2_hit = True
                    t2_time = bar_time
                if not t3_hit and len(targets) > 2 and bar_low <= targets[2]:
                    t3_hit = True
                    t3_time = bar_time
                    if not exit_triggered:
                        exit_triggered = True
                        exit_reason = "t3"
                        exit_price = targets[2]
                        exit_time = bar_time
                if bar_close < entry_price and last_bar_time:
                    time_in_profit_secs += 60
        
        last_bar_time = bar_time
    
    if entry_triggered and not exit_triggered and bars:
        exit_reason = "close"
        exit_price = bars[-1]['close']
        exit_time = bars[-1].get('timestamp')
    
    if entry_triggered:
        pnl = (exit_price - entry_price) if is_long else (entry_price - exit_price)
    else:
        pnl = 0
    
    def time_diff_secs(t1, t2):
        if t1 and t2:
            if isinstance(t1, str):
                try:
                    t1 = datetime.fromisoformat(t1.replace('Z', '+00:00'))
                except:
                    return None
            if isinstance(t2, str):
                try:
                    t2 = datetime.fromisoformat(t2.replace('Z', '+00:00'))
                except:
                    return None
            return int((t2 - t1).total_seconds())
        return None
    
    return {
        "entry_triggered": entry_triggered,
        "exit_reason": exit_reason,
        "exit_price": exit_price,
        "pnl_points": round(pnl, 2) if pnl else 0,
        "actual_mae": round(max_adverse, 2),
        "actual_mae_price": mae_price,
        "actual_mfe": round(max_favorable, 2),
        "actual_mfe_price": mfe_price,
        "time_to_mae_secs": time_diff_secs(entry_time, mae_time),
        "time_in_trade_secs": time_diff_secs(entry_time, exit_time),
        "time_in_profit_secs": time_in_profit_secs,
        "time_to_t1_secs": time_diff_secs(entry_time, t1_time),
        "time_to_t2_secs": time_diff_secs(entry_time, t2_time),
        "time_to_t3_secs": time_diff_secs(entry_time, t3_time),
        "t1_hit": t1_hit,
        "t2_hit": t2_hit,
        "t3_hit": t3_hit,
        "bars_analyzed": len(bars)
    }


def fetch_historical_bars_for_trade(contract, entry_date, entry_time, api_key=None):
    """
    Fetch 1-min bars from Databento for trade analysis.
    Returns list of bars from entry_time to end of session.
    """
    try:
        import databento as db
    except ImportError:
        print("Databento not installed")
        return None
    
    api_key = api_key or os.environ.get('DATABENTO_API_KEY', '')
    if not api_key:
        print("No DATABENTO_API_KEY found")
        return None
    
    try:
        ET = pytz.timezone('America/New_York')
        
        # Parse entry datetime
        hour, minute = map(int, entry_time.split(':')[:2])
        entry_dt = ET.localize(datetime.strptime(entry_date, '%Y-%m-%d').replace(hour=hour, minute=minute))
        
        # End of session (5:00 PM ET or extend if after hours)
        end_dt = entry_dt.replace(hour=17, minute=0)
        if entry_dt.hour >= 17:
            end_dt += timedelta(days=1)
        
        # Convert to UTC for Databento
        start_ts = entry_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_ts = end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        print(f"Fetching OHLCV bars from {start_ts} to {end_ts}")
        
        # Use parent symbol for continuous contract
        client = db.Historical(key=api_key)
        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=['GC.FUT'],
            stype_in='parent',
            schema='ohlcv-1m',
            start=start_ts,
            end=end_ts,
        )
        
        records = list(data)
        print(f"Got {len(records)} bar records")
        
        if not records:
            return None
        
        bars = []
        for record in records:
            # Databento uses nanoseconds for prices in fixed-point
            try:
                ts = record.ts_event
                if hasattr(ts, 'isoformat'):
                    ts_str = ts.isoformat()
                else:
                    # ts_event is in nanoseconds since epoch
                    ts_dt = datetime.utcfromtimestamp(ts / 1e9)
                    ts_str = ts_dt.isoformat()
                
                bars.append({
                    'timestamp': ts_str,
                    'open': record.open / 1e9,
                    'high': record.high / 1e9,
                    'low': record.low / 1e9,
                    'close': record.close / 1e9,
                    'volume': record.volume
                })
            except Exception as e:
                print(f"Error parsing record: {e}")
                continue
        
        print(f"Parsed {len(bars)} bars")
        return bars if bars else None
        
    except Exception as e:
        print(f"Error fetching historical bars: {e}")
        import traceback
        traceback.print_exc()
        return None
