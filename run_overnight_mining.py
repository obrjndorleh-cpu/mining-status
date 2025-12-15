"""
24/7 DATA MINING OPERATION

Runs continuously, mining YouTube for high-quality robot training data.
Like crypto mining, but for robot training data!

Features:
- Runs indefinitely (overnight/24/7)
- Cycles through action categories
- Automatic quality filtering
- Progress tracking
- Error handling (keeps running even if individual videos fail)
- MongoDB integration for structured data storage
"""

import time
import json
from pathlib import Path
from datetime import datetime
from auto_dataset_curator import AutoDatasetCurator
import subprocess


class DataMiningOperation:
    """
    24/7 Data Mining Operation for Robot Training Data
    """

    def __init__(self, output_dir='data_mine', quality_threshold=70.0):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.curator = AutoDatasetCurator(
            output_dir=str(self.output_dir),
            quality_threshold=quality_threshold
        )

        self.mining_log = self.output_dir / 'mining_log.json'
        self.load_mining_stats()

        # Action categories to mine
        self.ACTION_CATEGORIES = {
            'opening': [
                "opening refrigerator side view",
                "opening cabinet door tutorial",
                "opening drawer demonstration",
                "opening bottle cap",
                "opening door handle",
            ],
            'closing': [
                "closing refrigerator door",
                "closing cabinet gently",
                "closing drawer demonstration",
                "closing door tutorial",
            ],
            'pouring': [
                "pouring water into glass",
                "pouring liquid demonstration",
                "barista pouring technique",
                "careful pouring tutorial",
            ],
            'grasping': [
                "picking up object demonstration",
                "grasping technique physical therapy",
                "ergonomic picking tutorial",
                "hand grip demonstration",
            ],
            'placing': [
                "placing object carefully",
                "setting down demonstration",
                "careful placement tutorial",
            ],
            'pushing': [
                "pushing button demonstration",
                "pushing door open",
                "pressing switch tutorial",
            ],
            'pulling': [
                "pulling door handle",
                "pulling drawer demonstration",
                "pulling lever tutorial",
            ],
            'twisting': [
                "twisting bottle cap",
                "turning knob demonstration",
                "rotating object tutorial",
            ],
            'sliding': [
                "sliding door demonstration",
                "sliding object tutorial",
            ],
            'lifting': [
                "lifting object ergonomic",
                "safe lifting demonstration",
                "proper lifting technique",
            ]
        }

    def load_mining_stats(self):
        """Load mining operation statistics"""
        if self.mining_log.exists():
            with open(self.mining_log, 'r') as f:
                self.stats = json.load(f)
        else:
            self.stats = {
                'started_at': datetime.now().isoformat(),
                'total_runtime_hours': 0.0,
                'videos_mined': 0,
                'videos_accepted': 0,
                'videos_rejected': 0,
                'acceptance_rate': 0.0,
                'mining_sessions': [],
                'last_category': None,
                'last_query_index': 0
            }

    def save_mining_stats(self):
        """Save mining statistics"""
        with open(self.mining_log, 'w') as f:
            json.dump(self.stats, f, indent=2)

    def mine_continuously(self, videos_per_query=10, max_duration=20, sleep_between_queries=30,
                         auto_process=False, delete_after_extract=False):
        """
        Run continuous mining operation

        Args:
            videos_per_query: How many candidate videos to download per query
            max_duration: Maximum video duration (seconds)
            sleep_between_queries: Sleep time between queries (seconds)
            auto_process: Automatically process videos through pipeline
            delete_after_extract: Delete videos after extracting data (saves space!)
        """
        print("="*70)
        print("⛏️  24/7 DATA MINING OPERATION STARTED")
        print("="*70)
        print(f"Output directory: {self.output_dir}")
        print(f"Quality threshold: {self.curator.quality_threshold}/100")
        print(f"Videos per query: {videos_per_query}")
        print(f"Action categories: {len(self.ACTION_CATEGORIES)}")
        print(f"Auto-process: {'YES' if auto_process else 'NO'}")
        print(f"Delete after extract: {'YES ♻️' if delete_after_extract else 'NO'}")
        print()
        if delete_after_extract:
            print("💡 INFINITE MINING MODE:")
            print("   Videos deleted after data extraction = Never run out of space!")
            print()
        print("💡 TIP: This will run forever. Press Ctrl+C to stop.")
        print("="*70)
        print()

        # Initialize extract-and-delete pipeline if needed
        extract_pipeline = None
        if delete_after_extract:
            from extract_and_delete_pipeline import ExtractAndDeletePipeline
            extract_pipeline = ExtractAndDeletePipeline(
                data_dir=str(self.output_dir / 'permanent_data')
            )

        session_start = time.time()
        session_stats = {
            'started_at': datetime.now().isoformat(),
            'videos_mined': 0,
            'videos_accepted': 0,
            'queries_executed': 0
        }

        try:
            while True:
                # Cycle through all action categories
                for category_name, queries in self.ACTION_CATEGORIES.items():
                    print(f"\n{'='*70}")
                    print(f"⛏️  MINING CATEGORY: {category_name.upper()}")
                    print(f"{'='*70}\n")

                    for query_idx, query in enumerate(queries):
                        # Skip if we already processed this in last session
                        if (self.stats['last_category'] == category_name and
                            query_idx < self.stats['last_query_index']):
                            continue

                        print(f"\n🔍 Query {query_idx + 1}/{len(queries)}: {query}")
                        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                        try:
                            # Mine this query
                            accepted = self.curator.curate_from_search(
                                query,
                                max_videos=videos_per_query,
                                max_duration=max_duration
                            )

                            # Update stats
                            session_stats['videos_mined'] += videos_per_query
                            session_stats['videos_accepted'] += len(accepted)
                            session_stats['queries_executed'] += 1

                            self.stats['videos_mined'] += videos_per_query
                            self.stats['videos_accepted'] += len(accepted)
                            self.stats['last_category'] = category_name
                            self.stats['last_query_index'] = query_idx

                            # Auto-process and optionally delete videos
                            if auto_process and accepted:
                                print(f"\n⚙️  AUTO-PROCESSING {len(accepted)} accepted videos...")
                                for video_info in accepted:
                                    video_path = Path(video_info['path'])

                                    if delete_after_extract and extract_pipeline:
                                        # Extract data and delete video
                                        print(f"\n♻️  Processing with delete: {video_path.name}")
                                        extract_pipeline.process_and_delete(video_path)
                                    else:
                                        # Just process, keep video
                                        print(f"\n⚙️  Processing: {video_path.name}")
                                        import subprocess
                                        subprocess.run([
                                            'python', 'unified_pipeline.py',
                                            str(video_path),
                                            str(self.output_dir / 'robot_data' / f"{video_path.stem}.mp4"),
                                            '--enable-vision'
                                        ], timeout=300)

                                print(f"✅ Processed {len(accepted)} videos")

                            # Calculate rates
                            if self.stats['videos_mined'] > 0:
                                self.stats['acceptance_rate'] = (
                                    self.stats['videos_accepted'] / self.stats['videos_mined']
                                )

                            # Update runtime
                            runtime_hours = (time.time() - session_start) / 3600
                            self.stats['total_runtime_hours'] += runtime_hours

                            # Save progress
                            self.save_mining_stats()

                            # Print progress
                            self.print_progress(session_stats, runtime_hours)

                        except Exception as e:
                            print(f"\n⚠️  Error mining query '{query}': {e}")
                            print("   Continuing to next query...\n")

                        # Sleep between queries to avoid rate limiting
                        if query_idx < len(queries) - 1:
                            print(f"\n⏳ Sleeping {sleep_between_queries}s before next query...")
                            time.sleep(sleep_between_queries)

                    # Reset for next category
                    self.stats['last_query_index'] = 0

                # Completed full cycle
                print("\n" + "="*70)
                print("✅ COMPLETED FULL CYCLE OF ALL CATEGORIES")
                print("="*70)
                print("🔄 Starting next cycle in 60 seconds...")
                print("="*70 + "\n")
                time.sleep(60)

                # Reset category tracking for new cycle
                self.stats['last_category'] = None
                self.stats['last_query_index'] = 0

        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("⛔ MINING OPERATION STOPPED BY USER")
            print("="*70)

            # Save final session stats
            session_stats['ended_at'] = datetime.now().isoformat()
            session_stats['runtime_hours'] = (time.time() - session_start) / 3600
            self.stats['mining_sessions'].append(session_stats)
            self.save_mining_stats()

            # Print final summary
            self.print_final_summary()

    def print_progress(self, session_stats, runtime_hours):
        """Print mining progress"""
        print()
        print("📊 CURRENT SESSION STATS:")
        print(f"   Runtime: {runtime_hours:.2f} hours")
        print(f"   Videos mined: {session_stats['videos_mined']}")
        print(f"   Videos accepted: {session_stats['videos_accepted']}")
        print(f"   Queries executed: {session_stats['queries_executed']}")
        if session_stats['videos_mined'] > 0:
            rate = session_stats['videos_accepted'] / session_stats['videos_mined']
            print(f"   Acceptance rate: {rate:.1%}")
        print()
        print("📊 TOTAL STATS (ALL TIME):")
        print(f"   Total runtime: {self.stats['total_runtime_hours']:.2f} hours")
        print(f"   Total videos mined: {self.stats['videos_mined']}")
        print(f"   Total accepted: {self.stats['videos_accepted']}")
        print(f"   Overall acceptance rate: {self.stats['acceptance_rate']:.1%}")

    def print_final_summary(self):
        """Print final mining summary"""
        print()
        print("📊 FINAL MINING SUMMARY")
        print("="*70)
        print(f"Total runtime: {self.stats['total_runtime_hours']:.2f} hours")
        print(f"Total videos mined: {self.stats['videos_mined']}")
        print(f"Total accepted: {self.stats['videos_accepted']}")
        print(f"Overall acceptance rate: {self.stats['acceptance_rate']:.1%}")
        print()
        print(f"Mining sessions: {len(self.stats['mining_sessions'])}")
        print()
        print(f"📁 Data stored in: {self.output_dir}")
        print(f"📊 Stats saved to: {self.mining_log}")
        print("="*70)


