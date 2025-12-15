"""
BATCH VIDEO PROCESSOR

Process multiple videos automatically and export to unified HDF5 dataset.
Enables scaling to 100s-1000s of videos for robot training.
"""

import json
from pathlib import Path
from unified_pipeline import UnifiedPipeline
from core.export.hdf5_exporter import HDF5Exporter
import time


class BatchProcessor:
    """
    Process multiple videos in batch and create unified dataset
    """

    def __init__(self, enable_vision=True, output_dir='batch_output'):
        self.enable_vision = enable_vision
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.pipeline = UnifiedPipeline(
            enable_vision=enable_vision,
            output_dir=str(self.output_dir / 'individual')
        )

        self.hdf5_exporter = HDF5Exporter()

    def process_video_list(self, video_files, output_dataset='robot_dataset.hdf5'):
        """
        Process a list of videos and create unified HDF5 dataset

        Args:
            video_files: List of paths to video files
            output_dataset: Name of output HDF5 file

        Returns:
            dict with processing results
        """
        print("="*70)
        print("BATCH VIDEO PROCESSOR")
        print("="*70)
        print(f"Videos to process: {len(video_files)}")
        print(f"Vision enabled: {self.enable_vision}")
        print(f"Output dataset: {output_dataset}")
        print("="*70)
        print()

        results = {
            'total': len(video_files),
            'processed': 0,
            'failed': 0,
            'demos': [],
            'errors': [],
            'start_time': time.time()
        }

        # Process each video
        for i, video_file in enumerate(video_files, 1):
            video_path = Path(video_file)

            print(f"\n[{i}/{len(video_files)}] Processing: {video_path.name}")
            print("-" * 70)

            try:
                # Run pipeline
                result = self.pipeline.process(str(video_path))

                if result:
                    # Extract demo data
                    demo_data = {
                        'action': result.get('action', 'unknown'),
                        'confidence': result.get('confidence', 0.0),
                        'method': result.get('method', 'unknown'),
                        'objects': result.get('objects', ['unknown']),
                        'kinematics': result.get('kinematics', {})
                    }

                    results['demos'].append(demo_data)
                    results['processed'] += 1

                    print(f"✅ Success: {demo_data['action']} ({demo_data['confidence']:.0%})")
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'video': video_path.name,
                        'error': 'Pipeline returned None'
                    })
                    print(f"❌ Failed: Pipeline returned None")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'video': video_path.name,
                    'error': str(e)
                })
                print(f"❌ Error: {e}")

        # Create unified HDF5 dataset
        if results['demos']:
            print()
            print("="*70)
            print("CREATING UNIFIED DATASET")
            print("="*70)

            dataset_path = self.output_dir / output_dataset
            self.hdf5_exporter.export_dataset(results['demos'], dataset_path)

            results['dataset_file'] = str(dataset_path)
            results['dataset_size_mb'] = dataset_path.stat().st_size / 1024 / 1024

        # Calculate statistics
        results['duration'] = time.time() - results['start_time']
        results['success_rate'] = results['processed'] / results['total'] if results['total'] > 0 else 0

        # Print summary
        self._print_summary(results)

        # Save results JSON
        results_file = self.output_dir / 'batch_results.json'
        with open(results_file, 'w') as f:
            # Make copy without non-serializable data
            save_results = {k: v for k, v in results.items() if k != 'demos'}
            save_results['demo_count'] = len(results['demos'])
            json.dump(save_results, f, indent=2)

        print(f"\n💾 Results saved: {results_file}")

        return results

    def process_directory(self, video_dir, pattern='*.mp4', output_dataset='robot_dataset.hdf5'):
        """
        Process all videos in a directory

        Args:
            video_dir: Directory containing videos
            pattern: File pattern to match (e.g., '*.mp4', '*.mov')
            output_dataset: Name of output HDF5 file

        Returns:
            dict with processing results
        """
        video_dir = Path(video_dir)

        # Find all matching videos
        video_files = list(video_dir.glob(pattern))

        # Also check for .mov files if pattern was .mp4
        if pattern == '*.mp4':
            video_files.extend(video_dir.glob('*.mov'))

        video_files = sorted(video_files)

        print(f"📁 Found {len(video_files)} videos in {video_dir}")
        print()

        if not video_files:
            print("❌ No videos found")
            return None

        return self.process_video_list(video_files, output_dataset)

    def _print_summary(self, results):
        """Print processing summary"""
        print()
        print("="*70)
        print("BATCH PROCESSING SUMMARY")
        print("="*70)
        print(f"Total videos: {results['total']}")
        print(f"Processed successfully: {results['processed']} ({results['success_rate']:.0%})")
        print(f"Failed: {results['failed']}")
        print(f"Duration: {results['duration']:.1f}s ({results['duration']/60:.1f}m)")
        print()

        if results['demos']:
            # Action distribution
            actions = [d['action'] for d in results['demos']]
            action_counts = {}
            for action in actions:
                action_counts[action] = action_counts.get(action, 0) + 1

            print("Action Distribution:")
            for action, count in sorted(action_counts.items(), key=lambda x: -x[1]):
                print(f"  {action.upper()}: {count} ({count/len(results['demos'])*100:.0%})")
            print()

            # Average confidence
            avg_conf = sum(d['confidence'] for d in results['demos']) / len(results['demos'])
            print(f"Average Confidence: {avg_conf:.0%}")
            print()

            # Dataset info
            if 'dataset_file' in results:
                print(f"Dataset: {results['dataset_file']}")
                print(f"Size: {results['dataset_size_mb']:.2f} MB")
                print(f"Demos: {len(results['demos'])}")

        if results['errors']:
            print()
            print("Errors:")
            for error in results['errors'][:5]:  # Show first 5
                print(f"  ❌ {error['video']}: {error['error']}")
            if len(results['errors']) > 5:
                print(f"  ... and {len(results['errors']) - 5} more")

        print("="*70)


def main():
    """
    Command-line interface for batch processing
    """
    import argparse

    parser = argparse.ArgumentParser(description='Batch process videos for robot training')
    parser.add_argument('input', help='Directory containing videos OR text file with video paths')
    parser.add_argument('--output', default='batch_output', help='Output directory')
    parser.add_argument('--dataset', default='robot_dataset.hdf5', help='Output dataset name')
    parser.add_argument('--pattern', default='*.mp4', help='File pattern (for directory input)')
    parser.add_argument('--no-vision', action='store_true', help='Disable vision stream')

    args = parser.parse_args()

    # Create processor
    processor = BatchProcessor(
        enable_vision=not args.no_vision,
        output_dir=args.output
    )

    # Check if input is directory or file list
    input_path = Path(args.input)

    if input_path.is_dir():
        # Process directory
        results = processor.process_directory(
            input_path,
            pattern=args.pattern,
            output_dataset=args.dataset
        )
    elif input_path.is_file():
        # Read file list
        with open(input_path, 'r') as f:
            video_files = [line.strip() for line in f if line.strip()]

        results = processor.process_video_list(video_files, output_dataset=args.dataset)
    else:
        print(f"❌ Error: {input_path} not found")
        return

    if results:
        print(f"\n✅ Batch processing complete!")
        print(f"   Success rate: {results['success_rate']:.0%}")
        print(f"   Dataset: {results.get('dataset_file', 'N/A')}")


if __name__ == '__main__':
    main()
