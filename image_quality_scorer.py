"""
IMAGE QUALITY SCORER
Score images 0-100 for robot training suitability

Scoring criteria (same as video):
- Pose detection (0-50 points)
- Hand detection (0-20 points)
- Lighting quality (0-15 points)
- Image clarity (0-10 points)
- Resolution (0-5 points)

Usage:
    scorer = ImageQualityScorer()
    result = scorer.score_image('image.jpg')
    print(f"Score: {result['score']}/100")
"""

import cv2
import mediapipe as mp
import numpy as np
from pathlib import Path


class ImageQualityScorer:
    """Score images for robot training data quality"""

    def __init__(self):
        """Initialize MediaPipe models"""
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands

        # Initialize detectors
        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=1,
            min_detection_confidence=0.5
        )

        self.hands = self.mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=2,
            min_detection_confidence=0.5
        )

    def score_image(self, image_path):
        """
        Score image quality 0-100

        Args:
            image_path: Path to image file

        Returns:
            dict with score, rating, and breakdown
        """
        image_path = Path(image_path)

        if not image_path.exists():
            return {'score': 0, 'rating': 'ERROR', 'error': 'File not found'}

        # Read image
        image = cv2.imread(str(image_path))

        if image is None:
            return {'score': 0, 'rating': 'ERROR', 'error': 'Could not read image'}

        # Convert to RGB for MediaPipe
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Get image properties
        height, width = image.shape[:2]
        resolution = width * height

        # Initialize breakdown
        breakdown = {
            'pose_detection': {'detected': False, 'score': 0},
            'hand_detection': {'detected': False, 'score': 0},
            'lighting': {'mean_brightness': 0, 'score': 0},
            'clarity': {'score': 0},
            'resolution': {'pixels': resolution, 'score': 0}
        }

        # 1. Pose Detection (0-50 points)
        pose_results = self.pose.process(image_rgb)

        if pose_results.pose_landmarks:
            # Pose detected - full points
            breakdown['pose_detection']['detected'] = True
            breakdown['pose_detection']['score'] = 50

            # Check pose visibility (bonus quality check)
            visible_landmarks = sum(
                1 for lm in pose_results.pose_landmarks.landmark
                if lm.visibility > 0.5
            )
            visibility_ratio = visible_landmarks / 33  # 33 total landmarks

            # Adjust score based on visibility
            breakdown['pose_detection']['score'] = visibility_ratio * 50

        # 2. Hand Detection (0-20 points)
        hand_results = self.hands.process(image_rgb)

        if hand_results.multi_hand_landmarks:
            hands_detected = len(hand_results.multi_hand_landmarks)
            breakdown['hand_detection']['detected'] = True
            breakdown['hand_detection']['hands_count'] = hands_detected
            breakdown['hand_detection']['score'] = min(hands_detected * 10, 20)

        # 3. Lighting Quality (0-15 points)
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        std_brightness = np.std(gray)

        # Ideal brightness: 100-150, good contrast: std > 40
        brightness_score = 0
        if 80 <= mean_brightness <= 170:
            brightness_score = 10
        elif 60 <= mean_brightness <= 190:
            brightness_score = 7
        elif mean_brightness < 50 or mean_brightness > 200:
            brightness_score = 2
        else:
            brightness_score = 5

        contrast_score = min(std_brightness / 10, 5)  # Max 5 points

        lighting_score = brightness_score + contrast_score

        breakdown['lighting']['mean_brightness'] = float(mean_brightness)
        breakdown['lighting']['std_brightness'] = float(std_brightness)
        breakdown['lighting']['score'] = lighting_score

        # 4. Image Clarity (0-10 points)
        # Use Laplacian variance (blur detection)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        clarity_var = laplacian.var()

        # Higher variance = sharper image
        if clarity_var > 500:
            clarity_score = 10
        elif clarity_var > 300:
            clarity_score = 7
        elif clarity_var > 100:
            clarity_score = 5
        else:
            clarity_score = 2

        breakdown['clarity']['variance'] = float(clarity_var)
        breakdown['clarity']['score'] = clarity_score

        # 5. Resolution (0-5 points)
        # Prefer higher resolution images
        if resolution >= 1920 * 1080:  # Full HD+
            resolution_score = 5
        elif resolution >= 1280 * 720:  # HD
            resolution_score = 4
        elif resolution >= 854 * 480:   # 480p
            resolution_score = 3
        else:
            resolution_score = 2

        breakdown['resolution']['score'] = resolution_score

        # Calculate total score
        total_score = (
            breakdown['pose_detection']['score'] +
            breakdown['hand_detection']['score'] +
            breakdown['lighting']['score'] +
            breakdown['clarity']['score'] +
            breakdown['resolution']['score']
        )

        # Determine rating
        if total_score >= 80:
            rating = 'EXCELLENT'
            recommendation = 'Perfect for robot training'
        elif total_score >= 70:
            rating = 'GOOD'
            recommendation = 'Suitable for robot training'
        elif total_score >= 50:
            rating = 'FAIR'
            recommendation = 'Acceptable but not ideal'
        else:
            rating = 'POOR'
            recommendation = 'Not recommended for training'

        return {
            'score': round(total_score, 1),
            'rating': rating,
            'recommendation': recommendation,
            'breakdown': breakdown,
            'image_properties': {
                'width': width,
                'height': height,
                'resolution': resolution
            }
        }

    def __del__(self):
        """Cleanup MediaPipe resources"""
        self.pose.close()
        self.hands.close()


def main():
    """Test image quality scorer"""
    import argparse
    import json

    parser = argparse.ArgumentParser(description='Score image quality for robot training')
    parser.add_argument('image', help='Path to image file')
    parser.add_argument('--json', action='store_true',
                       help='Output JSON format')

    args = parser.parse_args()

    scorer = ImageQualityScorer()
    result = scorer.score_image(args.image)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("="*70)
        print("IMAGE QUALITY SCORE")
        print("="*70)
        print(f"Image: {args.image}")
        print(f"Score: {result['score']}/100")
        print(f"Rating: {result['rating']}")
        print(f"Recommendation: {result['recommendation']}")
        print()
        print("Breakdown:")
        print(f"  Pose detection: {result['breakdown']['pose_detection']['score']:.1f}/50")
        print(f"  Hand detection: {result['breakdown']['hand_detection']['score']:.1f}/20")
        print(f"  Lighting: {result['breakdown']['lighting']['score']:.1f}/15")
        print(f"  Clarity: {result['breakdown']['clarity']['score']:.1f}/10")
        print(f"  Resolution: {result['breakdown']['resolution']['score']:.1f}/5")
        print("="*70)


if __name__ == '__main__':
    main()
