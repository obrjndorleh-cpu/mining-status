"""
AUTOMATED DATASET CURATOR

Searches YouTube, downloads videos, scores quality, and keeps only the best ones.
This is the "algorithm" that builds a curated robot training dataset from YouTube's database.

Workflow:
1. Search YouTube with keywords
2. Download candidate videos
3. Quick quality analysis
4. Keep only high-quality videos (>threshold)
5. Process good videos through full pipeline
6. Export to HDF5 dataset
"""

import json
from pathlib import Path
from youtube_downloader import YouTubeDownloader
from video_quality_scorer import VideoQualityScorer
import subprocess
import time


class AutoDatasetCurator:
    """
    Automatically curate high-quality robot training dataset from YouTube
    """

    def __init__(self, output_dir='curated_dataset', quality_threshold=70.0):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.videos_dir = self.output_dir / 'videos'
        self.videos_dir.mkdir(exist_ok=True)

        self.data_dir = self.output_dir / 'robot_data'
        self.data_dir.mkdir(exist_ok=True)

        self.quality_threshold = quality_threshold

        self.downloader = YouTubeDownloader(output_dir=str(self.videos_dir))
        self.scorer = VideoQualityScorer()

        self.results_file = self.output_dir / 'curation_results.json'
        self.load_results()

    def load_results(self):
        """Load previous curation results"""
        if self.results_file.exists():
            with open(self.results_file, 'r') as f:
                self.results = json.load(f)
        else:
            self.results = {
                'search_queries': [],
                'videos_analyzed': 0,
                'videos_accepted': 0,
                'videos_rejected': 0,
                'acceptance_rate': 0.0,
                'quality_scores': [],
                'curated_videos': []
            }

    def save_results(self):
        """Save curation results"""
        # Update statistics
        self.results['acceptance_rate'] = (
            self.results['videos_accepted'] / self.results['videos_analyzed']
            if self.results['videos_analyzed'] > 0 else 0.0
        )

        with open(self.results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

    def curate_from_search(self, search_query, max_videos=10, max_duration=30):
        """
        Search YouTube, download, and curate videos

        Args:
            search_query: YouTube search query
            max_videos: Maximum videos to download
            max_duration: Maximum video duration (seconds)

        Returns:
            List of accepted high-quality videos
        """
        print("="*70)
        print("AUTOMATED DATASET CURATION")
        print("="*70)
        print(f"Search query: {search_query}")
        print(f"Max videos to analyze: {max_videos}")
        print(f"Quality threshold: {self.quality_threshold}/100")
        print()

        # Record search query
        if search_query not in self.results['search_queries']:
            self.results['search_queries'].append(search_query)

        # Search and download videos
        print("📥 STAGE 1: DOWNLOADING CANDIDATE VIDEOS")
        print("-"*70)

        downloaded_videos = self.downloader.search_and_download(
            search_query,
            max_results=max_videos,
            max_duration=max_duration
        )

        if not downloaded_videos:
            print("⚠️  No videos downloaded")
            return []

        print(f"✅ Downloaded {len(downloaded_videos)} candidate videos")
        print()

        # Quality scoring
        print("🔍 STAGE 2: QUALITY ANALYSIS")
        print("-"*70)

        accepted_videos = []
        rejected_videos = []

        for video_path in downloaded_videos:
            print(f"\nAnalyzing: {Path(video_path).name}")

            # Score video
            quality_result = self.scorer.score_video(video_path)
            score = quality_result['score']

            # Record score
            self.results['quality_scores'].append({
                'video': str(Path(video_path).name),
                'score': score,
                'query': search_query
            })
            self.results['videos_analyzed'] += 1

            # Decision
            if score >= self.quality_threshold:
                print(f"   ✅ ACCEPTED - Score: {score:.1f}/100 ({quality_result['rating']})")
                accepted_videos.append({
                    'path': str(video_path),
                    'score': score,
                    'query': search_query,
                    'quality_report': quality_result
                })
                self.results['videos_accepted'] += 1
                self.results['curated_videos'].append({
                    'video': str(Path(video_path).name),
                    'score': score,
                    'query': search_query
                })
            else:
                print(f"   ❌ REJECTED - Score: {score:.1f}/100 ({quality_result['rating']})")
                rejected_videos.append({
                    'path': str(video_path),
                    'score': score,
                    'reason': quality_result['recommendation']
                })
                self.results['videos_rejected'] += 1

        # Save results
        self.save_results()

        # Summary
        print()
        print("="*70)
        print("CURATION SUMMARY")
        print("="*70)
        print(f"Videos analyzed: {len(downloaded_videos)}")
        print(f"Accepted: {len(accepted_videos)} ({len(accepted_videos)/len(downloaded_videos)*100:.1f}%)")
        print(f"Rejected: {len(rejected_videos)} ({len(rejected_videos)/len(downloaded_videos)*100:.1f}%)")
        print()

        if accepted_videos:
            print("✅ ACCEPTED VIDEOS:")
            for v in sorted(accepted_videos, key=lambda x: x['score'], reverse=True):
                print(f"   🌟 {v['score']:.1f}/100 - {Path(v['path']).name}")

        if rejected_videos:
            print()
            print("❌ REJECTED VIDEOS:")
            for v in sorted(rejected_videos, key=lambda x: x['score'], reverse=True):
                print(f"   ❌ {v['score']:.1f}/100 - {Path(v['path']).name}")

        print("="*70)
        print()

        return accepted_videos

    def process_curated_videos(self, accepted_videos):
        """
        Process accepted videos through full pipeline

        Args:
            accepted_videos: List of accepted video dicts

        Returns:
            List of processed video results
        """
        if not accepted_videos:
            print("No videos to process")
            return []

        print("="*70)
        print("STAGE 3: PROCESSING CURATED VIDEOS")
        print("="*70)
        print(f"Processing {len(accepted_videos)} high-quality videos through full pipeline")
        print()

        processed_results = []

        for i, video_info in enumerate(accepted_videos, 1):
            video_path = video_info['path']
            video_name = Path(video_path).stem
            output_name = self.data_dir / video_name

            print(f"[{i}/{len(accepted_videos)}] Processing: {Path(video_path).name}")
            print(f"   Quality score: {video_info['score']:.1f}/100")

            try:
                # Run unified pipeline
                cmd = [
                    'python', 'unified_pipeline.py',
                    str(video_path),
                    str(output_name) + '.mp4',
                    '--enable-vision'
                ]

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout per video
                )

                if result.returncode == 0:
                    print(f"   ✅ Successfully processed")
                    processed_results.append({
                        'video': str(Path(video_path).name),
                        'quality_score': video_info['score'],
                        'processed': True,
                        'output_dir': str(self.data_dir)
                    })
                else:
                    print(f"   ⚠️  Processing failed: {result.stderr[:200]}")
                    processed_results.append({
                        'video': str(Path(video_path).name),
                        'quality_score': video_info['score'],
                        'processed': False,
                        'error': result.stderr[:500]
                    })

            except subprocess.TimeoutExpired:
                print(f"   ⏱️  Processing timeout (>5 minutes)")
                processed_results.append({
                    'video': str(Path(video_path).name),
                    'quality_score': video_info['score'],
                    'processed': False,
                    'error': 'Timeout'
                })
            except Exception as e:
                print(f"   ❌ Error: {e}")
                processed_results.append({
                    'video': str(Path(video_path).name),
                    'quality_score': video_info['score'],
                    'processed': False,
                    'error': str(e)
                })

            print()

        # Summary
        successful = sum(1 for r in processed_results if r['processed'])
        print("="*70)
        print("PROCESSING SUMMARY")
        print("="*70)
        print(f"Videos processed: {len(processed_results)}")
        print(f"Successful: {successful}")
        print(f"Failed: {len(processed_results) - successful}")
        print("="*70)

        return processed_results

    def print_statistics(self):
        """Print overall curation statistics"""
        print()
        print("="*70)
        print("DATASET CURATION STATISTICS")
        print("="*70)
        print(f"Total videos analyzed: {self.results['videos_analyzed']}")
        print(f"Accepted: {self.results['videos_accepted']} ({self.results['acceptance_rate']:.1%})")
        print(f"Rejected: {self.results['videos_rejected']}")
        print()

        if self.results['quality_scores']:
            scores = [s['score'] for s in self.results['quality_scores']]
            print(f"Average quality score: {sum(scores)/len(scores):.1f}/100")
            print(f"Highest score: {max(scores):.1f}/100")
            print(f"Lowest score: {min(scores):.1f}/100")

        print()
        print(f"Search queries used: {len(self.results['search_queries'])}")
        for query in self.results['search_queries']:
            count = sum(1 for v in self.results['curated_videos'] if v['query'] == query)
            print(f"   - '{query}': {count} videos")

        print("="*70)


