"""
Generate validation report for human review
Shows what system detected for each video
"""

import json
from pathlib import Path


def generate_report(video_files, output_dir='output'):
    """Generate human validation report"""

    output_dir = Path(output_dir)

    print("="*70)
    print("HUMAN VALIDATION REPORT")
    print("="*70)
    print(f"Videos to validate: {len(video_files)}")
    print()
    print("Instructions:")
    print("1. Watch each video")
    print("2. Note what action you see")
    print("3. Compare with system detection")
    print("4. Mark as ✅ Correct or ❌ Wrong")
    print("="*70)
    print()

    for i, video_path in enumerate(video_files, 1):
        video_path = Path(video_path)
        video_stem = video_path.stem

        print(f"\n{'='*70}")
        print(f"VIDEO #{i}: {video_path.name}")
        print(f"{'='*70}")
        print(f"📁 Location: {video_path}")
        print()

        # Load reconciled data
        reconciled_file = output_dir / f"{video_stem}_reconciled.json"

        if not reconciled_file.exists():
            print("⚠️  No reconciliation data found")
            print()
            continue

        with open(reconciled_file, 'r') as f:
            data = json.load(f)

        # Display system detection
        print("🤖 SYSTEM DETECTION:")
        print(f"   Action: {data.get('action', 'unknown').upper()}")
        print(f"   Confidence: {data.get('confidence', 0.0):.0%}")
        print(f"   Method: {data.get('method', 'unknown')}")

        if 'reasoning' in data:
            print(f"   Reasoning: {data['reasoning']}")

        if data.get('conflict_detected'):
            print(f"   ⚠️  Conflict: Discarded '{data.get('discarded', 'unknown')}' in favor of '{data['action']}'")

        print()

        # Load physics detection for more details
        physics_file = output_dir / f"{video_stem}_physics_detection.json"
        if physics_file.exists():
            with open(physics_file, 'r') as f:
                physics = json.load(f)

            if physics.get('actions'):
                print("📊 PHYSICS DETECTED:")
                for action in physics['actions'][:5]:  # Show first 5
                    act_name = action.get('action', 'unknown').upper()
                    duration = action.get('duration', 0)
                    conf = action.get('confidence', 0)

                    extra = ""
                    if 'net_displacement' in action:
                        extra = f" (net_disp: {action['net_displacement']:+.2f}m)"
                    elif 'rotation_angle' in action:
                        extra = f" (rotation: {action['rotation_angle']:.0f}°)"

                    print(f"   - {act_name}: {duration:.1f}s @ {conf:.0%}{extra}")
                print()

        # Load vision detection
        vision_file = output_dir / f"{video_stem}_vision_detection.json"
        if vision_file.exists():
            with open(vision_file, 'r') as f:
                vision = json.load(f)

            if vision.get('action') != 'unknown':
                print("👁️  VISION DETECTED:")
                print(f"   Action: {vision['action'].upper()}")
                print(f"   Confidence: {vision.get('confidence', 0.0):.0%}")
                if 'reasoning' in vision:
                    print(f"   Reasoning: {vision['reasoning']}")
                print()

        # Validation template
        print("✏️  YOUR VALIDATION:")
        print(f"   [ ] Watch video: {video_path.name}")
        print(f"   [ ] What action did you see? _________________")
        print(f"   [ ] System said: {data.get('action', 'unknown').upper()}")
        print(f"   [ ] Correct? ✅ Yes  ❌ No  ⚠️  Partial")
        print(f"   [ ] Notes: _________________________________")
        print()

    print("="*70)
    print("VALIDATION TEMPLATE")
    print("="*70)
    print()
    print("Copy this and fill it out:")
    print()
    print("| Video | Ground Truth | System | Correct? | Notes |")
    print("|-------|--------------|--------|----------|-------|")
    for i, video_path in enumerate(video_files, 1):
        video_path = Path(video_path)
        video_stem = video_path.stem
        reconciled_file = output_dir / f"{video_stem}_reconciled.json"

        if reconciled_file.exists():
            with open(reconciled_file, 'r') as f:
                data = json.load(f)
            detected = data.get('action', 'unknown').upper()
        else:
            detected = 'N/A'

        print(f"| {video_path.name} | ________ | {detected} | _____ | _____ |")

    print()
    print("="*70)


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Generate validation report')
    parser.add_argument('videos', nargs='+', help='Video files to validate')
    parser.add_argument('--output-dir', default='output', help='Output directory')

    args = parser.parse_args()

    generate_report(args.videos, args.output_dir)


if __name__ == '__main__':
    main()
