"""
IMAGE DATA MINING OPERATION
24/7 autonomous image mining for robot training data

Similar to video mining but for images:
1. Download images from Unsplash/Pexels
2. Score quality (0-100)
3. Accept high-quality images (≥70)
4. Extract pose/hand data
5. Delete images after extraction
6. Upload to cloud

Usage:
    python run_image_mining.py --auto-process --delete-after-extract --threshold 70
"""

import time
from pathlib import Path
from datetime import datetime
import json
from image_downloader import ImageDownloader
from image_quality_scorer import ImageQualityScorer
from image_extraction_pipeline import ImageExtractionPipeline


class ImageMiningOperation:
    """Autonomous 24/7 image data mining"""

    def __init__(self, output_dir='data_mine_images', quality_threshold=70.0):
        """
        Args:
            output_dir: Base output directory
            quality_threshold: Minimum quality score (0-100)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        # Subdirectories
        self.images_dir = self.output_dir / 'images'
        self.data_dir = self.output_dir / 'permanent_data'
        self.hdf5_dir = self.data_dir / 'hdf5'
        self.json_dir = self.data_dir / 'json'

        self.images_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        self.hdf5_dir.mkdir(exist_ok=True)
        self.json_dir.mkdir(exist_ok=True)

        # Initialize components
        self.downloader = ImageDownloader(output_dir=self.images_dir)
        self.scorer = ImageQualityScorer()
        self.extractor = ImageExtractionPipeline()

        self.quality_threshold = quality_threshold

        # Action categories for robot training
        self.ACTION_CATEGORIES = {
            'REACHING': [
                'person reaching for object',
                'hand reaching towards',
                'arm extending to grab',
                'reaching up high',
                'reaching down low'
            ],
            'GRASPING': [
                'hand grasping object',
                'fingers holding item',
                'grip strength demonstration',
                'picking up object',
                'hand gripping tool'
            ],
            'LIFTING': [
                'person lifting object',
                'hands lifting heavy item',
                'weightlifting pose',
                'picking up box',
                'raising arms with weight'
            ],
            'PUSHING': [
                'person pushing door',
                'hands pushing object',
                'push motion',
                'pressing button',
                'pushing cart'
            ],
            'PULLING': [
                'person pulling rope',
                'hand pulling drawer',
                'pull motion',
                'opening door by pulling',
                'tug of war'
            ],
            'WAVING': [
                'person waving hand',
                'hand wave gesture',
                'greeting wave',
                'goodbye wave',
                'waving hello'
            ],
            'POINTING': [
                'person pointing finger',
                'hand pointing at',
                'index finger pointing',
                'pointing gesture',
                'directional pointing'
            ],
            'HOLDING': [
                'person holding object',
                'hands holding item',
                'carrying object',
                'holding cup',
                'holding phone'
            ]
        }

        self.stats = {
            'images_downloaded': 0,
            'images_accepted': 0,
            'images_rejected': 0,
            'images_processed': 0,
            'images_deleted': 0,
            'space_saved_mb': 0
        }

    def mine_continuously(self, images_per_query=30, auto_process=False,
                         delete_after_extract=False, sleep_between_queries=30):
        """
        Run continuous image mining

        Args:
            images_per_query: Images to download per search
            auto_process: Automatically extract data from accepted images
            delete_after_extract: Delete images after extraction
            sleep_between_queries: Seconds between queries
        """
        print("="*70)
        print("📸 IMAGE DATA MINING OPERATION STARTED")
        print("="*70)
        print(f"Output directory: {self.output_dir}")
        print(f"Quality threshold: {self.quality_threshold}/100")
        print(f"Images per query: {images_per_query}")
        print(f"Action categories: {len(self.ACTION_CATEGORIES)}")
        print(f"Auto-process: {'YES' if auto_process else 'NO'}")
        print(f"Delete after extract: {'YES ♻️' if delete_after_extract else 'NO'}")
        print()

        if delete_after_extract:
            print("💡 INFINITE MINING MODE (Images):")
            print("   Images deleted after data extraction = Never run out of space!")
            print()

        print("💡 TIP: Press Ctrl+C to stop.")
        print("="*70)
        print()

        try:
            while True:
                # Iterate through action categories
                for category_name, queries in self.ACTION_CATEGORIES.items():
                    print(f"\n{'='*70}")
                    print(f"📸 MINING CATEGORY: {category_name}")
                    print(f"{'='*70}\n")

                    for query_idx, query in enumerate(queries):
                        print(f"\n🔍 Query {query_idx + 1}/{len(queries)}: {query}")
                        print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                        try:
                            # Download images
                            downloaded = self.downloader.search_and_download(
                                query,
                                max_images=images_per_query
                            )

                            if not downloaded:
                                print("⚠️  No images downloaded")
                                continue

                            self.stats['images_downloaded'] += len(downloaded)

                            # Score images
                            print(f"\n🔍 QUALITY SCORING")
                            print("-"*70)

                            accepted = []
                            rejected = []

                            for img_path in downloaded:
                                img_path = Path(img_path)
                                print(f"\nScoring: {img_path.name}")

                                result = self.scorer.score_image(img_path)
                                score = result['score']

                                if score >= self.quality_threshold:
                                    print(f"   ✅ ACCEPTED - Score: {score:.1f}/100 ({result['rating']})")
                                    accepted.append({
                                        'path': str(img_path),
                                        'score': score,
                                        'result': result
                                    })
                                    self.stats['images_accepted'] += 1
                                else:
                                    print(f"   ❌ REJECTED - Score: {score:.1f}/100 ({result['rating']})")
                                    rejected.append({
                                        'path': str(img_path),
                                        'score': score
                                    })
                                    self.stats['images_rejected'] += 1

                            # Summary
                            print(f"\n{'='*70}")
                            print("SCORING SUMMARY")
                            print(f"{'='*70}")
                            print(f"Images scored: {len(downloaded)}")
                            print(f"Accepted: {len(accepted)} ({len(accepted)/len(downloaded)*100:.1f}%)")
                            print(f"Rejected: {len(rejected)} ({len(rejected)/len(downloaded)*100:.1f}%)")
                            print()

                            # Auto-process accepted images
                            if auto_process and accepted:
                                print(f"\n⚙️  AUTO-PROCESSING {len(accepted)} accepted images...")

                                for img_info in accepted:
                                    img_path = Path(img_info['path'])

                                    print(f"\n♻️  Processing: {img_path.name}")

                                    # Extract data
                                    hdf5_output = self.hdf5_dir / f"{img_path.stem}.hdf5"
                                    result = self.extractor.process_image(img_path, hdf5_output)

                                    if result['success']:
                                        self.stats['images_processed'] += 1

                                        # Move JSON to permanent storage
                                        json_src = Path(result['json_file'])
                                        json_dst = self.json_dir / json_src.name
                                        json_src.rename(json_dst)

                                        # Delete image if requested
                                        if delete_after_extract:
                                            img_size_mb = img_path.stat().st_size / (1024 * 1024)
                                            img_path.unlink()
                                            print(f"   🗑️  Deleted image: {img_path.name}")
                                            self.stats['images_deleted'] += 1
                                            self.stats['space_saved_mb'] += img_size_mb

                                    else:
                                        print(f"   ❌ Extraction failed: {result['error']}")

                                print(f"\n✅ Processed {len(accepted)} images")

                            # Sleep between queries
                            if query_idx < len(queries) - 1:
                                print(f"\n⏳ Sleeping {sleep_between_queries}s before next query...")
                                time.sleep(sleep_between_queries)

                        except Exception as e:
                            print(f"\n⚠️  Error: {e}")
                            print("   Continuing to next query...")

                # Completed full cycle
                print("\n" + "="*70)
                print("✅ COMPLETED FULL CYCLE")
                print("="*70)
                print(f"Images downloaded: {self.stats['images_downloaded']}")
                print(f"Images accepted: {self.stats['images_accepted']}")
                print(f"Images processed: {self.stats['images_processed']}")
                print(f"Images deleted: {self.stats['images_deleted']}")
                print(f"Space saved: {self.stats['space_saved_mb']:.1f} MB")
                print("="*70)
                print("\n🔄 Starting next cycle in 60 seconds...")
                time.sleep(60)

        except KeyboardInterrupt:
            print("\n\n" + "="*70)
            print("⛔ IMAGE MINING STOPPED")
            print("="*70)
            print("\nFinal Stats:")
            print(f"  Images downloaded: {self.stats['images_downloaded']}")
            print(f"  Images accepted: {self.stats['images_accepted']}")
            print(f"  Images processed: {self.stats['images_processed']}")
            print(f"  Images deleted: {self.stats['images_deleted']}")
            print(f"  Space saved: {self.stats['space_saved_mb']:.1f} MB")
            print("="*70)


def main():
    """Run image mining operation"""
    import argparse

    parser = argparse.ArgumentParser(description='24/7 Image Data Mining')
    parser.add_argument('--output-dir', default='data_mine_images',
                       help='Output directory')
    parser.add_argument('--threshold', type=float, default=70.0,
                       help='Quality threshold (0-100)')
    parser.add_argument('--images-per-query', type=int, default=30,
                       help='Images per search query')
    parser.add_argument('--sleep', type=int, default=30,
                       help='Sleep between queries (seconds)')
    parser.add_argument('--auto-process', action='store_true',
                       help='Automatically process accepted images')
    parser.add_argument('--delete-after-extract', action='store_true',
                       help='Delete images after extraction (INFINITE MODE)')

    args = parser.parse_args()

    miner = ImageMiningOperation(
        output_dir=args.output_dir,
        quality_threshold=args.threshold
    )

    miner.mine_continuously(
        images_per_query=args.images_per_query,
        auto_process=args.auto_process,
        delete_after_extract=args.delete_after_extract,
        sleep_between_queries=args.sleep
    )


if __name__ == '__main__':
    main()