def main():
    """
    Start the mining operation
    """
    import argparse

    parser = argparse.ArgumentParser(description='24/7 Data Mining for Robot Training Data')
    parser.add_argument('--output-dir', default='data_mine',
                       help='Output directory (default: data_mine)')
    parser.add_argument('--threshold', type=float, default=70.0,
                       help='Quality threshold (default: 70)')
    parser.add_argument('--videos-per-query', type=int, default=10,
                       help='Videos to download per query (default: 10)')
    parser.add_argument('--max-duration', type=int, default=20,
                       help='Maximum video duration (default: 20s)')
    parser.add_argument('--sleep', type=int, default=30,
                       help='Sleep between queries in seconds (default: 30)')
    parser.add_argument('--auto-process', action='store_true',
                       help='Automatically process videos through pipeline')
    parser.add_argument('--delete-after-extract', action='store_true',
                       help='Delete videos after extracting data (INFINITE MINING MODE)')

    args = parser.parse_args()

    # Create mining operation
    miner = DataMiningOperation(
        output_dir=args.output_dir,
        quality_threshold=args.threshold
    )

    # Start mining!
    miner.mine_continuously(
        videos_per_query=args.videos_per_query,
        max_duration=args.max_duration,
        sleep_between_queries=args.sleep,
        auto_process=args.auto_process,
        delete_after_extract=args.delete_after_extract
    )


if __name__ == '__main__':
    main()
