"""
HUMAN VALIDATION WORKFLOW

Process videos and present results for human verification.
User watches video and confirms if extracted data matches reality.

Workflow:
1. Download/process YouTube video
2. Extract action + kinematics
3. Show user the video
4. Show user what we detected
5. User validates: ✅ Correct or ❌ Wrong
6. Log results for system improvement
"""

import json
from pathlib import Path
import subprocess
from datetime import datetime


class HumanValidationWorkflow:
    """
    Interactive validation workflow
    """

    def __init__(self):
        self.results_file = Path('human_validation_results.json')
        self.load_results()

    def load_results(self):
        """Load previous validation results"""
        if self.results_file.exists():
            with open(self.results_file, 'r') as f:
                self.results = json.load(f)
        else:
            self.results = {
                'validations': [],
                'statistics': {
                    'total': 0,
                    'correct': 0,
                    'incorrect': 0,
                    'accuracy': 0.0
                }
            }

    def save_results(self):
        """Save validation results"""
        # Update statistics
        total = len(self.results['validations'])
        correct = sum(1 for v in self.results['validations'] if v['human_verdict'] == 'correct')

        self.results['statistics'] = {
            'total': total,
            'correct': correct,
            'incorrect': total - correct,
            'accuracy': correct / total if total > 0 else 0.0
        }

        with open(self.results_file, 'w') as f:
            json.dump(self.results, f, indent=2)

    def validate_video(self, video_path, robot_data_path):
        """
        Interactive validation of a single video

        Args:
            video_path: Path to video file
            robot_data_path: Path to robot_data.json or reconciled.json

        Returns:
            dict with validation result
        """
        print("="*70)
        print("HUMAN VALIDATION WORKFLOW")
        print("="*70)
        print()

        video_path = Path(video_path)
        robot_data_path = Path(robot_data_path)

        # Load robot data
        with open(robot_data_path, 'r') as f:
            robot_data = json.load(f)

        # Extract key information
        detected_action = robot_data.get('action', 'unknown')
        confidence = robot_data.get('confidence', 0.0)
        method = robot_data.get('method', 'unknown')
        reasoning = robot_data.get('reasoning', '')

        # Display what we detected
        print(f"📹 Video: {video_path.name}")
        print()
        print("🤖 SYSTEM DETECTION:")
        print(f"   Action: {detected_action.upper()}")
        print(f"   Confidence: {confidence:.0%}")
        print(f"   Method: {method}")
        if reasoning:
            print(f"   Reasoning: {reasoning}")
        print()

        # Show kinematics summary if available
        if 'kinematics' in robot_data:
            kinematics = robot_data['kinematics']
            positions = kinematics.get('positions', [])
            if positions and len(positions) > 1:
                net_disp = [positions[-1][i] - positions[0][i] for i in range(3)]
                print("📊 KINEMATICS SUMMARY:")
                print(f"   Frames: {len(positions)}")
                print(f"   Duration: {kinematics.get('timestamps', [0, 0])[-1]:.1f}s")
                print(f"   Net displacement: X={net_disp[0]:+.2f}m, Y={net_disp[1]:+.2f}m, Z={net_disp[2]:+.2f}m")
                if abs(net_disp[2]) > 0.1:
                    direction = "BACKWARD (pull)" if net_disp[2] > 0 else "FORWARD (push)"
                    print(f"   Primary motion: {direction}")
                print()

        # Try to open video for user to watch
        print("🎬 Opening video for you to watch...")
        print("   (Watch the video and determine what action actually happened)")
        print()

        try:
            # Try to open with default video player
            if video_path.suffix.lower() in ['.mp4', '.mov', '.avi']:
                subprocess.run(['open', str(video_path)], check=False)
                print("✅ Video opened in player")
            else:
                print("⚠️  Could not open video (unsupported format)")
        except Exception as e:
            print(f"⚠️  Could not open video: {e}")

        print()
        print("-"*70)
        print()

        # Get human validation
        print("VALIDATION QUESTIONS:")
        print()

        # Question 1: What action did you see?
        print("1. What action did you actually see in the video?")
        print("   Options: push, pull, lift, place, pour, twist_open, twist_close,")
        print("            open, close, slide, grasp, release, other")
        print()
        human_action = input("   Your answer: ").strip().lower()
        print()

        # Question 2: Is our detection correct?
        print(f"2. We detected: {detected_action.upper()}")
        print("   Is this correct?")
        print("   Options: yes, no, partial")
        print()
        verdict = input("   Your answer: ").strip().lower()
        print()

        # Question 3: Any notes?
        print("3. Any additional notes or observations?")
        print("   (Press Enter to skip)")
        print()
        notes = input("   Notes: ").strip()
        print()

        # Map verdict
        if verdict in ['yes', 'y', 'correct']:
            verdict_mapped = 'correct'
        elif verdict in ['no', 'n', 'wrong', 'incorrect']:
            verdict_mapped = 'incorrect'
        elif verdict in ['partial', 'p', 'somewhat']:
            verdict_mapped = 'partial'
        else:
            verdict_mapped = 'unknown'

        # Create validation record
        validation = {
            'timestamp': datetime.now().isoformat(),
            'video': str(video_path),
            'detected_action': detected_action,
            'detected_confidence': confidence,
            'detected_method': method,
            'human_action': human_action,
            'human_verdict': verdict_mapped,
            'notes': notes,
            'match': detected_action.lower() == human_action.lower()
        }

        # Save to results
        self.results['validations'].append(validation)
        self.save_results()

        # Print result
        print("="*70)
        print("VALIDATION RESULT")
        print("="*70)
        if validation['match']:
            print("✅ MATCH: System detection matches your observation")
        else:
            print("❌ MISMATCH:")
            print(f"   System said: {detected_action.upper()}")
            print(f"   You saw: {human_action.upper()}")
        print()
        print(f"Overall verdict: {verdict_mapped.upper()}")
        print()

        # Show current accuracy
        stats = self.results['statistics']
        print(f"📊 CURRENT ACCURACY: {stats['accuracy']:.0%} ({stats['correct']}/{stats['total']})")
        print("="*70)
        print()

        return validation

    def batch_validate(self, video_dir, output_dir):
        """
        Validate multiple videos interactively

        Args:
            video_dir: Directory with videos
            output_dir: Directory with robot_data.json files
        """
        video_dir = Path(video_dir)
        output_dir = Path(output_dir)

        # Find all videos and their outputs
        videos = list(video_dir.glob('*.mp4')) + list(video_dir.glob('*.mov'))

        print(f"Found {len(videos)} videos to validate")
        print()

        for i, video_path in enumerate(videos, 1):
            print(f"\n[{i}/{len(videos)}] Processing: {video_path.name}")
            print()

            # Find corresponding robot data
            robot_data_file = output_dir / f"{video_path.stem}_reconciled.json"
            if not robot_data_file.exists():
                robot_data_file = output_dir / f"{video_path.stem}_robot_data.json"

            if not robot_data_file.exists():
                print(f"⚠️  No robot data found for {video_path.name}")
                continue

            # Validate
            self.validate_video(video_path, robot_data_file)

            # Ask if continue
            if i < len(videos):
                cont = input("\nContinue to next video? (yes/no): ").strip().lower()
                if cont not in ['yes', 'y']:
                    break

        # Print final statistics
        self.print_statistics()

    def print_statistics(self):
        """Print validation statistics"""
        stats = self.results['statistics']

        print()
        print("="*70)
        print("HUMAN VALIDATION STATISTICS")
        print("="*70)
        print(f"Total validations: {stats['total']}")
        print(f"Correct: {stats['correct']} ({stats['correct']/stats['total']*100:.0%})" if stats['total'] > 0 else "Correct: 0")
        print(f"Incorrect: {stats['incorrect']}" if stats['total'] > 0 else "Incorrect: 0")
        print(f"Overall accuracy: {stats['accuracy']:.0%}")
        print()

        # Breakdown by action
        if self.results['validations']:
            print("Breakdown by detected action:")
            action_stats = {}
            for v in self.results['validations']:
                action = v['detected_action']
                if action not in action_stats:
                    action_stats[action] = {'total': 0, 'correct': 0}
                action_stats[action]['total'] += 1
                if v['match']:
                    action_stats[action]['correct'] += 1

            for action, counts in sorted(action_stats.items()):
                acc = counts['correct'] / counts['total'] if counts['total'] > 0 else 0
                print(f"  {action.upper()}: {counts['correct']}/{counts['total']} ({acc:.0%})")

        print("="*70)
        print()


def main():
    """
    Command-line interface
    """
    import argparse

    parser = argparse.ArgumentParser(description='Human validation workflow')
    parser.add_argument('video', nargs='?', help='Video file to validate')
    parser.add_argument('--robot-data', help='Robot data JSON file')
    parser.add_argument('--batch', action='store_true', help='Batch validate directory')
    parser.add_argument('--video-dir', default='youtube_videos', help='Video directory for batch')
    parser.add_argument('--output-dir', default='output', help='Output directory for batch')
    parser.add_argument('--stats', action='store_true', help='Show statistics only')

    args = parser.parse_args()

    workflow = HumanValidationWorkflow()

    if args.stats:
        workflow.print_statistics()
    elif args.batch:
        workflow.batch_validate(args.video_dir, args.output_dir)
    elif args.video:
        robot_data = args.robot_data or f"output/{Path(args.video).stem}_reconciled.json"
        workflow.validate_video(args.video, robot_data)
    else:
        print("Usage:")
        print("  Validate single video: python human_validation_workflow.py video.mp4")
        print("  Batch validate: python human_validation_workflow.py --batch")
        print("  Show stats: python human_validation_workflow.py --stats")


if __name__ == '__main__':
    main()
