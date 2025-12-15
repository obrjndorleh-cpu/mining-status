"""
IMAGE EXTRACTION PIPELINE
Extract robot training data from images

Extracts:
- Body pose keypoints (33 landmarks)
- Hand keypoints (21 per hand)
- 3D coordinates + visibility
- Action classification

Output:
- HDF5 file with single-frame data
- JSON metadata

Usage:
    pipeline = ImageExtractionPipeline()
    result = pipeline.process_image('image.jpg', 'output.hdf5')
"""

import cv2
import mediapipe as mp
import numpy as np
import h5py
import json
from pathlib import Path
from datetime import datetime


class ImageExtractionPipeline:
    """Extract robot training data from images"""

    def __init__(self):
        """Initialize MediaPipe models"""
        self.mp_pose = mp.solutions.pose
        self.mp_hands = mp.solutions.hands

        self.pose = self.mp_pose.Pose(
            static_image_mode=True,
            model_complexity=2,
            min_detection_confidence=0.5
        )

        self.hands = self.mp_hands.Hands(
            static_image_mode=True,
            max_num_hands=2,
            min_detection_confidence=0.5
        )

    def extract_pose_data(self, image_rgb):
        """Extract pose keypoints from image"""
        results = self.pose.process(image_rgb)

        if not results.pose_landmarks:
            return None

        # Extract landmarks as numpy array
        landmarks = []
        for lm in results.pose_landmarks.landmark:
            landmarks.append([lm.x, lm.y, lm.z, lm.visibility])

        return np.array(landmarks, dtype=np.float32)  # Shape: (33, 4)

    def extract_hand_data(self, image_rgb):
        """Extract hand keypoints from image"""
        results = self.hands.process(image_rgb)

        if not results.multi_hand_landmarks:
            return None, None

        left_hand = None
        right_hand = None

        for idx, hand_landmarks in enumerate(results.multi_hand_landmarks):
            # Extract landmarks
            landmarks = []
            for lm in hand_landmarks.landmark:
                landmarks.append([lm.x, lm.y, lm.z])

            hand_array = np.array(landmarks, dtype=np.float32)  # Shape: (21, 3)

            # Determine which hand
            if results.multi_handedness[idx].classification[0].label == 'Left':
                left_hand = hand_array
            else:
                right_hand = hand_array

        return left_hand, right_hand

    def process_image(self, image_path, output_path=None):
        """
        Process image and extract robot training data

        Args:
            image_path: Path to image file
            output_path: Path to save HDF5 file (optional)

        Returns:
            dict with extraction results
        """
        image_path = Path(image_path)

        if not image_path.exists():
            return {'success': False, 'error': 'Image not found'}

        print(f"🔍 Processing: {image_path.name}")

        # Read image
        image = cv2.imread(str(image_path))
        if image is None:
            return {'success': False, 'error': 'Could not read image'}

        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        height, width = image.shape[:2]

        # Extract pose
        print("   Extracting pose...")
        pose_data = self.extract_pose_data(image_rgb)

        if pose_data is None:
            return {'success': False, 'error': 'No pose detected'}

        # Extract hands
        print("   Extracting hands...")
        left_hand, right_hand = self.extract_hand_data(image_rgb)

        # Prepare output
        if output_path is None:
            output_path = image_path.with_suffix('.hdf5')
        else:
            output_path = Path(output_path)

        # Save to HDF5
        print(f"   Saving to HDF5...")
        with h5py.File(output_path, 'w') as f:
            # Image metadata
            f.attrs['source_image'] = str(image_path.name)
            f.attrs['width'] = width
            f.attrs['height'] = height
            f.attrs['extracted_at'] = datetime.now().isoformat()

            # Pose data
            f.create_dataset('pose/keypoints', data=pose_data)  # (33, 4)

            # Hand data
            if left_hand is not None:
                f.create_dataset('hands/left', data=left_hand)  # (21, 3)
            if right_hand is not None:
                f.create_dataset('hands/right', data=right_hand)  # (21, 3)

            # Image dimensions for denormalization
            f.create_dataset('metadata/image_size', data=np.array([width, height]))

        # Save JSON metadata
        metadata = {
            'source_image': str(image_path.name),
            'output_file': str(output_path.name),
            'image_size': {'width': width, 'height': height},
            'extracted_at': datetime.now().isoformat(),
            'pose_detected': True,
            'left_hand_detected': left_hand is not None,
            'right_hand_detected': right_hand is not None,
            'total_keypoints': 33 + (21 if left_hand is not None else 0) + (21 if right_hand is not None else 0)
        }

        json_path = output_path.with_suffix('.json')
        with open(json_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"   ✅ Saved: {output_path.name}")
        print(f"   ✅ Metadata: {json_path.name}")

        return {
            'success': True,
            'hdf5_file': str(output_path),
            'json_file': str(json_path),
            'metadata': metadata
        }

    def __del__(self):
        """Cleanup"""
        self.pose.close()
        self.hands.close()


def main():
    """Test image extraction pipeline"""
    import argparse

    parser = argparse.ArgumentParser(description='Extract robot training data from image')
    parser.add_argument('image', help='Path to image file')
    parser.add_argument('--output', help='Output HDF5 path (optional)')

    args = parser.parse_args()

    pipeline = ImageExtractionPipeline()
    result = pipeline.process_image(args.image, args.output)

    if result['success']:
        print("\n✅ Extraction complete!")
        print(f"   HDF5: {result['hdf5_file']}")
        print(f"   JSON: {result['json_file']}")
    else:
        print(f"\n❌ Failed: {result['error']}")


if __name__ == '__main__':
    main()
