"""
ROBOT DATA INSPECTOR
Validate robomimic-format HDF5 files before cloud upload

Checks:
- Correct robomimic structure
- Actions data validity
- Observations data validity
- Data consistency
- No corruption

Usage:
    python robot_data_inspector.py --batch --auto-approve
"""

import h5py
import json
import numpy as np
from pathlib import Path
from datetime import datetime


class RobotDataInspector:
    """Inspect robot training data (robomimic format)"""

    def __init__(self, data_dir='data_mine/permanent_data'):
        self.data_dir = Path(data_dir)
        self.hdf5_dir = self.data_dir / 'hdf5'
        self.json_dir = self.data_dir / 'json'

        self.approved_dir = self.data_dir / 'approved'
        self.rejected_dir = self.data_dir / 'rejected'

        self.approved_dir.mkdir(exist_ok=True)
        self.rejected_dir.mkdir(exist_ok=True)

        self.inspection_log = self.data_dir / 'robot_inspection_log.json'
        self.load_log()

    def load_log(self):
        """Load inspection history"""
        if self.inspection_log.exists():
            with open(self.inspection_log, 'r') as f:
                self.log = json.load(f)
        else:
            self.log = {
                'inspected': [],
                'approved': [],
                'rejected': [],
                'stats': {
                    'total_inspected': 0,
                    'total_approved': 0,
                    'total_rejected': 0
                }
            }

    def save_log(self):
        """Save inspection history"""
        with open(self.inspection_log, 'w') as f:
            json.dump(self.log, f, indent=2)

    def validate_robot_data(self, hdf5_path):
        """
        Validate robomimic-format HDF5 file

        Returns:
            dict with validation results
        """
        hdf5_path = Path(hdf5_path)

        validation = {
            'filename': hdf5_path.name,
            'valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }

        try:
            with h5py.File(hdf5_path, 'r') as f:
                # Check robomimic structure
                if 'data' not in f:
                    validation['valid'] = False
                    validation['errors'].append("Missing 'data' group")
                    return validation

                # Check for demo_0
                if 'data/demo_0' not in f:
                    validation['valid'] = False
                    validation['errors'].append("Missing 'data/demo_0' group")
                    return validation

                demo = f['data/demo_0']

                # Validate actions
                if 'actions' not in demo:
                    validation['errors'].append("Missing 'actions' group")
                    validation['valid'] = False
                else:
                    actions = demo['actions']

                    # Check delta_pos
                    if 'delta_pos' in actions:
                        delta_pos = actions['delta_pos'][:]
                        validation['stats']['num_actions'] = delta_pos.shape[0]

                        # Check for NaN/Inf
                        if np.any(np.isnan(delta_pos)):
                            validation['errors'].append("Actions contain NaN values")
                            validation['valid'] = False

                        if np.any(np.isinf(delta_pos)):
                            validation['errors'].append("Actions contain Inf values")
                            validation['valid'] = False

                        # Check reasonable ranges
                        if np.abs(delta_pos).max() > 10.0:
                            validation['warnings'].append(f"Large action values detected: max={np.abs(delta_pos).max():.2f}")

                    # Check gripper
                    if 'gripper_commands' in actions:
                        gripper = actions['gripper_commands'][:]
                        validation['stats']['gripper_actions'] = gripper.shape[0]

                # Validate observations
                if 'obs' not in demo:
                    validation['errors'].append("Missing 'obs' group")
                    validation['valid'] = False
                else:
                    obs = demo['obs']

                    # Check eef_pos
                    if 'eef_pos' in obs:
                        eef_pos = obs['eef_pos'][:]
                        validation['stats']['num_observations'] = eef_pos.shape[0]

                        # Check for NaN/Inf
                        if np.any(np.isnan(eef_pos)):
                            validation['errors'].append("Observations contain NaN values")
                            validation['valid'] = False

                        if np.any(np.isinf(eef_pos)):
                            validation['errors'].append("Observations contain Inf values")
                            validation['valid'] = False

                    # Check joint_pos
                    if 'joint_pos' in obs:
                        joint_pos = obs['joint_pos'][:]
                        validation['stats']['joint_dim'] = joint_pos.shape[1]

                        if joint_pos.shape[1] != 7:
                            validation['warnings'].append(f"Expected 7 joints, got {joint_pos.shape[1]}")

                # Check consistency
                num_actions = validation['stats'].get('num_actions', 0)
                num_obs = validation['stats'].get('num_observations', 0)

                if num_actions > 0 and num_obs > 0:
                    if abs(num_actions - (num_obs - 1)) > 1:
                        validation['warnings'].append(f"Action/observation mismatch: {num_actions} actions, {num_obs} obs")

                # Check rewards if present
                if 'rewards' in demo:
                    rewards = demo['rewards']
                    if 'rewards' in rewards:
                        reward_data = rewards['rewards'][:]
                        validation['stats']['num_rewards'] = reward_data.shape[0]

        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(f"File read error: {str(e)}")

        return validation

    def inspect_file(self, hdf5_path):
        """Inspect a single robot data file"""
        hdf5_path = Path(hdf5_path)

        print(f"\n{'='*70}")
        print(f"📁 {hdf5_path.name}")
        print(f"{'='*70}")
        print(f"Size: {hdf5_path.stat().st_size / 1024:.1f} KB")

        # Validate
        validation = self.validate_robot_data(hdf5_path)

        # Show results
        if validation['valid']:
            print("✅ VALID robot training data")
        else:
            print("❌ INVALID")

        if validation['errors']:
            print("\n❌ Errors:")
            for error in validation['errors']:
                print(f"   • {error}")

        if validation['warnings']:
            print("\n⚠️  Warnings:")
            for warning in validation['warnings']:
                print(f"   • {warning}")

        if validation['stats']:
            print("\n📊 Stats:")
            for key, value in validation['stats'].items():
                print(f"   • {key}: {value}")

        # Check JSON metadata
        json_path = self.json_dir / f"{hdf5_path.stem}_reconciled.json"
        if json_path.exists():
            with open(json_path, 'r') as f:
                metadata = json.load(f)
                print(f"\n🏷️  Metadata:")
                print(f"   • Action: {metadata.get('action', 'N/A')}")
                print(f"   • Confidence: {metadata.get('confidence', 'N/A')}")
                print(f"   • Method: {metadata.get('method', 'N/A')}")

        # Recommendation
        if validation['valid'] and len(validation['warnings']) == 0:
            recommendation = "APPROVE"
            print(f"\n✅ RECOMMENDATION: APPROVE")
        elif validation['valid'] and len(validation['warnings']) <= 2:
            recommendation = "APPROVE_WITH_WARNINGS"
            print(f"\n⚠️  RECOMMENDATION: APPROVE (with warnings)")
        else:
            recommendation = "REJECT"
            print(f"\n❌ RECOMMENDATION: REJECT")

        return {
            'file': str(hdf5_path),
            'validation': validation,
            'recommendation': recommendation,
            'inspected_at': datetime.now().isoformat()
        }

    def batch_inspect(self, auto_approve=False, auto_reject=False):
        """Batch inspect all files"""
        hdf5_files = list(self.hdf5_dir.glob('*.hdf5'))

        # Also check rejected dir (move back to hdf5 for re-inspection)
        rejected_files = list(self.rejected_dir.glob('*.hdf5'))
        if rejected_files:
            print(f"Found {len(rejected_files)} previously rejected files, re-inspecting...")
            for f in rejected_files:
                dest = self.hdf5_dir / f.name
                f.rename(dest)
            hdf5_files = list(self.hdf5_dir.glob('*.hdf5'))

        inspected_files = set(self.log['inspected'])
        uninspected = [f for f in hdf5_files if f.name not in inspected_files]

        if not uninspected:
            uninspected = hdf5_files  # Re-inspect all

        print("="*70)
        print(f"🔍 ROBOT DATA INSPECTION: {len(uninspected)} files")
        print("="*70)

        approved_count = 0
        rejected_count = 0

        for idx, hdf5_file in enumerate(uninspected):
            print(f"\n[{idx+1}/{len(uninspected)}]")

            result = self.inspect_file(hdf5_file)

            # Auto-decision
            if auto_approve and result['recommendation'] in ['APPROVE', 'APPROVE_WITH_WARNINGS']:
                decision = 'approve'
                print("🤖 AUTO-APPROVED")
            elif auto_reject and result['recommendation'] == 'REJECT':
                decision = 'reject'
                print("🤖 AUTO-REJECTED")
            else:
                decision = input("\nDecision [a]pprove / [r]eject / [s]kip: ").lower()

            # Process
            if decision in ['a', 'approve']:
                self.approve_file(hdf5_file)
                approved_count += 1
            elif decision in ['r', 'reject']:
                self.reject_file(hdf5_file)
                rejected_count += 1

            self.log['inspected'].append(hdf5_file.name)
            self.save_log()

        print("\n" + "="*70)
        print("✅ INSPECTION COMPLETE")
        print("="*70)
        print(f"Approved: {approved_count}")
        print(f"Rejected: {rejected_count}")
        print(f"\nApproved files at: {self.approved_dir}")

    def approve_file(self, hdf5_path):
        """Move to approved"""
        hdf5_path = Path(hdf5_path)
        dest = self.approved_dir / hdf5_path.name
        hdf5_path.rename(dest)

        json_path = self.json_dir / f"{hdf5_path.stem}_reconciled.json"
        if json_path.exists():
            json_dest = self.approved_dir / json_path.name
            json_path.rename(json_dest)

        self.log['approved'].append(hdf5_path.name)
        self.log['stats']['total_approved'] += 1

    def reject_file(self, hdf5_path):
        """Move to rejected"""
        hdf5_path = Path(hdf5_path)
        dest = self.rejected_dir / hdf5_path.name
        hdf5_path.rename(dest)

        json_path = self.json_dir / f"{hdf5_path.stem}_reconciled.json"
        if json_path.exists():
            json_dest = self.rejected_dir / json_path.name
            json_path.rename(json_dest)

        self.log['rejected'].append(hdf5_path.name)
        self.log['stats']['total_rejected'] += 1


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--batch', action='store_true')
    parser.add_argument('--auto-approve', action='store_true')
    parser.add_argument('--auto-reject', action='store_true')
    parser.add_argument('--file', help='Inspect single file')

    args = parser.parse_args()

    inspector = RobotDataInspector()

    if args.file:
        inspector.inspect_file(args.file)
    elif args.batch:
        inspector.batch_inspect(auto_approve=args.auto_approve, auto_reject=args.auto_reject)
    else:
        print("Use --batch or --file")


if __name__ == '__main__':
    main()
