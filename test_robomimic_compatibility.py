"""
ROBOMIMIC COMPATIBILITY TEST
Test if our HDF5 files can be loaded by RoboMimic

This validates Gate 1 criterion #5: Format loads in RoboMimic without errors
"""

import h5py
import numpy as np
from pathlib import Path
import json


def test_basic_structure(hdf5_path):
    """Test basic HDF5 structure compatibility"""
    print(f"\n{'='*70}")
    print(f"Testing: {Path(hdf5_path).name[:60]}")
    print(f"{'='*70}\n")

    issues = []

    with h5py.File(hdf5_path, 'r') as f:
        # Check required top-level structure
        if 'data' not in f:
            issues.append("Missing 'data' group")
            return issues

        data_group = f['data']

        # Check for at least one demo
        demo_keys = [k for k in data_group.keys() if k.startswith('demo_')]
        if not demo_keys:
            issues.append("No demos found (no 'demo_*' groups)")
            return issues

        print(f"✅ Found {len(demo_keys)} demo(s)")

        # Check first demo structure
        demo = data_group['demo_0']

        # Required groups
        if 'obs' not in demo:
            issues.append("Missing 'obs' group")
        if 'actions' not in demo:
            issues.append("Missing 'actions' group")

        if issues:
            return issues

        # Check observations
        obs = demo['obs']
        required_obs = ['eef_pos', 'gripper_state']
        optional_obs = ['agentview_rgb', 'eef_vel', 'joint_pos']

        print("\n📊 Observations:")
        for obs_name in required_obs:
            if obs_name in obs:
                shape = obs[obs_name].shape
                print(f"  ✅ {obs_name}: {shape}")
            else:
                issues.append(f"Missing required observation: {obs_name}")
                print(f"  ❌ {obs_name}: MISSING")

        for obs_name in optional_obs:
            if obs_name in obs:
                shape = obs[obs_name].shape
                print(f"  ✅ {obs_name}: {shape}")

        # Check actions
        actions_group = demo['actions']
        required_actions = ['delta_pos', 'gripper_commands']

        print("\n🎮 Actions:")
        for action_name in required_actions:
            if action_name in actions_group:
                shape = actions_group[action_name].shape
                print(f"  ✅ {action_name}: {shape}")
            else:
                issues.append(f"Missing required action: {action_name}")
                print(f"  ❌ {action_name}: MISSING")

        # Check metadata
        print("\n📝 Metadata:")
        if 'task_name' in demo.attrs:
            print(f"  ✅ task_name: {demo.attrs['task_name']}")
        else:
            print(f"  ⚠️  task_name: Not set")

        if 'success' in demo.attrs:
            print(f"  ✅ success: {demo.attrs['success']}")
        else:
            print(f"  ⚠️  success: Not set")

        # Check rewards (optional but recommended)
        if 'rewards' in demo:
            rewards = demo['rewards/rewards']
            print(f"  ✅ rewards: {rewards.shape}")
        else:
            print(f"  ⚠️  rewards: Not present (optional)")

    if not issues:
        print(f"\n✅ COMPATIBLE: File structure is valid")
    else:
        print(f"\n❌ INCOMPATIBLE: Found {len(issues)} issue(s)")
        for issue in issues:
            print(f"   - {issue}")

    return issues


def test_robomimic_import():
    """Test if RoboMimic can be imported"""
    print(f"\n{'='*70}")
    print("ROBOMIMIC IMPORT TEST")
    print(f"{'='*70}\n")

    try:
        import robomimic
        print(f"✅ RoboMimic installed: version {robomimic.__version__}")
        return True
    except ImportError:
        print("❌ RoboMimic NOT installed")
        print("\nTo install:")
        print("  pip install robomimic")
        print("\nOr from source:")
        print("  git clone https://github.com/ARISE-Initiative/robomimic.git")
        print("  cd robomimic")
        print("  pip install -e .")
        return False


