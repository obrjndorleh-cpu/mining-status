"""
PHASE 1: COMPUTE TIMESTEP-BASED ACTIONS
From extracted data, compute what we can without new models

Input: test_video_full_extraction.json (1,127 frames)
Output: Timestep-based robot actions with deltas, velocity, gripper commands
"""

import json
import numpy as np
from pathlib import Path
from scipy.ndimage import gaussian_filter1d

class TimestepActionComputer:
    """
    Compute robot-ready timestep actions from extracted data
    """

    def __init__(self):
        print("🔧 Initializing timestep action computer...")

    def process(self, extraction_file):
        """
        Convert comprehensive extraction to timestep-based actions
        """
        print(f"\n{'='*70}")
        print(f"PHASE 1: COMPUTING TIMESTEP ACTIONS")
        print(f"{'='*70}\n")

        # Load extracted data
        print(f"📂 Loading: {extraction_file}")
        with open(extraction_file, 'r') as f:
            data = json.load(f)

        metadata = data['metadata']
        frames = data['frames']

        print(f"   Total frames: {len(frames)}")
        print(f"   Duration: {metadata['duration']:.2f}s")
        print(f"   FPS: {metadata['fps']}")

        # Extract trajectories
        print(f"\n📊 EXTRACTING TRAJECTORIES...")
        trajectories = self._extract_trajectories(frames)

        # Smooth trajectories
        print(f"\n🎯 SMOOTHING TRAJECTORIES...")
        smoothed = self._smooth_trajectories(trajectories)

        # Compute derivatives
        print(f"\n⚡ COMPUTING VELOCITIES & ACCELERATIONS...")
        derivatives = self._compute_derivatives(smoothed, metadata['fps'])

        # Compute delta actions
        print(f"\n🎮 COMPUTING DELTA ACTIONS...")
        delta_actions = self._compute_delta_actions(smoothed, derivatives, metadata['fps'])

        # Compute gripper commands
        print(f"\n🤏 COMPUTING GRIPPER COMMANDS...")
        gripper_commands = self._compute_gripper_commands(trajectories['hand_openness'])

        # Build timestep format
        print(f"\n📦 BUILDING TIMESTEP FORMAT...")
        timestep_data = self._build_timestep_format(
            frames, trajectories, smoothed, derivatives,
            delta_actions, gripper_commands, metadata
        )

        # Analyze results
        print(f"\n📈 ANALYZING RESULTS...")
        analysis = self._analyze_results(timestep_data, metadata)

        return {
            'metadata': metadata,
            'timesteps': timestep_data,
            'analysis': analysis
        }

    def _extract_trajectories(self, frames):
        """
        Extract clean trajectories from frame data
        """
        wrist_pos = []
        wrist_visibility = []
        hand_openness = []
        timestamps = []
        frame_indices = []

        for frame in frames:
            frame_indices.append(frame['frame_idx'])
            timestamps.append(frame['timestamp'])

            # Wrist position
            if frame['pose']['detected'] and 'wrist_right' in frame['pose']:
                wrist = frame['pose']['wrist_right']
                wrist_pos.append([wrist['x'], wrist['y'], wrist['z']])
                wrist_visibility.append(wrist['visibility'])
            else:
                wrist_pos.append([np.nan, np.nan, np.nan])
                wrist_visibility.append(0.0)

            # Hand openness
            if frame['hands']['detected'] and frame['hands']['hands']:
                # Use first detected hand (usually right hand)
                hand_openness.append(frame['hands']['hands'][0]['openness'])
            else:
                hand_openness.append(np.nan)

        wrist_pos = np.array(wrist_pos)
        wrist_visibility = np.array(wrist_visibility)
        hand_openness = np.array(hand_openness)

        # Interpolate missing values
        wrist_pos = self._interpolate_missing(wrist_pos)
        hand_openness = self._interpolate_missing(hand_openness)

        print(f"   Valid wrist positions: {np.sum(wrist_visibility > 0.5)}/{len(frames)}")
        print(f"   Valid hand openness: {np.sum(~np.isnan(hand_openness))}/{len(frames)}")

        return {
            'wrist_pos': wrist_pos,
            'wrist_visibility': wrist_visibility,
            'hand_openness': hand_openness,
            'timestamps': np.array(timestamps),
            'frame_indices': np.array(frame_indices)
        }

    def _interpolate_missing(self, data):
        """
        Interpolate missing values (NaN) in trajectory
        """
        if len(data.shape) == 1:
            # 1D data (e.g., hand openness)
            mask = np.isnan(data)
            if np.all(mask):
                return data  # All NaN, can't interpolate

            indices = np.arange(len(data))
            valid_indices = indices[~mask]
            valid_values = data[~mask]

            if len(valid_values) > 0:
                data[mask] = np.interp(indices[mask], valid_indices, valid_values)
        else:
            # 2D data (e.g., wrist position)
            for i in range(data.shape[1]):
                mask = np.isnan(data[:, i])
                if np.all(mask):
                    continue

                indices = np.arange(len(data))
                valid_indices = indices[~mask]
                valid_values = data[~mask, i]

                if len(valid_values) > 0:
                    data[mask, i] = np.interp(indices[mask], valid_indices, valid_values)

        return data

    def _smooth_trajectories(self, trajectories):
        """
        Apply Gaussian smoothing to reduce noise
        """
        sigma = 2.0  # Smoothing parameter

        smoothed = {}

        # Smooth wrist position (per axis)
        wrist_smooth = np.zeros_like(trajectories['wrist_pos'])
        for i in range(3):
            wrist_smooth[:, i] = gaussian_filter1d(
                trajectories['wrist_pos'][:, i],
                sigma=sigma
            )
        smoothed['wrist_pos'] = wrist_smooth

        # Smooth hand openness
        smoothed['hand_openness'] = gaussian_filter1d(
            trajectories['hand_openness'],
            sigma=sigma
        )

        print(f"   Applied Gaussian smoothing (σ={sigma})")

        return smoothed

    def _compute_derivatives(self, smoothed, fps):
        """
        Compute velocity and acceleration
        """
        dt = 1.0 / fps

        # Velocity (first derivative)
        velocity = np.diff(smoothed['wrist_pos'], axis=0) / dt
        # Pad to match length
        velocity = np.vstack([velocity, velocity[-1:]])

        # Acceleration (second derivative)
        acceleration = np.diff(velocity, axis=0) / dt
        acceleration = np.vstack([acceleration, acceleration[-1:]])

        # Speed (magnitude of velocity)
        speed = np.linalg.norm(velocity, axis=1)

        print(f"   Velocity range: {velocity.min():.3f} to {velocity.max():.3f}")
        print(f"   Speed range: {speed.min():.3f} to {speed.max():.3f}")
        print(f"   Mean speed: {speed.mean():.3f}")

        return {
            'velocity': velocity,
            'acceleration': acceleration,
            'speed': speed
        }

    def _compute_delta_actions(self, smoothed, derivatives, fps):
        """
        Compute frame-to-frame delta actions
        """
        dt = 1.0 / fps

        # Delta position (same as velocity * dt)
        delta_pos = np.diff(smoothed['wrist_pos'], axis=0)
        delta_pos = np.vstack([delta_pos, delta_pos[-1:]])

        # Delta hand openness
        delta_openness = np.diff(smoothed['hand_openness'])
        delta_openness = np.append(delta_openness, delta_openness[-1])

        print(f"   Delta position magnitude: {np.linalg.norm(delta_pos, axis=1).mean():.6f}")
        print(f"   Delta openness range: {delta_openness.min():.6f} to {delta_openness.max():.6f}")

        return {
            'delta_pos': delta_pos,
            'delta_openness': delta_openness
        }

    def _compute_gripper_commands(self, hand_openness_raw):
        """
        Convert continuous hand openness to discrete gripper commands

        Returns:
            -1: closing
             0: holding
            +1: opening
        """
        threshold = 0.02  # Threshold for detecting change

        delta_openness = np.diff(hand_openness_raw)
        delta_openness = np.append(delta_openness, delta_openness[-1])

        gripper_cmd = np.zeros(len(delta_openness))
        gripper_cmd[delta_openness < -threshold] = -1  # Closing
        gripper_cmd[delta_openness > threshold] = 1    # Opening
        # Rest remain 0 (holding)

        num_closing = np.sum(gripper_cmd == -1)
        num_holding = np.sum(gripper_cmd == 0)
        num_opening = np.sum(gripper_cmd == 1)

        print(f"   Closing frames: {num_closing}")
        print(f"   Holding frames: {num_holding}")
        print(f"   Opening frames: {num_opening}")

        return gripper_cmd

    def _build_timestep_format(self, frames, trajectories, smoothed,
                               derivatives, delta_actions, gripper_commands, metadata):
        """
        Build final timestep-based format
        """
        timesteps = []

        for i in range(len(frames)):
            timestep = {
                # Metadata
                'timestep': i,
                'frame_idx': int(trajectories['frame_indices'][i]),
                'timestamp': float(trajectories['timestamps'][i]),

                # Observations (state)
                'observations': {
                    'end_effector_pos': smoothed['wrist_pos'][i].tolist(),
                    'end_effector_pos_raw': trajectories['wrist_pos'][i].tolist(),
                    'gripper_openness': float(smoothed['hand_openness'][i]),
                    'gripper_openness_raw': float(trajectories['hand_openness'][i]),
                    'wrist_visibility': float(trajectories['wrist_visibility'][i]),
                },

                # Kinematics
                'kinematics': {
                    'velocity': derivatives['velocity'][i].tolist(),
                    'acceleration': derivatives['acceleration'][i].tolist(),
                    'speed': float(derivatives['speed'][i])
                },

                # Actions (control commands)
                'actions': {
                    'delta_pos': delta_actions['delta_pos'][i].tolist(),
                    'delta_openness': float(delta_actions['delta_openness'][i]),
                    'gripper_command': int(gripper_commands[i]),  # -1, 0, or 1
                }
            }

            timesteps.append(timestep)

        print(f"   Built {len(timesteps)} timesteps")

        return timesteps

    def _analyze_results(self, timestep_data, metadata):
        """
        Analyze the computed timestep data
        """
        print(f"\n{'='*70}")
        print(f"TIMESTEP DATA ANALYSIS")
        print(f"{'='*70}\n")

        # Extract arrays for analysis
        positions = np.array([t['observations']['end_effector_pos'] for t in timestep_data])
        velocities = np.array([t['kinematics']['velocity'] for t in timestep_data])
        speeds = np.array([t['kinematics']['speed'] for t in timestep_data])
        delta_positions = np.array([t['actions']['delta_pos'] for t in timestep_data])
        gripper_cmds = np.array([t['actions']['gripper_command'] for t in timestep_data])
        openness = np.array([t['observations']['gripper_openness'] for t in timestep_data])

        print(f"📊 POSITION STATISTICS:")
        print(f"   X range: {positions[:, 0].min():.3f} to {positions[:, 0].max():.3f}")
        print(f"   Y range: {positions[:, 1].min():.3f} to {positions[:, 1].max():.3f}")
        print(f"   Z range: {positions[:, 2].min():.3f} to {positions[:, 2].max():.3f}")
        print(f"   Total displacement: {np.linalg.norm(positions[-1] - positions[0]):.3f}")

        print(f"\n⚡ VELOCITY STATISTICS:")
        print(f"   Mean speed: {speeds.mean():.4f} units/s")
        print(f"   Max speed: {speeds.max():.4f} units/s")
        print(f"   Min speed: {speeds.min():.4f} units/s")

        print(f"\n🎮 ACTION STATISTICS:")
        print(f"   Mean delta per frame: {np.linalg.norm(delta_positions, axis=1).mean():.6f}")
        print(f"   Max delta per frame: {np.linalg.norm(delta_positions, axis=1).max():.6f}")

        print(f"\n🤏 GRIPPER STATISTICS:")
        print(f"   Opening commands: {np.sum(gripper_cmds == 1)}")
        print(f"   Holding commands: {np.sum(gripper_cmds == 0)}")
        print(f"   Closing commands: {np.sum(gripper_cmds == -1)}")
        print(f"   Openness range: {openness.min():.3f} to {openness.max():.3f}")

        # Detect motion phases
        print(f"\n🔍 MOTION PHASES:")
        high_speed_threshold = speeds.mean() + speeds.std()
        high_speed_frames = np.sum(speeds > high_speed_threshold)
        print(f"   High-speed frames: {high_speed_frames} ({high_speed_frames/len(speeds)*100:.1f}%)")
        print(f"   Low-speed frames: {len(speeds) - high_speed_frames} ({(len(speeds)-high_speed_frames)/len(speeds)*100:.1f}%)")

        return {
            'total_timesteps': len(timestep_data),
            'duration_sec': float(metadata['duration']),
            'fps': float(metadata['fps']),
            'position_range': {
                'x': [float(positions[:, 0].min()), float(positions[:, 0].max())],
                'y': [float(positions[:, 1].min()), float(positions[:, 1].max())],
                'z': [float(positions[:, 2].min()), float(positions[:, 2].max())]
            },
            'velocity_stats': {
                'mean_speed': float(speeds.mean()),
                'max_speed': float(speeds.max())
            },
            'gripper_stats': {
                'opening_frames': int(np.sum(gripper_cmds == 1)),
                'holding_frames': int(np.sum(gripper_cmds == 0)),
                'closing_frames': int(np.sum(gripper_cmds == -1))
            }
        }


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage: python compute_timestep_actions.py <extraction_file.json>")
        print("\nExample:")
        print("  python compute_timestep_actions.py test_video_full_extraction.json")
        return

    extraction_file = sys.argv[1]

    if not Path(extraction_file).exists():
        print(f"❌ File not found: {extraction_file}")
        return

    # Process
    computer = TimestepActionComputer()
    results = computer.process(extraction_file)

    # Save output
    output_file = Path(extraction_file).stem.replace('_full_extraction', '') + '_timestep_actions.json'

    print(f"\n💾 SAVING RESULTS...")
    print(f"   Output: {output_file}")

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ PHASE 1 COMPLETE")
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"   Input: {len(results['timesteps'])} frames")
    print(f"   Output: {len(results['timesteps'])} timesteps")
    print(f"   Format: Timestep-based (robot-ready)")
    print(f"   Missing: Metric depth, orientation")
    print(f"\n📌 NEXT STEPS:")
    print(f"   1. ✅ Computed: velocity, acceleration, delta actions, gripper commands")
    print(f"   2. ⏳ TODO: Add metric depth (Depth-Anything V2)")
    print(f"   3. ⏳ TODO: Add coordinate frame transformation")
    print(f"   4. ⏳ TODO: Add orientation estimation")
    print(f"   5. ⏳ TODO: Export to HDF5 format")


if __name__ == "__main__":
    main()
