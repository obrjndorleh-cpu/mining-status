"""
PHASE 2: ADD METRIC DEPTH
Use Depth-Anything V2 to convert normalized coordinates to metric depth

Input: test_video.mp4 + test_video_timestep_actions.json
Output: Enhanced timestep data with metric 3D coordinates
"""

import cv2
import json
import numpy as np
import torch
from pathlib import Path
from depth_anything_v2.dpt import DepthAnythingV2
from tqdm import tqdm

class MetricDepthAdder:
    """
    Add metric depth estimation to timestep data
    """

    def __init__(self, encoder='vits'):
        """
        Args:
            encoder: 'vits' (small, fast), 'vitb' (medium), 'vitl' (large, accurate)
        """
        print(f"🔧 Initializing Metric Depth Adder...")

        # Model configuration
        self.encoder = encoder
        model_configs = {
            'vits': {'encoder': 'vits', 'features': 64, 'out_channels': [48, 96, 192, 384]},
            'vitb': {'encoder': 'vitb', 'features': 128, 'out_channels': [96, 192, 384, 768]},
            'vitl': {'encoder': 'vitl', 'features': 256, 'out_channels': [256, 512, 1024, 1024]}
        }

        print(f"   Model: Depth-Anything V2 ({encoder})")

        # Device
        self.device = 'mps' if torch.backends.mps.is_available() else 'cpu'
        print(f"   Device: {self.device}")

        # Load model
        print(f"   Loading pretrained weights...")
        self.model = DepthAnythingV2(**model_configs[encoder])

        checkpoint_url = f'https://huggingface.co/depth-anything/Depth-Anything-V2-{encoder.upper()}/resolve/main/depth_anything_v2_{encoder}.pth'
        checkpoint = torch.hub.load_state_dict_from_url(checkpoint_url, map_location='cpu')
        self.model.load_state_dict(checkpoint)

        self.model = self.model.to(self.device)
        self.model.eval()

        print(f"   ✅ Model loaded")

    def process(self, video_path, timestep_file):
        """
        Add metric depth to timestep data

        Args:
            video_path: Path to original video
            timestep_file: Path to timestep_actions.json
        """
        print(f"\n{'='*70}")
        print(f"PHASE 2: ADDING METRIC DEPTH")
        print(f"{'='*70}\n")

        # Load timestep data
        print(f"📂 Loading timestep data: {timestep_file}")
        with open(timestep_file, 'r') as f:
            data = json.load(f)

        metadata = data['metadata']
        timesteps = data['timesteps']

        print(f"   Timesteps: {len(timesteps)}")
        print(f"   Duration: {metadata['duration']:.2f}s")

        # Load video
        print(f"\n📹 Loading video: {video_path}")
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        video_fps = cap.get(cv2.CAP_PROP_FPS)
        video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        print(f"   Resolution: {video_width}x{video_height}")
        print(f"   FPS: {video_fps}")

        # Process all frames
        print(f"\n🎬 PROCESSING FRAMES WITH DEPTH MODEL...")

        depth_maps = []
        frame_idx = 0

        with torch.no_grad():
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                if frame_idx % 30 == 0:
                    print(f"   Frame {frame_idx}/{len(timesteps)}")

                # Run depth estimation
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                depth_map = self.model.infer_image(frame_rgb)

                depth_maps.append(depth_map)
                frame_idx += 1

        cap.release()

        print(f"\n✅ Processed {len(depth_maps)} frames")

        # Extract depth at wrist positions
        print(f"\n🎯 EXTRACTING DEPTH AT WRIST POSITIONS...")
        enhanced_timesteps = self._add_depth_to_timesteps(
            timesteps, depth_maps, video_width, video_height
        )

        # Analyze depth distribution
        print(f"\n📊 ANALYZING DEPTH DISTRIBUTION...")
        analysis = self._analyze_depth(enhanced_timesteps, depth_maps)

        return {
            'metadata': {
                **metadata,
                'depth_model': self.encoder,
                'depth_device': self.device,
                'video_resolution': [video_width, video_height]
            },
            'timesteps': enhanced_timesteps,
            'analysis': {
                **data.get('analysis', {}),
                'depth_stats': analysis
            }
        }

    def _add_depth_to_timesteps(self, timesteps, depth_maps, width, height):
        """
        Add depth values to each timestep
        """
        enhanced = []

        for i, ts in enumerate(timesteps):
            if i >= len(depth_maps):
                break

            depth_map = depth_maps[i]

            # Get normalized wrist position
            wrist_pos = ts['observations']['end_effector_pos']
            x_norm, y_norm, z_relative = wrist_pos

            # Convert normalized to pixel coordinates
            x_pixel = int(x_norm * width)
            y_pixel = int(y_norm * height)

            # Clamp to valid range
            x_pixel = int(np.clip(x_pixel, 0, width - 1))
            y_pixel = int(np.clip(y_pixel, 0, height - 1))

            # Extract depth at wrist position
            depth_value = float(depth_map[y_pixel, x_pixel])

            # Create enhanced timestep
            enhanced_ts = {
                **ts,
                'observations': {
                    **ts['observations'],
                    'depth_raw': depth_value,  # Raw depth from model
                    'depth_pixel_coords': [x_pixel, y_pixel],
                },
                'depth_map_stats': {
                    'min': float(depth_map.min()),
                    'max': float(depth_map.max()),
                    'mean': float(depth_map.mean()),
                    'std': float(depth_map.std())
                }
            }

            enhanced.append(enhanced_ts)

        print(f"   Enhanced {len(enhanced)} timesteps")
        return enhanced

    def _analyze_depth(self, timesteps, depth_maps):
        """
        Analyze depth distribution
        """
        print(f"\n{'='*70}")
        print(f"DEPTH ANALYSIS")
        print(f"{'='*70}\n")

        # Extract depth values
        wrist_depths = np.array([ts['observations']['depth_raw'] for ts in timesteps])

        # Global depth stats
        all_depths = np.concatenate([dm.flatten() for dm in depth_maps[:100]])  # Sample first 100 frames

        print(f"📊 GLOBAL DEPTH STATISTICS:")
        print(f"   Scene depth range: {all_depths.min():.3f} to {all_depths.max():.3f}")
        print(f"   Scene depth mean: {all_depths.mean():.3f}")
        print(f"   Scene depth std: {all_depths.std():.3f}")

        print(f"\n🎯 WRIST DEPTH STATISTICS:")
        print(f"   Wrist depth range: {wrist_depths.min():.3f} to {wrist_depths.max():.3f}")
        print(f"   Wrist depth mean: {wrist_depths.mean():.3f}")
        print(f"   Wrist depth std: {wrist_depths.std():.3f}")

        # Depth variation over time
        depth_variation = np.diff(wrist_depths)
        print(f"\n📈 TEMPORAL VARIATION:")
        print(f"   Mean frame-to-frame change: {np.abs(depth_variation).mean():.4f}")
        print(f"   Max frame-to-frame change: {np.abs(depth_variation).max():.4f}")

        return {
            'scene_depth_range': [float(all_depths.min()), float(all_depths.max())],
            'scene_depth_mean': float(all_depths.mean()),
            'wrist_depth_range': [float(wrist_depths.min()), float(wrist_depths.max())],
            'wrist_depth_mean': float(wrist_depths.mean()),
            'wrist_depth_std': float(wrist_depths.std()),
            'temporal_variation': float(np.abs(depth_variation).mean())
        }