def main():
    """
    Run automated dataset curation
    """
    import argparse

    parser = argparse.ArgumentParser(description='Automatically curate robot training dataset from YouTube')
    parser.add_argument('--queries', nargs='+', required=True,
                       help='Search queries (e.g., "opening refrigerator tutorial")')
    parser.add_argument('--max-per-query', type=int, default=10,
                       help='Maximum videos per query (default: 10)')
    parser.add_argument('--max-duration', type=int, default=30,
                       help='Maximum video duration (default: 30s)')
    parser.add_argument('--threshold', type=float, default=70.0,
                       help='Quality threshold (default: 70)')
    parser.add_argument('--output-dir', default='curated_dataset',
                       help='Output directory (default: curated_dataset)')
    parser.add_argument('--process', action='store_true',
                       help='Process accepted videos through full pipeline')

    args = parser.parse_args()

    # Create curator
    curator = AutoDatasetCurator(
        output_dir=args.output_dir,
        quality_threshold=args.threshold
    )

    # Process each search query
    all_accepted_videos = []

    for query in args.queries:
        print(f"\n{'='*70}")
        print(f"SEARCH QUERY: {query}")
        print(f"{'='*70}\n")

        accepted = curator.curate_from_search(
            query,
            max_videos=args.max_per_query,
            max_duration=args.max_duration
        )

        all_accepted_videos.extend(accepted)

        # Wait between queries to avoid rate limiting
        if len(args.queries) > 1:
            print("\n⏱️  Waiting 10 seconds before next query...")
            time.sleep(10)

    # Process accepted videos if requested
    if args.process and all_accepted_videos:
        processed = curator.process_curated_videos(all_accepted_videos)

    # Print final statistics
    curator.print_statistics()


if __name__ == '__main__':
    main()
