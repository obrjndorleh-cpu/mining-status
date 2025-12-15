"""
Simple video test script
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.pipeline import VideoIntelligencePipeline

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_video.py <video_file>")
        print("\nAvailable videos:")
        for video in Path('.').glob('*.mp4'):
            print(f"  - {video.name}")
        return

    video_path = sys.argv[1]

    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        return

    print(f"🚀 Processing: {video_path}\n")

    pipeline = VideoIntelligencePipeline(config={
        'sample_fps': 5,
        'min_confidence': 0.5
    })

    result = pipeline.process_video(
        video_path=video_path,
        output_path=f"{Path(video_path).stem}_result.json"
    )

    print("\n" + "="*70)
    print("✅ RESULTS")
    print("="*70)
    print(f"Duration: {result['video_metadata']['duration']:.2f}s")
    print(f"Quality Score: {result['quality_score']}/100")
    print(f"Actions: {len(result['actions'])}")

    if result['actions']:
        print("\nACTION SEQUENCE:")
        for i, action in enumerate(result['actions'], 1):
            print(f"  {i}. {action['label'].upper():10s} "
                  f"{action['start_time']:5.2f}s → {action['end_time']:5.2f}s "
                  f"(conf: {action['confidence']:.2f})")
            if 'target_object' in action:
                print(f"      → Target: {action['target_object']}")

    print(f"\n💾 Result: {Path(video_path).stem}_result.json")
    print(f"⏱️  Time: {result['processing_time_seconds']:.1f}s\n")

if __name__ == "__main__":
    main()