def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python add_metric_depth.py <video_file> <timestep_actions.json>")
        print("\nExample:")
        print("  python add_metric_depth.py test_video.mp4 test_video_timestep_actions.json")
        return

    video_path = sys.argv[1]
    timestep_file = sys.argv[2]

    if not Path(video_path).exists():
        print(f"❌ Video not found: {video_path}")
        return

    if not Path(timestep_file).exists():
        print(f"❌ Timestep file not found: {timestep_file}")
        return

    # Process
    adder = MetricDepthAdder(encoder='vits')  # Use small model for speed
    results = adder.process(video_path, timestep_file)

    # Save output
    output_file = Path(timestep_file).stem.replace('_timestep_actions', '') + '_with_depth.json'

    print(f"\n💾 SAVING RESULTS...")
    print(f"   Output: {output_file}")

    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n✅ PHASE 2 COMPLETE")
    print(f"\n{'='*70}")
    print(f"SUMMARY")
    print(f"{'='*70}")
    print(f"   Input: {len(results['timesteps'])} timesteps")
    print(f"   Output: {len(results['timesteps'])} timesteps with depth")
    print(f"   Depth model: Depth-Anything V2 ({adder.encoder})")
    print(f"   Depth range: {results['analysis']['depth_stats']['wrist_depth_range']}")
    print(f"\n📌 NEXT STEPS:")
    print(f"   1. ✅ Computed: velocity, acceleration, delta actions, gripper commands")
    print(f"   2. ✅ Added: metric depth estimation")
    print(f"   3. ⏳ TODO: Convert to metric 3D coordinates (x, y, z in meters)")
    print(f"   4. ⏳ TODO: Add coordinate frame transformation")
    print(f"   5. ⏳ TODO: Add orientation estimation")
    print(f"   6. ⏳ TODO: Export to HDF5 format")


if __name__ == "__main__":
    main()
