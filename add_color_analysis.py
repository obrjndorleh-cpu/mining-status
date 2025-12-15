"""
ADD COLOR ANALYSIS
Extract color information for robot tasks like sorting, classification

Color is critical for:
- Object sorting (red vs blue blocks)
- Object identification (ripe vs unripe fruit)
- State detection (on/off indicators)
"""

import cv2
import json
import numpy as np
from pathlib import Path
from collections import Counter

class ColorAnalyzer:
    """
    Extract color information from video frames
    """

    def __init__(self):
        print("🎨 Initializing Color Analyzer...")

    def process(self, video_path, extraction_file):
        """
        Add color analysis to existing extraction

        Args:
            video_path: Path to video
            extraction_file: Path to full extraction JSON
        """
        print(f"\n{'='*70}")
        print(f"ADDING COLOR ANALYSIS")
        print(f"{'='*70}\n")

        # Load extraction data
        print(f"📂 Loading extraction: {extraction_file}")
        with open(extraction_file, 'r') as f:
            data = json.load(f)

        frames_data = data['frames']
        metadata = data['metadata']

        # Load video
        print(f"📹 Loading video: {video_path}")
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        print(f"\n🎨 EXTRACTING COLOR INFORMATION...")

        enhanced_frames = []
        frame_idx = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % 100 == 0:
                print(f"   Frame {frame_idx}/{len(frames_data)}")

            # Get corresponding extraction data
            frame_data = frames_data[frame_idx]

            # Extract colors
            color_info = self._extract_frame_colors(frame, frame_data)

            # Add to frame data
            enhanced_frame = {
                **frame_data,
                'colors': color_info
            }

            enhanced_frames.append(enhanced_frame)
            frame_idx += 1

        cap.release()

        print(f"\n✅ Processed {frame_idx} frames with color")

        # Analyze color patterns
        print(f"\n📊 ANALYZING COLOR PATTERNS...")
        color_analysis = self._analyze_colors(enhanced_frames)

        return {
            'metadata': {
                **metadata,
                'color_analysis_enabled': True,
                'color_space': 'HSV + RGB'
            },
            'frames': enhanced_frames,
            'analysis': {
                **data.get('analysis', {}),
                'colors': color_analysis
            }
        }

    def _extract_frame_colors(self, frame, frame_data):
        """
        Extract color information from a single frame
        """
        height, width = frame.shape[:2]

        # Convert to different color spaces
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        frame_lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

        color_info = {
            'scene_colors': {},
            'hand_colors': {},
            'object_colors': {},
            'person_clothing': {}
        }

        # 1. Scene-level color statistics
        color_info['scene_colors'] = {
            'dominant_rgb': self._get_dominant_color(frame_rgb),
            'mean_rgb': frame_rgb.mean(axis=(0, 1)).tolist(),
            'brightness': float(frame_lab[:, :, 0].mean()),  # L channel
            'saturation': float(frame_hsv[:, :, 1].mean())   # S channel
        }

        # 2. Hand region colors (if hand detected)
        if frame_data['hands'].get('detected'):
            hand_colors = []
            for hand in frame_data['hands']['hands']:
                # Get bounding box of hand landmarks
                landmarks = hand['landmarks']
                x_coords = [landmarks[lm]['x'] for lm in landmarks]
                y_coords = [landmarks[lm]['y'] for lm in landmarks]

                x_min = int(min(x_coords) * width)
                x_max = int(max(x_coords) * width)
                y_min = int(min(y_coords) * height)
                y_max = int(max(y_coords) * height)

                # Clamp to valid range
                x_min = max(0, x_min)
                x_max = min(width, x_max)
                y_min = max(0, y_min)
                y_max = min(height, y_max)

                if x_max > x_min and y_max > y_min:
                    hand_region = frame_rgb[y_min:y_max, x_min:x_max]

                    if hand_region.size > 0:
                        hand_colors.append({
                            'label': hand['label'],
                            'mean_rgb': hand_region.mean(axis=(0, 1)).tolist(),
                            'dominant_rgb': self._get_dominant_color(hand_region),
                            'skin_tone_estimate': self._estimate_skin_tone(hand_region)
                        })

            color_info['hand_colors'] = hand_colors

        # 3. Object region colors (if objects detected)
        if frame_data['objects'].get('detected') and 'objects' in frame_data['objects']:
            object_colors = []
            for obj in frame_data['objects']['objects']:
                bbox = obj['bbox']
                x1 = int(bbox['x1'])
                y1 = int(bbox['y1'])
                x2 = int(bbox['x2'])
                y2 = int(bbox['y2'])

                # Clamp to valid range
                x1 = max(0, min(width, x1))
                x2 = max(0, min(width, x2))
                y1 = max(0, min(height, y1))
                y2 = max(0, min(height, y2))

                if x2 > x1 and y2 > y1:
                    obj_region = frame_rgb[y1:y2, x1:x2]

                    if obj_region.size > 0:
                        object_colors.append({
                            'class': obj['class'],
                            'mean_rgb': obj_region.mean(axis=(0, 1)).tolist(),
                            'dominant_rgb': self._get_dominant_color(obj_region),
                            'color_name': self._rgb_to_color_name(
                                obj_region.mean(axis=(0, 1))
                            )
                        })

            color_info['object_colors'] = object_colors

        # 4. Person clothing colors (extract from torso region)
        if frame_data['pose'].get('detected'):
            clothing_colors = self._extract_clothing_colors(frame_rgb, frame_data['pose'], width, height)
            color_info['person_clothing'] = clothing_colors

        return color_info

    def _get_dominant_color(self, region, k=1):
        """
        Get dominant color in region using k-means clustering
        """
        # Reshape to list of pixels
        pixels = region.reshape(-1, 3)

        # Sample if too large (for performance)
        if len(pixels) > 1000:
            indices = np.random.choice(len(pixels), 1000, replace=False)
            pixels = pixels[indices]

        # Use k-means to find dominant color
        from scipy.cluster.vq import kmeans, vq

        try:
            pixels_float = pixels.astype(np.float32)
            centroids, _ = kmeans(pixels_float, k)
            dominant = centroids[0].astype(int).tolist()
        except:
            # Fallback to mean
            dominant = pixels.mean(axis=0).astype(int).tolist()

        return dominant

    def _estimate_skin_tone(self, hand_region):
        """
        Estimate skin tone category
        """
        mean_color = hand_region.mean(axis=(0, 1))
        r, g, b = mean_color

        # Simple heuristic for skin tone classification
        # Based on RGB ratios typical of human skin
        if r > 200 and g > 180:
            return "light"
        elif r > 150 and g > 100:
            return "medium"
        else:
            return "dark"

    def _extract_clothing_colors(self, frame_rgb, pose_data, width, height):
        """
        Extract clothing colors from torso region
        """
        if 'landmarks' not in pose_data:
            return {}

        landmarks = pose_data['landmarks']

        # Define torso region using shoulders and hips
        try:
            # Get key landmarks
            left_shoulder = landmarks.get('LEFT_SHOULDER', {})
            right_shoulder = landmarks.get('RIGHT_SHOULDER', {})
            left_hip = landmarks.get('LEFT_HIP', {})
            right_hip = landmarks.get('RIGHT_HIP', {})

            if not all([left_shoulder, right_shoulder, left_hip, right_hip]):
                return {}

            # Calculate torso bounding box
            x_coords = [
                left_shoulder['x'] * width,
                right_shoulder['x'] * width,
                left_hip['x'] * width,
                right_hip['x'] * width
            ]
            y_coords = [
                left_shoulder['y'] * height,
                right_shoulder['y'] * height,
                left_hip['y'] * height,
                right_hip['y'] * height
            ]

            x_min = int(max(0, min(x_coords) - 20))  # Add margin
            x_max = int(min(width, max(x_coords) + 20))
            y_min = int(max(0, min(y_coords)))
            y_max = int(min(height, max(y_coords)))

            if x_max > x_min and y_max > y_min:
                torso_region = frame_rgb[y_min:y_max, x_min:x_max]

                if torso_region.size > 0:
                    mean_rgb = torso_region.mean(axis=(0, 1))
                    dominant = self._get_dominant_color(torso_region)

                    return {
                        'upper_body_mean_rgb': mean_rgb.tolist(),
                        'upper_body_dominant_rgb': dominant,
                        'upper_body_color_name': self._rgb_to_color_name(mean_rgb),
                        'region_size': torso_region.shape[:2]
                    }
        except Exception as e:
            pass

        return {}

    def _rgb_to_color_name(self, rgb):
        """
        Convert RGB to basic color name
        """
        r, g, b = rgb

        # Simple color classification
        max_channel = max(r, g, b)
        min_channel = min(r, g, b)

        # Check if grayscale
        if max_channel - min_channel < 30:
            if max_channel < 50:
                return "black"
            elif max_channel > 200:
                return "white"
            else:
                return "gray"

        # Check dominant channel
        if r > g and r > b:
            if r > 200:
                return "red"
            else:
                return "brown"
        elif g > r and g > b:
            return "green"
        elif b > r and b > g:
            return "blue"
        elif r > 150 and g > 150:
            return "yellow"
        elif r > 150 and b > 150:
            return "magenta"
        elif g > 150 and b > 150:
            return "cyan"
        else:
            return "mixed"

    def _analyze_colors(self, frames):
        """
        Analyze color patterns across all frames
        """
        print(f"\n{'='*70}")
        print(f"COLOR ANALYSIS")
        print(f"{'='*70}\n")

        # Collect scene brightness over time
        brightness = [f['colors']['scene_colors']['brightness'] for f in frames]
        saturation = [f['colors']['scene_colors']['saturation'] for f in frames]

        print(f"📊 SCENE LIGHTING:")
        print(f"   Average brightness: {np.mean(brightness):.1f}/255")
        print(f"   Brightness range: {np.min(brightness):.1f} to {np.max(brightness):.1f}")
        print(f"   Average saturation: {np.mean(saturation):.1f}/255")

        # Lighting consistency
        brightness_std = np.std(brightness)
        if brightness_std < 10:
            lighting = "Consistent (good for robots)"
        elif brightness_std < 30:
            lighting = "Moderate variation"
        else:
            lighting = "High variation (challenging)"

        print(f"   Lighting consistency: {lighting}")

        # Analyze object colors if available
        object_colors = []
        for frame in frames:
            if frame['colors']['object_colors']:
                for obj_color in frame['colors']['object_colors']:
                    object_colors.append({
                        'class': obj_color['class'],
                        'color_name': obj_color['color_name'],
                        'rgb': obj_color['mean_rgb']
                    })

        if object_colors:
            print(f"\n🎨 OBJECT COLORS DETECTED:")
            # Count color occurrences per object class
            color_counts = {}
            for obj in object_colors:
                key = f"{obj['class']} ({obj['color_name']})"
                color_counts[key] = color_counts.get(key, 0) + 1

            for obj_color, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
                print(f"   • {obj_color}: {count} frames")

        # Hand skin tone
        hand_tones = []
        for frame in frames:
            if frame['colors']['hand_colors']:
                for hand in frame['colors']['hand_colors']:
                    hand_tones.append(hand['skin_tone_estimate'])

        if hand_tones:
            most_common_tone = Counter(hand_tones).most_common(1)[0][0]
            print(f"\n✋ HAND SKIN TONE: {most_common_tone}")

        # Analyze clothing colors
        clothing_colors = []
        for frame in frames:
            if frame['colors']['person_clothing']:
                clothing = frame['colors']['person_clothing']
                if 'upper_body_color_name' in clothing:
                    clothing_colors.append(clothing['upper_body_color_name'])

        if clothing_colors:
            clothing_counter = Counter(clothing_colors)
            most_common_clothing = clothing_counter.most_common(3)
            print(f"\n👕 OUTFIT COLORS DETECTED:")
            for color, count in most_common_clothing:
                freq = count / len(clothing_colors) * 100
                print(f"   • {color}: {count} frames ({freq:.1f}%)")

        return {
            'scene_brightness_mean': float(np.mean(brightness)),
            'scene_saturation_mean': float(np.mean(saturation)),
            'lighting_consistency': lighting,
            'object_colors_detected': len(object_colors) > 0,
            'clothing_colors_detected': len(clothing_colors) > 0
        }


