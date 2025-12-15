"""
COMPUTE HAND ORIENTATION
Add hand rotation/orientation to existing extraction data

Computes:
- Hand normal vector (palm orientation)
- Hand rotation angles (roll, pitch, yaw)
- Wrist rotation rate (for twist detection)
"""

import json
import numpy as np
from pathlib import Path


class HandOrientationComputer:
    """
    Compute hand orientation from 21 landmarks
    """

    def __init__(self):
        print("🔧 Hand Orientation Computer")

    def process(self, extraction_file):
        """
        Add hand orientation to extraction data
        """
        print(f"\n{'='*70}")
        print(f"COMPUTING HAND ORIENTATION")
        print(f"{'='*70}\n")

        # Load extraction
        print(f"📂 Loading: {extraction_file}")
        with open(extraction_file, 'r') as f:
            data = json.load(f)

        frames = data['frames']
        print(f"   Frames: {len(frames)}\n")

        # Compute orientation for each frame
        print("🔄 Computing orientations...")
        orientations_added = 0

        for frame_idx, frame in enumerate(frames):
            if frame_idx % 100 == 0:
                print(f"   Frame {frame_idx}/{len(frames)}")

            if not frame['hands']['detected']:
                continue

            hands = frame['hands'].get('hands', [])
            if not hands:
                continue

            # Compute orientation for first hand
            hand = hands[0]
            landmarks = hand['landmarks']

            orientation = self._compute_orientation(landmarks)

            if orientation:
                hand['orientation'] = orientation
                orientations_added += 1

        print(f"\n✅ Added orientation to {orientations_added} frames\n")

        # Save results
        output_file = Path(extraction_file).stem + '_with_orientation.json'
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"💾 Saved to: {output_file}\n")

        return output_file

    def _compute_orientation(self, landmarks):
        """
        Compute hand orientation from landmarks

        Returns:
            {
                'palm_normal': [x, y, z],  # Normal vector to palm
                'roll': float,   # Rotation around wrist->middle_finger axis (degrees)
                'pitch': float,  # Tilt up/down (degrees)
                'yaw': float     # Rotation left/right (degrees)
            }
        """
        try:
            # Key points for orientation
            wrist = np.array([
                landmarks['WRIST']['x'],
                landmarks['WRIST']['y'],
                landmarks['WRIST']['z']
            ])

            middle_mcp = np.array([  # Middle finger base
                landmarks['MIDDLE_FINGER_MCP']['x'],
                landmarks['MIDDLE_FINGER_MCP']['y'],
                landmarks['MIDDLE_FINGER_MCP']['z']
            ])

            index_mcp = np.array([  # Index finger base
                landmarks['INDEX_FINGER_MCP']['x'],
                landmarks['INDEX_FINGER_MCP']['y'],
                landmarks['INDEX_FINGER_MCP']['z']
            ])

            pinky_mcp = np.array([  # Pinky finger base
                landmarks['PINKY_MCP']['x'],
                landmarks['PINKY_MCP']['y'],
                landmarks['PINKY_MCP']['z']
            ])

            # Compute hand coordinate frame
            # X-axis: wrist → middle finger (forward)
            x_axis = middle_mcp - wrist
            x_axis = x_axis / (np.linalg.norm(x_axis) + 1e-8)

            # Y-axis: index → pinky (across palm)
            y_axis_raw = pinky_mcp - index_mcp

            # Z-axis: normal to palm (using cross product)
            z_axis = np.cross(x_axis, y_axis_raw)
            z_axis = z_axis / (np.linalg.norm(z_axis) + 1e-8)

            # Re-orthogonalize Y-axis
            y_axis = np.cross(z_axis, x_axis)
            y_axis = y_axis / (np.linalg.norm(y_axis) + 1e-8)

            # Palm normal is Z-axis
            palm_normal = z_axis

            # Compute Euler angles (roll, pitch, yaw)
            # Roll: rotation around X-axis (wrist->finger direction)
            # Pitch: tilt up/down
            # Yaw: rotation left/right

            # Pitch: angle of x_axis from horizontal plane
            pitch = np.arcsin(-x_axis[1])  # Negative because Y is down in image

            # Yaw: horizontal rotation
            yaw = np.arctan2(x_axis[0], -x_axis[2])

            # Roll: rotation of hand around its forward axis
            # Project y_axis onto plane perpendicular to x_axis
            roll = np.arctan2(y_axis[1], y_axis[2])

            return {
                'palm_normal': palm_normal.tolist(),
                'x_axis': x_axis.tolist(),  # Forward (wrist->fingers)
                'y_axis': y_axis.tolist(),  # Across palm
                'z_axis': z_axis.tolist(),  # Out of palm
                'roll': float(np.degrees(roll)),
                'pitch': float(np.degrees(pitch)),
                'yaw': float(np.degrees(yaw))
            }

        except (KeyError, TypeError, ZeroDivisionError) as e:
            return None


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python compute_hand_orientation.py <full_extraction.json>")
        print("\nExample:")
        print("  python compute_hand_orientation.py test_video_03_full_extraction_with_colors.json")
        return

    extraction_file = sys.argv[1]

    if not Path(extraction_file).exists():
        print(f"❌ File not found: {extraction_file}")
        return

    computer = HandOrientationComputer()
    output_file = computer.process(extraction_file)

    print(f"✅ COMPLETE")
    print(f"   Next: Use this file for action detection with rotation/twist/pour support")


if __name__ == "__main__":
    main()
