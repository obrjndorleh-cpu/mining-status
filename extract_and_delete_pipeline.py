"""
EXTRACT-AND-DELETE PIPELINE

Process videos → Extract robot data → Delete video → Keep mining forever!

This is the PRODUCTION approach:
- Videos are temporary (just the source material)
- Robot data is permanent (the valuable product)
- Delete videos after extraction = infinite mining capacity

Storage efficiency:
- Video: ~1MB each
- Robot data: ~50KB each
- 20x more data in same disk space!
"""

import subprocess
import json
from pathlib import Path
import shutil


class ExtractAndDeletePipeline:
    """
    Process videos, extract data, delete videos to save space
    """

    def __init__(self, data_dir='permanent_data', keep_hdf5=True, keep_json=True):
        """
        Args:
            data_dir: Where to store permanent robot data
            keep_hdf5: Keep HDF5 files (for robot training)
            keep_json: Keep JSON files (for inspection/debugging)
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

        # Organize by data type
        self.hdf5_dir = self.data_dir / 'hdf5'
        self.json_dir = self.data_dir / 'json'
        self.logs_dir = self.data_dir / 'logs'

        if keep_hdf5:
            self.hdf5_dir.mkdir(exist_ok=True)
        if keep_json:
            self.json_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        self.keep_hdf5 = keep_hdf5
        self.keep_json = keep_json

        self.processing_log = self.logs_dir / 'processing_log.json'
        self.load_log()

    def load_log(self):
        """Load processing log"""
        if self.processing_log.exists():
            with open(self.processing_log, 'r') as f:
                self.log = json.load(f)
        else:
            self.log = {
                'videos_processed': 0,
                'videos_deleted': 0,
                'space_saved_mb': 0.0,
                'processing_history': []
            }

    def save_log(self):
        """Save processing log"""
        with open(self.processing_log, 'w') as f:
            json.dump(self.log, f, indent=2)

    def process_and_delete(self, video_path, enable_vision=True, temp_output_dir='output_temp'):
        """
        Process video → Extract data → Delete video

        Args:
            video_path: Path to video file
            enable_vision: Use vision stream for detection
            temp_output_dir: Temporary directory for processing

        Returns:
            dict with processing result
        """
        video_path = Path(video_path)
        video_name = video_path.stem
        video_size_mb = video_path.stat().st_size / (1024 * 1024)

        print(f"\n{'='*70}")
        print(f"🔄 PROCESSING: {video_path.name}")
        print(f"{'='*70}")
        print(f"Video size: {video_size_mb:.2f} MB")
        print()

        result = {
            'video': str(video_path.name),
            'size_mb': video_size_mb,
            'processed': False,
            'deleted': False,
            'data_files': []
        }

        try:
            # Stage 1: Process through unified pipeline
            print("⚙️  Stage 1: Extracting robot data...")

            temp_output = Path(temp_output_dir)
            temp_output.mkdir(exist_ok=True)

            cmd = [
                'python', 'unified_pipeline.py',
                str(video_path),
                str(temp_output / f"{video_name}.mp4"),
            ]
            if enable_vision:
                cmd.append('--enable-vision')

            proc_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if proc_result.returncode != 0:
                print(f"   ❌ Processing failed: {proc_result.stderr[:200]}")
                result['error'] = proc_result.stderr[:500]
                return result

            print("   ✅ Data extracted successfully")
            result['processed'] = True

            # Stage 2: Move important data to permanent storage
            print("💾 Stage 2: Saving permanent data...")

            output_dir = Path('output')
            saved_files = []

            # Save HDF5 (robot training data)
            if self.keep_hdf5:
                hdf5_file = output_dir / f"{video_name}.hdf5"
                if hdf5_file.exists():
                    dest = self.hdf5_dir / hdf5_file.name
                    shutil.move(str(hdf5_file), str(dest))
                    saved_files.append(str(dest))
                    print(f"   ✅ Saved: {dest.name}")

            # Save JSON files (metadata, reconciled data, etc.)
            if self.keep_json:
                json_patterns = [
                    f"{video_name}_reconciled.json",
                    f"{video_name}_robot_data.json",
                    f"{video_name}_kinematics.json",
                ]

                for pattern in json_patterns:
                    json_file = output_dir / pattern
                    if json_file.exists():
                        dest = self.json_dir / json_file.name
                        shutil.move(str(json_file), str(dest))
                        saved_files.append(str(dest))

                print(f"   ✅ Saved {len(saved_files)} data files")

            result['data_files'] = saved_files

            # Stage 3: Delete video and temporary files
            print("🗑️  Stage 3: Deleting video to free space...")

            # Delete the video file
            video_path.unlink()
            print(f"   ✅ Deleted video: {video_path.name}")
            result['deleted'] = True

            # Delete temporary processing files
            temp_files = [
                f"{video_name}_extraction.json",
                f"{video_name}_physics_detection.json",
                f"{video_name}_vision_detection.json",
                f"{video_name}_full_extraction.json",
            ]

            for temp_file in temp_files:
                temp_path = output_dir / temp_file
                if temp_path.exists():
                    temp_path.unlink()

            # Clean up temp output dir
            if temp_output.exists():
                shutil.rmtree(temp_output)

            # Update statistics
            self.log['videos_processed'] += 1
            self.log['videos_deleted'] += 1
            self.log['space_saved_mb'] += video_size_mb
            self.log['processing_history'].append(result)
            self.save_log()

            print()
            print(f"✅ COMPLETE: Kept data, freed {video_size_mb:.2f} MB")
            print(f"📊 Total space saved: {self.log['space_saved_mb']:.2f} MB")
            print(f"{'='*70}")

            return result

        except subprocess.TimeoutExpired:
            print(f"   ⏱️  Timeout (>5 minutes)")
            result['error'] = 'Processing timeout'
            return result

        except Exception as e:
            print(f"   ❌ Error: {e}")
            result['error'] = str(e)
            return result

    def batch_process_and_delete(self, video_dir='data_mine/videos'):
        """
        Process all videos in directory, delete them as you go

        Args:
            video_dir: Directory containing videos to process
        """
        video_dir = Path(video_dir)

        if not video_dir.exists():
            print(f"❌ Directory not found: {video_dir}")
            return

        videos = list(video_dir.glob('*.mp4')) + list(video_dir.glob('*.mov'))

        if not videos:
            print(f"⚠️  No videos found in {video_dir}")
            return

        print("="*70)
        print("⚙️  EXTRACT-AND-DELETE BATCH PROCESSING")
        print("="*70)
        print(f"Videos to process: {len(videos)}")
        print(f"Permanent storage: {self.data_dir}")
        print()
        print("🎯 Strategy: Extract data → Delete video → Free space → Keep mining!")
        print("="*70)
        print()

        processed_count = 0
        deleted_count = 0
        total_space_freed = 0.0

        for i, video_path in enumerate(videos, 1):
            print(f"\n[{i}/{len(videos)}] Processing: {video_path.name}")

            result = self.process_and_delete(video_path)

            if result['processed']:
                processed_count += 1
            if result['deleted']:
                deleted_count += 1
                total_space_freed += result['size_mb']

            # Show progress
            print(f"\n📊 Batch Progress:")
            print(f"   Processed: {processed_count}/{len(videos)}")
            print(f"   Deleted: {deleted_count}/{len(videos)}")
            print(f"   Space freed: {total_space_freed:.2f} MB")

        # Final summary
        print()
        print("="*70)
        print("✅ BATCH PROCESSING COMPLETE")
        print("="*70)
        print(f"Videos processed: {processed_count}/{len(videos)}")
        print(f"Videos deleted: {deleted_count}/{len(videos)}")
        print(f"Total space freed: {total_space_freed:.2f} MB ({total_space_freed/1024:.2f} GB)")
        print()
        print(f"📁 Permanent data stored in: {self.data_dir}")
        print(f"   HDF5 files: {len(list(self.hdf5_dir.glob('*.hdf5')))} files")
        print(f"   JSON files: {len(list(self.json_dir.glob('*.json')))} files")
        print("="*70)

    def print_statistics(self):
        """Print processing statistics"""
        print()
        print("="*70)
        print("📊 EXTRACT-AND-DELETE STATISTICS")
        print("="*70)
        print(f"Videos processed: {self.log['videos_processed']}")
        print(f"Videos deleted: {self.log['videos_deleted']}")
        print(f"Space saved: {self.log['space_saved_mb']:.2f} MB ({self.log['space_saved_mb']/1024:.2f} GB)")
        print()

        if self.hdf5_dir.exists():
            hdf5_count = len(list(self.hdf5_dir.glob('*.hdf5')))
            print(f"📦 HDF5 Training Data: {hdf5_count} files")

        if self.json_dir.exists():
            json_count = len(list(self.json_dir.glob('*.json')))
            print(f"📄 JSON Metadata: {json_count} files")

        print()
        print("💡 Storage Efficiency:")
        if self.log['videos_processed'] > 0:
            avg_video_size = self.log['space_saved_mb'] / self.log['videos_deleted'] if self.log['videos_deleted'] > 0 else 0
            avg_data_size = 0.05  # Approximate 50KB per data file
            efficiency = avg_video_size / avg_data_size if avg_data_size > 0 else 0
            print(f"   Average video: {avg_video_size:.2f} MB")
            print(f"   Average data: {avg_data_size:.2f} MB")
            print(f"   Efficiency gain: {efficiency:.0f}x more samples in same space!")

        print("="*70)


def main():
    """
    CLI for extract-and-delete pipeline
    """
    import argparse

    parser = argparse.ArgumentParser(description='Extract robot data and delete videos to save space')
    parser.add_argument('videos', nargs='*', help='Video files to process')
    parser.add_argument('--batch-dir', help='Process all videos in directory')
    parser.add_argument('--data-dir', default='permanent_data',
                       help='Permanent data storage directory')
    parser.add_argument('--no-vision', action='store_true',
                       help='Disable vision stream (faster but less accurate)')
    parser.add_argument('--keep-hdf5', action='store_true', default=True,
                       help='Keep HDF5 files (default: True)')
    parser.add_argument('--keep-json', action='store_true', default=True,
                       help='Keep JSON files (default: True)')
    parser.add_argument('--stats', action='store_true',
                       help='Show statistics only')

    args = parser.parse_args()

    pipeline = ExtractAndDeletePipeline(
        data_dir=args.data_dir,
        keep_hdf5=args.keep_hdf5,
        keep_json=args.keep_json
    )

    if args.stats:
        pipeline.print_statistics()
    elif args.batch_dir:
        pipeline.batch_process_and_delete(args.batch_dir)
    elif args.videos:
        for video in args.videos:
            pipeline.process_and_delete(video, enable_vision=not args.no_vision)
        pipeline.print_statistics()
    else:
        print("Usage:")
        print("  Process single video:  python extract_and_delete_pipeline.py video.mp4")
        print("  Process directory:     python extract_and_delete_pipeline.py --batch-dir data_mine/videos")
        print("  Show statistics:       python extract_and_delete_pipeline.py --stats")


if __name__ == '__main__':
    main()