def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python add_color_analysis.py <video_file> <full_extraction.json>")
        print("\nExample:")
        print("  python add_color_analysis.py test_video.mp4 test_video_full_extraction.json")
        return

    video_path = sys.argv[1]
    extraction_file = sys.argv[2]

    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        return

    if not Path(extraction_file).exists():
        print(f"❌ Extraction file not found: {extraction_file}")
        return

    # Process
    analyzer = ColorAnalyzer()
    results = analyzer.process(video_path, extraction_file)

    # Save output
    output_file = Path(extraction_file).stem + '_with_colors.json'

    print(f"\n💾 SAVING RESULTS...")
    print(f"   Output: {output_file}")

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ COLOR ANALYSIS COMPLETE")
    print(f"\n{'='*70}")
    print(f"WHY COLOR MATTERS FOR ROBOTS")
    print(f"{'='*70}")
    print(f"\n🤖 Robot tasks that need color:")
    print(f"   • Sorting objects (red vs blue blocks)")
    print(f"   • Quality inspection (ripe vs unripe fruit)")
    print(f"   • State detection (LED on/off, indicator lights)")
    print(f"   • Object identification (distinguish similar objects)")
    print(f"   • Safety (recognize warning colors)")
    print(f"\n📦 What we now capture:")
    print(f"   • Scene lighting conditions")
    print(f"   • Dominant colors in hand region")
    print(f"   • Color of each detected object")
    print(f"   • RGB values for precise color matching")


if __name__ == "__main__":
    main()
