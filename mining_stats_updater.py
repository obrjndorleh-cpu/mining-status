"""
REAL-TIME MINING STATS UPDATER

Runs alongside mining and updates MongoDB every 5 minutes.
Check stats from phone via MongoDB mobile app!

Usage:
    python mining_stats_updater.py

Stats updated:
- Videos processed this session
- Videos accepted (quality > 70)
- Acceptance rate
- Rate limit status
- Space saved
- Mining speed (videos/hour)
"""

import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from cloud_mining_setup import CloudMiningSetup
import os


class MiningStatsUpdater:
    """Update mining statistics to cloud in real-time"""

    def __init__(self, update_interval=300):
        """
        Args:
            update_interval: Seconds between updates (default 300 = 5 minutes)
        """
        self.update_interval = update_interval
        self.cloud = CloudMiningSetup()

        if not self.cloud.client:
            print("❌ MongoDB not connected")
            print("💡 Set MONGODB_URI environment variable first!")
            print("   See PHONE_MONITORING.md for setup instructions")
            return

        self.stats_collection = self.cloud.db['mining_statistics']
        self.session_start = datetime.now()

        print("✅ Real-time stats updater started")
        print(f"   Updating every {update_interval}s ({update_interval/60:.1f} minutes)")
        print(f"   Check from phone via MongoDB mobile app!")
        print()

    def gather_stats(self):
        """Gather current mining statistics"""
        stats = {
            'timestamp': datetime.now(),
            'session_start': self.session_start,
            'uptime_hours': (datetime.now() - self.session_start).total_seconds() / 3600,
        }

        # Count permanent data files
        perm_data = Path('permanent_data')
        if perm_data.exists():
            hdf5_files = list(perm_data.glob('hdf5/*.hdf5'))
            json_files = list(perm_data.glob('json/*_reconciled.json'))

            stats['total_samples'] = len(hdf5_files)
            stats['total_json'] = len(json_files)

            # Calculate total size
            total_size = sum(f.stat().st_size for f in hdf5_files)
            stats['total_data_mb'] = total_size / (1024 * 1024)

        # Extract and delete log
        extract_log = Path('extract_and_delete.log')
        if extract_log.exists():
            with open(extract_log, 'r') as f:
                log_data = json.load(f)
                stats['videos_deleted'] = log_data.get('videos_deleted', 0)
                stats['space_saved_mb'] = log_data.get('space_saved_mb', 0)
                stats['last_processed'] = log_data.get('last_processed_time')

        # Rate limit status
        rate_limit_file = Path('rate_limit_config.json')
        if rate_limit_file.exists():
            with open(rate_limit_file, 'r') as f:
                rate_config = json.load(f)

                # Count downloads in last hour
                from collections import deque
                history = rate_config.get('download_history', [])

                now = datetime.now()
                one_hour_ago = now - timedelta(hours=1)
                one_day_ago = now - timedelta(days=1)

                downloads_hour = sum(
                    1 for d in history
                    if datetime.fromisoformat(d['timestamp']) > one_hour_ago
                )
                downloads_day = sum(
                    1 for d in history
                    if datetime.fromisoformat(d['timestamp']) > one_day_ago
                )

                stats['rate_limit'] = {
                    'downloads_this_hour': downloads_hour,
                    'downloads_today': downloads_day,
                    'hourly_limit': rate_config.get('max_per_hour', 70),
                    'daily_limit': rate_config.get('max_per_day', 700),
                    'status': 'OK' if downloads_hour < 60 else 'APPROACHING_LIMIT'
                }

        # Mining speed
        if stats.get('uptime_hours', 0) > 0:
            samples = stats.get('total_samples', 0)
            stats['mining_speed'] = {
                'samples_per_hour': samples / stats['uptime_hours'],
                'estimated_daily': (samples / stats['uptime_hours']) * 24
            }

        return stats

    def update_cloud(self):
        """Push stats to cloud"""
        if not self.cloud.client:
            return

        stats = self.gather_stats()

        # Insert into MongoDB
        self.stats_collection.insert_one(stats)

        print(f"[{datetime.now().strftime('%H:%M:%S')}] ☁️  Stats updated")
        print(f"   Samples: {stats.get('total_samples', 0)}")
        print(f"   Space saved: {stats.get('space_saved_mb', 0):.1f} MB")

        if 'rate_limit' in stats:
            rl = stats['rate_limit']
            print(f"   Rate limit: {rl['downloads_this_hour']}/{rl['hourly_limit']} this hour")

        if 'mining_speed' in stats:
            speed = stats['mining_speed']
            print(f"   Speed: {speed['samples_per_hour']:.1f} samples/hour")

        print()

    def run(self):
        """Run continuous stats updater"""
        if not self.cloud.client:
            return

        print("="*70)
        print("📊 REAL-TIME STATS UPDATER")
        print("="*70)
        print()

        try:
            while True:
                self.update_cloud()
                time.sleep(self.update_interval)

        except KeyboardInterrupt:
            print("\n⚠️  Stats updater stopped")
            print("   (Mining continues in background)")


def main():
    """Run stats updater"""
    import argparse

    parser = argparse.ArgumentParser(description='Real-time mining stats updater')
    parser.add_argument('--interval', type=int, default=300,
                       help='Update interval in seconds (default: 300 = 5 min)')
    parser.add_argument('--once', action='store_true',
                       help='Update once and exit (for testing)')

    args = parser.parse_args()

    updater = MiningStatsUpdater(update_interval=args.interval)

    if args.once:
        updater.update_cloud()
    else:
        updater.run()


if __name__ == '__main__':
    main()
