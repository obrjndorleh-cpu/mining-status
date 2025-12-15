"""
GATE 1 VALIDATION SCRIPT
Validates data quality before proceeding to policy training

Criteria:
1. RGB frames captured at 224x224, 10+ FPS ✓
2. Actions smooth (no jumps >10cm between frames)
3. Labels >85% accurate (manual inspection)
4. No NaN/Inf values in any modality
5. Format loads in RoboMimic without errors
"""

import h5py
import numpy as np
from pathlib import Path
import json
from typing import Dict, List, Tuple


class Gate1Validator:
    """Validate data quality for Gate 1"""

    def __init__(self, hdf5_dir: str):
        self.hdf5_dir = Path(hdf5_dir)
        self.results = {
            'total_files': 0,
            'passed': 0,
            'failed': 0,
            'issues': []
        }

    def validate_all(self, num_samples: int = 100) -> Dict:
        """
        Run all Gate 1 validation checks

        Args:
            num_samples: Number of random samples to check

        Returns:
            Validation report dict
        """
        print("="*70)
        print("GATE 1 VALIDATION")
        print("="*70)
        print()

        # Get all HDF5 files with RGB (> 1MB)
        hdf5_files = self._get_rgb_files()

        if len(hdf5_files) == 0:
            print("❌ No RGB demos found!")
            print("   Files must be > 1 MB to contain RGB frames")
            return self.results

        print(f"Found {len(hdf5_files)} RGB demos")
        print()

        # Sample random files
        sample_size = min(num_samples, len(hdf5_files))
        sample_files = np.random.choice(hdf5_files, sample_size, replace=False)

        print(f"Validating {sample_size} random samples...")
        print()

        # Run validation checks
        for i, file_path in enumerate(sample_files, 1):
            print(f"[{i}/{sample_size}] Checking: {file_path.name[:50]}...")

            try:
                issues = self._validate_file(file_path)

                if issues:
                    self.results['failed'] += 1
                    self.results['issues'].append({
                        'file': file_path.name,
                        'issues': issues
                    })
                    print(f"  ❌ FAILED ({len(issues)} issues)")
                else:
                    self.results['passed'] += 1
                    print(f"  ✅ PASSED")

                self.results['total_files'] += 1

            except Exception as e:
                print(f"  ⚠️  ERROR: {e}")
                self.results['failed'] += 1
                self.results['issues'].append({
                    'file': file_path.name,
                    'issues': [f'Exception: {str(e)}']
                })

        # Print summary
        print()
        print("="*70)
        print("GATE 1 VALIDATION SUMMARY")
        print("="*70)
        print(f"Total files checked: {self.results['total_files']}")
        print(f"Passed: {self.results['passed']} ({self.results['passed']/self.results['total_files']*100:.1f}%)")
        print(f"Failed: {self.results['failed']} ({self.results['failed']/self.results['total_files']*100:.1f}%)")
        print()

        # Gate 1 decision
        pass_rate = self.results['passed'] / self.results['total_files'] if self.results['total_files'] > 0 else 0

        if pass_rate >= 0.95:  # 95% pass rate
            print("✅ GATE 1: PASSED")
            print("   Ready to proceed to Gate 2 (policy training)")
        else:
            print("❌ GATE 1: FAILED")
            print(f"   Pass rate: {pass_rate:.1%} (need >95%)")
            print("   Fix issues before proceeding")

        print()

        # Show common issues
        if self.results['issues']:
            print("Common Issues:")
            issue_types = {}
            for item in self.results['issues']:
                for issue in item['issues']:
                    issue_type = issue.split(':')[0]
                    issue_types[issue_type] = issue_types.get(issue_type, 0) + 1

            for issue_type, count in sorted(issue_types.items(), key=lambda x: -x[1]):
                print(f"  - {issue_type}: {count} files")

        return self.results

    def _get_rgb_files(self) -> List[Path]:
        """Get HDF5 files that contain RGB (> 1 MB)"""
        rgb_files = []

        for file_path in self.hdf5_dir.glob('*.hdf5'):
            # RGB files should be ~28 MB, pose-only ~47 KB
            if file_path.stat().st_size > 1_000_000:  # > 1 MB
                rgb_files.append(file_path)

        return rgb_files

    def _validate_file(self, file_path: Path) -> List[str]:
        """
        Validate a single HDF5 file

        Returns:
            List of issue strings (empty if all checks pass)
        """
        issues = []

        with h5py.File(file_path, 'r') as f:
            demo = f['data/demo_0']

            # CHECK 1: RGB frames present and correct shape
            if 'obs/agentview_rgb' not in demo:
                issues.append("RGB: Missing RGB frames")
            else:
                rgb = demo['obs/agentview_rgb']

                # Check shape (N, H, W, 3)
                if len(rgb.shape) != 4:
                    issues.append(f"RGB: Wrong dimensions {rgb.shape} (expected 4D)")
                elif rgb.shape[1:] != (224, 224, 3):
                    issues.append(f"RGB: Wrong resolution {rgb.shape[1:]} (expected 224x224x3)")

                # Check dtype
                if rgb.dtype != np.uint8:
                    issues.append(f"RGB: Wrong dtype {rgb.dtype} (expected uint8)")

                # Check FPS (at least 10 FPS)
                if 'duration' in demo.attrs and 'total_frames' in demo.attrs:
                    duration = demo.attrs['duration']
                    frames = demo.attrs['total_frames']
                    fps = frames / duration if duration > 0 else 0
                    if fps < 10:
                        issues.append(f"RGB: Low FPS {fps:.1f} (need >10)")

            # CHECK 2: Action smoothness (no jumps > 10cm)
            if 'actions/delta_pos' in demo:
                actions = demo['actions/delta_pos'][:]

                # Check for NaN/Inf
                if np.any(np.isnan(actions)):
                    issues.append("Actions: Contains NaN values")
                if np.any(np.isinf(actions)):
                    issues.append("Actions: Contains Inf values")

                # Check for large jumps (>0.1m = 10cm)
                max_delta = np.max(np.abs(actions))
                if max_delta > 0.1:
                    issues.append(f"Actions: Large jump detected {max_delta:.3f}m (>10cm)")

            # CHECK 3: Observations have no NaN/Inf
            obs_datasets = ['obs/eef_pos', 'obs/eef_vel', 'obs/gripper_state']
            for ds_name in obs_datasets:
                if ds_name in demo:
                    data = demo[ds_name][:]
                    if np.any(np.isnan(data)):
                        issues.append(f"{ds_name}: Contains NaN values")
                    if np.any(np.isinf(data)):
                        issues.append(f"{ds_name}: Contains Inf values")

            # CHECK 4: Required datasets present
            required = [
                'obs/eef_pos',
                'obs/gripper_state',
                'actions/delta_pos',
                'actions/gripper_commands'
            ]

            for ds_name in required:
                if ds_name not in demo:
                    issues.append(f"Missing: {ds_name}")

            # CHECK 5: Observation/Action alignment (N obs, N-1 actions)
            if 'obs/eef_pos' in demo and 'actions/delta_pos' in demo:
                n_obs = len(demo['obs/eef_pos'])
                n_actions = len(demo['actions/delta_pos'])

                if n_actions != n_obs - 1:
                    issues.append(f"Misalignment: {n_obs} obs but {n_actions} actions (expected {n_obs-1})")

        return issues

    def save_report(self, output_path: str = 'gate1_validation_report.json'):
        """Save validation report to JSON"""
        with open(output_path, 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"Report saved: {output_path}")


def main():
    """Run Gate 1 validation"""
    import argparse

    parser = argparse.ArgumentParser(description='Gate 1 Data Quality Validation')
    parser.add_argument('hdf5_dir', help='Directory containing HDF5 files')
    parser.add_argument('--samples', type=int, default=100,
                       help='Number of samples to check (default: 100)')
    parser.add_argument('--output', default='gate1_validation_report.json',
                       help='Output report path')

    args = parser.parse_args()

    validator = Gate1Validator(args.hdf5_dir)
    results = validator.validate_all(num_samples=args.samples)
    validator.save_report(args.output)


if __name__ == '__main__':
    main()
