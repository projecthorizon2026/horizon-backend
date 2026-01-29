#!/usr/bin/env python3
"""
Red Folder Service - Live Event Transcription & Analysis
Port 8081 HTTP Server for Project Horizon

Uses Deepgram API for transcription of YouTube Live streams (Fed/Treasury press conferences)
with sentiment analysis, voice tone analysis, and market direction gauging.

Deepgram API works with file uploads, so we use a chunked approach:
1. Record 15-second audio chunks from YouTube stream
2. Upload each chunk to Deepgram for transcription
3. Analyze results

AUTO-SCHEDULER: Automatically starts transcription for scheduled Fed events
"""

import os
import sys
import json
import time
import asyncio
import threading
import subprocess
import tempfile
import re
import requests
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ============================================
# FED EVENT SCHEDULER
# ============================================
# Federal Reserve YouTube Channel
FED_YOUTUBE_CHANNEL = "https://www.youtube.com/@FederalReserve/live"
FED_YOUTUBE_SEARCH = "https://www.youtube.com/@FederalReserve/streams"

# High Impact Economic Events (year, month, day, hour, minute in ET)
# Format: (year, month, day, hour, minute, event_name, impact_level)
# Impact levels: "CRITICAL" (FOMC, CPI, NFP), "HIGH" (PPI, Retail, GDP), "MEDIUM" (other Fed speeches)
HIGH_IMPACT_EVENTS = [
    # ============= 2025 EVENTS =============
    # FOMC Press Conferences (2:30 PM ET) - CRITICAL
    (2025, 1, 29, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2025, 3, 19, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2025, 5, 7, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2025, 6, 18, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2025, 7, 30, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2025, 9, 17, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2025, 11, 5, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2025, 12, 17, 14, 30, "FOMC Press Conference", "CRITICAL"),

    # CPI Releases (8:30 AM ET) - CRITICAL
    (2025, 1, 15, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 2, 12, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 3, 12, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 4, 10, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 5, 13, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 6, 11, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 7, 11, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 8, 13, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 9, 10, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 10, 10, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 11, 13, 8, 30, "CPI Release", "CRITICAL"),
    (2025, 12, 10, 8, 30, "CPI Release", "CRITICAL"),

    # NFP/Jobs Report (First Friday, 8:30 AM ET) - CRITICAL
    (2025, 1, 10, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 2, 7, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 3, 7, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 4, 4, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 5, 2, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 6, 6, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 7, 3, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 8, 1, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 9, 5, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 10, 3, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 11, 7, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2025, 12, 5, 8, 30, "NFP Jobs Report", "CRITICAL"),

    # PPI Releases (8:30 AM ET) - HIGH
    (2025, 1, 14, 8, 30, "PPI Release", "HIGH"),
    (2025, 2, 13, 8, 30, "PPI Release", "HIGH"),
    (2025, 3, 13, 8, 30, "PPI Release", "HIGH"),
    (2025, 4, 11, 8, 30, "PPI Release", "HIGH"),
    (2025, 5, 15, 8, 30, "PPI Release", "HIGH"),
    (2025, 6, 12, 8, 30, "PPI Release", "HIGH"),
    (2025, 7, 15, 8, 30, "PPI Release", "HIGH"),
    (2025, 8, 14, 8, 30, "PPI Release", "HIGH"),
    (2025, 9, 11, 8, 30, "PPI Release", "HIGH"),
    (2025, 10, 9, 8, 30, "PPI Release", "HIGH"),
    (2025, 11, 14, 8, 30, "PPI Release", "HIGH"),
    (2025, 12, 11, 8, 30, "PPI Release", "HIGH"),

    # Retail Sales (8:30 AM ET) - HIGH
    (2025, 1, 16, 8, 30, "Retail Sales", "HIGH"),
    (2025, 2, 14, 8, 30, "Retail Sales", "HIGH"),
    (2025, 3, 17, 8, 30, "Retail Sales", "HIGH"),
    (2025, 4, 16, 8, 30, "Retail Sales", "HIGH"),
    (2025, 5, 15, 8, 30, "Retail Sales", "HIGH"),
    (2025, 6, 17, 8, 30, "Retail Sales", "HIGH"),
    (2025, 7, 16, 8, 30, "Retail Sales", "HIGH"),
    (2025, 8, 14, 8, 30, "Retail Sales", "HIGH"),
    (2025, 9, 17, 8, 30, "Retail Sales", "HIGH"),
    (2025, 10, 17, 8, 30, "Retail Sales", "HIGH"),
    (2025, 11, 14, 8, 30, "Retail Sales", "HIGH"),
    (2025, 12, 16, 8, 30, "Retail Sales", "HIGH"),

    # GDP Releases (8:30 AM ET) - HIGH
    (2025, 1, 30, 8, 30, "GDP Release", "HIGH"),
    (2025, 2, 27, 8, 30, "GDP Release", "HIGH"),
    (2025, 3, 27, 8, 30, "GDP Release", "HIGH"),
    (2025, 4, 30, 8, 30, "GDP Release", "HIGH"),
    (2025, 5, 29, 8, 30, "GDP Release", "HIGH"),
    (2025, 6, 26, 8, 30, "GDP Release", "HIGH"),
    (2025, 7, 30, 8, 30, "GDP Release", "HIGH"),
    (2025, 8, 28, 8, 30, "GDP Release", "HIGH"),
    (2025, 9, 25, 8, 30, "GDP Release", "HIGH"),
    (2025, 10, 30, 8, 30, "GDP Release", "HIGH"),
    (2025, 11, 26, 8, 30, "GDP Release", "HIGH"),
    (2025, 12, 23, 8, 30, "GDP Release", "HIGH"),

    # PCE Inflation (8:30 AM ET) - HIGH (Fed's preferred inflation gauge)
    (2025, 1, 31, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 2, 28, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 3, 28, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 4, 30, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 5, 30, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 6, 27, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 7, 31, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 8, 29, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 9, 26, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 10, 31, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 11, 27, 8, 30, "PCE Inflation", "HIGH"),
    (2025, 12, 23, 8, 30, "PCE Inflation", "HIGH"),

    # ============= 2026 EVENTS =============
    # FOMC Press Conferences (2:30 PM ET) - CRITICAL
    (2026, 1, 29, 14, 30, "FOMC Press Conference", "CRITICAL"),  # Jan 29 - Powell speaks
    (2026, 3, 18, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2026, 5, 6, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2026, 6, 17, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2026, 7, 29, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2026, 9, 16, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2026, 11, 4, 14, 30, "FOMC Press Conference", "CRITICAL"),
    (2026, 12, 16, 14, 30, "FOMC Press Conference", "CRITICAL"),

    # CPI Releases 2026 (8:30 AM ET) - CRITICAL
    (2026, 1, 14, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 2, 11, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 3, 11, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 4, 10, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 5, 12, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 6, 10, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 7, 14, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 8, 12, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 9, 10, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 10, 13, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 11, 12, 8, 30, "CPI Release", "CRITICAL"),
    (2026, 12, 10, 8, 30, "CPI Release", "CRITICAL"),

    # NFP/Jobs Report 2026 (First Friday, 8:30 AM ET) - CRITICAL
    (2026, 1, 9, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 2, 6, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 3, 6, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 4, 3, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 5, 1, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 6, 5, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 7, 2, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 8, 7, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 9, 4, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 10, 2, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 11, 6, 8, 30, "NFP Jobs Report", "CRITICAL"),
    (2026, 12, 4, 8, 30, "NFP Jobs Report", "CRITICAL"),
]

