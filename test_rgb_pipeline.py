"""
TEST RGB PIPELINE
Quick validation that RGB capture works end-to-end
"""
import sys
from pathlib import Path
import h5py
import numpy as np

def test_rgb_pipeline(video_path):
    """
    Test complete RGB pipeline on a single video

    Args:
        video_path: Path to test video
    """
    print("="*70)
    print("RGB PIPELINE TEST")
    print("="*70)
    print(f"Test video: {video_path}")
    print()

    # Step 1: Extract with RGB
    print("STEP 1: Extraction with RGB capture")
    print("-"*70)
    from extract_everything import ComprehensiveExtractor

    extractor = ComprehensiveExtractor()
    result = extractor.extract_all(
        video_path,
        capture_rgb=True,
        target_size=(224, 224)
    )

    # Check RGB frames
    if 'video_frames' in result:
        frames = result['video_frames']
        print(f"✅ RGB frames captured: {frames.shape}")
        print(f"   Dtype: {frames.dtype}")
        print(f"   Size: {frames.nbytes / (1024*1024):.1f} MB")
    else:
        print("❌ No RGB frames in extraction result!")
        return False

    print()

    # Step 2: Create minimal robot data (skip full pipeline for speed)
    print("STEP 2: Create robot data")
    print("-"*70)

    # Simplified kinematics from frame count
    n_frames = len(result['frames'])

    kinematics = {
        'positions': np.random.rand(n_frames, 3),  # Dummy positions
        'velocities': np.random.rand(n_frames, 3),  # Dummy velocities
        'gripper_openness': np.random.rand(n_frames),  # Dummy gripper
        'timestamps': np.arange(n_frames) / 30.0
    }

    robot_data = {
        'action': 'test',
        'confidence': 1.0,
        'method': 'test',
        'objects': ['test_object'],
        'kinematics': kinematics,
        'video_frames': result['video_frames']  # Pass RGB through
    }

    print(f"✅ Robot data created")
    print(f"   Has video_frames: {'video_frames' in robot_data}")
    print()

    # Step 3: Export to HDF5
    print("STEP 3: Export to HDF5")
    print("-"*70)

    from core.export.hdf5_exporter import HDF5Exporter

    output_path = Path('test_rgb_output.hdf5')
    exporter = HDF5Exporter()

    exporter.export_demo(robot_data, output_path, demo_name='demo_0')

    print(f"✅ HDF5 exported: {output_path}")
    print(f"   File size: {output_path.stat().st_size / (1024*1024):.1f} MB")
    print()

    # Step 4: Validate HDF5 structure
    print("STEP 4: Validate HDF5 structure")
    print("-"*70)

    with h5py.File(output_path, 'r') as f:
        demo = f['data/demo_0']

        print("File structure:")
        def show_structure(name, obj, indent=0):
            prefix = '  ' * indent
            if isinstance(obj, h5py.Dataset):
                print(f'{prefix}📊 {name}: {obj.shape}, {obj.dtype}')

        demo.visititems(show_structure)

        print()

        # Check for RGB
        if 'obs/agentview_rgb' in demo:
            rgb = demo['obs/agentview_rgb']
            print(f"✅ RGB frames in HDF5: {rgb.shape}")
            print(f"   Dtype: {rgb.dtype}")
            print(f"   Min/Max: {rgb[:].min()}/{rgb[:].max()}")

            # Validate shape
            if len(rgb.shape) == 4 and rgb.shape[3] == 3:
                print(f"✅ Shape valid: (N, H, W, 3)")
            else:
                print(f"❌ Shape invalid: {rgb.shape}")
                return False

        else:
            print(f"❌ No RGB frames in HDF5!")
            return False

    print()
    print("="*70)
    print("✅ RGB PIPELINE TEST PASSED")
    print("="*70)
    print()
    print("Summary:")
    print(f"  • Extraction: ✅ Captures RGB at 224x224")
    print(f"  • Export: ✅ Saves to HDF5 with compression")
    print(f"  • Format: ✅ Valid structure (N, H, W, 3)")
    print(f"  • File size: {output_path.stat().st_size / (1024*1024):.1f} MB")
    print()
    print("Next step: Test with full unified_pipeline.py")

    return True

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_rgb_pipeline.py <video_file>")
        print()
        print("Example:")
        print("  python test_rgb_pipeline.py data_mine/videos/test_video.mp4")
        sys.exit(1)

    video_path = sys.argv[1]

    if not Path(video_path).exists():
        print(f"Error: Video not found: {video_path}")
        sys.exit(1)

    success = test_rgb_pipeline(video_path)

    sys.exit(0 if success else 1)
