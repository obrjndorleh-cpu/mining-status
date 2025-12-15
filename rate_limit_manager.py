"""
RATE LIMIT MANAGER

Prevents YouTube from blocking your IP by enforcing conservative rate limits.

YouTube's unofficial limits (based on community observations):
- ~100 videos/hour from single IP
- ~1,000 videos/day from single IP
- Exceeding = Temporary ban (403 errors)

Our strategy:
- Conservative limits (safer than maximum)
- Exponential backoff on errors
- Daily/hourly quotas
- Automatic throttling
- IP rotation ready (for future scaling)
"""

import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import deque


class RateLimitManager:
    """
    Manage download rate limits to prevent IP bans
    """

    def __init__(self, config_file='rate_limit_config.json'):
        self.config_file = Path(config_file)
        self.load_config()

        # Download history (for tracking)
        self.download_history = deque(maxlen=1000)  # Last 1000 downloads
        self.load_history()

    def load_config(self):
        """Load rate limit configuration"""
        default_config = {
            # Conservative limits (70% of observed max)
            'max_per_hour': 70,          # YouTube observed max: ~100
            'max_per_day': 700,          # YouTube observed max: ~1000
            'min_delay_seconds': 10,     # Minimum delay between downloads
            'max_delay_seconds': 120,    # Maximum delay (backoff)
            'backoff_multiplier': 2.0,   # Exponential backoff on errors

            # Safety margins
            'hourly_buffer': 0.7,        # Use only 70% of hourly limit
            'daily_buffer': 0.7,         # Use only 70% of daily limit

            # Error handling
            'max_consecutive_errors': 3,
            'error_cooldown_minutes': 30,

            # Status
            'total_downloads': 0,
            'total_errors': 0,
            'last_reset': datetime.now().isoformat(),
            'ip_banned': False
        }

        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                loaded = json.load(f)
                # Merge with defaults
                default_config.update(loaded)

        self.config = default_config
        self.save_config()

    def save_config(self):
        """Save configuration"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)

    def load_history(self):
        """Load download history"""
        history_file = self.config_file.parent / 'download_history.json'
        if history_file.exists():
            try:
                with open(history_file, 'r') as f:
                    history = json.load(f)
                    # Convert timestamps back to datetime
                    for record in history[-1000:]:  # Last 1000
                        record['timestamp'] = datetime.fromisoformat(record['timestamp'])
                        self.download_history.append(record)
            except:
                pass

    def save_history(self):
        """Save download history"""
        history_file = self.config_file.parent / 'download_history.json'
        history_data = []
        for record in self.download_history:
            record_copy = record.copy()
            record_copy['timestamp'] = record['timestamp'].isoformat()
            history_data.append(record_copy)

        with open(history_file, 'w') as f:
            json.dump(history_data, f, indent=2)

    def get_downloads_in_window(self, hours=1):
        """Count downloads in last N hours"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return sum(1 for r in self.download_history
                  if r['timestamp'] > cutoff and r['success'])

    def can_download(self):
        """
        Check if we can download without exceeding limits

        Returns:
            (can_download: bool, reason: str, wait_seconds: int)
        """
        # Check if IP is banned
        if self.config.get('ip_banned'):
            return False, "IP banned - manual intervention required", 0

        # Check hourly limit
        downloads_last_hour = self.get_downloads_in_window(hours=1)
        hourly_limit = int(self.config['max_per_hour'] * self.config['hourly_buffer'])

        if downloads_last_hour >= hourly_limit:
            # Calculate how long until oldest download expires
            oldest_in_window = min(
                r['timestamp'] for r in self.download_history
                if r['timestamp'] > datetime.now() - timedelta(hours=1)
            )
            wait_seconds = int((oldest_in_window + timedelta(hours=1) - datetime.now()).total_seconds())
            return False, f"Hourly limit reached ({downloads_last_hour}/{hourly_limit})", max(60, wait_seconds)

        # Check daily limit
        downloads_last_day = self.get_downloads_in_window(hours=24)
        daily_limit = int(self.config['max_per_day'] * self.config['daily_buffer'])

        if downloads_last_day >= daily_limit:
            # Calculate time until reset
            oldest_in_window = min(
                r['timestamp'] for r in self.download_history
                if r['timestamp'] > datetime.now() - timedelta(hours=24)
            )
            wait_seconds = int((oldest_in_window + timedelta(hours=24) - datetime.now()).total_seconds())
            return False, f"Daily limit reached ({downloads_last_day}/{daily_limit})", wait_seconds

        # Check minimum delay between downloads
        if self.download_history:
            last_download = self.download_history[-1]['timestamp']
            time_since_last = (datetime.now() - last_download).total_seconds()
            min_delay = self.config['min_delay_seconds']

            if time_since_last < min_delay:
                wait_seconds = int(min_delay - time_since_last)
                return False, f"Too soon after last download (min delay: {min_delay}s)", wait_seconds

        # Check consecutive errors
        recent_errors = sum(
            1 for r in list(self.download_history)[-10:]
            if not r['success']
        )
        if recent_errors >= self.config['max_consecutive_errors']:
            cooldown = self.config['error_cooldown_minutes'] * 60
            return False, f"Too many errors ({recent_errors}), cooling down", cooldown

        return True, "OK", 0

    def record_download(self, success=True, error_code=None):
        """
        Record a download attempt

        Args:
            success: Whether download succeeded
            error_code: HTTP error code if failed (e.g., 403, 429)
        """
        record = {
            'timestamp': datetime.now(),
            'success': success,
            'error_code': error_code
        }

        self.download_history.append(record)
        self.config['total_downloads'] += 1

        if not success:
            self.config['total_errors'] += 1

            # Check for ban indicators
            if error_code in [403, 429]:  # Forbidden or Too Many Requests
                consecutive_bans = sum(
                    1 for r in list(self.download_history)[-5:]
                    if not r['success'] and r.get('error_code') in [403, 429]
                )

                if consecutive_bans >= 3:
                    print("\n" + "="*70)
                    print("⚠️  WARNING: POSSIBLE IP BAN DETECTED")
                    print("="*70)
                    print(f"Consecutive 403/429 errors: {consecutive_bans}")
                    print("Recommended actions:")
                    print("1. Stop mining immediately")
                    print("2. Wait 24 hours before retrying")
                    print("3. Consider using VPN or proxy")
                    print("4. Reduce rate limits in rate_limit_config.json")
                    print("="*70)

                    self.config['ip_banned'] = True

        self.save_config()
        self.save_history()

    def get_recommended_delay(self):
        """
        Get recommended delay before next download

        Returns:
            seconds to wait
        """
        # Base delay
        delay = self.config['min_delay_seconds']

        # Increase delay if approaching limits
        downloads_last_hour = self.get_downloads_in_window(hours=1)
        hourly_limit = int(self.config['max_per_hour'] * self.config['hourly_buffer'])
        usage_ratio = downloads_last_hour / hourly_limit if hourly_limit > 0 else 0

        # Exponential backoff as we approach limit
        if usage_ratio > 0.8:  # >80% of limit
            delay *= 3
        elif usage_ratio > 0.6:  # >60% of limit
            delay *= 2

        # Check recent errors
        recent_errors = sum(
            1 for r in list(self.download_history)[-10:]
            if not r['success']
        )
        if recent_errors > 0:
            delay *= (1 + recent_errors)  # Increase delay based on errors

        return min(delay, self.config['max_delay_seconds'])

    def print_status(self):
        """Print rate limit status"""
        downloads_last_hour = self.get_downloads_in_window(hours=1)
        downloads_last_day = self.get_downloads_in_window(hours=24)

        hourly_limit = int(self.config['max_per_hour'] * self.config['hourly_buffer'])
        daily_limit = int(self.config['max_per_day'] * self.config['daily_buffer'])

        print()
        print("="*70)
        print("📊 RATE LIMIT STATUS")
        print("="*70)
        print(f"Last hour:  {downloads_last_hour}/{hourly_limit} ({downloads_last_hour/hourly_limit*100:.1f}%)")
        print(f"Last 24h:   {downloads_last_day}/{daily_limit} ({downloads_last_day/daily_limit*100:.1f}%)")
        print()
        print(f"Total downloads: {self.config['total_downloads']}")
        print(f"Total errors: {self.config['total_errors']}")
        if self.config['total_downloads'] > 0:
            error_rate = self.config['total_errors'] / self.config['total_downloads'] * 100
            print(f"Error rate: {error_rate:.1f}%")
        print()

        can_download, reason, wait = self.can_download()
        if can_download:
            recommended_delay = self.get_recommended_delay()
            print(f"✅ Status: Can download (recommended delay: {recommended_delay}s)")
        else:
            print(f"⚠️  Status: {reason}")
            if wait > 0:
                print(f"   Wait: {wait}s ({wait/60:.1f} minutes)")

        if self.config.get('ip_banned'):
            print()
            print("🚫 IP BANNED - Manual intervention required!")
            print("   Wait 24 hours and reset: python rate_limit_manager.py --reset-ban")

        print("="*70)
        print()

    def reset_ban(self):
        """Reset ban status (use after waiting and changing IP)"""
        self.config['ip_banned'] = False
        self.save_config()
        print("✅ Ban status reset. Please use VPN or wait 24h before mining.")


def main():
    """
    CLI for rate limit manager
    """
    import argparse

    parser = argparse.ArgumentParser(description='YouTube rate limit manager')
    parser.add_argument('--status', action='store_true',
                       help='Show rate limit status')
    parser.add_argument('--reset-ban', action='store_true',
                       help='Reset IP ban status (use after changing IP)')
    parser.add_argument('--set-hourly', type=int,
                       help='Set hourly limit')
    parser.add_argument('--set-daily', type=int,
                       help='Set daily limit')

    args = parser.parse_args()

    manager = RateLimitManager()

    if args.reset_ban:
        manager.reset_ban()

    if args.set_hourly:
        manager.config['max_per_hour'] = args.set_hourly
        manager.save_config()
        print(f"✅ Hourly limit set to {args.set_hourly}")

    if args.set_daily:
        manager.config['max_per_day'] = args.set_daily
        manager.save_config()
        print(f"✅ Daily limit set to {args.set_daily}")

    manager.print_status()


if __name__ == '__main__':
    main()
