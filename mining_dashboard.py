"""
REAL-TIME MINING DASHBOARD
Comprehensive monitoring for video intelligence mining operation

Shows:
- System health (process, memory, CPU)
- Mining progress (demos, rate, acceptance)
- Recent videos with scores
- Deduplication stats
- Live log stream
"""

import time
import json
from pathlib import Path
from datetime import datetime
import subprocess
import os


class MiningDashboard:
    """Real-time dashboard for mining operation"""

    def __init__(self, log_file='mining_final_dedup.log', hdf5_dir='data_mine/permanent_data/hdf5'):
        self.log_file = Path(log_file)
        self.hdf5_dir = Path(hdf5_dir)
        self.dedup_file = Path('mining_processed_videos.json')
        self.start_time = datetime.now()

    def get_process_status(self):
        """Get mining process status"""
        try:
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True
            )
            lines = [l for l in result.stdout.split('\n') if 'run_overnight_mining.py' in l and 'grep' not in l]

            if lines:
                parts = lines[0].split()
                return {
                    'running': True,
                    'pid': parts[1],
                    'cpu': parts[2] + '%',
                    'memory': parts[3] + '%',
                    'status': parts[7]
                }
            return {'running': False}
        except Exception as e:
            return {'running': False, 'error': str(e)}

    def get_file_stats(self):
        """Get RGB file statistics"""
        if not self.hdf5_dir.exists():
            return {'count': 0, 'total_size': 0, 'recent': []}

        rgb_files = [f for f in self.hdf5_dir.glob('*.hdf5')
                     if f.stat().st_size > 1_000_000]

        rgb_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        total_size = sum(f.stat().st_size for f in rgb_files)

        recent = []
        for f in rgb_files[:5]:
            stat = f.stat()
            recent.append({
                'name': f.stem,
                'size_mb': stat.st_size / 1_000_000,
                'time': datetime.fromtimestamp(stat.st_mtime).strftime('%H:%M:%S')
            })

        return {
            'count': len(rgb_files),
            'total_size_mb': total_size / 1_000_000,
            'recent': recent
        }

    def get_dedup_stats(self):
        """Get deduplication statistics"""
        if not self.dedup_file.exists():
            return {'urls_tracked': 0, 'titles_tracked': 0}

        try:
            with open(self.dedup_file, 'r') as f:
                data = json.load(f)
            return {
                'urls_tracked': len(data.get('urls', [])),
                'titles_tracked': len(data.get('titles', [])),
                'last_updated': data.get('last_updated', 'unknown')
            }
        except Exception as e:
            return {'error': str(e)}

    def get_recent_log_entries(self, lines=30):
        """Get recent log entries"""
        if not self.log_file.exists():
            return []

        try:
            result = subprocess.run(
                ['tail', f'-{lines}', str(self.log_file)],
                capture_output=True,
                text=True
            )
            return result.stdout.split('\n')
        except Exception as e:
            return [f"Error reading log: {e}"]

    def parse_mining_stats(self):
        """Parse mining statistics from log"""
        if not self.log_file.exists():
            return {}

        try:
            result = subprocess.run(
                ['tail', '-500', str(self.log_file)],
                capture_output=True,
                text=True
            )

            stats = {
                'accepted': 0,
                'rejected': 0,
                'skipped_dedup': 0,
                'skipped_long': 0,
                'current_query': 'Unknown'
            }

            for line in result.stdout.split('\n'):
                if 'ACCEPTED' in line:
                    stats['accepted'] += 1
                elif 'REJECTED' in line:
                    stats['rejected'] += 1
                elif 'Already processed' in line:
                    stats['skipped_dedup'] += 1
                elif 'too long' in line:
                    stats['skipped_long'] += 1
                elif line.startswith('🔍 Query'):
                    stats['current_query'] = line.split(':', 1)[1].strip() if ':' in line else 'Unknown'

            # Calculate acceptance rate
            total = stats['accepted'] + stats['rejected']
            stats['acceptance_rate'] = (stats['accepted'] / total * 100) if total > 0 else 0

            return stats
        except Exception as e:
            return {'error': str(e)}

    def display(self):
        """Display dashboard"""
        # Clear screen
        os.system('clear')

        # Get all stats
        process = self.get_process_status()
        files = self.get_file_stats()
        dedup = self.get_dedup_stats()
        mining = self.parse_mining_stats()

        # Header
        print("=" * 80)
        print("🎯 VIDEO INTELLIGENCE MINING DASHBOARD")
        print("=" * 80)
        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # System Health
        print("🔧 SYSTEM HEALTH")
        print("-" * 80)
        if process.get('running'):
            print(f"✅ Mining Process: RUNNING (PID {process['pid']})")
            print(f"   CPU: {process['cpu']} | Memory: {process['memory']} | Status: {process['status']}")
        else:
            print("❌ Mining Process: NOT RUNNING")
            if 'error' in process:
                print(f"   Error: {process['error']}")
        print()

        # Gate 1 Progress
        print("📊 GATE 1 PROGRESS (RGB Demos)")
        print("-" * 80)
        progress_pct = (files['count'] / 100) * 100
        bar_length = 50
        filled = int(bar_length * progress_pct / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"[{bar}] {files['count']}/100 ({progress_pct:.1f}%)")
        print(f"Total Size: {files['total_size_mb']:.1f} MB")
        print()

        # Mining Statistics
        print("⛏️  MINING STATISTICS (Recent 500 log lines)")
        print("-" * 80)
        print(f"Current Query: {mining.get('current_query', 'Unknown')}")
        print(f"Accepted: {mining.get('accepted', 0)}")
        print(f"Rejected: {mining.get('rejected', 0)}")
        print(f"Acceptance Rate: {mining.get('acceptance_rate', 0):.1f}%")
        print(f"Skipped (Dedup): {mining.get('skipped_dedup', 0)}")
        print(f"Skipped (Too Long): {mining.get('skipped_long', 0)}")
        print()

        # Deduplication
        print("🔒 DEDUPLICATION")
        print("-" * 80)
        print(f"URLs Tracked: {dedup.get('urls_tracked', 0)}")
        print(f"Titles Tracked: {dedup.get('titles_tracked', 0)}")
        if 'last_updated' in dedup:
            print(f"Last Updated: {dedup['last_updated']}")
        print()

        # Recent Files
        print("📁 RECENT RGB FILES (Top 5)")
        print("-" * 80)
        for file in files.get('recent', []):
            print(f"⏰ {file['time']} | {file['size_mb']:5.1f} MB | {file['name'][:60]}")
        print()

        # Live Log (last 15 lines)
        print("📜 LIVE LOG (Last 15 lines)")
        print("-" * 80)
        log_lines = self.get_recent_log_entries(15)
        for line in log_lines[-15:]:
            # Truncate long lines
            if len(line) > 78:
                line = line[:75] + '...'
            print(line)
        print()

        print("=" * 80)
        print("Press Ctrl+C to exit | Auto-refresh every 10 seconds")
        print("=" * 80)

    def run(self, refresh_interval=10):
        """Run dashboard with auto-refresh"""
        print("Starting Mining Dashboard...")
        print(f"Refresh interval: {refresh_interval} seconds")
        print("Press Ctrl+C to exit")
        time.sleep(2)

        try:
            while True:
                self.display()
                time.sleep(refresh_interval)
        except KeyboardInterrupt:
            print("\n\n👋 Dashboard stopped")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Real-time Mining Dashboard')
    parser.add_argument('--refresh', type=int, default=10, help='Refresh interval (seconds)')
    parser.add_argument('--log', default='mining_final_dedup.log', help='Log file to monitor')

    args = parser.parse_args()

    dashboard = MiningDashboard(log_file=args.log)
    dashboard.run(refresh_interval=args.refresh)
