#!/usr/bin/env python3
"""
MINING PROGRESS MONITOR
Monitor mining progress in real-time (macOS compatible)
"""

import time
import os
from pathlib import Path
from datetime import datetime
import json


def get_file_stats(hdf5_dir):
    """Get statistics on HDF5 files"""
    hdf5_files = list(Path(hdf5_dir).glob('*.hdf5'))

    total_files = len(hdf5_files)
    rgb_files = []
    pose_only_files = []
    total_size = 0

    for file_path in hdf5_files:
        size = file_path.stat().st_size
        total_size += size

        # RGB files are ~28 MB, pose-only ~47 KB
        if size > 1_000_000:  # > 1 MB
            rgb_files.append({
                'name': file_path.name,
                'size': size,
                'modified': file_path.stat().st_mtime
            })
        else:
            pose_only_files.append(file_path.name)

    # Sort RGB files by modification time (newest first)
    rgb_files.sort(key=lambda x: x['modified'], reverse=True)

    return {
        'total_files': total_files,
        'rgb_count': len(rgb_files),
        'pose_only_count': len(pose_only_files),
        'total_size_mb': total_size / (1024 * 1024),
        'rgb_files': rgb_files[:10],  # Most recent 10
    }


def get_mining_stats(log_file):
    """Get mining statistics from log file"""
    if not Path(log_file).exists():
        return None

    stats = {
        'last_update': None,
        'status': 'unknown'
    }

    # Try to read last few lines
    try:
        with open(log_file, 'r') as f:
            lines = f.readlines()
            if lines:
                stats['last_update'] = datetime.now().strftime('%H:%M:%S')
                stats['status'] = 'running'
                # Could parse more details from log
    except:
        pass

    return stats


def check_process_running(pid_file='mining_pid.txt'):
    """Check if mining process is still running"""
    try:
        # Check if process exists
        import subprocess
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        return 'run_overnight_mining' in result.stdout
    except:
        return False


def clear_screen():
    """Clear terminal screen"""
    os.system('clear')


def format_size(size_bytes):
    """Format bytes to human readable"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def print_dashboard(hdf5_dir, log_file):
    """Print mining dashboard"""
    clear_screen()

    print("="*70)
    print("MINING PROGRESS DASHBOARD")
    print("="*70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Process status
    is_running = check_process_running()
    status = "🟢 RUNNING" if is_running else "🔴 STOPPED"
    print(f"Mining Status: {status}")
    print()

    # File statistics
    stats = get_file_stats(hdf5_dir)

    print("="*70)
    print("FILE STATISTICS")
    print("="*70)
    print(f"Total HDF5 files: {stats['total_files']}")
    print(f"RGB demos (>1MB): {stats['rgb_count']}")
    print(f"Pose-only demos: {stats['pose_only_count']}")
    print(f"Total storage: {stats['total_size_mb']:.1f} MB")
    print()

    # Progress to goal
    goal = 100
    progress = (stats['rgb_count'] / goal) * 100
    bar_length = 40
    filled = int(bar_length * stats['rgb_count'] / goal)
    bar = '█' * filled + '░' * (bar_length - filled)

    print("="*70)
    print(f"PROGRESS TO GATE 1 (100 RGB DEMOS)")
    print("="*70)
    print(f"[{bar}] {stats['rgb_count']}/{goal} ({progress:.1f}%)")
    print()

    # Recent RGB files
    if stats['rgb_files']:
        print("="*70)
        print("MOST RECENT RGB DEMOS (Last 10)")
        print("="*70)
        for i, file_info in enumerate(stats['rgb_files'], 1):
            name = file_info['name'][:50]
            size = format_size(file_info['size'])
            mod_time = datetime.fromtimestamp(file_info['modified']).strftime('%H:%M:%S')
            print(f"{i:2d}. [{mod_time}] {name:50s} {size:>10s}")
    else:
        print("⏳ Waiting for first RGB demo...")
        print("   (Mining process downloading and quality checking videos)")

    print()
    print("="*70)
    print("Press Ctrl+C to exit | Updates every 30 seconds")
    print("="*70)


def main():
    """Monitor mining progress"""
    import argparse

    parser = argparse.ArgumentParser(description='Monitor mining progress')
    parser.add_argument('--hdf5-dir', default='data_mine/permanent_data/hdf5',
                       help='HDF5 directory to monitor')
    parser.add_argument('--log-file', default='mining_rgb_fixed.log',
                       help='Mining log file')
    parser.add_argument('--interval', type=int, default=30,
                       help='Update interval in seconds (default: 30)')

    args = parser.parse_args()

    print("Starting mining monitor...")
    print(f"HDF5 directory: {args.hdf5_dir}")
    print(f"Update interval: {args.interval}s")
    print()
    time.sleep(2)

    try:
        while True:
            print_dashboard(args.hdf5_dir, args.log_file)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")


if __name__ == '__main__':
    main()
