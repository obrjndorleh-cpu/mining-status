"""
VIDEO QUALITY SCORER

Quickly analyzes videos to determine if they're suitable for robot data extraction.
Scores videos 0-100 based on tracking quality, visibility, lighting, etc.

This is the "algorithm" that filters YouTube's database for quality training data.
"""

import cv2
import mediapipe as mp
import numpy as np
from pathlib import Path
import json


class VideoQualityScorer:
    """
    Score videos for robot data extraction quality

    Criteria:
    - Pose detection rate (0-50 points)
    - Hand detection rate (0-20 points)
    - Lighting quality (0-15 points)
    - Single action detection (0-10 points)
    - Optimal duration (0-5 points)

    Total: 0-100 points
    Threshold: >70 = Good for robot training
    """

    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands

    def score_video(self, video_path, sample_duration=5.0, sample_interval=0.5):
        """
        Quick quality score by sampling first few seconds

        Args:
            video_path: Path to video file
            sample_duration: How many seconds to sample (default: 5s)
            sample_interval: Sample every N seconds (default: 0.5s = 2 fps)

        Returns:
            dict with score and detailed breakdown
        """
        video_path = Path(video_path)

        print(f"🔍 Analyzing: {video_path.name}")
        print(f"   Sampling first {sample_duration}s at {1/sample_interval:.1f} fps")

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            return {
                'score': 0,
                'reason': 'Cannot open video',
                'breakdown': {}
            }

        # Get video metadata
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Sample frames
        frame_interval = int(fps * sample_interval)
        max_frames = int(fps * sample_duration)

        sampled_frames = []
        frame_idx = 0

        while frame_idx < max_frames and frame_idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            if not ret:
                break
            sampled_frames.append(frame)
            frame_idx += frame_interval

        cap.release()

        if len(sampled_frames) == 0:
            return {
                'score': 0,
                'reason': 'No frames extracted',
                'breakdown': {}
            }

        # Analyze sampled frames
        pose_detections = []
        hand_detections = []
        brightness_values = []

        with self.mp_pose.Pose(
            static_image_mode=True,
            min_detection_confidence=0.5
        ) as pose, self.mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=2,
            min_detection_confidence=0.5
        ) as hands:

            for frame in sampled_frames:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Pose detection
                pose_result = pose.process(frame_rgb)
                pose_detections.append(pose_result.pose_landmarks is not None)

                # Hand detection
                hand_result = hands.process(frame_rgb)
                hand_detections.append(hand_result.multi_hand_landmarks is not None)

                # Lighting analysis
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                brightness = np.mean(gray)
                brightness_values.append(brightness)

        # Calculate scores
        breakdown = {}

        # 1. Pose Detection Rate (0-50 points)
        pose_rate = sum(pose_detections) / len(pose_detections)
        pose_score = pose_rate * 50
        breakdown['pose_detection'] = {
            'rate': pose_rate,
            'score': pose_score,
            'max': 50
        }

        # 2. Hand Detection Rate (0-20 points)
        hand_rate = sum(hand_detections) / len(hand_detections)
        hand_score = hand_rate * 20
        breakdown['hand_detection'] = {
            'rate': hand_rate,
            'score': hand_score,
            'max': 20
        }

        # 3. Lighting Quality (0-15 points)
        mean_brightness = np.mean(brightness_values)
        brightness_std = np.std(brightness_values)

        # Optimal brightness: 80-180, consistent (low std)
        if 80 <= mean_brightness <= 180:
            brightness_score = 10
        elif 50 <= mean_brightness <= 200:
            brightness_score = 5
        else:
            brightness_score = 0

        # Consistency bonus (low std = consistent lighting)
        if brightness_std < 20:
            consistency_score = 5
        elif brightness_std < 40:
            consistency_score = 3
        else:
            consistency_score = 0

        lighting_score = brightness_score + consistency_score
        breakdown['lighting'] = {
            'mean_brightness': mean_brightness,
            'consistency': brightness_std,
            'score': lighting_score,
            'max': 15
        }

        # 4. Single Action Indicator (0-10 points)
        # If pose detection is consistent (either high or low throughout),
        # likely single continuous action
        pose_consistency = 1 - np.std(pose_detections)
        action_score = pose_consistency * 10
        breakdown['action_consistency'] = {
            'consistency': pose_consistency,
            'score': action_score,
            'max': 10
        }

        # 5. Optimal Duration (0-5 points)
        if 5 <= duration <= 20:
            duration_score = 5
        elif 3 <= duration <= 30:
            duration_score = 3
        else:
            duration_score = 1

        breakdown['duration'] = {
            'seconds': duration,
            'score': duration_score,
            'max': 5
        }

        # Total score
        total_score = (
            pose_score +
            hand_score +
            lighting_score +
            action_score +
            duration_score
        )

        # Quality rating
        if total_score >= 80:
            rating = "EXCELLENT"
            emoji = "🌟"
        elif total_score >= 70:
            rating = "GOOD"
            emoji = "✅"
        elif total_score >= 50:
            rating = "FAIR"
            emoji = "⚠️"
        else:
            rating = "POOR"
            emoji = "❌"

        result = {
            'video': str(video_path.name),
            'score': round(total_score, 1),
            'rating': rating,
            'emoji': emoji,
            'metadata': {
                'duration': duration,
                'resolution': f"{width}x{height}",
                'fps': fps,
                'frames_sampled': len(sampled_frames)
            },
            'breakdown': breakdown,
            'recommendation': self._get_recommendation(total_score, breakdown)
        }

        return result

    def _get_recommendation(self, score, breakdown):
        """Generate recommendation based on score"""
        if score >= 70:
            return "✅ RECOMMENDED - Process this video for robot training data"

        # Identify main issues
        issues = []
        if breakdown['pose_detection']['rate'] < 0.5:
            issues.append("Low pose detection - person not visible or bad angle")
        if breakdown['hand_detection']['rate'] < 0.3:
            issues.append("Low hand detection - hands not clearly visible")
        if breakdown['lighting']['score'] < 8:
            issues.append("Poor lighting - too dark or inconsistent")

        if issues:
            return "❌ NOT RECOMMENDED - " + "; ".join(issues)
        else:
            return "⚠️ MARGINAL - May work but not ideal"

    def print_report(self, result):
        """Print detailed quality report"""
        print()
        print("="*70)
        print(f"{result['emoji']} VIDEO QUALITY REPORT: {result['rating']}")
        print("="*70)
        print(f"Video: {result['video']}")
        print(f"Overall Score: {result['score']}/100")
        print()

        print("📊 BREAKDOWN:")
        for category, data in result['breakdown'].items():
            cat_name = category.replace('_', ' ').title()
            score = data['score']
            max_score = data['max']
            bar_length = int((score / max_score) * 20) if max_score > 0 else 0
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"   {cat_name:20s} [{bar}] {score:.1f}/{max_score}")

            # Additional details
            if 'rate' in data:
                print(f"      → Detection rate: {data['rate']:.1%}")
            if 'mean_brightness' in data:
                print(f"      → Brightness: {data['mean_brightness']:.0f}/255")
                print(f"      → Consistency: {data['consistency']:.1f} std")
            if 'seconds' in data:
                print(f"      → Duration: {data['seconds']:.1f}s")

        print()
        print("💡 RECOMMENDATION:")
        print(f"   {result['recommendation']}")
        print("="*70)
        print()