# Alias for backward compatibility
FED_EVENTS = HIGH_IMPACT_EVENTS

# Auto-scheduler state
auto_scheduler_enabled = True
last_auto_check = None
auto_started_event = None

# Deepgram API configuration
DEEPGRAM_API_KEY = os.environ.get('DEEPGRAM_API_KEY', '76c2874a31e7f07102d526a6f3bd5f0e949c5281')

# Chunk duration in seconds (Deepgram processes files, not streams)
# Shorter = faster updates but more API calls
CHUNK_DURATION = 5

# Historical events file path
HISTORICAL_EVENTS_FILE = os.path.join(os.path.dirname(__file__), 'red_folder_history.json')

# Load historical events from file
def load_historical_events():
    try:
        if os.path.exists(HISTORICAL_EVENTS_FILE):
            with open(HISTORICAL_EVENTS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading historical events: {e}")
    return []

# Save historical events to file
def save_historical_events(events):
    try:
        with open(HISTORICAL_EVENTS_FILE, 'w') as f:
            json.dump(events, f, indent=2)
    except Exception as e:
        print(f"Error saving historical events: {e}")

# Get current Gold price from main backend
def get_gold_price():
    try:
        response = requests.get('http://localhost:8080/', timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('current_price', 0) or data.get('session_high', 0) or 0
    except:
        pass
    return 0

# Global state
red_folder_state = {
    # Stream status
    'stream_active': False,
    'stream_url': '',
    'stream_title': '',
    'stream_start_time': '',
    'stream_start_price': 0,  # Gold price when stream started

    # Transcription
    'transcript_buffer': [],  # List of {timestamp, text, is_final}
    'current_segment': '',

    # Sentiment Analysis
    'sentiment': {
        'current': 'neutral',  # bullish/bearish/neutral
        'score': 0.0,          # -1.0 to 1.0
        'confidence': 0.0,
        'history': []          # Rolling window of scores
    },

    # Voice Tone Analysis
    'voice_tone': {
        'confidence_level': 0.0,    # 0-100
        'hesitation_count': 0,
        'stress_indicators': 0,
        'speaking_rate': 0.0,       # words per minute
        'pause_frequency': 0.0
    },

    # Keyword Tracking (comprehensive for all high-impact events)
    'keywords': {
        # FOMC / Fed Policy
        'inflation': {'count': 0, 'last_timestamp': ''},
        'rates': {'count': 0, 'last_timestamp': ''},
        'interest': {'count': 0, 'last_timestamp': ''},
        'hawkish': {'count': 0, 'last_timestamp': ''},
        'dovish': {'count': 0, 'last_timestamp': ''},
        'tightening': {'count': 0, 'last_timestamp': ''},
        'easing': {'count': 0, 'last_timestamp': ''},
        'cut': {'count': 0, 'last_timestamp': ''},
        'hike': {'count': 0, 'last_timestamp': ''},
        'pause': {'count': 0, 'last_timestamp': ''},
        'pivot': {'count': 0, 'last_timestamp': ''},
        'restrictive': {'count': 0, 'last_timestamp': ''},
        'accommodative': {'count': 0, 'last_timestamp': ''},
        'target': {'count': 0, 'last_timestamp': ''},
        'mandate': {'count': 0, 'last_timestamp': ''},
        'policy': {'count': 0, 'last_timestamp': ''},
        'quantitative': {'count': 0, 'last_timestamp': ''},
        'tapering': {'count': 0, 'last_timestamp': ''},
        # Employment / NFP
        'employment': {'count': 0, 'last_timestamp': ''},
        'jobs': {'count': 0, 'last_timestamp': ''},
        'labor': {'count': 0, 'last_timestamp': ''},
        'unemployment': {'count': 0, 'last_timestamp': ''},
        'payrolls': {'count': 0, 'last_timestamp': ''},
        'nonfarm': {'count': 0, 'last_timestamp': ''},
        'workforce': {'count': 0, 'last_timestamp': ''},
        'wages': {'count': 0, 'last_timestamp': ''},
        'hiring': {'count': 0, 'last_timestamp': ''},
        'layoffs': {'count': 0, 'last_timestamp': ''},
        'participation': {'count': 0, 'last_timestamp': ''},
        'jobless': {'count': 0, 'last_timestamp': ''},
        'claims': {'count': 0, 'last_timestamp': ''},
        # CPI / Inflation
        'cpi': {'count': 0, 'last_timestamp': ''},
        'consumer': {'count': 0, 'last_timestamp': ''},
        'prices': {'count': 0, 'last_timestamp': ''},
        'core': {'count': 0, 'last_timestamp': ''},
        'headline': {'count': 0, 'last_timestamp': ''},
        'pce': {'count': 0, 'last_timestamp': ''},
        'deflation': {'count': 0, 'last_timestamp': ''},
        'disinflation': {'count': 0, 'last_timestamp': ''},
        'transitory': {'count': 0, 'last_timestamp': ''},
        'shelter': {'count': 0, 'last_timestamp': ''},
        'energy': {'count': 0, 'last_timestamp': ''},
        'food': {'count': 0, 'last_timestamp': ''},
        'services': {'count': 0, 'last_timestamp': ''},
        'goods': {'count': 0, 'last_timestamp': ''},
        # GDP / Growth
        'gdp': {'count': 0, 'last_timestamp': ''},
        'growth': {'count': 0, 'last_timestamp': ''},
        'recession': {'count': 0, 'last_timestamp': ''},
        'expansion': {'count': 0, 'last_timestamp': ''},
        'contraction': {'count': 0, 'last_timestamp': ''},
        'economy': {'count': 0, 'last_timestamp': ''},
        'economic': {'count': 0, 'last_timestamp': ''},
        'output': {'count': 0, 'last_timestamp': ''},
        'productivity': {'count': 0, 'last_timestamp': ''},
        'spending': {'count': 0, 'last_timestamp': ''},
        # Market Sentiment
        'confidence': {'count': 0, 'last_timestamp': ''},
        'uncertainty': {'count': 0, 'last_timestamp': ''},
        'risk': {'count': 0, 'last_timestamp': ''},
        'outlook': {'count': 0, 'last_timestamp': ''},
        'forecast': {'count': 0, 'last_timestamp': ''},
        'expectations': {'count': 0, 'last_timestamp': ''},
        'surprise': {'count': 0, 'last_timestamp': ''},
        'beat': {'count': 0, 'last_timestamp': ''},
        'miss': {'count': 0, 'last_timestamp': ''},
        'revised': {'count': 0, 'last_timestamp': ''},
        'stronger': {'count': 0, 'last_timestamp': ''},
        'weaker': {'count': 0, 'last_timestamp': ''},
        'higher': {'count': 0, 'last_timestamp': ''},
        'lower': {'count': 0, 'last_timestamp': ''},
        'accelerate': {'count': 0, 'last_timestamp': ''},
        'decelerate': {'count': 0, 'last_timestamp': ''},
        # Retail / Consumer
        'retail': {'count': 0, 'last_timestamp': ''},
        'sales': {'count': 0, 'last_timestamp': ''},
        'demand': {'count': 0, 'last_timestamp': ''},
        # General
        'data': {'count': 0, 'last_timestamp': ''},
        'balanced': {'count': 0, 'last_timestamp': ''},
        'progress': {'count': 0, 'last_timestamp': ''},
    },

    # Market Direction Gauge
    'market_direction': {
        'signal': 'neutral',  # bullish/bearish/neutral
        'strength': 0.0,      # 0-100
        'components': {
            'sentiment_weight': 0.0,
            'tone_weight': 0.0,
            'keyword_weight': 0.0
        }
    },

    # Metadata
    'last_update': '',
    'error': None,
    'data_source': 'DEEPGRAM',
    'video_position': 0,  # Current position in video (seconds)

    # Scheduler
    'scheduler': {
        'enabled': True,
        'next_event': None,
        'next_time': None,
        'auto_started': False
    },

    # Historical events (loaded from file)
    'historical_events': []
}

# Load historical events on startup
red_folder_state['historical_events'] = load_historical_events()

# Stream control
stream_running = False
stream_thread = None


# ============================================
# SENTIMENT ANALYZER
# ============================================
class SentimentAnalyzer:
    """Analyze text sentiment for market direction"""

    BULLISH_TERMS = {
        # Growth & Economic strength
        'growth': 0.3, 'strong': 0.25, 'improving': 0.3, 'expansion': 0.4,
        'robust': 0.35, 'solid': 0.25, 'healthy': 0.3, 'positive': 0.2,
        # Dovish policy signals
        'dovish': 0.5, 'easing': 0.45, 'accommodation': 0.35, 'accommodative': 0.35,
        'supportive': 0.3, 'flexibility': 0.25, 'patient': 0.3, 'gradual': 0.2,
        'pause': 0.35, 'cut': 0.4, 'cuts': 0.4, 'lower': 0.2, 'reduce': 0.25,
        # Employment
        'employment': 0.25, 'jobs': 0.25, 'hiring': 0.3, 'labor': 0.15,
        'payrolls': 0.2, 'workforce': 0.15,
        # Confidence
        'confidence': 0.25, 'optimistic': 0.35, 'encouraged': 0.3,
        'progress': 0.3, 'achievement': 0.25, 'achieving': 0.2,
        # Stability
        'stable': 0.25, 'stability': 0.25, 'balanced': 0.2, 'moderate': 0.15,
        'soft': 0.3, 'landing': 0.2, 'resilient': 0.3, 'recovery': 0.35,
        # Market support
        'support': 0.25, 'stimulus': 0.4, 'liquidity': 0.2
    }

    BEARISH_TERMS = {
        # Inflation concerns
        'inflation': 0.35, 'inflationary': 0.35, 'prices': 0.15, 'elevated': 0.3,
        'persistent': 0.35, 'sticky': 0.3, 'upside': 0.2, 'pressures': 0.25,
        # Hawkish policy signals
        'hawkish': 0.5, 'tightening': 0.4, 'tighter': 0.35, 'restrictive': 0.4,
        'hike': 0.4, 'hikes': 0.4, 'raise': 0.3, 'higher': 0.2, 'increase': 0.15,
        'rates': 0.15, 'hold': 0.15, 'longer': 0.2,
        # Economic concerns
        'concern': 0.25, 'concerned': 0.25, 'risk': 0.2, 'risks': 0.2,
        'recession': 0.5, 'slowdown': 0.35, 'slowing': 0.3, 'weakness': 0.35,
        'decline': 0.3, 'declining': 0.3, 'contraction': 0.4,
        # Uncertainty
        'uncertainty': 0.3, 'uncertain': 0.25, 'volatile': 0.3, 'volatility': 0.25,
        'challenging': 0.25, 'difficult': 0.2, 'headwinds': 0.3,
        # Vigilance
        'vigilant': 0.25, 'careful': 0.15, 'cautious': 0.2, 'watching': 0.15,
        'monitoring': 0.15, 'data-dependent': 0.1, 'dependent': 0.1
    }

    def __init__(self):
        self.history = []
        self.window_size = 20

    def analyze(self, text: str) -> dict:
        text_lower = text.lower()
        words = text_lower.split()

        bullish_score = 0.0
        bearish_score = 0.0
        keywords_found = []

        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)

            if clean_word in self.BULLISH_TERMS:
                bullish_score += self.BULLISH_TERMS[clean_word]
                keywords_found.append((clean_word, 'bullish'))

            if clean_word in self.BEARISH_TERMS:
                bearish_score += self.BEARISH_TERMS[clean_word]
                keywords_found.append((clean_word, 'bearish'))

        total = bullish_score + bearish_score
        if total > 0:
            score = (bullish_score - bearish_score) / max(total, 1)
        else:
            score = 0.0

        score = max(-1.0, min(1.0, score))

        self.history.append(score)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        smoothed_score = sum(self.history) / len(self.history) if self.history else 0.0

        if smoothed_score > 0.05:
            sentiment = 'bullish'
        elif smoothed_score < -0.05:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'

        confidence = min(1.0, len(keywords_found) / 5.0)

        return {
            'sentiment': sentiment,
            'score': smoothed_score,
            'confidence': confidence,
            'keywords_found': keywords_found
        }


# ============================================
# VOICE TONE ANALYZER
# ============================================
class VoiceToneAnalyzer:
    """Analyze voice patterns from transcript"""

    def __init__(self):
        self.word_count = 0
        self.hesitation_words = ['um', 'uh', 'ah', 'er', 'hmm', 'well', 'so', 'like']
        self.start_time = None
        self.hesitation_count = 0

    def analyze(self, text: str) -> dict:
        if not text:
            return self._get_current_state()

        if self.start_time is None:
            self.start_time = time.time()

        words = text.lower().split()
        self.word_count += len(words)

        # Count hesitation words
        for word in words:
            clean_word = re.sub(r'[^\w]', '', word)
            if clean_word in self.hesitation_words:
                self.hesitation_count += 1

        return self._get_current_state()

    def _get_current_state(self) -> dict:
        elapsed = time.time() - self.start_time if self.start_time else 1
        wpm = (self.word_count / elapsed) * 60 if elapsed > 0 else 0

        # Estimate confidence based on hesitation ratio
        hesitation_ratio = self.hesitation_count / max(1, self.word_count) * 100
        confidence = max(0, 100 - hesitation_ratio * 10)

        return {
            'confidence_level': confidence,
            'hesitation_count': self.hesitation_count,
            'stress_indicators': max(0, self.hesitation_count - 3),
            'speaking_rate': wpm,
            'pause_frequency': hesitation_ratio
        }

    def reset(self):
        self.word_count = 0
        self.hesitation_count = 0
        self.start_time = None


# ============================================
# KEYWORD TRACKER
# ============================================
class KeywordTracker:
    """Track keyword occurrences in transcript"""

    # Comprehensive keywords for all high-impact economic events
    KEYWORDS = [
        # FOMC / Fed Policy
        'inflation', 'rates', 'interest', 'hawkish', 'dovish',
        'tightening', 'easing', 'cut', 'hike', 'pause', 'pivot',
        'restrictive', 'accommodative', 'target', 'mandate', 'policy',
        'balance sheet', 'quantitative', 'tapering',

        # Employment / NFP
        'employment', 'jobs', 'labor', 'unemployment', 'payrolls',
        'nonfarm', 'workforce', 'hiring', 'layoffs', 'wages',
        'participation', 'jobless', 'claims',

        # CPI / Inflation
        'cpi', 'consumer', 'prices', 'core', 'headline',
        'pce', 'deflation', 'disinflation', 'transitory',
        'shelter', 'energy', 'food', 'services', 'goods',

        # GDP / Growth
        'gdp', 'growth', 'recession', 'expansion', 'contraction',
        'economy', 'economic', 'output', 'productivity', 'spending',

        # Market Sentiment
        'confidence', 'uncertainty', 'risk', 'outlook', 'forecast',
        'expectations', 'surprise', 'beat', 'miss', 'revised',
        'stronger', 'weaker', 'higher', 'lower', 'accelerate', 'decelerate',

        # Retail / Consumer
        'retail', 'sales', 'consumer', 'spending', 'demand',

        # General
        'data', 'balanced', 'progress', 'soft landing', 'hard landing'
    ]

    def track(self, text: str) -> dict:
        text_lower = text.lower()
        timestamp = datetime.now().strftime('%H:%M:%S')

        for keyword in self.KEYWORDS:
            count = text_lower.count(keyword)
            if count > 0:
                red_folder_state['keywords'][keyword]['count'] += count
                red_folder_state['keywords'][keyword]['last_timestamp'] = timestamp

        return red_folder_state['keywords']


# ============================================
# MARKET DIRECTION GAUGE
# ============================================
class MarketDirectionGauge:
    """Aggregate signals into market direction"""

    def __init__(self):
        self.sentiment_weight = 0.5
        self.tone_weight = 0.2
        self.keyword_weight = 0.3

    def calculate(self, sentiment: dict, voice_tone: dict, keywords: dict) -> dict:
        sentiment_score = sentiment.get('score', 0) * 50

        confidence = voice_tone.get('confidence_level', 50)
        hesitations = voice_tone.get('hesitation_count', 0)
        tone_score = (confidence - 50) / 2 - hesitations * 2
        tone_score = max(-50, min(50, tone_score))

        # Bullish for Gold: dovish Fed, strong economy, rate cuts
        bullish_keywords = [
            'growth', 'dovish', 'easing', 'cut', 'pivot', 'accommodative',
            'employment', 'jobs', 'hiring', 'expansion', 'beat', 'stronger',
            'confidence', 'retail', 'spending', 'progress'
        ]
        # Bearish for Gold: hawkish Fed, inflation concerns, rate hikes
        bearish_keywords = [
            'inflation', 'hawkish', 'tightening', 'hike', 'restrictive',
            'recession', 'rates', 'unemployment', 'layoffs', 'miss', 'weaker',
            'uncertainty', 'core', 'shelter', 'prices', 'headline'
        ]

        bullish_count = sum(keywords.get(k, {}).get('count', 0) for k in bullish_keywords)
        bearish_count = sum(keywords.get(k, {}).get('count', 0) for k in bearish_keywords)

        total_kw = bullish_count + bearish_count
        if total_kw > 0:
            keyword_score = ((bullish_count - bearish_count) / total_kw) * 50
        else:
            keyword_score = 0

        total_score = (
            sentiment_score * self.sentiment_weight +
            tone_score * self.tone_weight +
            keyword_score * self.keyword_weight
        )

        if total_score > 15:
            signal = 'bullish'
        elif total_score < -15:
            signal = 'bearish'
        else:
            signal = 'neutral'

        strength = min(100, abs(total_score) * 2)

        return {
            'signal': signal,
            'strength': strength,
            'components': {
                'sentiment_weight': sentiment_score / 50,
                'tone_weight': tone_score / 50,
                'keyword_weight': keyword_score / 50
            }
        }


# ============================================
# DEEPGRAM API CLIENT
# ============================================
class DeepgramClient:
    """Deepgram API client for transcription"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = 'https://api.deepgram.com/v1/listen'

    def transcribe_file(self, audio_file_path: str) -> dict:
        """
        Upload audio file to Deepgram and get transcription
        Uses pre-recorded audio endpoint
        """
        try:
            with open(audio_file_path, 'rb') as f:
                audio_data = f.read()

            headers = {
                'Authorization': f'Token {self.api_key}',
                'Content-Type': 'audio/wav'
            }

            params = {
                'model': 'nova-2',
                'smart_format': 'true',
                'punctuate': 'true'
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                params=params,
                data=audio_data,
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                # Extract transcript from Deepgram response
                transcript = ''
                try:
                    channels = data.get('results', {}).get('channels', [])
                    if channels:
                        alternatives = channels[0].get('alternatives', [])
                        if alternatives:
                            transcript = alternatives[0].get('transcript', '')
                except:
                    pass
                return {'text': transcript, 'raw': data}
            else:
                return {'error': f'Deepgram API error: {response.status_code} - {response.text}'}

        except Exception as e:
            return {'error': str(e)}


# ============================================
# YOUTUBE AUDIO EXTRACTOR (CHUNKED)
# ============================================
class YouTubeAudioExtractor:
    """Extract audio chunks from YouTube for Deepgram processing"""

    def __init__(self, url: str):
        self.url = url
        self.title = ''
        self.position = 0  # Track position in seconds for recorded videos
        self.stream_url = None  # Cache the stream URL

    def get_stream_info(self) -> dict:
        """Get stream title"""
        try:
            cmd = ['yt-dlp', '--js-runtimes', 'node', '--get-title', self.url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            self.title = result.stdout.strip() if result.returncode == 0 else 'Unknown Stream'
            return {'title': self.title, 'url': self.url}
        except Exception as e:
            return {'title': 'Unknown Stream', 'url': self.url, 'error': str(e)}

    def record_chunk(self, duration: int = 15) -> str:
        """
        Record a chunk of audio from YouTube stream/video
        Returns path to temporary WAV file
        Tracks position for recorded videos to advance through content
        """
        try:
            # Create temp file for audio chunk
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_path = temp_file.name
            temp_file.close()

            # Get stream URL if not cached
            if not self.stream_url:
                # Try bestaudio first, then fall back to best (combined) for live streams
                for fmt in ['bestaudio', 'best']:
                    stream_cmd = ['yt-dlp', '--js-runtimes', 'node', '-g', '-f', fmt, self.url]
                    stream_result = subprocess.run(stream_cmd, capture_output=True, text=True, timeout=60)

                    if stream_result.returncode == 0:
                        self.stream_url = stream_result.stdout.strip()
                        print(f"Got stream URL with format: {fmt}")
                        break
                    else:
                        print(f"Format {fmt} not available, trying next...")

                if not self.stream_url:
                    print(f"yt-dlp error: Could not get stream URL")
                    return None

            # Record with ffmpeg - use -ss to seek to current position
            ffmpeg_cmd = [
                'ffmpeg',
                '-y',  # Overwrite
                '-ss', str(self.position),  # Seek to current position
                '-i', self.stream_url,
                '-t', str(duration),
                '-ar', '16000',  # 16kHz for transcription
                '-ac', '1',  # Mono
                '-f', 'wav',
                temp_path
            ]

            result = subprocess.run(ffmpeg_cmd, capture_output=True, timeout=duration + 30)

            # Advance position for next chunk
            self.position += duration

            # Check if file was created and has content
            if os.path.exists(temp_path) and os.path.getsize(temp_path) > 1000:
                return temp_path
            else:
                # Video might have ended, reset position
                print(f"Audio chunk too small or missing, video may have ended at {self.position}s")
                return None

        except Exception as e:
            print(f"Error recording chunk: {e}")
            return None

    def reset_position(self):
        """Reset position to start of video"""
        self.position = 0
        self.stream_url = None


# ============================================
# TRANSCRIPTION PROCESSOR
# ============================================
class TranscriptionProcessor:
    """Process audio chunks and update state"""

    def __init__(self):
        self.sentiment_analyzer = SentimentAnalyzer()
        self.voice_tone_analyzer = VoiceToneAnalyzer()
        self.keyword_tracker = KeywordTracker()
        self.market_gauge = MarketDirectionGauge()
        self.deepgram_client = DeepgramClient(DEEPGRAM_API_KEY) if DEEPGRAM_API_KEY else None

    def process_audio_chunk(self, audio_path: str) -> str:
        """
        Send audio to Deepgram and get transcript
        Falls back to local whisper if Deepgram fails
        """
        transcript = ''

        # Try Deepgram API first
        if self.deepgram_client:
            result = self.deepgram_client.transcribe_file(audio_path)
            if 'error' not in result:
                transcript = result.get('text', '')

        # Fallback: use local whisper if available
        if not transcript:
            transcript = self._local_transcribe(audio_path)

        return transcript

    def _local_transcribe(self, audio_path: str) -> str:
        """
        Fallback local transcription using whisper CLI or similar
        """
        try:
            # Try using whisper CLI if installed
            cmd = ['whisper', audio_path, '--model', 'tiny', '--output_format', 'txt', '--output_dir', '/tmp']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                # Read the output file
                txt_path = audio_path.replace('.wav', '.txt')
                if os.path.exists(txt_path):
                    with open(txt_path, 'r') as f:
                        return f.read().strip()
        except:
            pass

        # If whisper not available, return placeholder
        return "[Transcription service unavailable - set DEEPGRAM_API_KEY or install whisper]"

    def analyze_transcript(self, transcript: str):
        """Analyze transcript and update state"""
        global red_folder_state

        if not transcript:
            return

        timestamp = datetime.now().strftime('%H:%M:%S')

        # Add to transcript buffer
        red_folder_state['transcript_buffer'].append({
            'timestamp': timestamp,
            'text': transcript,
            'is_final': True
        })

        # Keep buffer manageable
        if len(red_folder_state['transcript_buffer']) > 100:
            red_folder_state['transcript_buffer'].pop(0)

        # Sentiment analysis
        sentiment_result = self.sentiment_analyzer.analyze(transcript)
        red_folder_state['sentiment'] = {
            'current': sentiment_result['sentiment'],
            'score': sentiment_result['score'],
            'confidence': sentiment_result['confidence'],
            'history': self.sentiment_analyzer.history[-20:]
        }

        # Voice tone analysis
        tone_result = self.voice_tone_analyzer.analyze(transcript)
        red_folder_state['voice_tone'] = tone_result

        # Keyword tracking
        self.keyword_tracker.track(transcript)

        # Market direction
        direction = self.market_gauge.calculate(
            red_folder_state['sentiment'],
            red_folder_state['voice_tone'],
            red_folder_state['keywords']
        )
        red_folder_state['market_direction'] = direction

        red_folder_state['last_update'] = timestamp

    def reset(self):
        """Reset analyzers"""
        self.sentiment_analyzer = SentimentAnalyzer()
        self.voice_tone_analyzer.reset()


# ============================================
# STREAM MANAGER
# ============================================
def stream_loop(url: str):
    """Main loop for processing YouTube stream"""
    global stream_running, red_folder_state

    extractor = YouTubeAudioExtractor(url)
    processor = TranscriptionProcessor()

    # Get stream info
    info = extractor.get_stream_info()
    red_folder_state['stream_title'] = info.get('title', 'Unknown')

    print(f"Starting stream processing: {info.get('title')}")

    while stream_running:
        try:
            # Record chunk
            red_folder_state['current_segment'] = f'Recording audio chunk... ({extractor.position}s)'
            red_folder_state['video_position'] = extractor.position
            audio_path = extractor.record_chunk(CHUNK_DURATION)

            if audio_path and os.path.exists(audio_path):
                # Transcribe
                red_folder_state['current_segment'] = 'Transcribing...'
                transcript = processor.process_audio_chunk(audio_path)

                # Analyze
                if transcript and not transcript.startswith('[Transcription'):
                    processor.analyze_transcript(transcript)
                    print(f"[{extractor.position}s] {transcript[:80]}...")

                # Cleanup
                try:
                    os.remove(audio_path)
                except:
                    pass
            else:
                # No audio - might be end of video
                red_folder_state['current_segment'] = 'Waiting for audio...'
                time.sleep(2)

            red_folder_state['current_segment'] = ''

        except Exception as e:
            print(f"Stream loop error: {e}")
            red_folder_state['error'] = str(e)
            time.sleep(5)

    print("Stream processing stopped")


def find_fed_live_stream() -> str:
    """
    Try to find the current Fed live stream URL
    """
    try:
        # Try the direct live URL first
        cmd = ['yt-dlp', '--js-runtimes', 'node', '-g', '-f', 'bestaudio', FED_YOUTUBE_CHANNEL]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            return FED_YOUTUBE_CHANNEL

        # Try to find latest live/premiere from streams page
        cmd = ['yt-dlp', '--js-runtimes', 'node', '--flat-playlist', '--print', 'url',
               '--match-filter', 'live_status=is_live', FED_YOUTUBE_SEARCH]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            urls = result.stdout.strip().split('\n')
            if urls:
                return urls[0]

        return None
    except Exception as e:
        print(f"Error finding Fed live stream: {e}")
        return None


def check_fed_schedule() -> dict:
    """
    Check if we're within a high-impact event window
    Returns event info if within 24 hours before or 6 hours after scheduled start
    Times are stored in ET - server runs in UTC, so we add 5 hours for conversion
    """
    # Get current time in UTC (Railway runs in UTC)
    now_naive = datetime.utcnow()

    # Check for active events
    for event in HIGH_IMPACT_EVENTS:
        try:
            year, month, day, hour, minute, event_name = event[:6]
            impact_level = event[6] if len(event) > 6 else "HIGH"

            # Event time is stored as ET, convert to UTC by adding 5 hours
            # (ET is UTC-5, so 14:30 ET = 19:30 UTC)
            event_time_et = datetime(year, month, day, hour, minute)
            event_time_utc = event_time_et + timedelta(hours=5)

            # Use UTC time for comparison
            now_naive = datetime.utcnow()

            # Check if within window: 24 hours before to 6 hours after (wide window for visibility)
            window_start = event_time_utc - timedelta(hours=24)
            window_end = event_time_utc + timedelta(hours=6)

            if window_start <= now_naive <= window_end:
                return {
                    'active': True,
                    'event_name': event_name,
                    'impact_level': impact_level,
                    'scheduled_time': event_time_et.strftime('%Y-%m-%d %H:%M ET'),
                    'minutes_until': int((event_time_utc - now_naive).total_seconds() / 60),
                    'status': 'upcoming' if now_naive < event_time_utc else 'in_progress'
                }
        except (ValueError, IndexError):
            continue

    # Find next 3 upcoming events
    upcoming = []
    now_naive = datetime.utcnow()
    for event in HIGH_IMPACT_EVENTS:
        try:
            year, month, day, hour, minute, event_name = event[:6]
            impact_level = event[6] if len(event) > 6 else "HIGH"
            event_time_et = datetime(year, month, day, hour, minute)
            event_time_utc = event_time_et + timedelta(hours=5)  # Convert ET to UTC
            if event_time_utc > now_naive:
                upcoming.append({
                    'event_name': event_name,
                    'impact_level': impact_level,
                    'event_time': event_time_utc,
                    'formatted_time': event_time_et.strftime('%Y-%m-%d %H:%M ET'),
                    'days_until': (event_time_utc - now_naive).days
                })
        except (ValueError, IndexError):
            continue

    # Sort by time and get next 3
    upcoming.sort(key=lambda x: x['event_time'])
    upcoming = upcoming[:3]

    if upcoming:
        next_event = upcoming[0]
        return {
            'active': False,
            'next_event': next_event['event_name'],
            'next_time': next_event['formatted_time'],
            'impact_level': next_event['impact_level'],
            'days_until': next_event['days_until'],
            'upcoming_events': [
                {'name': e['event_name'], 'time': e['formatted_time'], 'impact': e['impact_level']}
                for e in upcoming
            ]
        }

    return {'active': False, 'next_event': None}


def auto_start_fed_event():
    """
    Automatically start transcription if a Fed event is active
    """
    global auto_started_event, red_folder_state

    if not auto_scheduler_enabled:
        return None

    if red_folder_state.get('stream_active'):
        return None  # Already streaming

    schedule = check_fed_schedule()

    if schedule.get('active') and schedule.get('status') == 'in_progress':
        event_name = schedule.get('event_name', 'Fed Event')

        # Don't restart if we already auto-started this event
        if auto_started_event == event_name:
            return None

        print(f"[AUTO-SCHEDULER] Fed event detected: {event_name}")

        # Try to find live stream
        live_url = find_fed_live_stream()

        if live_url:
            print(f"[AUTO-SCHEDULER] Found live stream: {live_url}")
            auto_started_event = event_name
            return start_stream(live_url)
        else:
            print("[AUTO-SCHEDULER] No live stream found yet")
            red_folder_state['error'] = f"Fed event active ({event_name}) but no live stream found"

    return None


def start_stream(url: str):
    """Start transcription stream"""
    global stream_running, stream_thread, red_folder_state

    if red_folder_state['stream_active']:
        return {'error': 'Stream already active'}

    # Capture Gold price at start
    start_price = get_gold_price()

    # Reset state
    red_folder_state['transcript_buffer'] = []
    red_folder_state['current_segment'] = ''
    red_folder_state['sentiment'] = {'current': 'neutral', 'score': 0.0, 'confidence': 0.0, 'history': []}
    red_folder_state['voice_tone'] = {'confidence_level': 0, 'hesitation_count': 0, 'stress_indicators': 0, 'speaking_rate': 0, 'pause_frequency': 0}
    for kw in red_folder_state['keywords']:
        red_folder_state['keywords'][kw] = {'count': 0, 'last_timestamp': ''}
    red_folder_state['market_direction'] = {'signal': 'neutral', 'strength': 0, 'components': {'sentiment_weight': 0, 'tone_weight': 0, 'keyword_weight': 0}}
    red_folder_state['error'] = None
    red_folder_state['stream_url'] = url
    red_folder_state['stream_start_time'] = datetime.now().isoformat()
    red_folder_state['stream_start_price'] = start_price
    red_folder_state['stream_active'] = True

    # Start stream thread
    stream_running = True
    stream_thread = threading.Thread(target=stream_loop, args=(url,), daemon=True)
    stream_thread.start()

    return {'status': 'started', 'message': 'Stream processing started (chunked mode)'}


def stop_stream():
    """Stop transcription stream and save to history"""
    global stream_running, red_folder_state

    # Capture final state before stopping
    end_price = get_gold_price()
    start_price = red_folder_state.get('stream_start_price', 0)
    price_move = round(end_price - start_price, 2) if start_price > 0 and end_price > 0 else 0

    # Save to historical events if we have meaningful data
    if red_folder_state.get('stream_title') and len(red_folder_state.get('transcript_buffer', [])) > 0:
        # Get event name from title or scheduler
        event_name = red_folder_state.get('stream_title', 'Unknown Event')
        scheduler = red_folder_state.get('scheduler', {})

        # Try to extract clean event name
        if scheduler.get('event_active'):
            event_name = scheduler.get('next_event', event_name)

        # Parse start time
        start_time_str = red_folder_state.get('stream_start_time', '')
        try:
            start_dt = datetime.fromisoformat(start_time_str)
            date_str = start_dt.strftime('%b %d, %Y')
            time_str = start_dt.strftime('%H:%M ET')
        except:
            date_str = datetime.now().strftime('%b %d, %Y')
            time_str = datetime.now().strftime('%H:%M ET')

        # Create historical event record
        historical_event = {
            'event': event_name[:50],  # Truncate long titles
            'date': date_str,
            'time': time_str,
            'sentiment': round(red_folder_state['sentiment'].get('score', 0), 2),
            'direction': red_folder_state['market_direction'].get('signal', 'neutral'),
            'strength': round(red_folder_state['market_direction'].get('strength', 0), 1),
            'gcMove': price_move,
            'startPrice': round(start_price, 2),
            'endPrice': round(end_price, 2),
            'transcribed': True,
            'timestamp': datetime.now().isoformat()
        }

        # Add to historical events (keep last 50)
        red_folder_state['historical_events'].insert(0, historical_event)
        red_folder_state['historical_events'] = red_folder_state['historical_events'][:50]

        # Save to file
        save_historical_events(red_folder_state['historical_events'])
        print(f"[HISTORY] Saved event: {event_name} | Sentiment: {historical_event['sentiment']} | Direction: {historical_event['direction']} | GC Move: {price_move}")

    stream_running = False
    red_folder_state['stream_active'] = False
    red_folder_state['current_segment'] = ''
    red_folder_state['stream_start_price'] = 0

    return {'status': 'stopped', 'price_move': price_move}


# ============================================
# HTTP SERVER
# ============================================
class RedFolderHandler(BaseHTTPRequestHandler):
    """HTTP handler for Red Folder API"""

    def log_message(self, format, *args):
        pass

    def _set_cors_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()

        response = json.dumps(red_folder_state)
        self.wfile.write(response.encode())

    def do_POST(self):
        path = urlparse(self.path).path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'

        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        response = {}

        if path == '/start':
            url = data.get('url', '')
            if url:
                response = start_stream(url)
            else:
                response = {'error': 'URL required'}

        elif path == '/stop':
            response = stop_stream()

        else:
            response = {'error': 'Unknown endpoint'}

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())


def scheduler_loop():
    """Background thread that checks for Fed events and auto-starts"""
    global red_folder_state

    print("[SCHEDULER] Auto-scheduler started")

    while True:
        try:
            # Update schedule info in state
            schedule = check_fed_schedule()
            red_folder_state['scheduler'] = {
                'enabled': auto_scheduler_enabled,
                'next_event': schedule.get('next_event') or schedule.get('event_name'),
                'next_time': schedule.get('next_time') or schedule.get('scheduled_time'),
                'impact_level': schedule.get('impact_level', 'HIGH'),
                'event_active': schedule.get('active', False),
                'auto_started': auto_started_event is not None,
                'upcoming_events': schedule.get('upcoming_events', [])
            }

            # Try to auto-start if event is active
            if auto_scheduler_enabled and not red_folder_state.get('stream_active'):
                auto_start_fed_event()

        except Exception as e:
            print(f"[SCHEDULER] Error: {e}")

        # Check every 30 seconds
        time.sleep(30)


def run_server(port: int = 8081):
    """Run the HTTP server"""
    # Start scheduler thread
    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()

    server = HTTPServer(('', port), RedFolderHandler)
    print(f"Red Folder service running on port {port}")
    print(f"DEEPGRAM_API_KEY: {'SET' if DEEPGRAM_API_KEY else 'NOT SET'}")
    print(f"Mode: Chunked transcription ({CHUNK_DURATION}s chunks)")
    print(f"Auto-scheduler: ENABLED")
    print(f"Fallback: Local whisper (if installed)")
    server.serve_forever()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    run_server(port)
