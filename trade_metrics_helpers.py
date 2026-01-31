"""
Trade Metrics Helper Functions for Project Horizon
Uses trades schema and aggregates to 1-min bars
"""
from datetime import datetime, timedelta
from collections import defaultdict
import pytz
import os

def aggregate_trades_to_bars(trade_records, front_month_iid):
    """Aggregate tick data into 1-minute OHLCV bars"""
    bars_dict = defaultdict(lambda: {'open': None, 'high': 0, 'low': float('inf'), 'close': None, 'volume': 0, 'trades': 0})
    
    for record in trade_records:
        if record.instrument_id != front_month_iid:
            continue
        
        # Get timestamp and round to minute
        ts_ns = record.ts_event
        ts_sec = ts_ns / 1e9
        ts_dt = datetime.utcfromtimestamp(ts_sec)
        minute_key = ts_dt.replace(second=0, microsecond=0)
        
        # Get price (fixed-point in Databento)
        price = record.price / 1e9
        size = record.size
        
        bar = bars_dict[minute_key]
        if bar['open'] is None:
            bar['open'] = price
        bar['high'] = max(bar['high'], price)
        bar['low'] = min(bar['low'], price)
        bar['close'] = price
        bar['volume'] += size
        bar['trades'] += 1
    
    # Convert to list sorted by time
    bars = []
    for ts, bar in sorted(bars_dict.items()):
        if bar['open'] is not None:
            bars.append({
                'timestamp': ts.isoformat(),
                'open': bar['open'],
                'high': bar['high'],
                'low': bar['low'],
                'close': bar['close'],
                'volume': bar['volume']
            })
    
    return bars


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
    Fetch trades from Databento and aggregate to 1-min bars.
    """
    try:
        import databento as db
    except ImportError:
        print("ERROR: Databento not installed")
        return None
    
    if not api_key:
        print("ERROR: No API key provided")
        return None
    
    try:
        ET = pytz.timezone('America/New_York')
        UTC = pytz.UTC
        
        # Parse entry datetime in ET
        hour, minute = map(int, entry_time.split(':')[:2])
        entry_dt = ET.localize(datetime.strptime(entry_date, '%Y-%m-%d').replace(hour=hour, minute=minute))
        
        # End of session (5:00 PM ET next day if after 5 PM)
        end_dt = entry_dt.replace(hour=17, minute=0)
        if entry_dt.hour >= 17:
            end_dt += timedelta(days=1)
        
        # Convert to UTC
        start_utc = entry_dt.astimezone(UTC)
        end_utc = end_dt.astimezone(UTC)
        
        start_ts = start_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_ts = end_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        print(f"📊 Fetching trades for bar aggregation")
        print(f"   Entry (ET): {entry_dt}")
        print(f"   Range: {start_ts} to {end_ts}")
        
        client = db.Historical(key=api_key)
        data = client.timeseries.get_range(
            dataset='GLBX.MDP3',
            symbols=['GC.FUT'],
            stype_in='parent',
            schema='trades',
            start=start_ts,
            end=end_ts
        )
        
        records = list(data)
        print(f"   Got {len(records)} trade records")
        
        if not records:
            print("   WARNING: No trade records returned")
            return {"debug": "no_records", "start": start_ts, "end": end_ts}
        
        # Find front month instrument
        by_instrument = {}
        for r in records:
            iid = r.instrument_id
            by_instrument[iid] = by_instrument.get(iid, 0) + 1
        
        front_month_iid = max(by_instrument.items(), key=lambda x: x[1])[0]
        print(f"   Front month instrument ID: {front_month_iid}")
        
        # Aggregate to 1-min bars
        bars = aggregate_trades_to_bars(records, front_month_iid)
        print(f"   Aggregated to {len(bars)} 1-min bars")
        
        if bars:
            print(f"   First bar: {bars[0]['timestamp']} O:{bars[0]['open']:.2f} H:{bars[0]['high']:.2f} L:{bars[0]['low']:.2f} C:{bars[0]['close']:.2f}")
            print(f"   Last bar: {bars[-1]['timestamp']} C:{bars[-1]['close']:.2f}")
        
        return bars if bars else {"debug": "no_bars_after_agg", "record_count": len(records)}
        
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"ERROR fetching trades: {e}")
        print(tb)
        return {"debug": "exception", "error": str(e), "traceback": tb[:500]}