def main():
    """
    Test the quality scorer on videos
    """
    import argparse

    parser = argparse.ArgumentParser(description='Score video quality for robot training')
    parser.add_argument('videos', nargs='+', help='Video files to score')
    parser.add_argument('--sample-duration', type=float, default=5.0,
                       help='Seconds to sample (default: 5s)')
    parser.add_argument('--save', help='Save results to JSON file')
    parser.add_argument('--threshold', type=float, default=70.0,
                       help='Quality threshold (default: 70)')

    args = parser.parse_args()

    scorer = VideoQualityScorer()
    results = []

    print("="*70)
    print("VIDEO QUALITY SCORER")
    print("="*70)
    print(f"Analyzing {len(args.videos)} videos...")
    print(f"Quality threshold: {args.threshold}/100")
    print()

    for video_path in args.videos:
        result = scorer.score_video(video_path, sample_duration=args.sample_duration)
        scorer.print_report(result)
        results.append(result)

    # Summary
    print()
    print("="*70)
    print("SUMMARY")
    print("="*70)

    good_videos = [r for r in results if r['score'] >= args.threshold]

    print(f"Total videos analyzed: {len(results)}")
    print(f"Videos above threshold ({args.threshold}): {len(good_videos)}")
    print()

    if good_videos:
        print("✅ RECOMMENDED VIDEOS:")
        for r in sorted(good_videos, key=lambda x: x['score'], reverse=True):
            print(f"   {r['emoji']} {r['score']:.1f}/100 - {r['video']}")

    poor_videos = [r for r in results if r['score'] < args.threshold]
    if poor_videos:
        print()
        print("❌ NOT RECOMMENDED:")
        for r in sorted(poor_videos, key=lambda x: x['score'], reverse=True):
            print(f"   {r['emoji']} {r['score']:.1f}/100 - {r['video']}")

    # Save results
    if args.save:
        with open(args.save, 'w') as f:
            json.dump(results, f, indent=2)
        print()
        print(f"💾 Saved results to: {args.save}")

    print("="*70)


if __name__ == '__main__':
    main()