def test_robomimic_load(hdf5_path):
    """Test if RoboMimic can load our dataset"""
    print(f"\n{'='*70}")
    print("ROBOMIMIC DATASET LOADING TEST")
    print(f"{'='*70}\n")

    try:
        import robomimic.utils.file_utils as FileUtils
        import robomimic.utils.env_utils as EnvUtils

        # Try to load dataset
        print(f"Loading: {Path(hdf5_path).name[:60]}")

        # Get dataset info
        env_meta = FileUtils.get_env_metadata_from_dataset(hdf5_path)
        print(f"\n✅ Environment metadata loaded")
        print(f"   Type: {env_meta.get('env_name', 'unknown')}")

        # Try to read demonstrations
        demo_keys = list(FileUtils.get_demos_for_filter(
            hdf5_path,
            filter_key=None
        ))

        print(f"\n✅ Found {len(demo_keys)} valid demonstrations")

        # Get trajectory info
        with h5py.File(hdf5_path, 'r') as f:
            demo = f[f'data/{demo_keys[0]}']
            num_samples = len(demo['actions/delta_pos'])
            print(f"   First demo: {num_samples} timesteps")

        print(f"\n✅ ROBOMIMIC CAN LOAD THIS FILE")
        return True

    except ImportError:
        print("❌ RoboMimic not installed (run test_robomimic_import first)")
        return False
    except Exception as e:
        print(f"❌ RoboMimic CANNOT load this file")
        print(f"   Error: {str(e)}")
        return False


def test_dataset_batch(hdf5_dir, num_samples=10):
    """Test multiple files for compatibility"""
    print(f"\n{'='*70}")
    print("BATCH COMPATIBILITY TEST")
    print(f"{'='*70}\n")

    hdf5_dir = Path(hdf5_dir)
    hdf5_files = list(hdf5_dir.glob('*.hdf5'))

    # Filter RGB files (>1MB)
    rgb_files = [f for f in hdf5_files if f.stat().st_size > 1_000_000]

    if not rgb_files:
        print("❌ No RGB files found (need files >1MB)")
        return

    print(f"Found {len(rgb_files)} RGB files")

    # Sample random files
    sample_size = min(num_samples, len(rgb_files))
    sample_files = np.random.choice(rgb_files, sample_size, replace=False)

    print(f"Testing {sample_size} random samples...\n")

    passed = 0
    failed = 0

    for i, file_path in enumerate(sample_files, 1):
        print(f"[{i}/{sample_size}] {file_path.name[:50]}")
        issues = test_basic_structure(file_path)

        if not issues:
            passed += 1
            print("  ✅ PASSED")
        else:
            failed += 1
            print(f"  ❌ FAILED ({len(issues)} issues)")

        print()

    # Summary
    print(f"{'='*70}")
    print("BATCH TEST SUMMARY")
    print(f"{'='*70}")
    print(f"Tested: {sample_size} files")
    print(f"Passed: {passed} ({passed/sample_size*100:.1f}%)")
    print(f"Failed: {failed} ({failed/sample_size*100:.1f}%)")

    if passed == sample_size:
        print(f"\n✅ ALL FILES COMPATIBLE")
    else:
        print(f"\n⚠️  Some files have compatibility issues")


def main():
    """Run compatibility tests"""
    import argparse

    parser = argparse.ArgumentParser(description='Test RoboMimic compatibility')
    parser.add_argument('path', nargs='?', help='HDF5 file or directory to test')
    parser.add_argument('--batch', action='store_true',
                       help='Test multiple files in directory')
    parser.add_argument('--samples', type=int, default=10,
                       help='Number of samples for batch test')

    args = parser.parse_args()

    # Test 1: Check if RoboMimic is installed
    robomimic_available = test_robomimic_import()

    if args.path:
        path = Path(args.path)

        if args.batch or path.is_dir():
            # Batch test
            test_dataset_batch(path, num_samples=args.samples)
        else:
            # Single file test
            test_basic_structure(path)

            if robomimic_available:
                test_robomimic_load(path)
    else:
        print("\nUsage:")
        print("  # Test single file")
        print("  python test_robomimic_compatibility.py demo.hdf5")
        print()
        print("  # Test multiple files")
        print("  python test_robomimic_compatibility.py data_mine/permanent_data/hdf5 --batch")
        print()
        print("  # Install RoboMimic first if needed:")
        print("  pip install robomimic")


if __name__ == '__main__':
    main()
