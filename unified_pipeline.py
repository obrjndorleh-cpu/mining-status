"""
UNIFIED VIDEO-TO-ROBOT-DATA PIPELINE

Single coherent entry point for processing videos into robot training data.

Architecture:
    1. Extraction: Pose, Hands, Objects, Colors, Orientation
    2. Kinematics: Metric 3D, Velocities, Accelerations
    3. Dual-Stream Detection:
       - Stream A: Physics-based (deterministic)
       - Stream B: Vision-based (AI semantic)
    4. Reconciliation: Merge streams, resolve conflicts
    5. Export: HDF5 robot training data

Philosophy: Quality data through coherent, validated processing
"""

import json
import numpy as np
from pathlib import Path
import sys


class UnifiedPipeline:
    """
    Coherent video processing pipeline with dual-stream detection
    """

    def __init__(self, enable_vision=False, enable_reconciliation=True, output_dir='output'):
        """
        Initialize unified pipeline

        Args:
            enable_vision: Enable vision stream (requires API)
            enable_reconciliation: Enable reconciliation junction
            output_dir: Directory for output files
        """
        self.enable_vision = enable_vision
        self.enable_reconciliation = enable_reconciliation
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        print("="*70)
        print("UNIFIED VIDEO-TO-ROBOT-DATA PIPELINE")
        print("="*70)
        print(f"Vision Stream: {'ENABLED' if enable_vision else 'DISABLED'}")
        print(f"Reconciliation: {'ENABLED' if enable_reconciliation else 'DISABLED'}")
        print(f"Output Directory: {output_dir}")
        print("="*70)
        print()

    def process(self, video_file):
        """
        Process video through complete pipeline

        Args:
            video_file: Path to input video

        Returns:
            dict: Complete processing results with robot data
        """
        video_path = Path(video_file)
        video_name = video_path.stem

        print(f"📹 Processing video: {video_file}")
        print()

        # ==================== STAGE 1: EXTRACTION ====================
        print("="*70)
        print("STAGE 1: MULTI-MODAL EXTRACTION")
        print("="*70)

        extraction_result = self._stage1_extraction(video_file)

        if extraction_result is None:
            print("❌ Extraction failed")
            return None

        print(f"✅ Extraction complete: {extraction_result['frames_processed']} frames")
        print()

        # Save extraction (excluding RGB frames - they're in memory only)
        extraction_file = self.output_dir / f"{video_name}_extraction.json"
        extraction_for_json = {k: v for k, v in extraction_result.items() if k != 'video_frames'}
        with open(extraction_file, 'w') as f:
            json.dump(extraction_for_json, f, indent=2)
        print(f"💾 Saved: {extraction_file}")
        print()

        # ==================== STAGE 2: KINEMATICS ====================
        print("="*70)
        print("STAGE 2: KINEMATIC ANALYSIS")
        print("="*70)

        kinematics_result = self._stage2_kinematics(extraction_result)

        if kinematics_result is None:
            print("❌ Kinematics computation failed")
            return None

        print(f"✅ Kinematics computed: {len(kinematics_result['positions'])} timesteps")
        print()

        # Save kinematics
        kinematics_file = self.output_dir / f"{video_name}_kinematics.json"
        with open(kinematics_file, 'w') as f:
            json.dump(kinematics_result, f, indent=2)
        print(f"💾 Saved: {kinematics_file}")
        print()

        # ==================== STAGE 3: DUAL-STREAM DETECTION ====================
        print("="*70)
        print("STAGE 3: DUAL-STREAM ACTION DETECTION")
        print("="*70)

        # Stream A: Physics
        print("🔬 STREAM A: Physics-Based Detection")
        print("-"*70)
        physics_result = self._stream_physics(kinematics_result, extraction_result)
        print(f"✅ Physics detected {len(physics_result['actions'])} actions")
        print()

        # Stream B: Vision (if enabled)
        if self.enable_vision:
            print("👁️  STREAM B: Vision-Based Detection")
            print("-"*70)
            vision_result = self._stream_vision(video_file, kinematics_result)
            print(f"✅ Vision detected: {vision_result['action']}")
            print()
        else:
            vision_result = None
            print("⚠️  Vision stream disabled (using physics only)")
            print()

        # Save detection results
        physics_file = self.output_dir / f"{video_name}_physics_detection.json"
        with open(physics_file, 'w') as f:
            json.dump(physics_result, f, indent=2)
        print(f"💾 Saved: {physics_file}")

        if vision_result:
            vision_file = self.output_dir / f"{video_name}_vision_detection.json"
            with open(vision_file, 'w') as f:
                json.dump(vision_result, f, indent=2)
            print(f"💾 Saved: {vision_file}")
        print()

        # ==================== STAGE 4: RECONCILIATION ====================
        if self.enable_reconciliation and vision_result:
            print("="*70)
            print("STAGE 4: RECONCILIATION JUNCTION")
            print("="*70)

            reconciled_result = self._stage4_reconciliation(
                physics_result,
                vision_result,
                kinematics_result,
                extraction_result
            )

            print(f"✅ Reconciliation complete: {reconciled_result['action']}")
            print()

            # Save reconciled result
            reconciled_file = self.output_dir / f"{video_name}_reconciled.json"
            with open(reconciled_file, 'w') as f:
                json.dump(reconciled_result, f, indent=2)
            print(f"💾 Saved: {reconciled_file}")
            print()

        else:
            # No reconciliation - use physics only
            reconciled_result = {
                'action': physics_result['actions'][0]['action'] if physics_result['actions'] else 'unknown',
                'confidence': physics_result['actions'][0]['confidence'] if physics_result['actions'] else 0,
                'method': 'physics_only',
                'physics_result': physics_result,
                'vision_result': None
            }

        # ==================== STAGE 5: ROBOT DATA EXPORT ====================
        print("="*70)
        print("STAGE 5: ROBOT DATA EXPORT")
        print("="*70)

        robot_data = self._stage5_export(
            reconciled_result,
            kinematics_result,
            extraction_result,
            video_name
        )

        print(f"✅ Robot data generated")
        print()

        # Save robot data (JSON for now, HDF5 later) - exclude video_frames
        robot_file = self.output_dir / f"{video_name}_robot_data.json"
        robot_data_for_json = {k: v for k, v in robot_data.items() if k != 'video_frames'}
        with open(robot_file, 'w') as f:
            json.dump(robot_data_for_json, f, indent=2)
        print(f"💾 Saved: {robot_file}")
        print()

        # ==================== COMPLETE ====================
        print("="*70)
        print("✅ PIPELINE COMPLETE")
        print("="*70)
        print()
        print("📊 Summary:")
        print(f"   Video: {video_file}")
        print(f"   Frames: {extraction_result['frames_processed']}")
        print(f"   Action: {reconciled_result['action'].upper()}")
        print(f"   Confidence: {reconciled_result['confidence']:.0%}")
        print(f"   Method: {reconciled_result['method']}")
        print()
        print("📁 Output files:")
        for file in sorted(self.output_dir.glob(f"{video_name}_*")):
            print(f"   - {file.name}")
        print()

        return {
            'extraction': extraction_result,
            'kinematics': kinematics_result,
            'physics': physics_result,
            'vision': vision_result,
            'reconciled': reconciled_result,
            'robot_data': robot_data
        }

    def _stage1_extraction(self, video_file):
        """
        Stage 1: Extract all features from video

        Uses existing extraction pipeline
        """
        video_path = Path(video_file)
        video_name = video_path.stem

        # Check if extraction already exists
        extraction_file = Path(f"{video_name}_full_extraction_with_colors_with_orientation.json")

        if extraction_file.exists():
            print(f"✅ Using existing extraction: {extraction_file}")
            with open(extraction_file, 'r') as f:
                result = json.load(f)

            # Load RGB frames if available
            rgb_file = Path(f"{video_name}_rgb_frames.npz")
            video_frames = None
            if rgb_file.exists():
                print(f"  ✅ Loading RGB frames from: {rgb_file}")
                rgb_data = np.load(rgb_file)
                video_frames = rgb_data['rgb_frames']
                print(f"     RGB shape: {video_frames.shape}")

            return {
                'frames': result['frames'],
                'metadata': result['metadata'],
                'frames_processed': len(result['frames']),
                'video_frames': video_frames
            }

        # Otherwise, run extraction pipeline
        print("Running extraction pipeline...")
        print("  - Pose extraction (MediaPipe)")
        print("  - Hand tracking (MediaPipe)")
        print("  - Object detection (YOLOv8)")
        print("  - Color analysis")
        print("  - Hand orientation")
        print()

        # Run extraction commands
        import subprocess

        try:
            # Step 1: Extract everything
            print("  Running extract_everything.py...")
            subprocess.run([sys.executable, 'extract_everything.py', video_file], check=True)

            # Step 2: Add colors
            print("  Running add_color_analysis.py...")
            extraction_json = f"{video_name}_full_extraction.json"
            subprocess.run([sys.executable, 'add_color_analysis.py', video_file, extraction_json], check=True)

            # Step 3: Add orientation
            print("  Running compute_hand_orientation.py...")
            colors_json = f"{video_name}_full_extraction_with_colors.json"
            subprocess.run([sys.executable, 'compute_hand_orientation.py', colors_json], check=True)

            # Load final result
            final_json = f"{video_name}_full_extraction_with_colors_with_orientation.json"
            with open(final_json, 'r') as f:
                result = json.load(f)

            # Load RGB frames if available
            rgb_file = Path(f"{video_name}_rgb_frames.npz")
            video_frames = None
            if rgb_file.exists():
                print(f"  ✅ Loading RGB frames from: {rgb_file}")
                rgb_data = np.load(rgb_file)
                video_frames = rgb_data['rgb_frames']
                print(f"     RGB shape: {video_frames.shape}")

            return {
                'frames': result['frames'],
                'metadata': result['metadata'],
                'frames_processed': len(result['frames']),
                'video_frames': video_frames
            }

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def _apply_hand_aware_tracking(self, raw_positions, gripper_openness):
        """
        Apply hand-aware tracking to filter out motion when hand is not holding object.

        STRATEGY:
        - When hand CLOSED (openness < 0.3): Track position (object in hand)
        - When hand OPEN (openness > 0.7): Hold last valid position (hand moving without object)
        - Transition (0.3 - 0.7): Interpolate smoothly

        This prevents tracking hand motion when not manipulating objects
        (e.g., reaching to turn off camera, waving, etc.)
        """
        CLOSED_THRESHOLD = 0.3  # Hand is grasping object
        OPEN_THRESHOLD = 0.7    # Hand is clearly open

        filtered_positions = []
        last_valid_position = raw_positions[0].copy()

        for i in range(len(raw_positions)):
            openness = gripper_openness[i]

            if openness < CLOSED_THRESHOLD:
                # Hand is closed - object is being held
                # Track wrist position as object proxy
                filtered_positions.append(raw_positions[i].copy())
                last_valid_position = raw_positions[i].copy()

            elif openness > OPEN_THRESHOLD:
                # Hand is open - no object being held
                # Hold last valid position (ignore wrist motion)
                filtered_positions.append(last_valid_position.copy())

            else:
                # Transition zone (0.3 - 0.7) - hand opening or closing
                # Interpolate based on how close to closed/open
                # Closer to closed = more tracking, closer to open = more holding
                blend_factor = (openness - CLOSED_THRESHOLD) / (OPEN_THRESHOLD - CLOSED_THRESHOLD)
                # blend_factor: 0 = fully closed (track), 1 = fully open (hold)

                blended_pos = (1 - blend_factor) * raw_positions[i] + blend_factor * last_valid_position
                filtered_positions.append(blended_pos)

                # Update last valid if mostly closed
                if blend_factor < 0.5:
                    last_valid_position = blended_pos.copy()

        return np.array(filtered_positions)

    def _extract_detected_objects(self, extraction_data):
        """
        Extract list of detected objects from extraction data
        Used for object-action compatibility checking
        """
        if not extraction_data or 'frames' not in extraction_data:
            return ['unknown']

        # Collect all unique detected objects across frames
        detected_objects = set()

        for frame_data in extraction_data['frames']:
            if 'objects' in frame_data:
                for obj in frame_data['objects']:
                    if 'name' in obj and obj['name'] != 'person':
                        detected_objects.add(obj['name'].lower())

        if not detected_objects:
            return ['unknown']

        return list(detected_objects)

    def _detect_action_boundaries(self, positions, timestamps):
        """
        Detect action boundaries using directional displacement reversal.

        KEY INSIGHT: When motion REVERSES direction significantly, the action ended.
        Cut at the peak of FIRST dominant motion, before any reversal.
        """
        if len(positions) < 10:
            return positions

        # Calculate Z-displacement (depth - most common action axis)
        z_displacements = positions[:, 2] - positions[0, 2]

        # Find ALL local peaks (both backward and forward)
        max_backward_idx = np.argmax(z_displacements)  # Most backward (positive Z)
        max_forward_idx = np.argmin(z_displacements)    # Most forward (negative Z)

        max_backward = z_displacements[max_backward_idx]
        max_forward = z_displacements[max_forward_idx]

        # Check BOTH directions for reversal (regardless of which is larger)
        # This catches cases where "pull then reach forward" has larger forward at end

        # Check backward peak for forward reversal
        if max_backward > 0.3 and max_backward_idx < len(positions) - 10:  # Significant backward motion
            # Check if motion reversed forward after this peak
            post_peak_min = np.min(z_displacements[max_backward_idx:])
            reversal = post_peak_min - max_backward  # Should be negative if reversed

            if reversal < -0.2 and abs(reversal) > abs(max_backward) * 0.3:
                # Significant reversal! Action ended at backward peak
                print(f"  🎯 Boundary detected: PULL ended at t={timestamps[max_backward_idx]:.1f}s (peak backward: +{max_backward:.2f}m)")
                boundary_positions = positions.copy()
                for i in range(max_backward_idx + 1, len(positions)):
                    boundary_positions[i] = positions[max_backward_idx]
                return boundary_positions

        # Check forward peak for backward reversal
        if abs(max_forward) > 0.3 and max_forward_idx < len(positions) - 10:  # Significant forward motion
            # Check if motion reversed backward after this peak
            post_peak_max = np.max(z_displacements[max_forward_idx:])
            reversal = post_peak_max - max_forward  # Should be positive if reversed

            if reversal > 0.2 and abs(reversal) > abs(max_forward) * 0.3:
                # Significant reversal! Action ended at forward peak
                boundary_positions = positions.copy()
                for i in range(max_forward_idx + 1, len(positions)):
                    boundary_positions[i] = positions[max_forward_idx]
                return boundary_positions

        # No significant reversal detected, return original
        return positions

    def _stage2_kinematics(self, extraction_result):
        """
        Stage 2: Compute kinematics from extraction
        """
        print("Computing kinematics...")
        print("  - Metric 3D conversion")
        print("  - Velocity computation")
        print("  - Acceleration computation")
        print()

        frames = extraction_result['frames']
        timestamps = [f['timestamp'] for f in frames]

        # Extract positions with HAND-AWARE tracking
        # Only track wrist position when hand is closed (holding object)
        raw_positions = []
        gripper_openness = []

        for frame in frames:
            # Get wrist position (end effector)
            if frame['pose']['detected'] and 'RIGHT_WRIST' in frame['pose'].get('landmarks', {}):
                wrist = frame['pose']['landmarks']['RIGHT_WRIST']
                pos = [wrist['x'], wrist['y'], wrist['z']]
            else:
                pos = [0.0, 0.0, 0.0]

            raw_positions.append(pos)

            # Get gripper openness
            if frame['hands']['detected'] and frame['hands'].get('hands'):
                openness = frame['hands']['hands'][0]['openness']
            else:
                openness = 0.0

            gripper_openness.append(openness)

        raw_positions = np.array(raw_positions)
        gripper_openness = np.array(gripper_openness)
        timestamps = np.array(timestamps)

        # HAND-AWARE FILTERING: Only use position when hand is holding object
        # This filters out hand motion when not manipulating objects
        hand_aware_positions = self._apply_hand_aware_tracking(raw_positions, gripper_openness)

        # ACTION BOUNDARY DETECTION: Detect displacement reversal
        # Stop tracking when motion reverses (action complete, returning hand to rest)
        positions = self._detect_action_boundaries(hand_aware_positions, timestamps)

        # Compute velocities
        velocities = []
        for i in range(len(positions)):
            if i == 0:
                vel = [0.0, 0.0, 0.0]
            else:
                dt = timestamps[i] - timestamps[i-1]
                if dt > 0:
                    vel = ((positions[i] - positions[i-1]) / dt).tolist()
                else:
                    vel = [0.0, 0.0, 0.0]
            velocities.append(vel)

        velocities = np.array(velocities)

        # Compute accelerations
        accelerations = []
        for i in range(len(velocities)):
            if i == 0:
                acc = [0.0, 0.0, 0.0]
            else:
                dt = timestamps[i] - timestamps[i-1]
                if dt > 0:
                    acc = ((velocities[i] - velocities[i-1]) / dt).tolist()
                else:
                    acc = [0.0, 0.0, 0.0]
            accelerations.append(acc)

        # Compute speeds
        speeds = [np.linalg.norm(v) for v in velocities]

        return {
            'timestamps': timestamps.tolist(),
            'positions': positions.tolist(),
            'velocities': velocities.tolist(),
            'accelerations': accelerations,
            'speeds': speeds,
            'gripper_openness': gripper_openness.tolist()
        }

    def _stream_physics(self, kinematics, extraction):
        """
        Stream A: Physics-based detection
        """
        print("Running physics-based action detection...")

        # Use existing advanced action detector
        from advanced_action_detection import AdvancedActionDetector

        # Create temporary files for detector
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            # Save kinematics as metric_3d format
            metric_data = {
                'metadata': extraction['metadata'],
                'timesteps': []
            }

            for i in range(len(kinematics['timestamps'])):
                metric_data['timesteps'].append({
                    'timestamp': kinematics['timestamps'][i],
                    'observations': {
                        'end_effector_pos_metric': kinematics['positions'][i],
                        'gripper_openness': kinematics['gripper_openness'][i]
                    },
                    'kinematics': {
                        'velocity': kinematics['velocities'][i],
                        'acceleration': kinematics['accelerations'][i],
                        'speed': kinematics['speeds'][i]
                    }
                })

            metric_file = os.path.join(tmpdir, 'metric.json')
            with open(metric_file, 'w') as f:
                json.dump(metric_data, f)

            # Save extraction (excluding video_frames)
            extraction_file = os.path.join(tmpdir, 'extraction.json')
            extraction_for_json = {k: v for k, v in extraction.items() if k != 'video_frames'}
            with open(extraction_file, 'w') as f:
                json.dump(extraction_for_json, f)

            # Run detector
            detector = AdvancedActionDetector()
            actions = detector.detect_actions(metric_file, extraction_file)

        return {
            'actions': actions,
            'method': 'physics',
            'detector': 'advanced_action_detection'
        }

    def _stream_vision(self, video_file, kinematics):
        """
        Stream B: Vision-based detection using Claude API
        """
        print("Running vision-based action detection...")

        try:
            from core.detection.vision_detector import VisionActionDetector

            detector = VisionActionDetector()
            # Pass kinematics to focus on active motion period
            result = detector.detect(video_file, num_frames=5, kinematics=kinematics)

            return result

        except Exception as e:
            print(f"⚠️  Vision detection failed: {e}")
            return {
                'action': 'unknown',
                'confidence': 0.0,
                'method': 'vision_error',
                'reasoning': f'Error: {str(e)}'
            }

    def _stage4_reconciliation(self, physics_result, vision_result, kinematics, extraction_data):
        """
        Stage 4: Reconciliation Junction
        """
        # Use smart reconciliation junction (intelligent decision-making)
        from core.detection.smart_reconciliation import SmartReconciliationJunction

        junction = SmartReconciliationJunction()

        # Extract detected objects for compatibility checking
        objects = self._extract_detected_objects(extraction_data)

        reconciled = junction.reconcile(physics_result, vision_result, kinematics, objects)

        return reconciled

    def _stage5_export(self, reconciled, kinematics, extraction, video_name):
        """
        Stage 5: Export robot training data
        """
        print("Generating robot training data...")
        print("  Formats: JSON + HDF5 (industry standard)")
        print()

        # Extract detected objects
        objects = self._extract_detected_objects(extraction)

        # Extract RGB frames if available
        video_frames = extraction.get('video_frames', None)
        if video_frames is not None:
            print(f"  ✅ RGB frames available: {video_frames.shape}")
        else:
            print(f"  ⚠️  No RGB frames (pose-only mode)")

        # Prepare robot data
        robot_data = {
            'metadata': {
                'video': video_name,
                'frames': len(kinematics['timestamps']),
                'duration': kinematics['timestamps'][-1],
                'action': reconciled['action'],
                'confidence': reconciled['confidence'],
                'detection_method': reconciled['method']
            },
            'action': reconciled['action'],
            'confidence': reconciled['confidence'],
            'method': reconciled['method'],
            'objects': objects,
            'kinematics': kinematics
        }

        # Add RGB frames if available
        if video_frames is not None:
            robot_data['video_frames'] = video_frames

        # Export to HDF5
        try:
            from core.export.hdf5_exporter import HDF5Exporter

            hdf5_exporter = HDF5Exporter()
            hdf5_path = self.output_dir / f"{video_name}.hdf5"

            hdf5_exporter.export_demo(robot_data, hdf5_path, demo_name='demo_0')

            print(f"✅ HDF5 exported: {hdf5_path.name}")
        except Exception as e:
            print(f"⚠️  HDF5 export failed: {e}")
            print("   (JSON export still available)")

        return robot_data


def main():
    """
    Command-line interface
    """
    if len(sys.argv) < 2:
        print("Usage: python unified_pipeline.py <video_file> [--enable-vision] [--output-dir DIR]")
        print()
        print("Example:")
        print("  python unified_pipeline.py video.mp4")
        print("  python unified_pipeline.py video.mp4 --enable-vision")
        print("  python unified_pipeline.py video.mp4 --output-dir results/")
        return

    video_file = sys.argv[1]

    # Parse options
    enable_vision = '--enable-vision' in sys.argv

    output_dir = 'output'
    if '--output-dir' in sys.argv:
        idx = sys.argv.index('--output-dir')
        if idx + 1 < len(sys.argv):
            output_dir = sys.argv[idx + 1]

    # Create pipeline
    pipeline = UnifiedPipeline(
        enable_vision=enable_vision,
        enable_reconciliation=True,
        output_dir=output_dir
    )

    # Process video
    result = pipeline.process(video_file)

    if result:
        print("="*70)
        print("🎉 SUCCESS!")
        print("="*70)
    else:
        print("="*70)
        print("❌ FAILED")
        print("="*70)


if __name__ == "__main__":
    main()
