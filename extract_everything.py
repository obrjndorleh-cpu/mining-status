"""
COMPREHENSIVE DATA EXTRACTION
Extract EVERY possible data point from video

Goal: See what we CAN extract, then figure out what we NEED
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import cv2
import numpy as np
import json
from datetime import datetime

from core.extractors.pose_extractor import PoseExtractor
from core.extractors.hand_tracker import HandTracker
from core.extractors.object_detector import ObjectDetector

class ComprehensiveExtractor:
    """
    Extract EVERYTHING possible from video
    """

    def __init__(self):
        print("🔬 Initializing comprehensive extraction...")
        self.pose_extractor = PoseExtractor()
        self.hand_tracker = HandTracker()
        self.object_detector = ObjectDetector()

    def extract_all(self, video_path, capture_rgb=True, target_size=(224, 224)):
        """
        Extract every single data point we can get

        Args:
            video_path: Path to video file
            capture_rgb: Store RGB frames for robot learning (default: True)
            target_size: Resize frames to this size for efficiency (default: 224x224)
        """
        print(f"\n{'='*70}")
        print(f"COMPREHENSIVE DATA EXTRACTION")
        print(f"Video: {video_path}")
        print(f"RGB Capture: {'ENABLED' if capture_rgb else 'DISABLED'}")
        print(f"Target Size: {target_size if capture_rgb else 'N/A'}")
        print(f"{'='*70}\n")

        # Load video
        cap = cv2.VideoCapture(video_path)

        # Metadata
        metadata = {
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'total_frames': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'duration': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / cap.get(cv2.CAP_PROP_FPS),
            'rgb_capture_enabled': capture_rgb,
            'rgb_target_size': target_size if capture_rgb else None
        }

        print(f"📊 VIDEO METADATA:")
        print(f"   Duration: {metadata['duration']:.2f}s")
        print(f"   Resolution: {metadata['width']}x{metadata['height']}")
        print(f"   FPS: {metadata['fps']}")
        print(f"   Total frames: {metadata['total_frames']}")
        if capture_rgb:
            print(f"   RGB Output: {target_size[0]}x{target_size[1]}")

        # Process ALL frames (no sampling)
        print(f"\n🎬 PROCESSING ALL FRAMES...")

        frame_data = []
        rgb_frames = [] if capture_rgb else None
        frame_count = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            timestamp = frame_count / metadata['fps']

            if frame_count % 30 == 0:  # Print progress every second
                print(f"   Frame {frame_count}/{metadata['total_frames']} ({timestamp:.1f}s)")

            # Store RGB frame for robot learning
            if capture_rgb:
                # Convert BGR to RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Resize to target size for efficiency
                if frame_rgb.shape[:2] != target_size:
                    frame_resized = cv2.resize(frame_rgb, target_size)
                else:
                    frame_resized = frame_rgb

                rgb_frames.append(frame_resized)

            # Extract everything from this frame
            frame_info = self.extract_frame(frame, frame_count, timestamp)
            frame_data.append(frame_info)

            frame_count += 1

        cap.release()

        print(f"\n✅ Processed {frame_count} frames")
        if capture_rgb:
            print(f"✅ Captured {len(rgb_frames)} RGB frames ({target_size[0]}x{target_size[1]})")
            # Calculate storage estimate
            frame_size_mb = (rgb_frames[0].nbytes * len(rgb_frames)) / (1024 * 1024) if rgb_frames else 0
            print(f"   Estimated RGB size: {frame_size_mb:.1f} MB (uncompressed)")

        # Analyze what we extracted
        analysis = self.analyze_extraction(frame_data, metadata)

        result = {
            'metadata': metadata,
            'frames': frame_data,
            'analysis': analysis
        }

        # Add RGB frames if captured
        if capture_rgb and rgb_frames:
            result['video_frames'] = np.array(rgb_frames, dtype=np.uint8)

        return result

    def extract_frame(self, frame, frame_idx, timestamp):
        """
        Extract ALL data from a single frame
        """
        data = {
            'frame_idx': frame_idx,
            'timestamp': timestamp
        }

        # 1. POSE DATA (33 keypoints)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pose_result = self.pose_extractor.pose.process(frame_rgb)

        if pose_result.pose_landmarks:
            landmarks = pose_result.pose_landmarks.landmark

            # Extract ALL 33 landmarks
            data['pose'] = {
                'detected': True,
                'landmarks': {}
            }

            for idx, landmark in enumerate(landmarks):
                name = self.pose_extractor.mp_pose.PoseLandmark(idx).name
                data['pose']['landmarks'][name] = {
                    'x': landmark.x,
                    'y': landmark.y,
                    'z': landmark.z,
                    'visibility': landmark.visibility
                }

            # Key points for manipulation
            data['pose']['wrist_right'] = {
                'x': landmarks[16].x,
                'y': landmarks[16].y,
                'z': landmarks[16].z,
                'visibility': landmarks[16].visibility
            }
            data['pose']['wrist_left'] = {
                'x': landmarks[15].x,
                'y': landmarks[15].y,
                'z': landmarks[15].z,
                'visibility': landmarks[15].visibility
            }
        else:
            data['pose'] = {'detected': False}

        # 2. HAND DATA (21 landmarks per hand)
        hand_result = self.hand_tracker.hands.process(frame_rgb)

        if hand_result.multi_hand_landmarks:
            data['hands'] = {'detected': True, 'hands': []}

            for hand_landmarks, handedness in zip(
                hand_result.multi_hand_landmarks,
                hand_result.multi_handedness
            ):
                hand_info = {
                    'label': handedness.classification[0].label,
                    'confidence': handedness.classification[0].score,
                    'landmarks': {}
                }

                # Extract all 21 landmarks
                for idx, landmark in enumerate(hand_landmarks.landmark):
                    name = self.hand_tracker.mp_hands.HandLandmark(idx).name
                    hand_info['landmarks'][name] = {
                        'x': landmark.x,
                        'y': landmark.y,
                        'z': landmark.z
                    }

                # Calculate hand openness
                hand_info['openness'] = self.hand_tracker._calculate_hand_openness(
                    hand_info['landmarks']
                )

                data['hands']['hands'].append(hand_info)
        else:
            data['hands'] = {'detected': False}

        # 3. OBJECT DATA (YOLO detections)
        # Only run every 5th frame (optimization)
        if frame_idx % 5 == 0:
            results = self.object_detector.model(frame, verbose=False)[0]

            data['objects'] = {'detected': True, 'objects': []}

            if results.boxes is not None:
                for box in results.boxes:
                    if float(box.conf[0]) >= self.object_detector.confidence_threshold:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        class_id = int(box.cls[0])

                        data['objects']['objects'].append({
                            'class': self.object_detector.class_names[class_id],
                            'class_id': class_id,
                            'confidence': float(box.conf[0]),
                            'bbox': {
                                'x1': float(x1),
                                'y1': float(y1),
                                'x2': float(x2),
                                'y2': float(y2),
                                'center_x': float((x1 + x2) / 2),
                                'center_y': float((y1 + y2) / 2),
                                'width': float(x2 - x1),
                                'height': float(y2 - y1)
                            }
                        })
        else:
            data['objects'] = {'detected': False, 'reason': 'skipped_for_performance'}

        # 4. IMAGE STATISTICS
        data['image_stats'] = {
            'mean_brightness': float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).mean()),
            'std_brightness': float(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).std()),
        }

        return data

    def analyze_extraction(self, frame_data, metadata):
        """
        Analyze what we successfully extracted
        """
        print(f"\n{'='*70}")
        print(f"EXTRACTION ANALYSIS")
        print(f"{'='*70}\n")

        total_frames = len(frame_data)

        # Pose detection rate
        pose_detected = sum(1 for f in frame_data if f['pose']['detected'])
        pose_rate = pose_detected / total_frames * 100

        print(f"📍 POSE TRACKING:")
        print(f"   Detected: {pose_detected}/{total_frames} frames ({pose_rate:.1f}%)")

        # Hand detection rate
        hands_detected = sum(1 for f in frame_data if f['hands']['detected'])
        hands_rate = hands_detected / total_frames * 100

        print(f"\n✋ HAND TRACKING:")
        print(f"   Detected: {hands_detected}/{total_frames} frames ({hands_rate:.1f}%)")

        # Object detection
        objects_frames = [f for f in frame_data if f['objects'].get('detected')]
        unique_objects = set()
        for f in objects_frames:
            for obj in f['objects']['objects']:
                unique_objects.add(obj['class'])

        print(f"\n📦 OBJECT DETECTION:")
        print(f"   Unique objects: {len(unique_objects)}")
        print(f"   Objects found: {sorted(unique_objects)}")

        # Wrist trajectory
        wrist_positions = []
        for f in frame_data:
            if f['pose']['detected']:
                wrist = f['pose']['wrist_right']
                if wrist['visibility'] > 0.5:
                    wrist_positions.append([
                        wrist['x'],
                        wrist['y'],
                        wrist['z']
                    ])

        wrist_positions = np.array(wrist_positions)

        print(f"\n🎯 WRIST TRAJECTORY:")
        print(f"   Valid points: {len(wrist_positions)}")
        if len(wrist_positions) > 0:
            print(f"   X range: {wrist_positions[:, 0].min():.3f} to {wrist_positions[:, 0].max():.3f}")
            print(f"   Y range: {wrist_positions[:, 1].min():.3f} to {wrist_positions[:, 1].max():.3f}")
            print(f"   Z range: {wrist_positions[:, 2].min():.3f} to {wrist_positions[:, 2].max():.3f}")

            # Compute total movement
            movement = np.linalg.norm(np.diff(wrist_positions, axis=0), axis=1)
            total_movement = movement.sum()
            print(f"   Total movement: {total_movement:.3f} (normalized units)")

        # Hand openness over time
        openness_values = []
        for f in frame_data:
            if f['hands']['detected'] and f['hands']['hands']:
                openness_values.append(f['hands']['hands'][0]['openness'])

        if openness_values:
            openness_values = np.array(openness_values)
            print(f"\n🤏 HAND OPENNESS:")
            print(f"   Min: {openness_values.min():.3f}")
            print(f"   Max: {openness_values.max():.3f}")
            print(f"   Mean: {openness_values.mean():.3f}")
            print(f"   Std: {openness_values.std():.3f}")

        return {
            'pose_detection_rate': pose_rate,
            'hands_detection_rate': hands_rate,
            'unique_objects': list(unique_objects),
            'wrist_trajectory_points': len(wrist_positions),
            'hand_openness_range': [float(openness_values.min()), float(openness_values.max())] if len(openness_values) > 0 else None
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_everything.py <video_file>")
        return

    video_path = sys.argv[1]

    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        return

    extractor = ComprehensiveExtractor()
    results = extractor.extract_all(video_path)

    # Save RGB frames separately (numpy can't be JSON serialized)
    video_frames = results.pop('video_frames', None)

    # Save frame data and metadata to JSON
    output_file = Path(video_path).stem + "_full_extraction.json"
    print(f"\n💾 Saving frame data to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)

    # Save RGB frames to numpy file
    if video_frames is not None:
        rgb_file = Path(video_path).stem + "_rgb_frames.npz"
        print(f"💾 Saving RGB frames to: {rgb_file}")
        np.savez_compressed(rgb_file, rgb_frames=video_frames)
        print(f"   RGB frames: {video_frames.shape}")
        print(f"   Size: {Path(rgb_file).stat().st_size / (1024*1024):.1f} MB")

    print(f"\n✅ EXTRACTION COMPLETE")
    print(f"   Total data points extracted: {len(results['frames']) * 100}+")
    print(f"   Frame data: {output_file}")
    if video_frames is not None:
        print(f"   RGB frames: {rgb_file}")

if __name__ == "__main__":
    main()
