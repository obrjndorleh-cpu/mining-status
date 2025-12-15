"""
PHASE 2.5: CONVERT TO METRIC 3D COORDINATES
Transform normalized coords + depth → metric 3D (x, y, z in arbitrary units)

Note: Units are still relative until we add scale calibration
"""

import json
import numpy as np
from pathlib import Path

class MetricCoordinateConverter:
    """
    Convert normalized 2D + depth to metric 3D coordinates
    """

    def __init__(self, video_width, video_height, focal_length_estimate=None):
        """
        Args:
            video_width: Video width in pixels
            video_height: Video height in pixels
            focal_length_estimate: Focal length in pixels (None = auto-estimate)
        """
        print(f"🔧 Initializing Metric Coordinate Converter...")

        self.width = video_width
        self.height = video_height

        # Estimate focal length if not provided
        # Common heuristic: focal_length ≈ max(width, height)
        if focal_length_estimate is None:
            self.focal_length = max(video_width, video_height) * 0.8
            print(f"   Estimated focal length: {self.focal_length:.1f} pixels")
        else:
            self.focal_length = focal_length_estimate
            print(f"   Using focal length: {self.focal_length:.1f} pixels")

        # Principal point (optical center) - typically image center
        self.cx = video_width / 2.0
        self.cy = video_height / 2.0

        print(f"   Principal point: ({self.cx:.1f}, {self.cy:.1f})")
        print(f"   Resolution: {video_width}x{video_height}")

    def process(self, depth_file):
        """
        Convert all timesteps to metric 3D coordinates

        Args:
            depth_file: Path to JSON with depth data
        """
        print(f"\n{'='*70}")
        print(f"CONVERTING TO METRIC 3D COORDINATES")
        print(f"{'='*70}\n")

        # Load data
        print(f"📂 Loading: {depth_file}")
        with open(depth_file, 'r') as f:
            data = json.load(f)

        timesteps = data['timesteps']
        print(f"   Timesteps: {len(timesteps)}")

        # Convert each timestep
        print(f"\n🔄 CONVERTING COORDINATES...")
        converted_timesteps = []

        for i, ts in enumerate(timesteps):
            if i % 100 == 0:
                print(f"   Timestep {i}/{len(timesteps)}")

            converted_ts = self._convert_timestep(ts)
            converted_timesteps.append(converted_ts)

        # Recompute kinematics with metric coordinates
        print(f"\n⚡ RECOMPUTING KINEMATICS WITH METRIC COORDINATES...")
        fps = data['metadata']['fps']
        converted_timesteps = self._recompute_kinematics(converted_timesteps, fps)

        # Analyze results
        print(f"\n📊 ANALYZING METRIC COORDINATES...")
        analysis = self._analyze_metric_coords(converted_timesteps)

        return {
            'metadata': {
                **data['metadata'],
                'coordinate_system': 'camera_frame_metric',
                'focal_length_pixels': self.focal_length,
                'principal_point': [self.cx, self.cy],
                'units': 'relative_metric (not yet absolute meters)'
            },
            'timesteps': converted_timesteps,
            'analysis': {
                **data.get('analysis', {}),
                'metric_coords': analysis
            }
        }

    def _convert_timestep(self, ts):
        """
        Convert a single timestep to metric 3D
        """
        # Get normalized coordinates and depth
        x_norm, y_norm, z_relative = ts['observations']['end_effector_pos']
        depth = ts['observations']['depth_raw']

        # Convert normalized to pixel coordinates
        x_pixels = x_norm * self.width
        y_pixels = y_norm * self.height

        # Apply pinhole camera model
        # x_cam = (x_pixels - cx) * depth / focal_length
        x_metric = (x_pixels - self.cx) * depth / self.focal_length
        y_metric = (y_pixels - self.cy) * depth / self.focal_length
        z_metric = depth

        # Create enhanced timestep
        enhanced_ts = {
            **ts,
            'observations': {
                **ts['observations'],
                # Keep original normalized
                'end_effector_pos_normalized': [x_norm, y_norm, z_relative],
                # Add metric 3D
                'end_effector_pos': [x_metric, y_metric, z_metric],
                'end_effector_pos_metric': [x_metric, y_metric, z_metric]
            }
        }

        return enhanced_ts

    def _recompute_kinematics(self, timesteps, fps):
        """
        Recompute velocity, acceleration with metric coordinates
        """
        from scipy.ndimage import gaussian_filter1d

        dt = 1.0 / fps

        # Extract metric positions
        positions = np.array([
            ts['observations']['end_effector_pos_metric']
            for ts in timesteps
        ])

        # Velocity (numerical derivative)
        velocity = np.diff(positions, axis=0) / dt
        velocity = np.vstack([velocity, velocity[-1:]])

        # Smooth velocity
        velocity_smooth = np.zeros_like(velocity)
        for i in range(3):
            velocity_smooth[:, i] = gaussian_filter1d(velocity[:, i], sigma=2.0)

        # Acceleration
        acceleration = np.diff(velocity_smooth, axis=0) / dt
        acceleration = np.vstack([acceleration, acceleration[-1:]])

        # Speed
        speed = np.linalg.norm(velocity_smooth, axis=1)

        # Update timesteps
        for i, ts in enumerate(timesteps):
            ts['kinematics'] = {
                'velocity': velocity_smooth[i].tolist(),
                'acceleration': acceleration[i].tolist(),
                'speed': float(speed[i])
            }

            # Recompute delta actions
            if i > 0:
                delta_pos = positions[i] - positions[i-1]
            else:
                delta_pos = np.zeros(3)

            ts['actions']['delta_pos'] = delta_pos.tolist()

        return timesteps

    def _analyze_metric_coords(self, timesteps):
        """
        Analyze metric 3D coordinates
        """
        print(f"\n{'='*70}")
        print(f"METRIC COORDINATE ANALYSIS")
        print(f"{'='*70}\n")

        # Extract positions
        positions = np.array([
            ts['observations']['end_effector_pos_metric']
            for ts in timesteps
        ])

        velocities = np.array([
            ts['kinematics']['velocity']
            for ts in timesteps
        ])

        speeds = np.array([
            ts['kinematics']['speed']
            for ts in timesteps
        ])

        print(f"📊 POSITION STATISTICS (metric units):")
        print(f"   X range: {positions[:, 0].min():.3f} to {positions[:, 0].max():.3f}")
        print(f"   Y range: {positions[:, 1].min():.3f} to {positions[:, 1].max():.3f}")
        print(f"   Z range: {positions[:, 2].min():.3f} to {positions[:, 2].max():.3f}")

        # Total displacement
        total_displacement = np.linalg.norm(positions[-1] - positions[0])
        print(f"   Total displacement: {total_displacement:.3f}")

        # Workspace volume
        workspace_volume = (
            (positions[:, 0].max() - positions[:, 0].min()) *
            (positions[:, 1].max() - positions[:, 1].min()) *
            (positions[:, 2].max() - positions[:, 2].min())
        )
        print(f"   Workspace volume: {workspace_volume:.3f} cubic units")

        print(f"\n⚡ VELOCITY STATISTICS (metric units/s):")
        print(f"   Mean speed: {speeds.mean():.4f}")
        print(f"   Max speed: {speeds.max():.4f}")
        print(f"   Speed std: {speeds.std():.4f}")

        # Velocity components
        print(f"\n   Velocity components (mean):")
        print(f"     X: {velocities[:, 0].mean():.4f}")
        print(f"     Y: {velocities[:, 1].mean():.4f}")
        print(f"     Z: {velocities[:, 2].mean():.4f}")

        return {
            'position_range': {
                'x': [float(positions[:, 0].min()), float(positions[:, 0].max())],
                'y': [float(positions[:, 1].min()), float(positions[:, 1].max())],
                'z': [float(positions[:, 2].min()), float(positions[:, 2].max())]
            },
            'workspace_volume': float(workspace_volume),
            'total_displacement': float(total_displacement),
            'velocity_stats': {
                'mean_speed': float(speeds.mean()),
                'max_speed': float(speeds.max()),
                'mean_components': {
                    'x': float(velocities[:, 0].mean()),
                    'y': float(velocities[:, 1].mean()),
                    'z': float(velocities[:, 2].mean())
                }
            }
        }


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python convert_to_metric_3d.py <depth_file.json>")
        print("\nExample:")
        print("  python convert_to_metric_3d.py test_video_with_depth.json")
        return

    depth_file = sys.argv[1]

    if not Path(depth_file).exists():
        print(f"❌ File not found: {depth_file}")
        return

    # Load metadata to get video dimensions
    with open(depth_file, 'r') as f:
        data = json.load(f)

    video_width, video_height = data['metadata']['video_resolution']

    # Create converter
    converter = MetricCoordinateConverter(video_width, video_height)
    results = converter.process(depth_file)

    # Save output
    output_file = Path(depth_file).stem.replace('_with_depth', '') + '_metric_3d.json'

    print(f"\n💾 SAVING RESULTS...")
    print(f"   Output: {output_file}")

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ METRIC CONVERSION COMPLETE")
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"   Input: {len(results['timesteps'])} timesteps")
    print(f"   Output: {len(results['timesteps'])} timesteps in metric 3D")
    print(f"   Coordinate system: Camera frame (right-handed)")
    print(f"   Units: Relative metric (scale calibration needed)")
    print(f"\n⚠️  NOTE: Coordinates are in relative metric units")
    print(f"   To get absolute meters, multiply by calibration scale factor")
    print(f"\n📌 NEXT STEPS:")
    print(f"   1. ✅ Computed: velocity, acceleration, delta actions, gripper commands")
    print(f"   2. ✅ Added: metric depth estimation")
    print(f"   3. ✅ Converted: to metric 3D coordinates")
    print(f"   4. ⏳ TODO: Scale calibration (relative → absolute meters)")
    print(f"   5. ⏳ TODO: Coordinate frame transformation (camera → world)")
    print(f"   6. ⏳ TODO: Add orientation estimation")
    print(f"   7. ⏳ TODO: Export to HDF5 format")


if __name__ == "__main__":
    main()
