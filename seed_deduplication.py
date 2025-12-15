"""
Seed deduplication database with existing HDF5 files
This prevents re-downloading videos we already have
"""

from pathlib import Path
from deduplication_manager import DeduplicationManager


def seed_from_existing_files():
    """Seed deduplication manager from existing HDF5 files"""

    dedup = DeduplicationManager()
    hdf5_dir = Path('data_mine/permanent_data/hdf5')

    # Get all RGB files (>1MB)
    rgb_files = [f for f in hdf5_dir.glob('*.hdf5')
                 if f.stat().st_size > 1_000_000]

    print(f"🌱 Seeding deduplication database...")
    print(f"Found {len(rgb_files)} existing RGB files")
    print()

    for hdf5_file in rgb_files:
        # Use filename as title (we don't have original URL)
        # This will at least prevent title-based duplicates
        video_title = hdf5_file.stem  # filename without .hdf5

        # Create a synthetic URL based on title hash
        # (we don't have the original URL, but this prevents re-processing)
        import hashlib
        url_hash = hashlib.md5(video_title.encode()).hexdigest()
        synthetic_url = f"https://youtube.com/watch?v=LOCAL_{url_hash}"

        # Mark as processed
        dedup.mark_processed(synthetic_url, video_title)

        print(f"  ✅ Registered: {video_title[:60]}...")

    print()
    print(f"✅ Seeded {len(rgb_files)} files into deduplication database")
    dedup.print_stats()


if __name__ == "__main__":
    seed_from_existing_files()
