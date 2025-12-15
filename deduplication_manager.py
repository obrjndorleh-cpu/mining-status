"""
DEDUPLICATION MANAGER
Prevents mining from processing the same videos multiple times

Tracks:
1. Video URLs that have been processed
2. HDF5 files that exist
3. Progress metrics to detect stuck state

Author: Engineering Partner
Date: 2025-12-14
Purpose: Fix infinite loop bug - ensure unique demos only
"""

import json
from pathlib import Path
from datetime import datetime
import hashlib


class DeduplicationManager:
    """
    Manages deduplication across mining sessions

    Two-layer protection:
    1. URL tracking - persistent across sessions
    2. HDF5 existence check - fast runtime check

    Both must pass to process a video.
    """

    def __init__(self,
                 processed_file='mining_processed_videos.json',
                 hdf5_dir='data_mine/permanent_data/hdf5'):
        """
        Initialize deduplication manager

        Args:
            processed_file: JSON file tracking processed video URLs
            hdf5_dir: Directory containing HDF5 output files
        """
        self.processed_file = Path(processed_file)
        self.hdf5_dir = Path(hdf5_dir)
        self.hdf5_dir.mkdir(parents=True, exist_ok=True)

        # Load processed videos
        self.processed_urls = self._load_processed()
        self.processed_titles = self._load_processed_titles()

        # Progress tracking
        self.session_start = datetime.now()
        self.initial_count = self._count_rgb_files()

    def _load_processed(self):
        """Load set of processed video URLs"""
        if self.processed_file.exists():
            try:
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('urls', []))
            except Exception as e:
                print(f"⚠️  Could not load processed URLs: {e}")
                return set()
        return set()

    def _load_processed_titles(self):
        """Load set of processed video titles (normalized)"""
        if self.processed_file.exists():
            try:
                with open(self.processed_file, 'r') as f:
                    data = json.load(f)
                    return set(data.get('titles', []))
            except Exception as e:
                return set()
        return set()

    def _save_processed(self):
        """Save processed videos to disk"""
        data = {
            'urls': list(self.processed_urls),
            'titles': list(self.processed_titles),
            'last_updated': datetime.now().isoformat(),
            'total_processed': len(self.processed_urls)
        }

        with open(self.processed_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _normalize_title(self, title):
        """Normalize video title for comparison"""
        # Remove common variations
        normalized = title.lower()
        normalized = normalized.replace(' ', '')
        normalized = normalized.replace('_', '')
        normalized = normalized.replace('-', '')
        # Remove common suffixes
        for suffix in ['.mp4', '.avi', '.mov', '.mkv']:
            normalized = normalized.replace(suffix.lower(), '')
        return normalized

    def _count_rgb_files(self):
        """Count RGB files (>1MB) in HDF5 directory"""
        if not self.hdf5_dir.exists():
            return 0

        rgb_files = [f for f in self.hdf5_dir.glob('*.hdf5')
                     if f.stat().st_size > 1_000_000]
        return len(rgb_files)

    def _hdf5_exists(self, video_name):
        """Check if HDF5 file already exists for this video"""
        # Try exact match
        hdf5_path = self.hdf5_dir / f"{video_name}.hdf5"
        if hdf5_path.exists() and hdf5_path.stat().st_size > 1_000_000:
            return True

        # Try normalized match (in case of slight name variations)
        normalized = self._normalize_title(video_name)
        for existing_file in self.hdf5_dir.glob('*.hdf5'):
            if existing_file.stat().st_size > 1_000_000:
                existing_normalized = self._normalize_title(existing_file.stem)
                if normalized == existing_normalized:
                    return True

        return False

    def should_process(self, video_url, video_title):
        """
        Determine if video should be processed

        Args:
            video_url: YouTube video URL
            video_title: Video title/filename

        Returns:
            tuple: (should_process: bool, reason: str)
        """
        # Check 1: Already processed by URL?
        if video_url in self.processed_urls:
            return False, f"Already processed (URL tracked)"

        # Check 2: Already processed by title?
        normalized_title = self._normalize_title(video_title)
        if normalized_title in self.processed_titles:
            return False, f"Already processed (title match)"

        # Check 3: HDF5 file exists?
        if self._hdf5_exists(video_title):
            # Add to tracking even if we didn't process it
            # (might have been created manually)
            self.processed_urls.add(video_url)
            self.processed_titles.add(normalized_title)
            self._save_processed()
            return False, f"HDF5 already exists"

        # All checks passed - safe to process
        return True, "New video"

    def mark_processed(self, video_url, video_title):
        """
        Mark video as processed

        Args:
            video_url: YouTube video URL
            video_title: Video title/filename
        """
        self.processed_urls.add(video_url)
        self.processed_titles.add(self._normalize_title(video_title))
        self._save_processed()

    def get_progress_stats(self):
        """
        Get progress statistics

        Returns:
            dict: Progress metrics
        """
        current_count = self._count_rgb_files()
        elapsed = (datetime.now() - self.session_start).total_seconds() / 3600

        new_demos = current_count - self.initial_count
        rate = new_demos / elapsed if elapsed > 0 else 0

        return {
            'initial_count': self.initial_count,
            'current_count': current_count,
            'new_demos': new_demos,
            'elapsed_hours': elapsed,
            'rate_per_hour': rate,
            'total_tracked': len(self.processed_urls),
            'is_making_progress': new_demos > 0
        }

    def check_stuck(self, min_hours=2):
        """
        Check if mining appears stuck

        Args:
            min_hours: Minimum hours before checking

        Returns:
            tuple: (is_stuck: bool, message: str)
        """
        stats = self.get_progress_stats()

        if stats['elapsed_hours'] < min_hours:
            return False, "Not enough time elapsed to determine"

        if stats['new_demos'] == 0:
            return True, f"No new demos in {stats['elapsed_hours']:.1f} hours - possibly stuck"

        if stats['rate_per_hour'] < 0.5:
            return True, f"Very slow progress: {stats['rate_per_hour']:.2f} demos/hour"

        return False, f"Making progress: {stats['new_demos']} demos in {stats['elapsed_hours']:.1f} hours"

    def print_stats(self):
        """Print current statistics"""
        stats = self.get_progress_stats()

        print("\n" + "="*70)
        print("📊 DEDUPLICATION & PROGRESS STATS")
        print("="*70)
        print(f"URLs tracked: {stats['total_tracked']}")
        print(f"RGB files at start: {stats['initial_count']}")
        print(f"RGB files now: {stats['current_count']}")
        print(f"New demos created: {stats['new_demos']}")
        print(f"Elapsed time: {stats['elapsed_hours']:.2f} hours")

        if stats['elapsed_hours'] > 0:
            print(f"Current rate: {stats['rate_per_hour']:.2f} demos/hour")

            is_stuck, message = self.check_stuck()
            if is_stuck:
                print(f"\n⚠️  WARNING: {message}")
            else:
                print(f"\n✅ {message}")

        print("="*70 + "\n")


if __name__ == "__main__":
    # Test deduplication manager
    dedup = DeduplicationManager()

    # Test cases
    test_videos = [
        ("https://youtube.com/watch?v=abc123", "Test Video.mp4"),
        ("https://youtube.com/watch?v=xyz789", "Another Video.mp4"),
        ("https://youtube.com/watch?v=abc123", "Test Video.mp4"),  # Duplicate URL
        ("https://youtube.com/watch?v=different", "Test_Video.mp4"),  # Duplicate title (normalized)
    ]

    print("Testing deduplication...")
    for url, title in test_videos:
        should_process, reason = dedup.should_process(url, title)
        print(f"{title}: {should_process} - {reason}")

        if should_process:
            dedup.mark_processed(url, title)

    dedup.print_stats()
